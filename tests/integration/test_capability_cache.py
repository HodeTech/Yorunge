import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from yorunge import api
from yorunge.adapters.capability_cache import StateCache, decode_record
from yorunge.adapters.state import open_store
from yorunge.adapters.state_schema import MIGRATIONS
from yorunge.application.capabilities import LocalPolicyProducer
from yorunge.domain.capabilities import (
    AuthorizationScope,
    CapabilityKey,
    CapabilityScopeV2,
    Evidence,
    ExecutionBinding,
    timestamp,
)
from yorunge.domain.errors import YorungeError


class Clock:
    def __init__(self):
        self.value = datetime(2026, 10, 27, tzinfo=UTC)
        self.elapsed = 0

    def now(self):
        return self.value

    def monotonic(self):
        return self.elapsed


def key_for(stamp, name="fixture.policy", *, identity=None, authorization=None):
    return CapabilityKey(
        capability_id=name,
        task="llm.train",
        scope=CapabilityScopeV2(
            schema_version=2,
            store_id=stamp.store_id,
            identity_epoch=stamp.identity_epoch,
            clock_generation=stamp.generation,
            service_id="evren-platform" if identity else "local",
            service_origin="https://api.ssyz.org.tr" if identity else None,
            api_base_path="/api/v1" if identity else None,
            account_id="account" if identity else None,
            project_id=None,
            credential_id=identity.credential_id if identity else None,
            credential_revision=identity.credential_revision if identity else None,
            authorization_scope=authorization,
            model=None,
            tool=None,
            execution=ExecutionBinding(
                backend="local", runtime_id=None, runtime_revision=None, environment_digest=None
            ),
        ),
    )


def test_real_api_cli_refresh_and_persistent_reopen_keep_offline_default(tmp_path, cli):
    root = tmp_path / "state"
    missing = api.query_capabilities(task="llm.train", state_dir=root)
    assert all(r.freshness == "miss" for r in missing.data.records)
    fresh = api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    assert fresh.data.records[0].effective_support == "supported"
    assert fresh.data.records[1].effective_support == "unsupported"
    result = cli(
        "capabilities",
        "--task",
        "llm.train",
        "--cached",
        "--state-dir",
        str(root),
        "--output",
        "json",
        state=True,
    )
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)["data"]["records"]
    assert [r["effective_support"] for r in actual] == ["supported", "unsupported"]
    offline = cli("capabilities", "--task", "llm.train", "--output", "json")
    assert offline.returncode == 0
    assert json.loads(offline.stdout)["data"]["records"][0]["schema_version"] == 1
    invalid = cli(
        "capabilities", "--task", "llm.train", "--cached", "--refresh", "--output", "json"
    )
    assert invalid.returncode == 2
    assert json.loads(invalid.stderr)["code"] == "invalid_request"


def test_exact_expiry_and_durable_clock_regression_do_not_revive_after_restart(tmp_path):
    root, clock = tmp_path / "state", Clock()
    with open_store(root) as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)
        cache.refresh(key, stamp, LocalPolicyProducer("supported", "fixture_policy"))
        clock.value += timedelta(seconds=180)
        assert cache.query(key, stamp).effective_support == "supported"
        clock.value -= timedelta(seconds=60)
        producer = LocalPolicyProducer("supported", "fixture_policy")
        with pytest.raises(YorungeError):
            cache.refresh(key, stamp, producer)
    clock.value += timedelta(seconds=120)  # clock catches up, old TTL still has a minute
    with open_store(root) as store:
        cache = StateCache(store, clock)
        current = cache.stamp()
        assert current.generation == 2
        assert cache.query(key_for(current), current).freshness == "miss"
        producer = LocalPolicyProducer("supported", "fixture_policy")
        with pytest.raises(YorungeError) as failure:
            cache.refresh(key, current, producer)
        assert failure.value.code == "state_changed"
        new_key = key_for(current)
        cache.refresh(new_key, current, LocalPolicyProducer("supported", "fixture_policy"))
        clock.value += timedelta(seconds=300)
        assert cache.query(new_key, current).freshness == "stale"


def test_producer_expiry_and_total_deadline_cannot_publish_fresh_result(tmp_path):
    clock = Clock()
    with open_store(tmp_path / "state") as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)

        class Expired:
            def observe(self, key, now):
                proof = LocalPolicyProducer("supported", "fixture_policy").observe(key, now)
                clock.value += timedelta(seconds=300)
                return proof

        producer = Expired()
        with pytest.raises(YorungeError) as failure:
            cache.refresh(key, stamp, producer)
        assert failure.value.code == "capability_expired"
        assert cache.query(key, stamp).freshness == "miss"
        clock.elapsed = 5
        assert cache.query(key, stamp).effective_support == "unknown"


def test_rotation_between_snapshot_and_commit_rejects_stale_writer(config, tmp_path, monkeypatch):
    root = tmp_path / "state"
    identity = api.observe_credential("evren-platform", config=config, state_dir=root).data.identity
    with open_store(root) as store:
        cache = StateCache(store, bindings=(identity,))
        stamp = cache.stamp()
        key = key_for(stamp, identity=identity)

        class Rotate:
            def observe(self, key, now):
                monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "changed-synthetic-value")
                api.observe_credential("evren-platform", config=config, state_dir=root)
                return LocalPolicyProducer("unknown", "not_verified").observe(key, now)

        producer = Rotate()
        with pytest.raises(YorungeError) as failure:
            cache.refresh(key, stamp, producer)
        assert failure.value.code == "state_changed"
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (0,)


def test_unknown_authorization_only_shows_bounded_historical_candidates(config, tmp_path):
    root, clock = tmp_path / "state", Clock()
    identity = api.observe_credential("evren-platform", config=config, state_dir=root).data.identity
    with open_store(root) as store:
        cache = StateCache(store, clock, bindings=(identity,))
        stamp = cache.stamp()
        scope = AuthorizationScope(permissions=("read",), resources=())
        known = key_for(stamp, identity=identity, authorization=scope)

        class VerifiedFixture:
            def observe(self, key, now):
                return (
                    Evidence(
                        kind="live_account",
                        producer_id="fixture-account",
                        producer_version="1",
                        provenance="synthetic-account-fixture",
                        support="supported",
                        reason_code="fixture_verified",
                        checked_at=timestamp(now),
                        expires_at=timestamp(now + timedelta(seconds=300)),
                    ),
                )

        cache.refresh(known, stamp, VerifiedFixture())
    with open_store(root) as store:
        cache = StateCache(store, clock, bindings=(identity,))
        stamp = cache.stamp()
        unknown = key_for(stamp, identity=identity)
        result = cache.query(unknown, stamp)
        assert result.freshness == "historical_only"
        assert result.effective_support == "unknown"
        assert result.historical_candidates[0].support == "supported"
        assert cache.query(known, stamp).effective_support == "supported"
        changed = key_for(
            stamp,
            identity=identity,
            authorization=AuthorizationScope(permissions=("write",), resources=()),
        )
        assert cache.query(changed, stamp).freshness == "miss"


def test_conflict_is_retained_after_aggregate_expiry_and_quota_pressure(tmp_path):
    clock = Clock()
    with open_store(tmp_path / "state", timeout=30) as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)
        cache.refresh(key, stamp, LocalPolicyProducer("unsupported", "first"))

        class OtherProducer:
            def observe(self, key, now):
                return tuple(
                    e.model_copy(update={"producer_id": "other"})
                    for e in LocalPolicyProducer("supported", "second").observe(key, now)
                )

        cache.refresh(key, stamp, OtherProducer())
        assert cache.query(key, stamp).effective_support == "unknown"
        clock.value += timedelta(seconds=31)
        for index in range(130):
            cache.refresh(
                key_for(stamp, "f" + str(index)), stamp, LocalPolicyProducer("supported", "other")
            )
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (
            128,
        )
        cache.refresh(key, stamp, OtherProducer())
        record = cache.query(key, stamp).record
        assert record.support == "unknown"
        assert {e.producer_id for e in record.evidence} == {"yorunge-local-policy", "other"}
        assert store.verify().store_schema_version == len(MIGRATIONS)


def test_cache_reset_and_restore_never_reactivate_old_epoch(tmp_path):
    root = tmp_path / "state"
    api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    from yorunge.adapters import maintenance, state_schema
    from yorunge.adapters.local_files import Deadline
    from yorunge.adapters.state import DB_NAME, backup

    with maintenance.target_lock(root, Deadline(), create=False):
        saved = backup(root, root / DB_NAME, Deadline(), state_schema.MIGRATIONS)
    preview = api.preview_identity_reset(state_dir=root).data
    api.reset_identity(preview.digest, state_dir=root)
    assert (
        api.query_capabilities(task="llm.train", state_dir=root).data.records[0].freshness == "miss"
    )
    preview = api.preview_state_restore(saved, state_dir=root).data
    api.restore_state(saved, preview.digest, state_dir=root)
    assert (
        api.query_capabilities(task="llm.train", state_dir=root).data.records[0].freshness == "miss"
    )


@pytest.mark.parametrize("bad", ["{}", '{"schema_version":2,"schema_version":2}', "NaN"])
def test_corrupt_payload_is_controlled_not_empty_success(tmp_path, bad):
    root = tmp_path / "state"
    api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    with sqlite3.connect(root / "state.sqlite3") as connection:
        connection.execute("UPDATE capability_cache SET payload=?", (bad,))
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_invalid"
    with pytest.raises(YorungeError):
        decode_record(bad)


def test_two_processes_merge_same_producer_conflicts_without_last_writer_win(tmp_path):
    import subprocess
    import sys
    import time

    root = tmp_path / "state"
    with open_store(root) as store:
        key = key_for(StateCache(store).stamp())
    code = """import sys,time
from pathlib import Path
from yorunge.adapters.state import open_store
from yorunge.adapters.state_schema import MIGRATIONS
from yorunge.adapters.capability_cache import StateCache
from yorunge.application.capabilities import LocalPolicyProducer
from yorunge.domain.capabilities import CapabilityKey
root,barrier=Path(sys.argv[1]),Path(sys.argv[2])
key=CapabilityKey.model_validate_json(sys.argv[3])
class Producer:
    def observe(self,key,now):
        (barrier/('ready-'+sys.argv[4])).write_text('ready')
        end=time.monotonic()+5
        while not (barrier/'go').exists():
            if time.monotonic()>end: raise AssertionError('barrier timeout')
            time.sleep(.001)
        return LocalPolicyProducer(sys.argv[4],'fixture_policy').observe(key,now)
with open_store(root) as store:
    cache=StateCache(store)
    stamp=cache.stamp()
    cache.refresh(key,stamp,Producer())
"""
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(root), str(tmp_path), key.model_dump_json(), support],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for support in ("supported", "unsupported")
    ]
    try:
        end = time.monotonic() + 8
        while not all(
            (tmp_path / ("ready-" + support)).exists() for support in ("supported", "unsupported")
        ):
            assert time.monotonic() < end
            time.sleep(0.005)
        (tmp_path / "go").write_text("go")
        for process in processes:
            _, error = process.communicate(timeout=10)
            assert process.returncode == 0, error
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
    with open_store(root) as store:
        cache = StateCache(store)
        result = cache.query(key, cache.stamp())
        assert result.effective_support == "unknown"
        assert len(result.record.evidence) == 2
        assert {e.support for e in result.record.evidence} == {"supported", "unsupported"}


def test_two_credentials_rotation_target_and_project_cache_isolation(
    config, tmp_path, monkeypatch, caplog
):
    root = tmp_path / "state"
    monkeypatch.setenv("SECOND_ENV", "different-synthetic-token")
    config.write_text("""schema_version=1
active_profile="one"
[profiles.one]
account_id="account"
project_id="project"
platform_key_env="EVREN_PLATFORM_API_KEY"
[profiles.two]
account_id="account"
project_id="project"
platform_key_env="SECOND_ENV"
""")
    one = api.query_capabilities(task="dataset.upload", config=config, state_dir=root, refresh=True)
    two = api.query_capabilities(
        task="dataset.upload", config=config, profile="two", state_dir=root, refresh=True
    )
    a = next(r for r in one.data.records if r.key.scope.service_id == "evren-platform")
    b = next(r for r in two.data.records if r.key.scope.service_id == "evren-platform")
    assert a.key.scope.credential_id != b.key.scope.credential_id
    assert a.key.digest() != b.key.digest()
    changed = api.query_capabilities(
        task="dataset.upload", config=config, project="other", state_dir=root
    )
    assert all(r.freshness == "miss" for r in changed.data.records)
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "rotated-synthetic-token")
    rotated = api.query_capabilities(
        task="dataset.upload", config=config, state_dir=root, refresh=True
    )
    r = next(r for r in rotated.data.records if r.key.scope.service_id == "evren-platform")
    assert r.key.scope.credential_id == a.key.scope.credential_id
    assert r.key.scope.credential_revision == 2
    with sqlite3.connect(root / "state.sqlite3") as connection:
        payload = "".join(
            row[0] for row in connection.execute("SELECT payload FROM capability_cache")
        )
    output = payload + rotated.model_dump_json() + caplog.text
    for secret in (
        "SECOND_ENV",
        "EVREN_PLATFORM_API_KEY",
        "rotated-synthetic-token",
        "different-synthetic-token",
    ):
        assert secret not in output


def test_real_v1_to_cache_migration_preserves_identity_and_verified_backup(
    config, tmp_path, monkeypatch
):
    from yorunge.adapters import state_schema
    from yorunge.adapters.local_files import Deadline
    from yorunge.adapters.state import read_backup

    root = tmp_path / "state"
    with monkeypatch.context() as patch:
        patch.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:1])
        old = api.observe_credential("evren-platform", config=config, state_dir=root).data.identity
    current = api.observe_credential("evren-platform", config=config, state_dir=root).data.identity
    assert current == old
    saved_versions = {
        read_backup(saved, Deadline(), state_schema.MIGRATIONS).source_version
        for saved in (root / "backups").iterdir()
    }
    assert saved_versions == set(range(1, len(state_schema.MIGRATIONS)))
    with open_store(root) as store:
        assert store.verify().store_schema_version == len(MIGRATIONS)
        assert store.connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(step.to_version,) for step in MIGRATIONS]


@pytest.mark.parametrize("cut", ["intent", "stage", "live"])
@pytest.mark.parametrize("old_version", [1, 2, 3])
def test_old_runtime_restore_intent_upgrades_even_when_completed_source_is_gone(
    config, tmp_path, monkeypatch, cut, old_version, execution_fixture
):
    import shutil
    import subprocess
    import sys

    from yorunge.adapters import maintenance, state_schema
    from yorunge.adapters.local_files import Deadline
    from yorunge.adapters.state import DB_NAME, backup

    source, target = tmp_path / "source", tmp_path / "target"
    historical_plan = None
    template = (
        api.prepare_execution_plan(task="llm.train", state_dir=tmp_path / "template").data.plan
        if old_version == 3
        else None
    )
    with monkeypatch.context() as patch:
        patch.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:old_version])
        api.observe_credential("evren-platform", config=config, state_dir=source)
        if template is not None:
            import hashlib

            from yorunge.domain.capabilities import canonical
            from yorunge.domain.execution import ExecutionPlan

            with open_store(source) as store:
                value = store.verify()
                body = template.model_dump(mode="json", exclude={"digest"})
                body["store_id"], body["identity_epoch"] = value.store_id, value.identity_epoch
                for capability in body["assessment"]["capabilities"]:
                    capability["key"]["scope"]["store_id"] = value.store_id
                    capability["key"]["scope"]["identity_epoch"] = value.identity_epoch
                body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
                historical_plan = ExecutionPlan.model_validate_json(canonical(body))
                store.connection.execute(
                    "INSERT INTO execution_plans VALUES(?,?,?,?,?,?,?)",
                    (
                        historical_plan.plan_id,
                        historical_plan.digest,
                        historical_plan.selection.task,
                        historical_plan.prepared_at,
                        historical_plan.expires_at,
                        historical_plan.status,
                        canonical(body).decode("ascii"),
                    ),
                )
        with maintenance.target_lock(source, Deadline(), create=False):
            saved = backup(source, source / DB_NAME, Deadline(), state_schema.MIGRATIONS)
    code = """import os,sys
from pathlib import Path
from yorunge import api
from yorunge.adapters import maintenance as m,state_schema as s
s.MIGRATIONS=s.MIGRATIONS[:int(sys.argv[4])]
root=Path(sys.argv[2]);mode=sys.argv[3]
write,reset,sync=m.write_new,m.reset_connection,m.sync_private
def write_cut(path,content):
    write(path,content)
    if mode=='intent' and path.name=='restore-intent.json': os._exit(73)
def reset_cut(*args,**kwargs):
    result=reset(*args,**kwargs)
    if mode=='stage': os._exit(73)
    return result
def sync_cut(path):
    sync(path)
    if mode=='live' and path==root/'state.sqlite3': os._exit(73)
m.write_new,m.reset_connection,m.sync_private=write_cut,reset_cut,sync_cut
preview=api.preview_state_restore(Path(sys.argv[1]),state_dir=root)
api.restore_state(Path(sys.argv[1]),preview.data.digest,state_dir=root)
raise AssertionError('cut not reached')
"""
    child = subprocess.run(
        [sys.executable, "-c", code, str(saved), str(target), cut, str(old_version)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert child.returncode == 73, child.stderr
    announced = json.loads((target / "restore-intent.json").read_text())["identity_epoch"]
    if cut != "intent":
        shutil.rmtree(source)
    preview = api.preview_state_recovery(state_dir=target).data
    result = api.recover_state(preview.digest, state_dir=target).data
    assert result.identity_epoch == announced
    assert result.store_schema_version == len(MIGRATIONS)
    assert not (target / "restore-intent.json").exists()
    assert (
        api.query_capabilities(task="llm.train", state_dir=target).data.records[0].freshness
        == "miss"
    )

    if historical_plan is not None:
        assert (
            api.show_execution_plan(historical_plan.plan_id, state_dir=target).data.plan
            == historical_plan
        )
        assert not api.validate_execution_plan(historical_plan.plan_id, state_dir=target).data.valid


def test_current_producer_version_is_required_for_effective_public_result(tmp_path):
    root = tmp_path / "state"
    api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    with sqlite3.connect(root / "state.sqlite3") as connection:
        rows = connection.execute("SELECT cache_key,payload FROM capability_cache").fetchall()
        for digest, payload in rows:
            value = json.loads(payload)
            for proof in value["evidence"]:
                proof["producer_version"] = "2"
            connection.execute(
                "UPDATE capability_cache SET payload=? WHERE cache_key=?",
                (json.dumps(value), digest),
            )
    current = api.query_capabilities(task="llm.train", state_dir=root)
    assert all(r.effective_support == "unknown" for r in current.data.records)
    assert all(r.reason_code == "evidence_source_changed" for r in current.data.records)


@pytest.mark.parametrize("advance", [300, -1])
def test_final_sql_gate_rolls_back_record_but_preserves_clock_fence(tmp_path, advance):
    clock = Clock()
    root = tmp_path / "state"
    with open_store(root) as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)

        def move_time(statement):
            if statement.startswith("INSERT OR REPLACE INTO capability_cache"):
                clock.value += timedelta(seconds=advance)

        store.connection.set_trace_callback(move_time)
        producer = LocalPolicyProducer("supported", "fixture_policy")
        with pytest.raises(YorungeError):
            cache.refresh(key, stamp, producer)
        store.connection.set_trace_callback(None)
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (0,)
        generation = store.connection.execute(
            "SELECT clock_generation FROM cache_clock"
        ).fetchone()[0]
        assert generation == (2 if advance < 0 else 1)
    clock.value += timedelta(seconds=2)
    with open_store(root) as store:
        cache = StateCache(store, clock)
        assert cache.stamp().generation == generation


def test_config_resolution_consumes_the_same_total_budget_before_store_io(tmp_path, monkeypatch):
    import time

    original = api._resolve
    elapsed = [0.0]

    def slow_context(**kwargs):
        result = original(**kwargs)
        elapsed[0] = 5.0
        return result

    monkeypatch.setattr(api, "_resolve", slow_context)
    monkeypatch.setattr(time, "monotonic", lambda: elapsed[0])
    root = tmp_path / "state"
    with pytest.raises(YorungeError) as failure:
        api.query_capabilities(task="llm.train", state_dir=root)
    assert failure.value.code == "state_busy"
    assert not root.exists()


def test_last_transaction_time_sample_rejects_expired_write(tmp_path):
    clock = Clock()
    with open_store(tmp_path / "state") as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)
        inserted = False
        samples_after_insert = 0
        original_now = clock.now

        def mark_insert(statement):
            nonlocal inserted
            if statement.startswith("INSERT OR REPLACE INTO capability_cache"):
                inserted = True

        def last_sample():
            nonlocal samples_after_insert
            if inserted:
                samples_after_insert += 1
                if samples_after_insert == 2:
                    clock.value += timedelta(seconds=300)
            return original_now()

        store.connection.set_trace_callback(mark_insert)
        clock.now = last_sample
        producer = LocalPolicyProducer("supported", "fixture_policy")
        with pytest.raises(YorungeError) as failure:
            cache.refresh(key, stamp, producer)
        assert failure.value.code == "capability_expired"
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (0,)


@pytest.mark.parametrize("advance,elapsed", [(300, 0), (-1, 0), (0, 5)])
def test_query_observes_and_fences_time_after_its_clock_commit(tmp_path, advance, elapsed):
    clock = Clock()
    with open_store(tmp_path / "state") as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)
        cache.refresh(key, stamp, LocalPolicyProducer("supported", "fixture_policy"))
        commits = 0

        def move_after_clock_commit(statement):
            nonlocal commits
            if statement == "COMMIT":
                commits += 1
                if commits == 1:
                    clock.value += timedelta(seconds=advance)
                    clock.elapsed += elapsed

        store.connection.set_trace_callback(move_after_clock_commit)
        result = cache.query(key, stamp)
        store.connection.set_trace_callback(None)
        assert result.effective_support == "unknown"
        assert result.freshness == ("clock_anomaly" if advance < 0 else "stale")
        assert result.checked_at == timestamp(clock.value)
        generation, high = store.connection.execute(
            "SELECT clock_generation,high_watermark FROM cache_clock"
        ).fetchone()
        assert generation == (2 if advance < 0 else 1)
        assert high >= timestamp(clock.value)


@pytest.mark.parametrize("regression", [False, True])
def test_query_rechecks_a_concurrent_durable_clock_before_presentation(
    tmp_path, monkeypatch, regression
):
    clock, root = Clock(), tmp_path / "state"
    with open_store(root) as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)
        cache.refresh(key, stamp, LocalPolicyProducer("supported", "fixture_policy"))
        finish = cache._finish

        def concurrent_clock(*args, **kwargs):
            other_clock = Clock()
            other_clock.value += timedelta(seconds=100)
            with open_store(root) as other:
                observer = StateCache(other, other_clock)
                observer.stamp()
                if regression:
                    other_clock.value -= timedelta(seconds=1)
                    observer.stamp()
            return finish(*args, **kwargs)

        monkeypatch.setattr(cache, "_finish", concurrent_clock)
        result = cache.query(key, stamp)
        assert result.effective_support == "unknown"
        assert result.freshness == "clock_anomaly"
    clock.value += timedelta(seconds=101)
    with open_store(root) as store:
        cache = StateCache(store, clock)
        current = cache.stamp()
        assert current.generation == 2
        assert cache.query(key_for(current), current).freshness == "miss"


@pytest.mark.parametrize("corruption", ["missing", "revision"])
def test_query_does_not_reuse_a_checkpoint_after_clock_corruption(
    tmp_path, monkeypatch, corruption
):
    clock, root = Clock(), tmp_path / "state"
    with open_store(root) as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        key = key_for(stamp)
        cache.refresh(key, stamp, LocalPolicyProducer("supported", "fixture_policy"))
        finish = cache._finish

        def corrupt_clock(*args, **kwargs):
            with sqlite3.connect(root / "state.sqlite3") as other:
                if corruption == "missing":
                    other.execute("DELETE FROM cache_clock")
                else:
                    other.execute("PRAGMA ignore_check_constraints=ON")
                    other.execute("UPDATE cache_clock SET mutation_revision=-1")
            return finish(*args, **kwargs)

        monkeypatch.setattr(cache, "_finish", corrupt_clock)
        with pytest.raises(YorungeError) as failure:
            cache.query(key, stamp)
        assert failure.value.code == "state_invalid"


@pytest.mark.parametrize("advance", [300, -1])
def test_public_view_rechecks_all_records_at_one_final_time(tmp_path, monkeypatch, advance):
    clock = Clock()
    monkeypatch.setattr("yorunge.adapters.capability_cache.SystemClock", lambda: clock)
    root = tmp_path / "state"
    api.query_capabilities(task="llm.train", state_dir=root, refresh=True)
    original_query = StateCache._read
    calls = 0

    def advance_between_records(self, key):
        nonlocal calls
        result = original_query(self, key)
        calls += 1
        if calls == 1:
            clock.value += timedelta(seconds=advance)
        return result

    monkeypatch.setattr(StateCache, "_read", advance_between_records)
    records = api.query_capabilities(task="llm.train", state_dir=root).data.records
    assert len(records) == 2
    assert all(r.effective_support == "unknown" for r in records)
    assert all(r.freshness == ("stale" if advance > 0 else "clock_anomaly") for r in records)
    assert all(r.checked_at == timestamp(clock.value) for r in records)


def test_cached_cli_explains_the_project_selection_blocker(tmp_path, cli):
    result = cli(
        "capabilities",
        "--task",
        "dataset.upload",
        "--refresh",
        "--state-dir",
        str(tmp_path / "state"),
        state=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Uzak görev öncesinde açık proje seçin." in result.stdout


@pytest.mark.parametrize("advance", [-50, 300])
def test_producer_clock_observation_survives_catchup_rejection_and_restart(tmp_path, advance):
    root, clock = tmp_path / "state", Clock()
    with open_store(root) as store:
        cache = StateCache(store, clock)
        initial = cache.stamp()
        key = key_for(initial)
        cache.refresh(key, initial, LocalPolicyProducer("supported", "fixture_policy"))
        clock.value += timedelta(seconds=100)
        stamp = cache.stamp()
        caught_up = clock.value
        commits = 0

        def jump_after_snapshot(statement):
            nonlocal commits
            if statement == "COMMIT":
                commits += 1
                if commits == 1:
                    clock.value += timedelta(seconds=advance)

        class CatchUp:
            def observe(self, key, now):
                clock.value = caught_up
                raise YorungeError("capability_expired")

        store.connection.set_trace_callback(jump_after_snapshot)
        producer = CatchUp()
        with pytest.raises(YorungeError):
            cache.refresh(key, stamp, producer)
        store.connection.set_trace_callback(None)
        clock.value = caught_up
        assert cache.query(key, stamp).effective_support == "unknown"
    clock.value += timedelta(seconds=301)
    with open_store(root) as store:
        cache = StateCache(store, clock)
        current = cache.stamp()
        assert current.generation == 2
        assert cache.query(key_for(current), current).freshness == "miss"


def test_intermediate_clock_sample_cannot_be_overwritten_before_tick(tmp_path):
    clock = Clock()
    with open_store(tmp_path / "state") as store:
        cache = StateCache(store, clock)
        stamp = cache.stamp()
        clock.value -= timedelta(seconds=1)
        cache.now()
        clock.value += timedelta(seconds=1)
        assert cache.stamp().generation == stamp.generation + 1
