import concurrent.futures
import json
import os
import stat
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from yorunge import api
from yorunge.adapters import configuration
from yorunge.adapters.files import load_config
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.domain.errors import YorungeError


def test_init_defaults_no_clobber_and_never_resolves_credentials(tmp_path, monkeypatch, cli):
    def denied(*args):
        raise AssertionError("unexpected credential read")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    result = api.initialize_config(profile="work", project="chosen").data
    path = tmp_path / ".config/yorunge/config.toml"
    assert result.config_path == str(path)
    assert result.backup_path is None
    assert result.project_id == "chosen"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    parsed = load_config(path)
    assert parsed.profiles["work"].platform_key_env == "EVREN_PLATFORM_API_KEY"
    assert parsed.profiles["work"].llm_key_env == "EVREN_LLM_API_KEY"
    before = path.read_bytes()
    with pytest.raises(YorungeError) as failure:
        api.initialize_config()
    assert failure.value.code == "config_exists"
    result = cli("init", "--output", "json")
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr) == failure.value.envelope()
    assert path.read_bytes() == before
    assert not (tmp_path / ".local/state/yorunge").exists()


def test_profiles_project_mutation_preserves_all_other_semantics_and_raw_backup(config):
    original = config.read_bytes()
    before = load_config(config)
    listed = api.list_profiles(config=config).data
    assert [item.name for item in listed.profiles] == ["work", "other"]
    assert listed.active_profile == "work"
    changed = api.activate_profile("other", config=config).data
    assert Path(changed.backup_path).read_bytes() == original
    assert changed.active_profile == "other"
    assert load_config(config).profiles == before.profiles
    changed = api.set_project("new-project", config=config, profile="work").data
    assert changed.selected_profile == "work"
    assert changed.active_profile == "other"
    assert api.show_context(config=config, profile="work").data.project_id == "new-project"
    assert load_config(config).profiles["other"] == before.profiles["other"]
    assert load_config(config).profiles["work"].tools == before.profiles["work"].tools
    api.clear_project(config=config, profile="work")
    assert load_config(config).profiles["work"].project_id is None
    assert stat.S_IMODE(config.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    "operation,args",
    [
        ("profiles", ()),
        ("use-profile", ("other",)),
        ("set-project", ("chosen",)),
        ("clear-project", ()),
    ],
)
def test_context_console_and_api_result_agree(config, cli, operation, args):
    before = config.read_bytes()
    calls = {
        "profiles": lambda: api.list_profiles(config=config),
        "use-profile": lambda: api.activate_profile("other", config=config),
        "set-project": lambda: api.set_project("chosen", config=config),
        "clear-project": lambda: api.clear_project(config=config),
    }
    expected = calls[operation]().model_dump(mode="json")
    config.write_bytes(before)
    result = cli("context", operation, *args, "--config", str(config), "--output", "json")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    actual = json.loads(result.stdout)
    if operation != "profiles":
        # Each update intentionally uses a fresh retained backup name.
        assert Path(actual["data"].pop("backup_path")).read_bytes() == before
        expected["data"].pop("backup_path")
    assert actual == expected


def test_two_initializers_never_clobber_each_other(tmp_path, cli):
    path = tmp_path / "config.toml"

    def run(name):
        return cli("init", "--config", str(path), "--profile", name, "--output", "json")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["first", "second"]))
    assert sorted(result.returncode for result in results) == [0, 2]
    rejected = next(result for result in results if result.returncode)
    assert json.loads(rejected.stderr)["code"] == "config_exists"
    assert len(load_config(path).profiles) == 1


def test_snapshot_conflict_cannot_lose_concurrent_update(config, monkeypatch):
    original = configuration.read_snapshot
    barrier = threading.Barrier(2)
    local = threading.local()

    def synchronized(path):
        result = original(path)
        if not getattr(local, "seen", False):
            local.seen = True
            barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(configuration, "read_snapshot", synchronized)

    def run(project):
        try:
            return api.set_project(project, config=config)
        except YorungeError as error:
            return error.code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["alpha", "beta"]))
    assert results.count("config_conflict") == 1
    assert load_config(config).profiles["work"].project_id in ("alpha", "beta")


@pytest.mark.parametrize("problem", ["symlink", "hardlink", "writable", "fifo", "malformed"])
def test_mutator_refuses_unsafe_config_without_changing_target(config, tmp_path, problem):
    target = config
    original = config.read_bytes()
    if problem == "symlink":
        target = tmp_path / "link.toml"
        target.symlink_to(config)
    elif problem == "hardlink":
        os.link(config, tmp_path / "other-link")
    elif problem == "writable":
        config.chmod(0o666)
    elif problem == "fifo":
        target = tmp_path / "pipe"
        os.mkfifo(target)
    else:
        config.write_text("schema_version = invalid")
        original = config.read_bytes()
    with pytest.raises(YorungeError) as failure:
        api.set_project("chosen", config=target)
    assert failure.value.code == "invalid_config"
    assert config.read_bytes() == original
    assert not list(tmp_path.glob(".*.backups"))


def test_read_only_config_symlink_behavior_is_preserved(config, tmp_path):
    alias = tmp_path / "alias.toml"
    alias.symlink_to(config)
    assert api.show_context(config=alias) == api.show_context(config=config)


def test_config_serialization_handles_non_bmp_url_without_semantic_loss(config):
    config.write_text(
        config.read_text().replace(
            "[profiles.work]", '[profiles.work]\nplatform_url="https://example.test/😀"'
        )
    )
    expected = load_config(config).profiles["work"].platform_url
    api.set_project("chosen", config=config)
    assert load_config(config).profiles["work"].platform_url == expected
    assert "😀" in config.read_text()


@pytest.mark.parametrize(
    "call",
    [
        lambda p: api.activate_profile(None, config=p),
        lambda p: api.set_project(None, config=p),
        lambda p: api.set_project("bad\nvalue", config=p),
        lambda p: api.initialize_config(config=p, profile=""),
        lambda p: api.initialize_config(config=Path(str(p) + "\x00")),
        lambda p: api.initialize_config(config=Path(str(p) + "\ud800")),
        lambda p: api.diagnose_local(state_dir=Path(str(p) + "\ud800")),
        lambda p: api.diagnose_local(state_dir=Path(str(p) + "\x00")),
    ],
)
def test_invalid_mutation_rejected_without_auxiliary_writes(tmp_path, call):
    path = tmp_path / "config.toml"
    with pytest.raises(YorungeError) as failure:
        call(path)
    assert failure.value.code == "invalid_request"
    assert list(tmp_path.iterdir()) == []


def test_doctor_missing_installation_reads_no_secrets_sqlite_or_writes(tmp_path, monkeypatch, cli):
    def denied(*args):
        raise AssertionError("unexpected credential read")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    report = api.diagnose_local().data
    checks = {item.name: item.status for item in report.checks}
    assert checks["configuration"] == "missing"
    assert checks["state"] == "missing"
    assert checks["platform_reference"] == "missing"
    assert checks["key_check"] == "not_checked"
    assert report.credential_values_read is False
    result = cli("doctor", "--output", "json", "--non-interactive")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"] == report.model_dump(mode="json")
    assert not (tmp_path / ".config").exists()
    assert not (tmp_path / ".local").exists()


@pytest.mark.parametrize(
    "problem", ["none", "missing-key", "wrong-key", "short-key", "intent", "journal"]
)
def test_doctor_existing_store_is_read_only_and_key_check_stays_unchecked(
    config, tmp_path, monkeypatch, cli, problem
):
    from yorunge.adapters import state

    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    key = next((root / "keys").glob("*.key"))
    if problem == "missing-key":
        key.unlink()
    elif problem == "wrong-key":
        key.write_bytes(b"x" * 32)
    elif problem == "short-key":
        key.write_bytes(b"x" * 31)
    elif problem in ("intent", "journal"):
        path = root / ("restore-intent.json" if problem == "intent" else state.DB_NAME + "-journal")
        path.write_bytes(b"synthetic")
        path.chmod(0o600)
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def denied(*args):
        raise AssertionError("doctor must not read key contents or create/migrate state")

    monkeypatch.setattr(state, "load_key", denied)
    monkeypatch.setattr(state, "new_key", denied)
    monkeypatch.setattr(state, "bootstrap", denied)
    original_read = state.read_private

    def bounded(path, *args):
        if path.suffix == ".key":
            denied()
        return original_read(path, *args)

    monkeypatch.setattr(state, "read_private", bounded)
    report = api.diagnose_local(config=config, state_dir=root).data
    checks = {item.name: item for item in report.checks}
    assert checks["key_check"].status == "not_checked"
    assert checks["remote_access"].status == "not_checked"
    if problem == "missing-key":
        assert checks["key"].status == "missing"
    elif problem == "short-key":
        assert checks["key"].status == "invalid"
    elif problem in ("intent", "journal"):
        assert checks["state"].code == "state_repair_required"
    else:
        assert checks["state"].status == "ok"
        assert checks["key"].status == "ok"  # Metadata only, wrong 32-byte content is not checked.
    result = cli(
        "doctor", "--config", str(config), "--state-dir", str(root), "--output", "json", state=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"] == report.model_dump(mode="json")
    assert {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_invalid_config_and_profile_are_independent_typed_diagnostics(config):
    missing = api.diagnose_local(config=config, profile="missing").data
    checks = {item.name: item for item in missing.checks}
    assert checks["configuration"].status == "ok"
    assert checks["profile"].code == "profile_not_found"
    config.write_text("invalid toml")
    broken = api.diagnose_local(config=config).data
    checks = {item.name: item for item in broken.checks}
    assert checks["configuration"].status == "invalid"
    assert checks["profile"].status == "not_checked"


@pytest.mark.parametrize("mode", ["exit", "error"])
@pytest.mark.parametrize(
    "action,phase",
    [
        *[
            ("init", value)
            for value in (
                "temporary-before",
                "temporary-after",
                "temporary-fsync",
                "publish-before",
                "publish-after",
                "parent-sync-before",
                "parent-sync-after",
                "final-sync-before",
                "final-sync-after",
            )
        ],
        *[
            ("update", value)
            for value in (
                "backup-before",
                "backup-after",
                "temporary-before",
                "temporary-after",
                "temporary-fsync",
                "publish-before",
                "publish-after",
                "parent-sync-before",
                "parent-sync-after",
                "final-sync-before",
                "final-sync-after",
            )
        ],
    ],
)
def test_configuration_failures_preserve_old_or_valid_new_file(
    config, tmp_path, action, phase, mode
):
    target = tmp_path / "new.toml" if action == "init" else config
    before = target.read_bytes() if action == "update" else None
    fixture = Path(__file__).parents[1] / "fixtures/configuration_failure.py"
    result = subprocess.run(
        [sys.executable, str(fixture), str(target), action, phase, mode],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode in ((71,) if mode == "exit" else (72, 75)), result.stderr
    if target.exists():
        actual = load_config(target)
        if action == "update":
            assert target.read_bytes() == before or actual.profiles["work"].project_id == "changed"
            if actual.profiles["work"].project_id == "changed":
                backups = list(target.with_name("." + target.name + ".backups").glob("*.toml"))
                assert len(backups) == 1
                assert backups[0].read_bytes() == before
        else:
            assert actual.active_profile == "created"
    else:
        assert action == "init"
    if action == "update" and phase in (
        "backup-before",
        "backup-after",
        "temporary-before",
        "temporary-after",
        "temporary-fsync",
    ):
        assert target.read_bytes() == before
    if mode == "error" and phase in (
        "publish-after",
        "parent-sync-before",
        "parent-sync-after",
        "final-sync-before",
        "final-sync-after",
    ):
        assert result.returncode == 75


def test_oversized_roundtrip_rejected_before_backups_or_lock(tmp_path):
    path = tmp_path / "many.toml"
    path.write_text(
        'schema_version=1\nactive_profile="p0"\n'
        + "\n".join(f"[profiles.p{i}]" for i in range(400))
    )
    assert len(load_config(path).profiles) == 400
    before = path.read_bytes()
    with pytest.raises(YorungeError) as failure:
        api.set_project("chosen", config=path)
    assert failure.value.code == "invalid_config"
    assert path.read_bytes() == before
    assert not path.with_name("." + path.name + ".lock").exists()


def test_config_lock_wait_is_bounded_and_inode_stable(config):
    with configuration.config_lock(config):
        inode = config.with_name("." + config.name + ".lock").stat().st_ino
        with pytest.raises(YorungeError) as failure:
            api.set_project("chosen", config=config)
        assert failure.value.code == "config_busy"
    assert config.with_name("." + config.name + ".lock").stat().st_ino == inode


def test_saved_plan_never_reloads_changed_profile_or_project(config, tmp_path):
    original = api.prepare_plan(config=config, task="llm.train").data
    saved = tmp_path / "plan.json"
    saved.write_text(original.model_dump_json())
    before = saved.read_bytes()
    api.activate_profile("other", config=config)
    api.set_project("new-project", config=config)
    assert api.load_plan(saved).data == original
    assert saved.read_bytes() == before


def test_editor_change_during_real_temporary_write_is_not_lost(config, monkeypatch):
    original = configuration.write_new
    editor_bytes = config.read_bytes() + b"\n# independent editor change\n"

    def write(path, content):
        original(path, content)
        if path.suffix == ".tmp":
            config.write_bytes(editor_bytes)

    monkeypatch.setattr(configuration, "write_new", write)
    with pytest.raises(YorungeError) as failure:
        api.set_project("changed", config=config)
    assert failure.value.code == "config_conflict"
    assert config.read_bytes() == editor_bytes


def test_typed_postpublication_validation_failure_is_uncertain(config, monkeypatch):
    original = configuration.sync_private

    def sync(path):
        path.chmod(0o640)
        original(path)

    monkeypatch.setattr(configuration, "sync_private", sync)
    with pytest.raises(YorungeError) as failure:
        api.set_project("published", config=config)
    assert failure.value.code == "config_write_uncertain"
    assert failure.value.exit_code == 5
    assert load_config(config).profiles["work"].project_id == "published"


def test_doctor_empty_state_directory_is_missing_without_creating_lock(tmp_path):
    root = tmp_path / "state"
    root.mkdir(mode=0o700)
    report = api.diagnose_local(state_dir=root).data
    checks = {item.name: item for item in report.checks}
    assert checks["state"].status == "missing"
    assert list(root.iterdir()) == []
    (root / "foreign-payload").write_bytes(b"retained")
    report = api.diagnose_local(state_dir=root).data
    checks = {item.name: item for item in report.checks}
    assert checks["state"].code == "state_repair_required"
    assert not (root / "store.lock").exists()


def test_doctor_sqlite_interruption_reports_busy_instead_of_corrupt(tmp_path, monkeypatch):
    from yorunge.adapters import state

    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    original = state.connect_readonly

    def interrupted(*args):
        connection = original(*args)
        connection.set_progress_handler(lambda: 1, 1)
        return connection

    monkeypatch.setattr(state, "connect_readonly", interrupted)
    report = api.diagnose_local(state_dir=root).data
    checks = {item.name: item for item in report.checks}
    assert checks["state"].status == "busy"
    assert checks["state"].code == "state_busy"


def test_doctor_explicit_missing_config_distinguished_from_broken_symlink(tmp_path):
    path = tmp_path / "missing.toml"
    report = api.diagnose_local(config=path).data
    checks = {item.name: item for item in report.checks}
    assert checks["configuration"].status == "missing"
    path.symlink_to(tmp_path / "missing-target")
    report = api.diagnose_local(config=path).data
    checks = {item.name: item for item in report.checks}
    assert checks["configuration"].status == "invalid"


def test_doctor_implicit_broken_symlink_is_invalid_but_context_fallback_unchanged(tmp_path):
    path = tmp_path / ".config/yorunge/config.toml"
    path.parent.mkdir(parents=True)
    path.symlink_to(tmp_path / "missing-target")
    implicit = api.diagnose_local().data
    explicit = api.diagnose_local(config=path).data
    assert implicit == explicit
    checks = {item.name: item for item in implicit.checks}
    assert checks["configuration"].status == "invalid"
    assert checks["profile"].status == "not_checked"
    assert api.show_context().data.profile == "default"
    report = api.diagnose_local(config=Path(str(path) + "\ud800")).data
    checks = {item.name: item for item in report.checks}
    assert checks["configuration"].status == "invalid"
