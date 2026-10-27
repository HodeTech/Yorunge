import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from yorunge import api
from yorunge.adapters import maintenance, state_schema
from yorunge.adapters.local_files import Deadline
from yorunge.adapters.state import DB_NAME, backup, metadata, open_store
from yorunge.domain.errors import YorungeError


def observed(config, root):
    return api.observe_credential("evren-platform", config=config, state_dir=root).data.identity


def migration_backup(root):
    with maintenance.target_lock(root, Deadline(), create=False):
        return backup(root, root / DB_NAME, Deadline(), state_schema.MIGRATIONS)


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_reset_preview_is_read_only_and_reset_preserves_history(config, tmp_path, monkeypatch):
    root = tmp_path / "state"
    first = observed(config, root)
    before = files(root)

    def denied(*args):
        raise AssertionError("preview must not read any key")

    with monkeypatch.context() as patch:
        patch.setattr(maintenance, "load_key", denied)
        preview = api.preview_identity_reset(state_dir=root).data
    assert files(root) == before
    assert preview.history_may_be_lost is False
    assert preview.current.binding_count == 1
    result = api.reset_identity(preview.digest, state_dir=root).data
    assert result.identity_epoch != first.identity_epoch
    second = observed(config, root)
    assert second.credential_id != first.credential_id
    assert second.credential_revision == 1
    with sqlite3.connect(root / DB_NAME) as connection:
        rows = connection.execute(
            "SELECT credential_id,revision FROM credential_bindings"
        ).fetchall()
    assert sorted(rows) == sorted([(first.credential_id, 1), (second.credential_id, 1)])


@pytest.mark.parametrize("problem", ["missing", "wrong", "short"])
def test_reset_works_without_claiming_old_key_recovered(config, tmp_path, problem):
    root = tmp_path / "state"
    old = observed(config, root)
    with open_store(root) as store:
        key_path = root / "keys" / (metadata(store.connection).active_key_id + ".key")
    if problem == "missing":
        key_path.unlink()
    else:
        key_path.write_bytes(b"x" * (32 if problem == "wrong" else 31))
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_repair_required"
    preview = api.preview_identity_reset(state_dir=root).data
    api.reset_identity(preview.digest, state_dir=root)
    assert observed(config, root).identity_epoch != old.identity_epoch
    if problem == "missing":
        assert not key_path.exists()
    else:
        assert key_path.read_bytes() == b"x" * (32 if problem == "wrong" else 31)


def test_stale_reset_consent_catches_revision_change_with_same_row_count(
    config, tmp_path, monkeypatch
):
    root = tmp_path / "state"
    observed(config, root)
    preview = api.preview_identity_reset(state_dir=root).data
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "changed")
    observed(config, root)
    before = files(root)
    with pytest.raises(YorungeError) as failure:
        api.reset_identity(preview.digest, state_dir=root)
    assert failure.value.code == "state_changed"
    assert files(root) == before


@pytest.mark.parametrize("existing", [False, True])
def test_restore_new_epoch_no_old_key_needed_safety_snapshot_and_explicit_loss(
    config, tmp_path, monkeypatch, existing
):
    source = tmp_path / "source"
    old = observed(config, source)
    saved = migration_backup(source)
    for key in (source / "keys").glob("*.key"):
        key.unlink()
    target = tmp_path / "target"
    if existing:
        observed(config, target)
        monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "after-backup")
        latest = observed(config, target)
    before = files(target) if existing else {}
    preview = api.preview_state_restore(saved, state_dir=target)
    assert preview.data.history_may_be_lost is True
    assert preview.warnings == ("restore_discards_post_backup_history",)
    assert (files(target) if existing else {}) == before
    assert target.exists() is existing
    result = api.restore_state(saved, preview.data.digest, state_dir=target).data
    assert result.identity_epoch != old.identity_epoch
    assert not (target / maintenance.INTENT_NAME).exists()
    assert api.initialize_state(state_dir=target).data == result
    current = observed(config, target)
    assert current.credential_id != old.credential_id
    assert current.credential_revision == 1
    if existing:
        snapshots = [
            p
            for p in (target / "backups").glob("*/complete.json")
            if json.loads(p.read_text())["purpose"] == "pre_restore"
        ]
        assert len(snapshots) == 1
        record = json.loads(snapshots[0].read_text())
        assert record["purpose"] == "pre_restore"
        connection = maintenance.connect_readonly(
            snapshots[0].parent / "snapshot.sqlite3", Deadline()
        )
        try:
            assert connection.execute(
                "SELECT credential_id,revision FROM credential_bindings"
            ).fetchall() == [(latest.credential_id, 2)]
        finally:
            connection.close()
        with pytest.raises(YorungeError) as failure:
            api.preview_state_restore(snapshots[0].parent, state_dir=tmp_path / "other")
        assert failure.value.code == "state_restore_unsupported"


def test_restore_rejects_stale_consent_without_creating_new_target(config, tmp_path):
    root = tmp_path / "source"
    observed(config, root)
    saved = migration_backup(root)
    target = tmp_path / "new"
    with pytest.raises(YorungeError) as failure:
        api.restore_state(saved, "0" * 64, state_dir=target)
    assert failure.value.code == "state_changed"
    assert not target.exists()


def test_operation_runtime_disables_restore_even_old_snapshot_and_no_target(
    config, tmp_path, monkeypatch
):
    root = tmp_path / "source"
    observed(config, root)
    saved = migration_backup(root)
    version = len(state_schema.MIGRATIONS)
    step = state_schema.Migration(
        version, version + 1, ("CREATE TABLE operations(id INTEGER PRIMARY KEY) STRICT",)
    )
    monkeypatch.setattr(state_schema, "MIGRATIONS", (*state_schema.MIGRATIONS, step))
    for call in (
        lambda: api.preview_state_restore(saved, state_dir=tmp_path / "missing"),
        lambda: api.restore_state(saved, "0" * 64, state_dir=tmp_path / "missing"),
    ):
        with pytest.raises(YorungeError) as failure:
            call()
        assert failure.value.code == "state_restore_unsupported"
    api.initialize_state(state_dir=root)
    with sqlite3.connect(root / DB_NAME) as connection:
        connection.execute("INSERT INTO operations VALUES(123)")
    preview = api.preview_identity_reset(state_dir=root).data
    api.reset_identity(preview.digest, state_dir=root)
    with sqlite3.connect(root / DB_NAME) as connection:
        assert connection.execute("SELECT * FROM operations").fetchall() == [(123,)]


def test_preview_rejects_hot_journal_without_recovery_and_locked_writer(config, tmp_path):
    root = tmp_path / "state"
    observed(config, root)
    journal = root / (DB_NAME + "-journal")
    journal.write_bytes(b"synthetic interrupted journal")
    journal.chmod(0o600)
    before = files(root)
    with pytest.raises(YorungeError) as failure:
        api.preview_identity_reset(state_dir=root)
    assert failure.value.code == "state_repair_required"
    assert files(root) == before
    journal.unlink()  # Test-owned synthetic sidecar, not a product recovery operation.
    inode = (root / "store.lock").stat().st_ino
    with open_store(root):
        with pytest.raises(YorungeError) as failure:
            api.preview_identity_reset(state_dir=root)
        assert failure.value.code == "state_busy"
    assert (root / "store.lock").stat().st_ino == inode


@pytest.mark.parametrize("partial", ["missing-lock", "empty-db", "foreign-db", "keys-only"])
def test_restore_preserves_ambiguous_partial_or_foreign_target(config, tmp_path, partial):
    root = tmp_path / "source"
    observed(config, root)
    saved = migration_backup(root)
    target = tmp_path / "target"
    api.initialize_state(state_dir=target)
    if partial == "missing-lock":
        (target / "store.lock").unlink()
    elif partial == "empty-db":
        (target / DB_NAME).write_bytes(b"")
    elif partial == "foreign-db":
        (target / DB_NAME).write_bytes(b"foreign")
    else:
        (target / DB_NAME).unlink()
    before = files(target)
    with pytest.raises(YorungeError):
        api.preview_state_restore(saved, state_dir=target)
    assert files(target) == before


def test_reset_console_preview_and_apply_share_api_contract(config, tmp_path, cli):
    root = tmp_path / "state"
    observed(config, root)
    preview = api.preview_identity_reset(state_dir=root)
    command = ("state", "reset", "--state-dir", str(root), "--output", "json")
    result = cli(*command, state=True)
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == preview.model_dump(mode="json")
    result = cli(*command, "--confirm", preview.data.digest, state=True)
    assert result.returncode == 0
    assert (
        json.loads(result.stdout)["data"] == api.initialize_state(state_dir=root).data.model_dump()
    )
    result = cli(*command, "--confirm", preview.data.digest, state=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "state_changed"


@pytest.mark.parametrize("mode", ["exit", "error"])
@pytest.mark.parametrize(
    "phase",
    [
        "key-before",
        "key-after",
        "key-sync-before",
        "key-sync-after",
        "pointer-before",
        "commit-before",
        "commit-after",
        "reset-after",
        "live-sync-before",
        "live-sync-after",
    ],
)
def test_reset_failure_boundaries_leave_old_or_new_valid_identity(config, tmp_path, phase, mode):
    root = tmp_path / "state"
    old = observed(config, root)
    inode = (root / "store.lock").stat().st_ino
    fixture = Path(__file__).parents[1] / "fixtures/maintenance_failure.py"
    result = subprocess.run(
        [sys.executable, str(fixture), str(root), str(root), "reset", phase, mode],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == (71 if mode == "exit" else 72), result.stderr
    info = api.initialize_state(state_dir=root).data
    current = observed(config, root)
    assert (root / "store.lock").stat().st_ino == inode
    if info.identity_epoch == old.identity_epoch:
        assert current == old
    else:
        assert current.credential_id != old.credential_id
        assert current.credential_revision == 1
    with sqlite3.connect(root / DB_NAME) as connection:
        assert connection.execute(
            "SELECT revision FROM credential_bindings WHERE credential_id=?", (old.credential_id,)
        ).fetchone() == (1,)


@pytest.mark.parametrize("mode", ["exit", "error"])
@pytest.mark.parametrize(
    "phase",
    [
        "key-before",
        "key-after",
        "key-sync-before",
        "key-sync-after",
        "intent-before",
        "intent-after",
        "copy-before",
        "copy-after",
        "pointer-before",
        "commit-before",
        "commit-after",
        "stage-after",
        "publish-before",
        "publish-after",
        "live-sync-before",
        "live-sync-after",
        "intent-remove-before",
        "intent-remove-after",
        "intent-remove-sync-before",
        "intent-remove-sync-after",
    ],
)
def test_restore_failure_boundaries_fail_closed_then_explicitly_recover(
    config, tmp_path, phase, mode
):
    root = tmp_path / "state"
    old = observed(config, root)
    saved = migration_backup(root)
    inode = (root / "store.lock").stat().st_ino
    fixture = Path(__file__).parents[1] / "fixtures/maintenance_failure.py"
    result = subprocess.run(
        [sys.executable, str(fixture), str(root), str(saved), "restore", phase, mode],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == (71 if mode == "exit" else 72), result.stderr
    if (root / maintenance.INTENT_NAME).exists():
        intent = json.loads((root / maintenance.INTENT_NAME).read_text())
        with pytest.raises(YorungeError) as failure:
            api.initialize_state(state_dir=root)
        assert failure.value.code == "state_repair_required"
        preview = api.preview_state_recovery(state_dir=root).data
        assert preview.announced_epoch == intent["identity_epoch"]
        recovered = api.recover_state(preview.digest, state_dir=root).data
        assert recovered.identity_epoch == intent["identity_epoch"]
        assert not (root / maintenance.INTENT_NAME).exists()
        assert observed(config, root).credential_id != old.credential_id
    else:
        current = observed(config, root)
        if phase.startswith("key-") or phase == "intent-before":
            assert current == old
        else:
            assert current.identity_epoch != old.identity_epoch
    assert (root / "store.lock").stat().st_ino == inode


def test_partial_stage_is_retained_and_rebuilt_under_same_announced_epoch(
    config, tmp_path, monkeypatch
):
    from yorunge.adapters.local_files import write_new

    root = tmp_path / "state"
    observed(config, root)
    saved = migration_backup(root)
    preview = api.preview_state_restore(saved, state_dir=root).data

    def incomplete(source, target, deadline):
        write_new(target, b"partial-owned-copy")
        raise OSError("synthetic partial copy")

    with monkeypatch.context() as patch:
        patch.setattr(maintenance, "copy_snapshot", incomplete)
        with pytest.raises(YorungeError):
            api.restore_state(saved, preview.digest, state_dir=root)
    recovery = api.preview_state_recovery(state_dir=root).data
    actual = api.recover_state(recovery.digest, state_dir=root).data
    assert actual.identity_epoch == recovery.announced_epoch
    retained = list(root.glob("interrupted-*.sqlite3"))
    assert len(retained) == 1
    assert retained[0].read_bytes() == b"partial-owned-copy"


@pytest.mark.parametrize("boundary", ["stage-after", "publish-after"])
def test_completed_new_pair_can_recover_without_original_backup(config, tmp_path, boundary):
    root = tmp_path / "state"
    observed(config, root)
    saved = migration_backup(root)
    fixture = Path(__file__).parents[1] / "fixtures/maintenance_failure.py"
    result = subprocess.run(
        [sys.executable, str(fixture), str(root), str(saved), "restore", boundary, "exit"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 71, result.stderr
    saved.rename(saved.with_name(saved.name + "-retained-elsewhere"))
    preview = api.preview_state_recovery(state_dir=root).data
    actual = api.recover_state(preview.digest, state_dir=root).data
    assert actual.identity_epoch == preview.announced_epoch


def test_missing_wrong_new_restore_key_remains_fail_closed(config, tmp_path, monkeypatch):
    root = tmp_path / "state"
    observed(config, root)
    saved = migration_backup(root)
    preview = api.preview_state_restore(saved, state_dir=root).data

    def stop(*args):
        raise OSError("synthetic after intent")

    with monkeypatch.context() as patch:
        patch.setattr(maintenance, "finish_restore", stop)
        with pytest.raises(YorungeError):
            api.restore_state(saved, preview.digest, state_dir=root)
    intent = maintenance.read_intent(root)
    key = root / "keys" / (intent.key_id + ".key")
    key.write_bytes(b"x" * 32)
    before = files(root)
    with pytest.raises(YorungeError) as failure:
        api.preview_state_recovery(state_dir=root)
    assert failure.value.code == "state_repair_required"
    assert files(root) == before


def test_orphaned_intent_stage_journal_is_retained_before_rebuild(config, tmp_path, monkeypatch):
    root = tmp_path / "state"
    observed(config, root)
    saved = migration_backup(root)
    preview = api.preview_state_restore(saved, state_dir=root).data

    def stop(*args):
        raise OSError("synthetic before staging")

    with monkeypatch.context() as patch:
        patch.setattr(maintenance, "finish_restore", stop)
        with pytest.raises(YorungeError):
            api.restore_state(saved, preview.digest, state_dir=root)
    intent = maintenance.read_intent(root)
    stage = root / ("restore-" + intent.stage_id + ".sqlite3")
    journal = stage.with_name(stage.name + "-journal")
    journal.write_bytes(b"retained orphaned stage journal")
    journal.chmod(0o600)
    recovery = api.preview_state_recovery(state_dir=root).data
    actual = api.recover_state(recovery.digest, state_dir=root).data
    assert actual.identity_epoch == intent.identity_epoch
    assert not journal.exists()
    retained = list(root.glob("interrupted-*.sqlite3-journal"))
    assert len(retained) == 1
    assert retained[0].read_bytes() == b"retained orphaned stage journal"


@pytest.mark.parametrize("action", ["reset", "restore", "recover"])
def test_explicit_empty_confirmation_is_rejected_before_io(tmp_path, cli, action):
    root = tmp_path / "missing"
    source = tmp_path / "missing-backup"
    call = {
        "reset": lambda: api.reset_identity("", state_dir=root),
        "restore": lambda: api.restore_state(source, "", state_dir=root),
        "recover": lambda: api.recover_state("", state_dir=root),
    }[action]
    with pytest.raises(YorungeError) as failure:
        call()
    assert failure.value.code == "invalid_request"
    command = ["state", action, "--state-dir", str(root), "--confirm", "", "--output", "json"]
    if action == "restore":
        command += ["--backup", str(source)]
    result = cli(*command, state=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr) == failure.value.envelope()
    assert not root.exists()


def test_recover_retries_interrupted_intent_barrier_before_any_publication(
    config, tmp_path, monkeypatch
):
    root = tmp_path / "state"
    observed(config, root)
    saved = migration_backup(root)
    preview = api.preview_state_restore(saved, state_dir=root).data
    original = os.fsync

    def fail_intent(descriptor):
        marker = root / maintenance.INTENT_NAME
        if marker.exists() and marker.stat().st_ino == os.fstat(descriptor).st_ino:
            raise OSError("synthetic failed intent content sync")
        return original(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_intent)
        with pytest.raises(YorungeError) as failure:
            api.restore_state(saved, preview.digest, state_dir=root)
        assert failure.value.code == "state_write_failed"
    intent = maintenance.read_intent(root)
    before = files(root)
    recovery = api.preview_state_recovery(state_dir=root).data
    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_intent)
        with pytest.raises(YorungeError) as failure:
            api.recover_state(recovery.digest, state_dir=root)
        assert failure.value.code == "state_write_failed"
    assert files(root) == before
    events = []
    original_sync = maintenance.sync_private
    original_replace = os.replace

    def sync(path):
        original_sync(path)
        if path == root / maintenance.INTENT_NAME:
            events.append("durable-intent")

    def publish(*args):
        assert events == ["durable-intent"]
        return original_replace(*args)

    monkeypatch.setattr(maintenance, "sync_private", sync)
    monkeypatch.setattr(os, "replace", publish)
    actual = api.recover_state(recovery.digest, state_dir=root).data
    assert actual.identity_epoch == intent.identity_epoch


@pytest.mark.parametrize("old_version", [1, 2, 3])
@pytest.mark.parametrize("pair_kind", ["stage", "live"])
@pytest.mark.parametrize(
    "boundary",
    [
        "migration-write",
        "migration-committed",
        "shadow-synced",
        "publish-before",
        "publish-after",
        "pair-synced",
    ],
)
def test_second_recovery_cut_preserves_completed_pair_without_original_backup(
    tmp_path,
    monkeypatch,
    old_version,
    pair_kind,
    boundary,
):
    import shutil
    import signal

    from yorunge.adapters import maintenance, state_schema
    from yorunge.adapters.local_files import Deadline
    from yorunge.adapters.state import DB_NAME, backup, open_store

    source, target = tmp_path / "source", tmp_path / "target"
    with monkeypatch.context() as patch:
        patch.setattr(state_schema, "MIGRATIONS", state_schema.MIGRATIONS[:old_version])
        with open_store(source) as store:
            saved = backup(source, source / DB_NAME, Deadline(), state_schema.MIGRATIONS)
    fixture = Path(__file__).parents[1] / "fixtures/recovery_upgrade_failure.py"
    old = subprocess.run(
        [sys.executable, str(fixture), "old", str(target), pair_kind, str(old_version), str(saved)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert old.returncode == 73, old.stderr
    intent = maintenance.read_intent(target)
    pair = target / (
        DB_NAME if pair_kind == "live" else "restore-" + intent.stage_id + maintenance.STAGE_SUFFIX
    )
    original = pair.read_bytes()
    shutil.rmtree(source)
    child = subprocess.run(
        [
            sys.executable,
            str(fixture),
            "upgrade",
            str(target),
            boundary,
            str(old_version),
            pair_kind,
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert child.returncode == -signal.SIGKILL, child.stderr
    if boundary in ("migration-write", "migration-committed", "shadow-synced", "publish-before"):
        preserved = pair.read_bytes() == original
        assert preserved, "completed pair was modified before shadow publication"
    if boundary == "migration-write":
        journals = list(target.glob("upgrade-*.sqlite3-journal"))
        assert len(journals) == 1
        assert journals[0].read_bytes()[:8] == bytes.fromhex("d9d505f920a163d7")
        assert not pair.with_name(pair.name + "-journal").exists()
    before = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    preview = api.preview_state_recovery(state_dir=target).data
    after = {p.relative_to(target): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    unchanged = before == after
    assert unchanged, "recovery preview changed private files"
    result = api.recover_state(preview.digest, state_dir=target).data
    assert result.identity_epoch == intent.identity_epoch
    assert result.store_schema_version == len(state_schema.MIGRATIONS)
    assert not (target / maintenance.INTENT_NAME).exists()
    assert (target / "keys" / (intent.key_id + ".key")).exists()
    with open_store(target) as store:
        store.verify()
