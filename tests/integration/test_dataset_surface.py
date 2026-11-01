"""Real API/CLI publication, failure precedence and the first local user journey."""

import asyncio
import errno
import json
import os
import signal
import stat
import subprocess
import sys
from functools import partial
from pathlib import Path

import pytest

from yorunge import api
from yorunge.adapters import dataset_files, dataset_reports
from yorunge.application import datasets
from yorunge.cli import main
from yorunge.domain import dataset_manifest as policy
from yorunge.domain.errors import MESSAGES, ManifestMismatch, YorungeError


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "a.txt").write_bytes(b"abc")
    (root / "empty.bin").write_bytes(b"")
    (root / "ölçüm.txt").write_bytes(b"hello")
    return root, tmp_path / "manifest.json"


def assert_error(call, code, exit_code=2):
    with pytest.raises(YorungeError) as failure:
        call()
    assert failure.value.code == code
    assert failure.value.exit_code == exit_code
    assert failure.value.envelope()["details"] == {}
    return failure.value


def test_real_api_publishes_golden_private_artifact_then_rehashes_every_file(tree):
    root, target = tree
    inspection = api.inspect_dataset(root, manifest_out=target)
    golden = Path(__file__).parents[1] / "fixtures/dataset-manifest-v1.json"
    assert target.read_bytes() == golden.read_bytes()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert target.stat().st_nlink == 1
    assert list(target.parent.glob(".yorunge-manifest-*.tmp")) == []
    assert inspection.warnings == ("local_files_only",)
    assert inspection.operation_id is None
    assert inspection.data.manifest_path == str(target)
    assert inspection.data.file_count == 3
    assert inspection.data.total_bytes == 8
    verified = api.verify_dataset(root, manifest=target)
    assert verified.data.matches is True
    assert verified.data.manifest_digest == inspection.data.manifest_digest
    (root / "a.txt").write_bytes(b"xyz")
    with pytest.raises(ManifestMismatch) as mismatch:
        api.verify_dataset(root, manifest=target)
    assert mismatch.value.exit_code == 7
    assert mismatch.value.envelope()["details"]["changed_file_count"] == 1
    assert target.read_bytes() == golden.read_bytes()


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_real_cli_journey_has_small_output_and_exact_mismatch_error(tree, cli, output):
    root, target = tree
    result = cli(
        "datasets", "inspect", str(root), "--manifest-out", str(target), "--output", output
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert len(result.stdout.encode("utf-8")) < 16384
    if output == "text":
        assert str(target) in result.stdout
        assert "Dosya: 3; byte: 8" in result.stdout
        assert "yorunge datasets verify" in result.stdout
    else:
        value = json.loads(result.stdout)
        if output == "ndjson":
            assert value["event"] == "result"
            value = value["payload"]
        assert value["warnings"] == ["local_files_only"]
        assert value["data"]["file_count"] == 3
        assert "files" not in value["data"]
    verified = cli("--output", output, "datasets", "verify", str(root), "--manifest", str(target))
    assert verified.returncode == 0, verified.stderr
    (root / "a.txt").write_bytes(b"xyz")
    changed = cli("datasets", "verify", str(root), "--manifest", str(target), "--output", output)
    assert changed.returncode == 7
    assert changed.stdout == ""
    if output != "text":
        error = json.loads(changed.stderr)
        assert error["code"] == "manifest_mismatch"
        assert set(error["details"]) == {
            "expected_digest",
            "actual_digest",
            "changed_file_count",
            "missing_file_count",
            "unexpected_file_count",
        }
        assert error["details"]["changed_file_count"] == 1
    assert "a.txt" not in changed.stderr


@pytest.mark.parametrize("kind", ["regular", "directory", "symlink", "dangling"])
def test_existing_target_of_every_kind_is_preserved_before_source_reads(tree, monkeypatch, kind):
    root, target = tree
    if kind == "regular":
        target.write_bytes(b"previous")
    elif kind == "directory":
        target.mkdir()
    else:
        target.symlink_to(target.parent / ("source/a.txt" if kind == "symlink" else "missing"))
    before = target.lstat()
    monkeypatch.setattr(
        os, "read", lambda *a: pytest.fail("source read before existing target ret")
    )
    assert_error(lambda: api.inspect_dataset(root, manifest_out=target), "manifest_output_exists")
    assert target.lstat() == before


@pytest.mark.parametrize("bad", [None, "source", 1, True])
@pytest.mark.parametrize("argument", ["root", "artifact"])
def test_api_path_types_are_strict_before_io(tree, monkeypatch, bad, argument):
    root, target = tree
    monkeypatch.setattr(Path, "cwd", lambda: pytest.fail("cwd before argument validation"))
    for use_case, option in (
        (api.inspect_dataset, "manifest_out"),
        (api.verify_dataset, "manifest"),
    ):
        selected_root = bad if argument == "root" else root
        selected_artifact = bad if argument == "artifact" else target
        assert_error(
            partial(use_case, selected_root, **{option: selected_artifact}), "invalid_request"
        )


def test_relative_pair_is_bound_once_and_absolute_pair_never_reads_cwd(tree, monkeypatch):
    root, target = tree
    calls = []

    def cwd():
        calls.append(1)
        assert len(calls) == 1
        return root.parent

    monkeypatch.setattr(Path, "cwd", cwd)
    result = api.inspect_dataset(Path("source"), manifest_out=Path("manifest.json"))
    assert result.data.manifest_path == str(target)
    assert calls == [1]
    monkeypatch.setattr(Path, "cwd", lambda: pytest.fail("absolute pair requested cwd"))
    assert api.verify_dataset(root, manifest=target).data.matches is True


@pytest.mark.parametrize("action", ["inspect", "verify"])
def test_unsupported_platform_precedes_all_path_io(tree, monkeypatch, action):
    root, target = tree
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(Path, "cwd", lambda: pytest.fail("unsupported cwd IO"))
    monkeypatch.setattr(os, "open", lambda *a, **k: pytest.fail("unsupported open IO"))
    call = (
        (lambda: api.inspect_dataset(Path("source"), manifest_out=target))
        if action == "inspect"
        else (lambda: api.verify_dataset(root, manifest=Path("manifest.json")))
    )
    assert_error(call, "input_unsupported")


@pytest.mark.parametrize("action", ["inspect", "verify"])
def test_artifact_inside_source_is_rejected_before_content_reads(tree, monkeypatch, action):
    root, _ = tree
    target = root / "manifest.json"
    target.write_bytes(b"not a manifest")
    monkeypatch.setattr(os, "read", lambda *a: pytest.fail("inside artifact read"))
    call = (
        (lambda: api.inspect_dataset(root, manifest_out=target))
        if action == "inspect"
        else (lambda: api.verify_dataset(root, manifest=target))
    )
    assert_error(call, "input_invalid")


def test_malformed_manifest_is_rejected_before_source_hash(tree, monkeypatch):
    root, target = tree
    target.write_bytes(b"{}")
    monkeypatch.setattr(dataset_files.DatasetTree, "scan", lambda *a: pytest.fail("invalid scan"))
    assert_error(lambda: api.verify_dataset(root, manifest=target), "manifest_invalid")


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
@pytest.mark.parametrize("code", ["input_invalid", "input_changed", "input_unsupported"])
def test_input_messages_give_dataset_recovery_in_all_renderers(
    tree, monkeypatch, capsys, output, code
):
    root, target = tree

    def reject(*a, **k):
        raise YorungeError(code)

    monkeypatch.setattr(api, "inspect_dataset", reject)
    assert (
        main(["datasets", "inspect", str(root), "--manifest-out", str(target), "--output", output])
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    message = captured.err if output == "text" else json.loads(captured.err)["message"]
    assert MESSAGES[code] in message
    assert "plan" not in message.lower()
    assert "bağlama" not in message.lower()


@pytest.mark.parametrize(
    "args",
    [
        ["--config", "missing"],
        ["--profile", "work"],
        ["--project", "p"],
        ["--state-dir", "s"],
        ["--recipe", "r"],
        ["--task", "dataset.upload"],
        ["--tool", "native"],
        ["--execution", "local"],
        ["--refresh"],
        ["--manifest-out", "other"],
        ["--output", "json"],
        ["--non-interactive", "--non-interactive"],
    ],
)
def test_cli_rejects_unsupported_or_duplicate_options_before_io(tree, cli, args):
    root, target = tree
    result = cli(
        "datasets", "inspect", str(root), "--manifest-out", str(target), "--output=json", *args
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "invalid_request"
    assert not target.exists()


@pytest.mark.parametrize("option", ["--config", "--profile", "--project"])
def test_global_context_flags_are_not_silently_ignored(tree, cli, option):
    root, target = tree
    result = cli(
        option,
        "missing",
        "datasets",
        "inspect",
        str(root),
        "--manifest-out",
        str(target),
        "--output=json",
    )
    assert result.returncode == 2
    assert json.loads(result.stderr)["code"] == "invalid_request"
    assert not target.exists()


def test_summary_encoded_byte_preflight_happens_before_any_publication(tree, monkeypatch):
    root, target = tree
    monkeypatch.setattr(policy, "MAX_SUMMARY_BYTES", 1)
    monkeypatch.setattr(
        dataset_reports.DatasetManifestWriter,
        "publish",
        lambda *a: pytest.fail("summary published"),
    )
    assert_error(lambda: api.inspect_dataset(root, manifest_out=target), "dataset_limit_exceeded")
    assert not target.exists()


def test_short_writes_complete_one_private_regular_file(tree, monkeypatch):
    root, target = tree
    original = os.write
    counts = []

    def short(fd, data):
        info = os.fstat(fd)
        assert stat.S_IMODE(info.st_mode) == 0o600
        count = original(fd, data[:7])
        counts.append(count)
        return count

    monkeypatch.setattr(os, "write", short)
    api.inspect_dataset(root, manifest_out=target)
    assert len(counts) > 1
    assert api.verify_dataset(root, manifest=target).data.matches is True


@pytest.mark.parametrize("failure", ["zero_write", "disk_full", "sync", "stage_stat"])
def test_prepublication_write_failures_clean_stage_and_never_create_target(
    tree, monkeypatch, failure
):
    root, target = tree

    def denied(*a, **k):
        raise OSError(errno.ENOSPC, "PRIVATE-PATH-NEVER-PRINT")

    if failure == "zero_write":
        monkeypatch.setattr(os, "write", lambda *a: 0)
    elif failure == "disk_full":
        monkeypatch.setattr(os, "write", denied)
    elif failure == "sync":
        monkeypatch.setattr(dataset_reports, "full_sync", denied)
    else:
        monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_check_stage", denied)
    error = assert_error(
        lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_failed"
    )
    assert "PRIVATE-PATH" not in str(error.envelope())
    assert not target.exists()
    assert list(target.parent.glob(".yorunge-manifest-*.tmp")) == []


def test_racing_target_is_never_overwritten_even_after_initial_check(tree, monkeypatch):
    root, target = tree
    original = dataset_reports.DatasetManifestWriter._publish_link

    def race(writer):
        target.write_bytes(b"other-owner")
        original(writer)

    monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_publish_link", race)
    assert_error(lambda: api.inspect_dataset(root, manifest_out=target), "manifest_output_exists")
    assert target.read_bytes() == b"other-owner"
    assert list(target.parent.glob(".yorunge-manifest-*.tmp")) == []


@pytest.mark.parametrize(
    "when", ["before_link", "after_link", "cleanup", "parent_sync", "final_target"]
)
def test_link_and_postpublication_failures_have_safe_uncertain_exit(tree, monkeypatch, when):
    root, target = tree
    original_link, original_unlink, original_fsync = os.link, os.unlink, os.fsync

    def link(*a, **k):
        if when != "before_link":
            original_link(*a, **k)
        if when in ("before_link", "after_link"):
            raise OSError(errno.EIO, "PRIVATE-PATH")

    def unlink(*a, **k):
        if when == "cleanup":
            raise OSError(errno.EIO, "PRIVATE-PATH")
        original_unlink(*a, **k)

    def fsync(fd):
        if when == "parent_sync" and stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError(errno.EIO, "PRIVATE-PATH")
        original_fsync(fd)

    original_check = dataset_reports.DatasetManifestWriter._check_target
    checks = []

    def check(*a, **k):
        checks.append(1)
        if when == "final_target" and len(checks) == 2:
            raise OSError(errno.EIO, "PRIVATE-PATH")
        original_check(*a, **k)

    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, link, unlink})
    monkeypatch.setattr(os, "supports_follow_symlinks", {*os.supports_follow_symlinks, link})
    monkeypatch.setattr(os, "unlink", unlink)
    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_check_target", check)
    error = assert_error(
        lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_uncertain", 5
    )
    assert "PRIVATE-PATH" not in str(error.envelope())
    assert target.exists() is (when != "before_link")
    if target.exists():
        assert api.verify_dataset(root, manifest=target).data.matches is True


@pytest.mark.parametrize("cancel", [KeyboardInterrupt, asyncio.CancelledError])
@pytest.mark.parametrize("attempted", [False, True])
def test_publication_cancel_preserves_distinct_sync_and_async_rules(
    tree, monkeypatch, cancel, attempted
):
    root, target = tree
    error = cancel()
    if attempted:
        original_link = os.link

        def interrupted(*a, **k):
            original_link(*a, **k)
            raise error

        monkeypatch.setattr(os, "link", interrupted)
        monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, interrupted})
        monkeypatch.setattr(
            os, "supports_follow_symlinks", {*os.supports_follow_symlinks, interrupted}
        )
    else:

        def interrupted(*a, **k):
            raise error

        monkeypatch.setattr(dataset_reports, "full_sync", interrupted)
    if cancel is KeyboardInterrupt and attempted:
        assert_error(
            lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_uncertain", 5
        )
    else:
        with pytest.raises(cancel) as caught:
            api.inspect_dataset(root, manifest_out=target)
        assert caught.value is error
        assert (
            MESSAGES["manifest_write_uncertain"] in getattr(error, "__notes__", ())
        ) is attempted
    assert target.exists() is attempted
    assert list(target.parent.glob(".yorunge-manifest-*.tmp")) == []


@pytest.mark.parametrize("stage", ["before", "after"])
def test_sigkill_leaves_only_stage_or_complete_target_and_never_auto_cleans(tree, stage):
    root, target = tree
    code = """
import os, signal, sys
from pathlib import Path
from yorunge import api
from yorunge.adapters.dataset_reports import DatasetManifestWriter
original = DatasetManifestWriter._publish_link
def kill(writer):
    if sys.argv[3] == "after": original(writer)
    os.kill(os.getpid(), signal.SIGKILL)
DatasetManifestWriter._publish_link = kill
api.inspect_dataset(Path(sys.argv[1]), manifest_out=Path(sys.argv[2]))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(root), str(target), stage],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == -signal.SIGKILL
    assert target.exists() is (stage == "after")
    remnants = list(target.parent.glob(".yorunge-manifest-*.tmp"))
    assert len(remnants) == 1
    assert stat.S_IMODE(remnants[0].stat().st_mode) == 0o600
    if stage == "after":
        assert api.verify_dataset(root, manifest=target).data.matches is True
        assert remnants[0].exists()
    else:
        api.inspect_dataset(root, manifest_out=target)
        assert remnants[0].exists()


def test_no_config_environment_state_resolution_for_real_api(tree, monkeypatch):
    root, target = tree

    def forbidden(*a, **k):
        pytest.fail("local dataset consulted config/environment/state")

    monkeypatch.setattr(api, "load_config", forbidden)
    monkeypatch.setattr(Path, "home", forbidden)
    monkeypatch.setattr(os.environ, "get", forbidden)
    api.inspect_dataset(root, manifest_out=target)
    assert api.verify_dataset(root, manifest=target).data.matches is True


@pytest.mark.parametrize(
    "failure,code,exit_code",
    [
        (BrokenPipeError, "output_closed", 6),
        (OSError, "output_write_failed", 1),
        (KeyboardInterrupt, "request_cancelled", 6),
    ],
)
def test_renderer_failure_after_api_success_preserves_complete_artifact(
    tree, monkeypatch, capsys, failure, code, exit_code
):
    from yorunge.cli.output import OutputRenderer

    root, target = tree

    def fail(*a, **k):
        raise failure()

    monkeypatch.setattr(OutputRenderer, "result", fail)
    assert (
        main(["datasets", "inspect", str(root), "--manifest-out", str(target), "--output=json"])
        == exit_code
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["code"] == code
    assert api.verify_dataset(root, manifest=target).data.matches is True


def test_cli_utf8_wire_does_not_depend_on_ascii_locale(tree):
    root, target = tree
    environment = dict(os.environ, LC_ALL="C", PYTHONIOENCODING="ascii")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "yorunge",
            "datasets",
            "inspect",
            str(root),
            "--manifest-out",
            str(target),
            "--output=json",
        ],
        capture_output=True,
        env=environment,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.decode("utf-8"))["data"]["manifest_path"] == str(target)
    assert result.stderr == b""


@pytest.mark.parametrize("which", ["root", "target"])
@pytest.mark.parametrize("unsafe", ["..", "control\x1b", "bidi\u202e", "surrogate\udcff"])
def test_unsafe_anchors_fail_before_filesystem_io(tree, monkeypatch, which, unsafe):
    root, target = tree
    argument = root.parent / unsafe
    root, target = (argument, target) if which == "root" else (root, argument)

    def denied(*a, **k):
        pytest.fail("unsafe anchor opened")

    monkeypatch.setattr(os, "open", denied)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, denied})
    assert_error(lambda: api.inspect_dataset(root, manifest_out=target), "input_invalid")


@pytest.mark.parametrize("after_link", [False, True])
def test_parent_swap_is_detected_and_does_not_publish_into_replacement(
    tree, monkeypatch, after_link
):
    root, _ = tree
    parent = root.parent / "reports"
    parent.mkdir()
    target = parent / "manifest.json"
    moved = root.parent / "old-reports"
    original = dataset_reports.DatasetManifestWriter._publish_link
    if after_link:

        def swap(writer):
            original(writer)
            parent.rename(moved)
            parent.mkdir()

        monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_publish_link", swap)
    else:
        original_check = dataset_reports.DatasetManifestWriter._check_stage

        def swap(writer, written):
            original_check(writer, written)
            parent.rename(moved)
            parent.mkdir()

        monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_check_stage", swap)
    error = assert_error(
        lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_uncertain", 5
    )
    assert error.envelope()["retryable"] is False
    assert not target.exists()
    # The swap immediately before link is an observed interval, not an atomic sandbox.
    # Any publication to the held old parent is reported as uncertain and stays complete.
    assert api.verify_dataset(root, manifest=moved / "manifest.json").data.matches is True


def test_stage_substitution_never_deletes_foreign_replacement(tree, monkeypatch):
    root, target = tree
    replacement = []
    original = dataset_reports.DatasetManifestWriter._check_stage

    def substitute(writer, written):
        path = writer.location.anchor.parent / writer.stage
        backup = path.with_suffix(".kept")
        path.rename(backup)
        path.write_bytes(b"other-owner")
        replacement.append(path)
        original(writer, written)

    monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_check_stage", substitute)
    assert_error(lambda: api.inspect_dataset(root, manifest_out=target), "input_changed")
    assert replacement[0].read_bytes() == b"other-owner"
    assert not target.exists()


@pytest.mark.parametrize("phase", ["pre", "post"])
def test_cleanup_io_cannot_mask_cancelled_error(tree, monkeypatch, phase):
    root, target = tree
    error = asyncio.CancelledError()
    original = dataset_reports.DatasetManifestWriter._publish_link

    def interrupt(writer):
        if phase == "post":
            original(writer)
        raise error

    def deny_unlink(*a, **k):
        raise OSError(errno.EIO, "PRIVATE-CLEANUP-PATH")

    monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_publish_link", interrupt)
    monkeypatch.setattr(os, "unlink", deny_unlink)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, deny_unlink})
    with pytest.raises(asyncio.CancelledError) as caught:
        api.inspect_dataset(root, manifest_out=target)
    assert caught.value is error
    assert all("PRIVATE" not in note for note in error.__notes__)
    assert (MESSAGES["manifest_write_uncertain"] in error.__notes__) is (phase == "post")


def test_postpublication_timeout_is_uncertain_and_artifact_remains_verifiable(tree, monkeypatch):
    root, target = tree
    original = dataset_reports.DatasetManifestWriter.publish

    def timeout(writer, manifest):
        original(writer, manifest)
        writer.location.budget.end = -1

    monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "publish", timeout)
    assert_error(
        lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_uncertain", 5
    )
    assert api.verify_dataset(root, manifest=target).data.matches is True


def test_outer_context_close_failure_cannot_report_success_after_link(tree, monkeypatch):
    root, target = tree
    original = os.close
    triggered = []

    def fail(fd):
        info = os.fstat(fd)
        original(fd)
        if target.exists() and stat.S_ISDIR(info.st_mode) and not triggered:
            triggered.append(1)
            raise OSError(errno.EIO, "PRIVATE-CLOSE-PATH")

    monkeypatch.setattr(os, "close", fail)
    assert_error(
        lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_uncertain", 5
    )
    assert triggered == [1]
    assert api.verify_dataset(root, manifest=target).data.matches is True


def test_summary_limit_counts_utf8_encoded_envelope_not_characters(tree, monkeypatch):
    from yorunge.domain.dataset_manifest import DatasetInspection
    from yorunge.domain.models import Result

    _, target = tree
    result = Result[DatasetInspection](
        data=DatasetInspection(
            schema_version=1,
            manifest_path=str(target.parent / "ö.json"),
            manifest_digest="0" * 64,
            file_count=0,
            total_bytes=0,
            unicode_version="15.0.0",
        ),
        warnings=("local_files_only",),
    )
    encoded = len(result.model_dump_json().encode("utf-8"))
    assert len(result.model_dump_json()) < encoded
    monkeypatch.setattr(policy, "MAX_SUMMARY_BYTES", encoded)
    datasets.check_summary(result)
    monkeypatch.setattr(policy, "MAX_SUMMARY_BYTES", encoded - 1)
    assert_error(lambda: datasets.check_summary(result), "dataset_limit_exceeded")


def test_real_task_cancel_before_sync_call_propagates_without_filesystem_action(tree):
    root, target = tree

    async def scenario():
        async def caller():
            await asyncio.sleep(0)
            api.inspect_dataset(root, manifest_out=target)

        task = asyncio.create_task(caller())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert not target.exists()


def test_to_thread_await_cancel_does_not_rollback_running_sync_publication(tree, monkeypatch):
    import threading

    root, target = tree
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    original = dataset_reports.DatasetManifestWriter._publish_link

    def paused(writer):
        entered.set()
        assert release.wait(5)
        original(writer)

    monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_publish_link", paused)

    async def scenario():
        def work():
            try:
                return api.inspect_dataset(root, manifest_out=target)
            finally:
                completed.set()

        task = asyncio.create_task(asyncio.to_thread(work))
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        try:
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not target.exists()
        finally:
            release.set()
        assert await asyncio.to_thread(completed.wait, 5)

    asyncio.run(scenario())
    assert api.verify_dataset(root, manifest=target).data.matches is True


@pytest.mark.parametrize("attempted", [False, True])
def test_cli_normalizes_real_keyboard_interrupt_at_publication_boundary(
    tree, monkeypatch, capsys, attempted
):
    root, target = tree
    if attempted:
        original = dataset_reports.DatasetManifestWriter._publish_link

        def interrupt(writer):
            original(writer)
            raise KeyboardInterrupt

        monkeypatch.setattr(dataset_reports.DatasetManifestWriter, "_publish_link", interrupt)
    else:

        def interrupt(*a):
            raise KeyboardInterrupt

        monkeypatch.setattr(dataset_reports, "full_sync", interrupt)
    assert main(
        ["datasets", "inspect", str(root), "--manifest-out", str(target), "--output=ndjson"]
    ) == (5 if attempted else 6)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["code"] == (
        "manifest_write_uncertain" if attempted else "request_cancelled"
    )
    assert target.exists() is attempted


def test_real_closed_stdout_pipe_after_durable_publish_keeps_artifact(tree):
    root, target = tree
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-m",
            "yorunge",
            "datasets",
            "inspect",
            str(root),
            "--manifest-out",
            str(target),
            "--output=json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    process.stdout.close()
    process.stdout = None
    _, stderr = process.communicate(timeout=10)
    assert process.returncode == 6
    assert json.loads(stderr)["code"] == "output_closed"
    assert b"Traceback" not in stderr
    assert api.verify_dataset(root, manifest=target).data.matches is True


@pytest.mark.parametrize("failure", [OSError, KeyboardInterrupt, asyncio.CancelledError])
def test_first_stage_identity_failure_preserves_unknown_name_without_unsafe_unlink(
    tree, monkeypatch, failure
):
    root, target = tree
    original_open, original_fstat = os.open, os.fstat
    stage_descriptors = set()
    error = failure()

    def opening(path, *a, **k):
        descriptor = original_open(path, *a, **k)
        if isinstance(path, str) and path.startswith(".yorunge-manifest-"):
            stage_descriptors.add(descriptor)
        return descriptor

    def failed_identity(descriptor):
        if descriptor in stage_descriptors:
            raise error
        return original_fstat(descriptor)

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, opening})
    monkeypatch.setattr(os, "fstat", failed_identity)
    if failure is OSError:
        assert_error(
            lambda: api.inspect_dataset(root, manifest_out=target), "manifest_write_failed"
        )
    else:
        with pytest.raises(failure) as caught:
            api.inspect_dataset(root, manifest_out=target)
        assert caught.value is error
        assert MESSAGES["manifest_write_uncertain"] not in getattr(error, "__notes__", ())
    assert not target.exists()
    remnants = list(target.parent.glob(".yorunge-manifest-*.tmp"))
    assert len(remnants) == 1
    assert remnants[0].read_bytes() == b""
    assert stat.S_IMODE(remnants[0].stat().st_mode) == 0o600


def test_shell_quote_growth_cannot_expand_text_summary_over_limit(tree, capsys):
    root, target = tree
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for number in range(18):
            name = str(number) + "'" * 188
            os.mkdir(name, dir_fd=descriptor)
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            root /= name
    finally:
        os.close(descriptor)
    assert main(["datasets", "inspect", str(root), "--manifest-out", str(target)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len(captured.out.encode("utf-8")) <= policy.MAX_SUMMARY_BYTES
    assert "yorunge datasets verify ROOT --manifest FILE" in captured.out
    assert str(target) in captured.out
    assert api.verify_dataset(root, manifest=target).data.matches is True


def test_text_boundary_includes_renderer_lf(capsys):
    from argparse import Namespace

    from yorunge.cli import dataset_text_result
    from yorunge.cli.output import OutputRenderer
    from yorunge.domain.dataset_manifest import DatasetInspection
    from yorunge.domain.models import Result

    data = DatasetInspection(
        schema_version=1,
        manifest_path="/tmp/manifest.json",
        manifest_digest="0" * 64,
        file_count=0,
        total_bytes=0,
        unicode_version="15.0.0",
    )
    root = Path("/tmp") / "/".join("'" * 200 for _ in range(16))
    args = Namespace(root=root)
    initial = dataset_text_result(args, data)
    # Make the complete quoted body exactly 16KiB; LF must still fit the output budget.
    padding = policy.MAX_SUMMARY_BYTES - len(initial.encode("utf-8"))
    assert 1 < padding < 255
    args.root = root / ("a" * (padding - 1))
    text = dataset_text_result(args, data)
    OutputRenderer("text").result(Result(data=data), text=text)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len(captured.out.encode("utf-8")) <= policy.MAX_SUMMARY_BYTES
    assert "verify ROOT --manifest FILE" in captured.out


@pytest.mark.parametrize("name", ["--manifest-out", "--output", "--non-interactive"])
def test_option_terminator_preserves_legal_positional_directory_names(
    tree, monkeypatch, capsys, name
):
    root, target = tree
    monkeypatch.chdir(root.parent)
    selected = root.parent / name
    selected.mkdir()
    assert (
        main(["datasets", "inspect", "--manifest-out", str(target), "--output=json", "--", name])
        == 0
    )
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["data"]["file_count"] == 0
    assert api.verify_dataset(selected, manifest=target).data.matches is True
