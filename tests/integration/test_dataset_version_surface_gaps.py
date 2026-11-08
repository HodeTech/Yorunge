"""Tests that kill the mutants the first review round of P02-3q (reviewer B) left alive.

Placed next to the surface tests; reuses their fixtures and helpers.
"""

import errno
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.version_network import loopback_versions
from tests.integration.test_binding_files import binding as held_binding
from tests.integration.test_binding_files import code_of
from tests.integration.test_binding_files import place as place
from tests.integration.test_dataset_version_reader import (
    BASE,
    DATASET,
    body,
    detail,
    listing,
    row,
    splits,
)
from tests.integration.test_dataset_version_surface import (
    CONSOLE,
    ENV,
    bind,
    check,
    execute,
    flags,
    manifest_file,
    parsed,
    popen,
    routes,
)
from tests.integration.test_dataset_version_surface import certificates as certificates
from tests.integration.test_dataset_version_surface import workspace as workspace
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api
from yorunge.adapters import artifact_publisher, binding_files, dataset_version_api, small_files
from yorunge.adapters.binding_files import binding_target
from yorunge.adapters.small_files import read_regular_file
from yorunge.adapters.target_directory import TargetDirectory, open_target_directory
from yorunge.domain.credentials import ServiceTarget
from yorunge.domain.errors import YorungeError

# ---------------------------------------------------------------------------------------------
# arguments are judged before the key or the state is touched (kills the API-level mutants)
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call",
    [
        lambda c: api.list_dataset_versions(5, **c),
        lambda c: api.list_dataset_versions(None, **c),
        lambda c: api.list_dataset_versions("11111111-1111-4111-8111-111111111111", page=True, **c),
        lambda c: api.list_dataset_versions(
            "11111111-1111-4111-8111-111111111111", page=10001, **c
        ),
        lambda c: api.show_dataset_version("11111111-1111-4111-8111-111111111111", "a b", **c),
        lambda c: api.show_dataset_version("11111111-1111-4111-8111-111111111111", "..", **c),
    ],
    ids=["id-int", "id-none", "page-bool", "page-10001", "tag-space", "tag-dotdot"],
)
def test_a_refused_argument_is_refused_before_the_key_is_read(workspace, monkeypatch, call):
    state, config, _ = workspace
    monkeypatch.delenv(ENV)  # a key that cannot be read must not be what is reported
    with pytest.raises(YorungeError) as error:
        call({"config": config, "state_dir": state})
    assert error.value.code == "invalid_request"


def test_the_last_page_is_a_valid_argument(workspace, monkeypatch):
    state, config, _ = workspace
    monkeypatch.delenv(ENV)
    with pytest.raises(YorungeError) as error:  # judged fine; the missing key is what stops it
        api.list_dataset_versions(DATASET, page=10_000, config=config, state_dir=state)
    assert error.value.code == "credential_unavailable"


def test_the_budget_of_one_use_is_thirty_seconds():
    use = dataset_version_api._Composition(lambda: None, None)  # type: ignore[arg-type]
    assert dataset_version_api.VERSION_SECONDS == 30.0
    assert use.deadline - use.started == 30.0


# ---------------------------------------------------------------------------------------------
# --page, relative paths, the warnings of bind, a missing tag (CLI processes)
# ---------------------------------------------------------------------------------------------


def test_list_asks_for_the_page_it_was_given_and_the_last_page_is_allowed(workspace, certificates):
    page2 = listing([], page=2, page_size=20, total=21, has_next=False)
    page2["data"] = [row(id="33333333-3333-4333-8333-333333333333", version_tag="v21")]
    table = routes(
        **{
            BASE + "?page=2": body(page2),
            BASE + "?page=10000": body(listing([], page=10000, total=0)),
        }
    )
    with TlsServer(certificates, table) as server:
        two = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            "--page",
            "2",
            "--output",
            "json",
            *flags(workspace),
        )
        last = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            "--page",
            "10000",
            "--output",
            "json",
            *flags(workspace),
        )
    assert parsed(two)["data"]["page"] == 2
    assert parsed(last)["data"]["page"] == 10_000
    assert [r.path for r in server.requests] == [BASE + "?page=2", BASE + "?page=10000"]


def run_in(cwd, server, certificates, *args):
    env = dict(os.environ, LC_ALL="C", PYTHONIOENCODING="ascii", PYTHONUTF8="0")
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-W",
            "error",
            str(CONSOLE),
            "--ca",
            str(certificates[0]),
            "--port",
            str(server.port),
            "--",
            *args,
        ],
        env=env,
        capture_output=True,
        timeout=60,
        cwd=cwd,
    )


def test_relative_paths_are_anchored_at_the_working_directory_and_reported_absolute(
    workspace, certificates
):
    state, config, directory = workspace
    directory = directory.resolve()
    (directory / "m.json").write_bytes(manifest_file(10).encoded())
    with TlsServer(certificates, routes()) as server:
        made = run_in(
            directory,
            server,
            certificates,
            "datasets",
            "versions",
            "bind",
            "--dataset-id",
            DATASET,
            "--version-tag",
            "v1",
            "--binding-out",
            "b.json",
            "--manifest",
            "m.json",
            "--output",
            "json",
            "--config",
            str(config),
            "--state-dir",
            str(state),
        )
        summary = parsed(made)["data"]
        assert summary["binding_path"] == str(directory / "b.json")
        assert summary["local_manifest"]["relation"] == "count_matches"
        again = run_in(
            directory,
            server,
            certificates,
            "datasets",
            "versions",
            "check",
            "--binding",
            "b.json",
            "--output",
            "json",
            "--config",
            str(config),
            "--state-dir",
            str(state),
        )
        assert parsed(again)["data"]["result"] == "unchanged"


def test_a_binding_without_a_split_skew_says_only_that_it_is_metadata(workspace, certificates):
    state, config, directory = workspace
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            bound = api.bind_dataset_version(
                DATASET, "v1", binding_out=directory / "b.json", config=config, state_dir=state
            )
    assert bound.warnings == ("provider_metadata_only",)


def test_bind_of_a_tag_the_provider_does_not_have_is_not_found_and_makes_no_file(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    table = routes(**{BASE + "/v1": Reply(status=404, body=b"{}")})
    with TlsServer(certificates, table) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "dataset_version_not_found"
    assert [r.path for r in server.requests] == [BASE + "/v1"]
    assert not out.exists()
    assert not list(out.parent.glob(".yorunge-binding-*"))


def test_nothing_is_linked_when_the_report_cannot_be_made(workspace, certificates, monkeypatch):
    state, config, directory = workspace
    out = directory / "b.json"

    def refusing(*args, **keywords):
        raise ValueError("the report is refused")

    monkeypatch.setattr(dataset_version_api, "bound_summary", refusing)
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            with pytest.raises(ValueError):
                api.bind_dataset_version(
                    DATASET, "v1", binding_out=out, config=config, state_dir=state
                )
    assert not out.exists()
    assert not list(directory.glob(".yorunge-binding-*"))


def test_a_manifest_over_the_byte_limit_is_a_manifest_error_before_the_provider_is_asked(
    workspace, certificates
):
    out, directory = workspace[2] / "binding.json", workspace[2]
    (directory / "m.json").write_bytes(b" " * (8 * 1024**2 + 1))
    with TlsServer(certificates, routes()) as server:
        process = bind(
            server, certificates, workspace, out, "--manifest", str(directory / "m.json")
        )
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "manifest_invalid"
    assert server.requests == []


@pytest.mark.parametrize(
    "arguments",
    [
        ("--binding-out", "/tmp/second.json"),
        ("--version-tag", "v2"),
        ("--manifest", "/tmp/a", "--manifest", "/tmp/b"),
        ("--state-dir", "/tmp/s"),
        ("--config", "/tmp/c"),
        ("--profile", "test", "--profile", "test"),
        ("--output", "text"),
        ("--non-interactive", "--non-interactive"),
    ],
)
def test_bind_refuses_every_repeated_option(workspace, certificates, arguments):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out, *arguments)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"
    assert server.requests == []
    assert not out.exists()


def test_check_refuses_a_repeated_binding(workspace, certificates):
    with TlsServer(certificates, routes()) as server:
        process = check(server, certificates, workspace, "/tmp/x", "--binding", "/tmp/y")
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"


@pytest.mark.parametrize(
    "command",
    [
        ("list",),
        ("show", "--dataset-id", DATASET),
        ("bind", "--dataset-id", DATASET, "--version-tag", "v1"),
        ("check",),
    ],
)
def test_a_required_option_that_is_missing_is_a_usage_error_and_asks_nothing(
    workspace, certificates, command
):
    with TlsServer(certificates, routes()) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            *command,
            "--output",
            "json",
            *flags(workspace),
        )
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"
    assert server.requests == []


# ---------------------------------------------------------------------------------------------
# the text of list, bind and check (no test reads it today)
# ---------------------------------------------------------------------------------------------


def text_of(process):
    assert process.returncode == 0, process.stderr
    return process.stdout.decode("utf-8")


def test_the_text_of_list_shows_rows_frozenness_and_the_next_page(workspace, certificates):
    page = listing(
        [row(), row(id="33333333-3333-4333-8333-333333333333", version_tag="v2", is_frozen=False)],
        page_size=2,
        total=5,
        has_next=True,
    )
    with TlsServer(certificates, routes(**{BASE + "?page=1": body(page)})) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            *flags(workspace),
        )
    text = text_of(process)
    first = next(line for line in text.splitlines() if line.startswith("- v1 ("))
    second = next(line for line in text.splitlines() if line.startswith("- v2 ("))
    assert "dondurulmuş" in first
    assert "DONDURULMAMIŞ" not in first
    assert "DONDURULMAMIŞ" in second
    assert "Sonraki sayfa var (--page 2)." in text
    assert "toplam 5" in text


def test_the_text_of_an_empty_page_says_so_and_has_no_next_page(workspace, certificates):
    page = listing([], page=1, total=0)
    with TlsServer(certificates, routes(**{BASE + "?page=1": body(page)})) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            *flags(workspace),
        )
    text = text_of(process)
    assert "Bu sayfada sürüm yok." in text
    assert "Sonraki sayfa" not in text


def test_the_text_of_show_names_a_partial_version_and_a_skewed_split_total(workspace, certificates):
    skewed = {"train": 6, "val": 2, "test": 1, "unassigned": 0}
    table = routes(
        **{
            BASE + "/v1": body(detail(is_partial=True, split_config=skewed)),
            BASE + "/v1/splits": body(splits(unassigned=0)),
        }
    )
    with TlsServer(certificates, table) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "show",
            "--dataset-id",
            DATASET,
            "--version-tag",
            "v1",
            *flags(workspace),
        )
    text = text_of(process)
    assert "KISMİ" in text
    assert "bölme sayıları toplamı öğe sayısından farklı" in text
    # and the plain case says neither
    with TlsServer(certificates, routes()) as server:
        plain = text_of(
            execute(
                server,
                certificates,
                "datasets",
                "versions",
                "show",
                "--dataset-id",
                DATASET,
                "--version-tag",
                "v1",
                *flags(workspace),
            )
        )
    assert "is_partial: hayır" in plain
    assert "KISMİ" not in plain
    assert "farklı" not in plain


@pytest.mark.parametrize("count,phrase", [(10, "sayısıyla aynı"), (9, "FARKLI")])
def test_the_text_of_bind_quotes_the_check_command_and_states_the_manifest_relation(
    workspace, certificates, count, phrase
):
    out = workspace[2] / "my binding's.json"
    manifest = workspace[2] / "m.json"
    manifest.write_bytes(manifest_file(count).encoded())
    with TlsServer(certificates, routes()) as server:
        process = bind(
            server, certificates, workspace, out, "--manifest", str(manifest), output="text"
        )
    text = text_of(process)
    assert f"Sürüm bağı kaydedildi: {out}" in text
    assert phrase in text
    import shlex

    assert (
        "Denetle: "
        + shlex.join(["yorunge", "datasets", "versions", "check", "--binding", str(out)])
        in text
    )
    assert "farklı" not in text.replace("FARKLI", "")  # no skew warning here


def test_the_text_of_bind_warns_about_a_partial_version_and_a_split_skew(workspace, certificates):
    skewed = {"train": 6, "val": 2, "test": 1, "unassigned": 0}
    table = routes(
        **{
            BASE + "/v1": body(detail(is_partial=True, split_config=skewed)),
            BASE + "/v1/splits": body(splits(unassigned=0)),
        }
    )
    out = workspace[2] / "b.json"
    with TlsServer(certificates, table) as server:
        text = text_of(bind(server, certificates, workspace, out, output="text"))
    assert "kısmi (is_partial)" in text
    assert "bölme sayıları toplamı öğe sayısından farklı" in text


def test_the_text_of_check_says_unchanged_and_only_provider_metadata(workspace, certificates):
    out = workspace[2] / "b.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        text = text_of(check(server, certificates, workspace, out, output="text"))
    assert text.startswith("Değişmedi: v1 (")
    assert "Yalnız sağlayıcı metadata'sı karşılaştırıldı" in text


# ---------------------------------------------------------------------------------------------
# sentinels for bind: an interrupt before the link leaves nothing; a closed stdout after it
# leaves the binding
# ---------------------------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_an_interrupt_while_bind_waits_for_the_provider_leaves_no_file_and_no_stage(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    # The interrupt ends the wait at once; the delay only has to outlast a slow test machine.
    table = routes(
        **{BASE + "/v1/splits": Reply(body=json.dumps(splits()).encode(), header_delay=30)}
    )
    with TlsServer(certificates, table) as server:
        process = popen(
            server,
            certificates,
            workspace,
            "datasets",
            "versions",
            "bind",
            "--dataset-id",
            DATASET,
            "--version-tag",
            "v1",
            "--binding-out",
            str(out),
            "--output=json",
            *flags(workspace),
        )
        try:
            end = time.monotonic() + 20
            while len(server.requests) < 2 and time.monotonic() < end:
                time.sleep(0.02)
            assert len(server.requests) == 2
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=20)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert process.returncode == 6
    assert stdout == b""
    assert json.loads(stderr)["code"] == "request_cancelled"
    assert (
        sorted(p.name for p in out.parent.iterdir() if p.name.startswith(("binding", ".yorunge")))
        == []
    )


def test_a_closed_stdout_after_bind_linked_leaves_a_whole_binding_and_the_rerun_says_so(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        process = popen(
            server,
            certificates,
            workspace,
            "datasets",
            "versions",
            "bind",
            "--dataset-id",
            DATASET,
            "--version-tag",
            "v1",
            "--binding-out",
            str(out),
            "--output=json",
            *flags(workspace),
        )
        assert process.stdout is not None
        process.stdout.close()
        try:
            assert process.wait(timeout=30) == 6
            stderr = process.stderr.read()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stderr.close()
        assert json.loads(stderr)["code"] == "output_closed"
        from yorunge.domain.dataset_version import decode_binding

        decode_binding(
            out.read_bytes()
        )  # whole: the link had happened, the report could not be written
        again = bind(server, certificates, workspace, out)
    assert json.loads(again.stderr)["code"] == "binding_output_exists"


# ---------------------------------------------------------------------------------------------
# the small-file reader and the binding target (in process)
# ---------------------------------------------------------------------------------------------


def swapped_at_open(monkeypatch, victim, how):
    other = victim.parent / "other.json"
    other.write_bytes(b"y" * 20)
    real = os.open
    done = []

    def opener(path, flags_, *a, **k):
        if (
            path == victim.name
            and flags_ & os.O_NOFOLLOW
            and not flags_ & os.O_DIRECTORY
            and not done
        ):
            done.append(1)
            victim.unlink()
            if how == "fifo":
                os.mkfifo(victim)
            elif how == "symlink":
                os.symlink(other, victim)
            elif how == "directory":
                victim.mkdir()
            else:
                victim.write_bytes(b"z" * 20)
        return real(path, flags_, *a, **k)

    os.supports_dir_fd.add(opener)
    monkeypatch.setattr(os, "open", opener)
    return opener


@pytest.mark.parametrize(
    "how,code",
    [
        ("fifo", "input_changed"),
        ("symlink", "input_invalid"),
        ("directory", "input_changed"),
        ("file", "input_changed"),
    ],
)
def test_a_file_swapped_between_the_look_and_the_open_is_not_read_and_does_not_block(
    place, monkeypatch, how, code
):
    victim = place / "a.json"
    victim.write_bytes(b"x" * 20)
    opener = swapped_at_open(monkeypatch, victim, how)
    box = []
    worker = threading.Thread(
        target=lambda: box.append(
            code_of(lambda: read_regular_file(victim, limit=100, oversize="binding_invalid"))
        ),
        daemon=True,
    )
    worker.start()
    worker.join(10)
    os.supports_dir_fd.discard(opener)
    assert box == [code], "a FIFO swapped in must not block the open"


def test_a_parent_swapped_after_the_file_was_read_is_not_the_file_that_was_read(place, monkeypatch):
    inner = place / "d"
    inner.mkdir()
    victim = inner / "a.json"
    victim.write_bytes(b"x" * 20)
    real, seen = small_files.directory_chain, []

    def swapping(anchor):
        seen.append(anchor)
        if len(seen) == 2:
            inner.rename(place / "d.moved")
            inner.mkdir()
            (inner / "a.json").write_bytes(b"x" * 20)
        return real(anchor)

    monkeypatch.setattr(small_files, "directory_chain", swapping)
    assert (
        code_of(lambda: read_regular_file(victim, limit=100, oversize="binding_invalid"))
        == "input_changed"
    )


def test_a_file_at_the_limit_that_grows_past_it_while_it_is_read_is_oversize(place, monkeypatch):
    path = place / "a.json"
    path.write_bytes(b"x" * 100)
    real, first = os.read, []

    def growing(descriptor, count):
        data = real(descriptor, count)
        if not first:
            first.append(1)
            with path.open("ab") as handle:
                handle.write(b"y")
        return data

    monkeypatch.setattr(small_files.os, "read", growing)
    assert (
        code_of(lambda: read_regular_file(path, limit=100, oversize="binding_invalid"))
        == "binding_invalid"
    )


def test_the_default_deadline_of_a_small_file_read_is_five_seconds():
    import inspect

    assert inspect.signature(read_regular_file).parameters["seconds"].default == 5.0


def test_a_name_with_a_nul_byte_is_a_closed_error_not_a_value_error(place):
    for action in (
        lambda: read_regular_file(Path(str(place) + "/a\0b"), limit=10, oversize="binding_invalid"),
    ):
        assert code_of(action) == "input_invalid"


def test_a_name_longer_than_the_file_system_allows_is_said_before_the_provider_is_asked(place):
    with binding_target(place / ("n" * 256)) as target:
        assert code_of(target.require_absent) == "binding_write_failed"


def test_a_dangling_symlink_is_a_taken_name_and_is_said_early(place):
    (place / "b.json").symlink_to(place / "nowhere")
    with binding_target(place / "b.json") as target:
        assert code_of(target.require_absent) == "binding_output_exists"


def test_a_directory_that_is_gone_is_a_closed_recheck_error(place):
    inner = place / "inner"
    inner.mkdir()
    directory = open_target_directory(
        inner / "x.json", invalid="binding_write_failed", failed="binding_write_failed"
    )
    try:
        inner.rmdir()
        assert code_of(directory.recheck) == "binding_write_failed"
    finally:
        directory.close()


@pytest.mark.parametrize(
    "error", [OSError(errno.EIO, "x"), UnicodeEncodeError("utf-8", "\udcff", 0, 1, "x")]
)
def test_an_os_or_unicode_error_of_the_block_before_the_link_is_write_failed(place, error):
    with pytest.raises(YorungeError) as raised:
        with binding_target(place / "b.json"):
            raise error
    assert raised.value.code == "binding_write_failed"


def test_a_stage_that_is_not_what_was_written_is_write_failed_and_leaves_nothing(
    place, monkeypatch
):
    real = binding_files.BindingWriter._sync

    def tampering(self, descriptor):
        real(self, descriptor)
        os.fchmod(descriptor, 0o644)

    monkeypatch.setattr(binding_files.BindingWriter, "_sync", tampering)
    with pytest.raises(YorungeError) as raised:
        with binding_target(place / "b.json") as target:
            target.publish(held_binding())
    assert raised.value.code == "binding_write_failed"
    assert list(place.iterdir()) == []


def test_the_stage_of_a_binding_is_named_for_a_binding(place, monkeypatch):
    names = []
    real = artifact_publisher.ArtifactPublisher._publish_link

    def spy(self):
        names.extend(p.name for p in place.iterdir())
        return real(self)

    monkeypatch.setattr(artifact_publisher.ArtifactPublisher, "_publish_link", spy)
    with binding_target(place / "b.json") as target:
        target.publish(held_binding())
    assert len(names) == 1
    assert names[0].startswith(".yorunge-binding-")
    assert names[0].endswith(".tmp")


def test_the_directory_handle_of_a_target_is_closed_on_every_path(place, monkeypatch):
    opened, closed = [], []
    real_open, real_close = binding_files.open_target_directory, TargetDirectory.close

    def opening(*arguments, **keywords):
        handle = real_open(*arguments, **keywords)
        opened.append(handle.descriptor)
        return handle

    def closing(self, primary=None):
        closed.append(self.descriptor)
        real_close(self, primary)

    monkeypatch.setattr(binding_files, "open_target_directory", opening)
    monkeypatch.setattr(TargetDirectory, "close", closing)
    bodies = (
        lambda target: None,
        lambda target: target.publish(held_binding()),
        lambda target: (_ for _ in ()).throw(YorungeError("remote_failed")),
    )
    for number, body_ in enumerate(bodies):
        try:
            with binding_target(place / f"b{number}.json") as target:
                body_(target)
        except YorungeError:
            pass
    assert len(opened) == len(bodies)
    assert closed == opened  # every path let go of its handle


def test_a_use_leaves_no_descriptor_and_no_thread_behind(workspace, certificates):
    state, config, directory = workspace
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            api.show_dataset_version(DATASET, "v1", config=config, state_dir=state)
            before = (len(os.listdir("/dev/fd")), threading.active_count())
            for _ in range(5):
                api.show_dataset_version(DATASET, "v1", config=config, state_dir=state)
            after = (len(os.listdir("/dev/fd")), threading.active_count())
    assert after == before


# ---------------------------------------------------------------------------------------------
# a unit test of the four uses on fakes (application/dataset_versions.py has none today)
# ---------------------------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402

from tests.contracts.test_dataset_version import SERVICE, observation  # noqa: E402
from yorunge.application import dataset_versions  # noqa: E402
from yorunge.domain.dataset_manifest import DatasetFile, build_manifest  # noqa: E402
from yorunge.domain.dataset_version import bind as make_binding  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 100.0

    def now(self):
        from datetime import UTC, datetime

        return datetime(2026, 11, 8, 12, 0, 0, tzinfo=UTC)

    def monotonic(self):
        return self.t


class Port:
    def __init__(self, shown):
        self.calls, self.shown = [], shown

    def versions(self, dataset_id, page, *, deadline):
        self.calls.append(("versions", dataset_id, page, deadline))
        return "PAGE"

    def version(self, dataset_id, tag, *, deadline, absent):
        self.calls.append(("version", dataset_id, tag, deadline, absent))
        return self.shown


def fakes(shown, target=SERVICE):
    clock, port = Clock(), Port(shown)
    snapshot = SimpleNamespace(
        context=SimpleNamespace(profile="p", account_id=None, project_id=None),
        credential=SimpleNamespace(target=target, secret=SimpleNamespace(reveal=lambda: "k" * 20)),
        preference=None,
    )

    class State:
        def capture(self, *, deadline):
            return snapshot

        def finish(self, snapshot_, *, deadline):
            return "validated"

    class Observer:
        def __init__(self, operation):
            self.operation = operation

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

        def observe(self, snapshot_, *, deadline):
            return self.operation(port, snapshot_, deadline)

    return State(), Observer, clock, port


def test_each_use_asks_the_reader_for_the_codes_and_the_reserve_it_owes():
    shown = observation()
    state, observer, clock, port = fakes(shown)
    outer = clock.t + 30.0
    network = outer - 5.0  # exchange reserves min(5, remaining / 3) for the final store check
    dataset_versions.show_version(
        state, observer, clock, dataset_id="d", version_tag="t", deadline=outer
    )
    dataset_versions.bind_version(
        state, observer, clock, dataset_id="d", version_tag="t", manifest=None, deadline=outer
    )
    dataset_versions.list_versions(state, observer, clock, dataset_id="d", page=7, deadline=outer)
    held = make_binding(shown, SERVICE)
    dataset_versions.check_binding(state, observer, clock, binding=held, deadline=outer)
    assert port.calls == [
        ("version", "d", "t", network, "dataset_version_not_found"),
        ("version", "d", "t", network, "dataset_version_not_found"),
        ("versions", "d", 7, network),
        ("version", held.dataset_id, held.version_tag, network, "dataset_version_missing"),
    ]


def test_check_compares_the_provider_before_it_reads_anything():
    shown = observation()
    other = ServiceTarget(service_origin="https://other.example.org", api_base_path="/api/v1")
    state, observer, clock, port = fakes(shown, target=other)
    held = make_binding(shown, SERVICE)
    with pytest.raises(YorungeError) as error:
        dataset_versions.check_binding(state, observer, clock, binding=held, deadline=clock.t + 30)
    assert error.value.code == "state_changed"
    assert port.calls == []


def test_bind_records_the_digest_and_count_of_the_manifest_it_was_given():
    shown = observation()
    state, observer, clock, port = fakes(shown)
    manifest = build_manifest(
        tuple(DatasetFile(path=f"f{i}", size=1, sha256=f"{i:02x}" * 32) for i in range(10))
    )
    held = dataset_versions.bind_version(
        state,
        observer,
        clock,
        dataset_id="d",
        version_tag="t",
        manifest=manifest,
        deadline=clock.t + 30,
    )
    assert held.local_manifest.digest == manifest.digest
    assert held.local_manifest.relation == "count_matches"


# ---------------------------------------------------------------------------------------------
# a few more: nameless target, a name replaced after the read, context options reach the loader
# ---------------------------------------------------------------------------------------------


def test_a_binding_out_without_a_name_is_a_mistake_before_anything_else(workspace, certificates):
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, "/")
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"
    assert server.requests == []


def test_a_name_replaced_after_the_read_is_not_the_file_that_was_read(place, monkeypatch):
    path = place / "a.json"
    path.write_bytes(b"x" * 20)
    other = place / "other.json"
    other.write_bytes(b"x" * 20)
    real, calls = os.stat, []

    def stat(name, *a, **k):
        calls.append(name)
        if name == "a.json" and calls.count("a.json") == 2:  # the look at the name after the read
            os.replace(other, path)
        return real(name, *a, **k)

    os.supports_dir_fd.add(stat)
    monkeypatch.setattr(small_files.os, "stat", stat)
    try:
        assert (
            code_of(lambda: read_regular_file(path, limit=100, oversize="binding_invalid"))
            == "input_changed"
        )
    finally:
        os.supports_dir_fd.discard(stat)


@pytest.mark.parametrize("name", ["list", "show", "bind"])
def test_profile_and_config_reach_the_loader_of_every_public_function(workspace, monkeypatch, name):
    state, config, directory = workspace
    seen = []

    def recording(config_, request, other):
        seen.append((config_, request.profile, request.project))  # a read needs no project
        raise YorungeError("invalid_request")  # stop here: only the wiring is looked at

    monkeypatch.setattr(api, "_context", recording)
    calls = {
        "list": lambda kw: api.list_dataset_versions(DATASET, **kw),
        "show": lambda kw: api.show_dataset_version(DATASET, "v1", **kw),
        "bind": lambda kw: api.bind_dataset_version(
            DATASET, "v1", binding_out=directory / "b.json", **kw
        ),
    }
    with pytest.raises(YorungeError):
        calls[name]({"config": config, "profile": "elsewhere", "state_dir": state})
    assert seen == [(config, "elsewhere", None)]


@pytest.mark.parametrize("bad", [{"config": "config.toml"}, {"state_dir": "state"}])
def test_a_config_or_state_dir_that_is_not_a_path_is_invalid_request(workspace, bad):
    state, config, _ = workspace
    arguments = {"config": config, "state_dir": state, **bad}
    with pytest.raises(YorungeError) as error:
        api.list_dataset_versions(DATASET, **arguments)
    assert error.value.code == "invalid_request"


def test_the_report_of_bind_says_what_the_file_says(workspace, certificates):
    out, directory = workspace[2] / "binding.json", workspace[2]
    skewed = {"train": 6, "val": 2, "test": 1, "unassigned": 0}
    manifest = directory / "m.json"
    manifest.write_bytes(manifest_file(9).encoded())
    table = routes(
        **{
            BASE + "/v1": body(detail(is_partial=True, split_config=skewed)),
            BASE + "/v1/splits": body(splits(unassigned=0)),
        }
    )
    with TlsServer(certificates, table) as server:
        report = parsed(bind(server, certificates, workspace, out, "--manifest", str(manifest)))[
            "data"
        ]
    held = json.loads(out.read_text())
    for field in (
        "dataset_id",
        "version_id",
        "version_tag",
        "is_partial",
        "split_total_matches_item_count",
        "observed_at",
        "local_manifest",
    ):
        assert report[field] == held[field], field
    assert report["binding_digest"] == held["digest"]
    assert report["binding_path"] == str(out)
    assert report["is_partial"] is True
    assert report["split_total_matches_item_count"] is False


def test_the_report_of_a_binding_accepts_a_path_up_to_the_byte_limit():
    from yorunge.domain.dataset_version import bound_summary

    longest = "/" + "x" * 4095  # 4096 bytes: what is_reportable_path allows
    report = bound_summary(make_binding(observation(), SERVICE), longest)
    assert report.binding_path == longest


def test_list_refuses_a_page_with_a_trailing_newline(workspace, certificates):
    with TlsServer(certificates, routes()) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            "--page",
            "1\n",
            "--output",
            "json",
            *flags(workspace),
        )
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"
    assert server.requests == []


def test_a_working_directory_that_is_gone_makes_a_relative_path_input_invalid(
    tmp_path, monkeypatch
):
    gone = tmp_path / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    gone.rmdir()
    with pytest.raises(YorungeError) as error:
        api.check_dataset_version(Path("b.json"))
    assert error.value.code == "input_invalid"
