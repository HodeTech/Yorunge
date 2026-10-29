import errno
import json
import sqlite3
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest

from yorunge import api
from yorunge.adapters.state import open_store
from yorunge.domain.errors import ApprovalNotEffective, YorungeError


@pytest.mark.parametrize("owner", ["plan", "approval"])
def test_cached_query_fences_other_plan_and_approval_expiry(
    tmp_path, execution_fixture, execution_clock, monkeypatch, owner
):
    from yorunge.adapters.capability_cache import StateCache
    from yorunge.domain.capabilities import instant, timestamp

    state, base = tmp_path / "state", execution_clock.value
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    assert plan.status == "prepared"
    expires = instant(plan.expires_at)
    if owner == "approval":

        def shorten(assessment):
            end = timestamp(execution_clock.value + timedelta(seconds=60))
            return assessment.model_copy(
                update={
                    "capabilities": tuple(
                        record.model_copy(
                            update={
                                "expires_at": end,
                                "evidence": tuple(
                                    proof.model_copy(update={"expires_at": end})
                                    for proof in record.evidence
                                ),
                            }
                        )
                        for record in assessment.capabilities
                    ),
                }
            )

        execution_fixture.change = shorten
        approval = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
        assert approval.effective
        expires = instant(approval.record.expires_at)
        assert expires < instant(plan.expires_at)
        execution_fixture.change = None
    execution_clock.value = base + timedelta(seconds=10)
    api.query_capabilities(task="llm.train", state_dir=state, refresh=True)
    finish = StateCache._finish

    def advance_after_query_commit(self, *args, **kwargs):
        execution_clock.value = expires + timedelta(seconds=1)
        return finish(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(StateCache, "_finish", advance_after_query_commit)
        records = api.query_capabilities(task="llm.train", state_dir=state).data.records
        assert all(record.freshness == "fresh" for record in records)
    with open_store(state) as store:
        assert store.connection.execute("SELECT high_watermark FROM cache_clock").fetchone()[
            0
        ] >= timestamp(execution_clock.value)
    execution_clock.value = expires - timedelta(seconds=1)
    validity = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert not validity.valid
    if owner == "approval":
        assert not validity.approval.effective
    with open_store(state) as store:
        assert (
            store.connection.execute("SELECT clock_generation FROM cache_clock").fetchone()[0] == 2
        )


def test_approval_revalidates_is_idempotent_and_revoke_requires_new_validation(
    tmp_path,
    execution_fixture,
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    first = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert first.effective
    assert first.record.plan_digest == plan.digest
    calls = execution_fixture.calls
    second = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert second.record == first.record
    assert execution_fixture.calls == calls + 1
    validity = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert validity.valid
    assert validity.approval.effective
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data
    assert shown.approval.record == first.record
    assert shown.approval.effective is None
    revoked = api.revoke_execution_approval(plan.plan_id, state_dir=state).data
    assert revoked.record.status == "revoked"
    assert revoked.effective is False
    assert (
        api.revoke_execution_approval(plan.plan_id, state_dir=state).data.record == revoked.record
    )
    validity = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert validity.valid
    assert validity.approval.effective is False
    assert api.list_execution_plans(state_dir=state).data.plans[0].approval_status == "revoked"
    third = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert third.record.approval_id != first.record.approval_id
    assert third.record.expires_at <= plan.expires_at
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.plan == plan


@pytest.mark.parametrize("confirmation", [None, "", "0" * 64, 4, True])
def test_approval_and_forget_require_the_full_digest_before_secret_or_input_reads(
    tmp_path,
    execution_fixture,
    monkeypatch,
    confirmation,
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    monkeypatch.setattr(
        "yorunge.adapters.secrets.EnvSecretReader.read", lambda *a: pytest.fail("secret read")
    )
    monkeypatch.setattr(
        "yorunge.adapters.input_files.DescriptorInputs.bind", lambda *a: pytest.fail("input read")
    )
    for action in (api.approve_execution_plan, api.forget_execution_plan):
        with pytest.raises(YorungeError) as failure:
            action(plan.plan_id, confirmation, state_dir=state)
        assert failure.value.code == "approval_required"
        assert failure.value.exit_code == 4


def test_public_blocked_approval_and_cli_error_codes(tmp_path, cli):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    with pytest.raises(YorungeError) as failure:
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    assert failure.value.code == "plan_not_valid"
    for action in ("approve", "forget"):
        missing = cli(
            "plan",
            "execution",
            action,
            "--plan-id",
            plan.plan_id,
            "--state-dir",
            str(state),
            "--output",
            "json",
            state=True,
        )
        assert missing.returncode == 4, missing.stderr
        assert json.loads(missing.stderr)["code"] == "approval_required"
    blocked = cli(
        "plan",
        "execution",
        "approve",
        "--plan-id",
        plan.plan_id,
        "--confirm",
        plan.digest,
        "--state-dir",
        str(state),
        "--output",
        "json",
        state=True,
    )
    assert blocked.returncode == 2
    assert json.loads(blocked.stderr)["code"] == "plan_not_valid"
    revoked = cli(
        "plan",
        "execution",
        "revoke",
        "--plan-id",
        plan.plan_id,
        "--state-dir",
        str(state),
        "--output",
        "json",
        state=True,
    )
    assert revoked.returncode == 0, revoked.stderr
    forgotten = cli(
        "plan",
        "execution",
        "forget",
        "--plan-id",
        plan.plan_id,
        "--confirm",
        plan.digest,
        "--state-dir",
        str(state),
        "--output",
        "json",
        state=True,
    )
    assert forgotten.returncode == 0, forgotten.stderr
    assert json.loads(forgotten.stdout)["data"]["local_only"] is True


def test_forget_cascades_only_selected_current_approval_and_preserves_other_history(
    tmp_path,
    execution_fixture,
):
    state = tmp_path / "state"
    first = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    second = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(first.plan_id, first.digest, state_dir=state)
    api.approve_execution_plan(second.plan_id, second.digest, state_dir=state)
    api.query_capabilities(task="llm.train", state_dir=state, refresh=True)
    api.revoke_execution_approval(first.plan_id, state_dir=state)
    api.approve_execution_plan(first.plan_id, first.digest, state_dir=state)
    removed = api.forget_execution_plan(first.plan_id, first.digest, state_dir=state).data
    assert removed.approval_removed
    assert removed.local_only
    assert api.validate_execution_plan(second.plan_id, state_dir=state).data.approval.effective
    with open_store(state) as store:
        assert store.connection.execute("SELECT count(*) FROM execution_plans").fetchone() == (1,)
        assert store.connection.execute("SELECT count(*) FROM execution_approvals").fetchone() == (
            1,
        )
        assert store.connection.execute("SELECT count(*) FROM capability_cache").fetchone() == (2,)
        assert store.connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_approval_preview_epoch_reset_and_clock_do_not_reactivate_records(
    tmp_path,
    execution_fixture,
    execution_clock,
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    preview = api.preview_identity_reset(state_dir=state).data
    approval = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert api.preview_identity_reset(state_dir=state).data.current.approval_count == 1
    with pytest.raises(YorungeError):
        api.reset_identity(preview.digest, state_dir=state)
    preview = api.preview_identity_reset(state_dir=state).data
    api.revoke_execution_approval(plan.plan_id, state_dir=state)
    with pytest.raises(YorungeError):
        api.reset_identity(preview.digest, state_dir=state)
    approval = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    execution_clock.value += timedelta(seconds=100)
    assert api.validate_execution_plan(plan.plan_id, state_dir=state).data.approval.effective
    execution_clock.value -= timedelta(seconds=1)
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.approval.effective
    # Revocation remains available while the clock is anomalous.
    assert (
        api.revoke_execution_approval(plan.plan_id, state_dir=state).data.record.status == "revoked"
    )
    execution_clock.value += timedelta(seconds=1)
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.valid
    current = api.preview_identity_reset(state_dir=state).data
    api.reset_identity(current.digest, state_dir=state)
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data
    assert shown.approval.record.approval_id == approval.record.approval_id
    assert not api.validate_execution_plan(plan.plan_id, state_dir=state).data.approval.effective


@pytest.mark.parametrize("idempotent", [False, True])
def test_approval_commit_expiry_discloses_record_without_active_success(
    tmp_path,
    execution_fixture,
    execution_clock,
    monkeypatch,
    idempotent,
):
    from yorunge.adapters.execution_store import PlanRepository
    from yorunge.domain.capabilities import instant

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    if idempotent:
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    original = PlanRepository.approve

    def delayed(self, *args):
        execution_clock.value = instant(plan.expires_at) - timedelta(seconds=0.2)

        def move(statement):
            if statement == "COMMIT":
                execution_clock.value += timedelta(seconds=0.3)

        self.store.connection.set_trace_callback(move)
        return original(self, *args)

    monkeypatch.setattr(PlanRepository, "approve", delayed)
    with pytest.raises(ApprovalNotEffective) as failure:
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    assert failure.value.exit_code == 2
    assert failure.value.envelope()["details"]["recorded"] is True
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data
    assert shown.approval.record.approval_id == failure.value.approval_id
    assert (
        api.validate_execution_plan(plan.plan_id, state_dir=state).data.approval.effective is False
    )


def test_approval_insert_failure_rolls_back_without_success(
    tmp_path, execution_fixture, monkeypatch
):
    from yorunge.adapters import execution_store

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan

    def fail(*args):
        raise sqlite3.OperationalError("fixture failure")

    monkeypatch.setattr(execution_store, "write_approval", fail)
    with pytest.raises(YorungeError):
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.approval.record is None


@pytest.mark.parametrize("phase", ["validating", "approved", "revoked"])
def test_other_process_approval_or_revoke_cannot_escape_selected_forget(
    tmp_path,
    execution_fixture,
    phase,
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    other = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    code = """import sys,time
from pathlib import Path
from yorunge import api
from yorunge.domain.errors import YorungeError
sys.path.insert(0,sys.argv[1])
from conftest import execution_validator_fixture
state,plan_id,digest,barrier,phase=Path(sys.argv[2]),sys.argv[3],sys.argv[4],Path(sys.argv[5]),sys.argv[6]
validator=execution_validator_fixture()
api._execution_validator=lambda:validator
def wait():
    (barrier/'ready').write_text('ready')
    end=time.monotonic()+15
    while not (barrier/'go').exists():
        if time.monotonic()>=end: raise AssertionError('barrier timeout')
        time.sleep(.005)
if phase=='validating': validator.change=lambda assessment:(wait() or assessment)
try:
    result=api.approve_execution_plan(plan_id,digest,state_dir=state)
    if phase=='revoked': api.revoke_execution_approval(plan_id,state_dir=state)
    if phase!='validating': wait()
    print('completed')
except YorungeError as error:
    print(error.code)
"""
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            code,
            str(Path(__file__).parents[1]),
            str(state),
            plan.plan_id,
            plan.digest,
            str(tmp_path),
            phase,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        end = time.monotonic() + 10
        while not (tmp_path / "ready").exists():
            assert child.poll() is None, child.communicate()
            assert time.monotonic() < end
            time.sleep(0.005)
        # Confirmation pins the plan body, not its prior approval/revocation status.
        removed = api.forget_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
        assert removed.approval_removed
        (tmp_path / "go").write_text("go")
        output, error = child.communicate(timeout=15)
        assert child.returncode == 0, error
        assert output.strip() == ("state_changed" if phase == "validating" else "completed")
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
    assert api.show_execution_plan(other.plan_id, state_dir=state).data.plan == other
    with open_store(state) as store:
        assert store.connection.execute("SELECT count(*) FROM execution_approvals").fetchone() == (
            0,
        )
        assert store.connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_restore_retains_historical_plan_approval_and_discards_post_snapshot_history(
    tmp_path,
    execution_fixture,
    schema5_runtime,
):
    from yorunge.adapters.state import DB_NAME, backup

    state = tmp_path / "state"
    first = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    approved = api.approve_execution_plan(first.plan_id, first.digest, state_dir=state).data
    with open_store(state) as store:
        saved = backup(store.root, store.root / DB_NAME, store.deadline, store.migrations)
    second = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(second.plan_id, second.digest, state_dir=state)
    preview = api.preview_state_restore(saved, state_dir=state).data
    assert preview.current.plan_count == 2
    assert preview.source.plan_count == 1
    assert preview.source.approval_count == 1
    api.restore_state(saved, preview.digest, state_dir=state)
    shown = api.show_execution_plan(first.plan_id, state_dir=state).data
    assert shown.plan == first
    assert shown.approval.record == approved.record
    assert not api.validate_execution_plan(first.plan_id, state_dir=state).data.approval.effective
    with pytest.raises(YorungeError) as failure:
        api.show_execution_plan(second.plan_id, state_dir=state)
    assert failure.value.code == "plan_not_found"


@pytest.mark.parametrize(
    "field,value",
    [
        ("plan_digest", "0" * 64),
        ("binding_digest", "0" * 64),
        ("clock_generation", 5),
        ("plan_schema_version", True),
        ("schema_version", 99),
    ],
)
def test_corrupt_approval_cannot_be_laundered_by_epoch_change(
    tmp_path,
    execution_fixture,
    field,
    value,
):
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    with open_store(state) as store:
        raw = json.loads(
            store.connection.execute("SELECT payload FROM execution_approvals").fetchone()[0]
        )
        raw[field] = value
        store.connection.execute("UPDATE execution_approvals SET payload=?", (json.dumps(raw),))
    for action in (
        lambda: api.show_execution_plan(plan.plan_id, state_dir=state),
        lambda: api.preview_identity_reset(state_dir=state),
    ):
        with pytest.raises(YorungeError) as failure:
            action()
        assert failure.value.code == "state_invalid"


def test_custom_approval_context_uses_one_private_secret_snapshot(
    tmp_path,
    execution_fixture,
    monkeypatch,
):
    config = tmp_path / "custom.toml"
    config.write_text(
        'schema_version=1\nactive_profile="default"\n[profiles.default]\n'
        '[profiles.work]\naccount_id="account"\nplatform_key_env="APPROVAL_PRIVATE_REF"\n'
    )
    monkeypatch.setenv("APPROVAL_PRIVATE_REF", "approval-private-synthetic-secret")
    state = tmp_path / "state"
    plan = api.prepare_execution_plan(
        task="dataset.upload", config=config, profile="work", project="project", state_dir=state
    ).data.plan
    from yorunge.adapters.secrets import EnvSecretReader

    original, reads = EnvSecretReader.read, []

    def read(self, reference):
        reads.append(reference.name)
        return original(self, reference)

    monkeypatch.setattr(EnvSecretReader, "read", read)
    approved = api.approve_execution_plan(
        plan.plan_id, plan.digest, config=config, profile="work", project="project", state_dir=state
    ).data
    assert approved.effective
    assert reads == ["APPROVAL_PRIVATE_REF"]
    assert "APPROVAL_PRIVATE_REF" not in approved.model_dump_json()
    assert "approval-private-synthetic-secret" not in repr(approved)
    with pytest.raises(YorungeError) as failure:
        api.approve_execution_plan(plan.plan_id, plan.digest, config=config, state_dir=state)
    assert failure.value.code == "plan_not_valid"


def test_cache_quota_and_expiry_cleanup_preserve_plan_and_approval_history(
    tmp_path,
    execution_fixture,
    execution_clock,
):
    from yorunge.adapters.capability_cache import StateCache
    from yorunge.application.capabilities import LocalPolicyProducer

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    approved = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data.record
    base = (
        api.query_capabilities(task="llm.train", state_dir=state, refresh=True).data.records[0].key
    )
    with open_store(state, timeout=30) as store:
        cache = StateCache(store, execution_clock, budget_seconds=30)
        stamp = cache.stamp()
        for index in range(130):
            cache.refresh(
                base.model_copy(update={"capability_id": f"fixture.{index}"}),
                stamp,
                LocalPolicyProducer("supported", "fixture_policy"),
            )
        execution_clock.value += timedelta(seconds=301)
        cache.refresh(base, stamp, LocalPolicyProducer("supported", "fixture_policy"))
        assert store.connection.execute("SELECT count(*) FROM execution_plans").fetchone() == (1,)
        assert store.connection.execute("SELECT count(*) FROM execution_approvals").fetchone() == (
            1,
        )
        store.verify()
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data
    assert shown.plan == plan
    assert shown.approval.record == approved


def test_idempotent_approval_never_outlives_current_shorter_proof(
    tmp_path,
    execution_fixture,
    execution_clock,
):
    from yorunge.domain.capabilities import timestamp

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    first = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data

    def shorter(assessment):
        end = timestamp(execution_clock.value + timedelta(seconds=10))
        record = assessment.capabilities[0]
        proof = record.evidence[0].model_copy(update={"expires_at": end})
        return assessment.model_copy(
            update={
                "capabilities": (
                    record.model_copy(update={"expires_at": end, "evidence": (proof,)}),
                )
            }
        )

    execution_fixture.change = shorter
    second = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data
    assert second.record == first.record
    assert second.valid_until < first.valid_until
    validation = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert validation.approval.valid_until <= validation.valid_until


def test_terminal_approval_expiry_is_durable_even_when_plan_still_valid(
    tmp_path,
    execution_fixture,
    execution_clock,
    monkeypatch,
):
    from yorunge.adapters.execution_store import PlanRepository
    from yorunge.domain.capabilities import instant, timestamp

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan

    def shorter(assessment):
        record = assessment.capabilities[0]
        end = timestamp(execution_clock.value + timedelta(seconds=10))
        return assessment.model_copy(
            update={
                "capabilities": (
                    record.model_copy(
                        update={
                            "expires_at": end,
                            "evidence": (
                                record.evidence[0].model_copy(update={"expires_at": end}),
                            ),
                        }
                    ),
                )
            }
        )

    execution_fixture.change = shorter
    approved = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data.record
    expiry = instant(approved.expires_at)
    execution_clock.value = expiry - timedelta(seconds=0.2)
    original = PlanRepository.finish
    armed = False

    def delayed(self, expected, *, valid_until=None):
        nonlocal armed
        if valid_until is not None and not armed:
            armed = True

            def move(statement):
                if statement == "COMMIT":
                    execution_clock.value += timedelta(seconds=0.3)

            self.store.connection.set_trace_callback(move)
        return original(self, expected, valid_until=valid_until)

    with monkeypatch.context() as patch:
        patch.setattr(PlanRepository, "finish", delayed)
        result = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert result.valid
    assert result.approval.effective is False
    with open_store(state) as store:
        assert (
            store.connection.execute("SELECT high_watermark FROM cache_clock").fetchone()[0]
            >= approved.expires_at
        )
    execution_clock.value = expiry - timedelta(seconds=0.1)
    result = api.validate_execution_plan(plan.plan_id, state_dir=state).data
    assert result.valid is False
    assert result.approval.effective is False


@pytest.mark.parametrize("idempotent", [False, True])
def test_final_transaction_sample_rejects_even_idempotent_expired_approval(
    tmp_path,
    execution_fixture,
    execution_clock,
    monkeypatch,
    idempotent,
):
    from yorunge.adapters.execution_store import PlanRepository
    from yorunge.domain.capabilities import instant

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    previous = (
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data.record
        if idempotent
        else None
    )
    original, original_now = PlanRepository.approve, execution_clock.now

    def at_final_sample(self, *args):
        samples = 0

        def sample():
            nonlocal samples
            samples += 1
            if samples == 4:
                execution_clock.value = instant(plan.expires_at)
            return original_now()

        monkeypatch.setattr(execution_clock, "now", sample)
        return original(self, *args)

    monkeypatch.setattr(PlanRepository, "approve", at_final_sample)
    with pytest.raises(YorungeError) as failure:
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    assert failure.value.code == "plan_not_valid"
    assert failure.value.envelope()["details"] == {}
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.approval.record == previous
    with open_store(state) as store:
        assert (
            store.connection.execute("SELECT high_watermark FROM cache_clock").fetchone()[0]
            >= plan.expires_at
        )


def test_forget_rolls_back_plan_if_approval_cascade_cannot_complete(
    tmp_path,
    execution_fixture,
    monkeypatch,
):
    from contextlib import contextmanager

    from yorunge.adapters import state as state_adapter

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    approved = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data.record
    original = state_adapter.open_store

    @contextmanager
    def denied_delete(*args, **kwargs):
        with original(*args, **kwargs) as store:
            store.connection.set_authorizer(
                lambda action, table, *rest: (
                    sqlite3.SQLITE_DENY
                    if action == sqlite3.SQLITE_DELETE and table == "execution_approvals"
                    else sqlite3.SQLITE_OK
                )
            )
            yield store

    monkeypatch.setattr(state_adapter, "open_store", denied_delete)
    with pytest.raises(YorungeError):
        api.forget_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data
    assert shown.plan == plan
    assert shown.approval.record == approved


@pytest.mark.parametrize("idempotent", [False, True])
@pytest.mark.parametrize("failure_kind", ["timeout", "io", "read_denied"])
def test_postcommit_failures_disclose_persisted_record_for_new_and_existing_approval(
    tmp_path,
    execution_fixture,
    execution_clock,
    monkeypatch,
    idempotent,
    failure_kind,
):
    from yorunge.adapters.execution_store import PlanRepository

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    previous = (
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data.record
        if idempotent
        else None
    )
    original = PlanRepository.approve

    def fail_after_commit(self, *args):
        if failure_kind == "timeout":

            def delay(statement):
                if statement == "COMMIT":
                    execution_clock.elapsed = 31

            self.store.connection.set_trace_callback(delay)
        result = original(self, *args)
        if failure_kind == "io":

            def io_failure(*args, **kwargs):
                raise OSError(errno.EIO, "fixture terminal clock failure")

            monkeypatch.setattr(self.cache, "_save_stamp", io_failure)
        elif failure_kind == "read_denied":
            self.store.connection.set_authorizer(
                lambda action, *rest: (
                    sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_SELECT else sqlite3.SQLITE_OK
                )
            )
        return result

    monkeypatch.setattr(PlanRepository, "approve", fail_after_commit)
    with pytest.raises(ApprovalNotEffective) as failure:
        api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state)
    details = failure.value.envelope()["details"]
    assert failure.value.exit_code == 2
    assert details["recorded"] is True
    assert (
        details["reason_code"]
        == {
            "timeout": "execution_timeout",
            "io": "state_write_failed",
            "read_denied": "state_invalid",
        }[failure_kind]
    )
    assert "kaydı oluştu" in str(failure.value)
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data
    assert shown.approval.record.approval_id == details["approval_id"]
    if idempotent:
        assert shown.approval.record == previous


@pytest.mark.parametrize("initial_status", ["none", "approved", "revoked"])
@pytest.mark.parametrize("failure_kind", ["timeout", "io", "read_denied"])
def test_revoke_postcommit_failure_discloses_only_a_known_persisted_record(
    tmp_path, execution_fixture, execution_clock, monkeypatch, initial_status, failure_kind
):
    from yorunge.adapters.execution_store import PlanRepository

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    previous = None
    if initial_status != "none":
        previous = api.approve_execution_plan(
            plan.plan_id, plan.digest, state_dir=state
        ).data.record
    if initial_status == "revoked":
        previous = api.revoke_execution_approval(plan.plan_id, state_dir=state).data.record
    original = PlanRepository.finish

    def fail_after_commit(self, expected, **kwargs):
        if failure_kind == "timeout":
            execution_clock.elapsed = 31
        elif failure_kind == "io":

            def io_failure(*args, **kwargs):
                raise OSError(errno.EIO, "fixture terminal clock failure")

            monkeypatch.setattr(self.cache, "_save_stamp", io_failure)
        else:
            self.store.connection.set_authorizer(
                lambda action, *rest: (
                    sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_SELECT else sqlite3.SQLITE_OK
                )
            )
        return original(self, expected, **kwargs)

    monkeypatch.setattr(PlanRepository, "finish", fail_after_commit)
    with pytest.raises(YorungeError) as failure:
        api.revoke_execution_approval(plan.plan_id, state_dir=state)
    expected_reason = {
        "timeout": "execution_timeout",
        "io": "state_write_failed",
        "read_denied": "state_invalid",
    }[failure_kind]
    actual = failure.value
    shown = api.show_execution_plan(plan.plan_id, state_dir=state).data.approval.record
    if previous is None:
        assert not isinstance(actual, ApprovalNotEffective)
        assert actual.code == expected_reason
        assert actual.envelope()["details"] == {}
        assert shown is None
    else:
        assert isinstance(actual, ApprovalNotEffective)
        assert actual.code == "plan_not_valid"
        assert actual.exit_code == 2
        assert actual.envelope()["details"] == {
            "plan_id": plan.plan_id,
            "approval_id": previous.approval_id,
            "recorded": True,
            "reason_code": expected_reason,
        }
        assert shown.approval_id == previous.approval_id
        assert shown.status == "revoked"
        if initial_status == "revoked":
            assert shown == previous


def test_revoke_precommit_failure_does_not_claim_revocation_was_recorded(
    tmp_path, execution_fixture, monkeypatch
):
    from yorunge.adapters import execution_store

    state = tmp_path / "state"
    plan = api.prepare_execution_plan(task="llm.train", state_dir=state).data.plan
    previous = api.approve_execution_plan(plan.plan_id, plan.digest, state_dir=state).data.record

    def fail_write(*args):
        raise YorungeError("state_write_failed")

    monkeypatch.setattr(execution_store, "write_approval", fail_write)
    with pytest.raises(YorungeError) as failure:
        api.revoke_execution_approval(plan.plan_id, state_dir=state)
    assert not isinstance(failure.value, ApprovalNotEffective)
    assert failure.value.code == "state_write_failed"
    assert failure.value.envelope()["details"] == {}
    assert api.show_execution_plan(plan.plan_id, state_dir=state).data.approval.record == previous
