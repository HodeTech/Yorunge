"""What round two of P02-3q found left unpinned: the root's project, the held directory, signals.

Each test passes on the fixed tree and fails on the tree it was written against: a project given at
the root of the command line used to be dropped, the close of the held directory had no test at
all, the card's "two binds give the same digest" and "SIGINT inside the publication is 5, after it
6" had no process-level test, and the list text hid two flags that `show` and `bind` print.
"""

import asyncio
import errno
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.http_server import TlsServer
from tests.integration.test_binding_files import binding as held_binding
from tests.integration.test_dataset_version_reader import BASE, DATASET, body, listing, row
from tests.integration.test_dataset_version_surface import (
    bind,
    execute,
    flags,
    parsed,
    routes,
)
from tests.integration.test_dataset_version_surface import certificates as certificates
from tests.integration.test_dataset_version_surface import workspace as workspace
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge.adapters.binding_files import binding_target
from yorunge.adapters.download_sink import open_sink
from yorunge.domain.download_response import DownloadResponse
from yorunge.domain.errors import MESSAGES, YorungeError

SIGNAL_CONSOLE = Path(__file__).parents[1] / "fixtures" / "version_signal_console.py"
PROJECT = "00000000-0000-4000-8000-000000000004"


# --- a project is refused wherever it is given ----------------------------------------------------


@pytest.mark.parametrize("position", ["root", "subcommand"])
@pytest.mark.parametrize("action", ["list", "show", "bind", "check"])
def test_a_project_is_refused_wherever_it_is_given_not_dropped(
    workspace, certificates, action, position
):
    _, _, directory = workspace
    arguments = {
        "list": ["list", "--dataset-id", DATASET],
        "show": ["show", "--dataset-id", DATASET, "--version-tag", "v1"],
        "bind": [
            "bind",
            "--dataset-id",
            DATASET,
            "--version-tag",
            "v1",
            "--binding-out",
            str(directory / "b.json"),
        ],
        "check": ["check", "--binding", str(directory / "missing.json")],
    }[action]
    with TlsServer(certificates, routes()) as server:
        project = ["--project", PROJECT]
        process = execute(
            server,
            certificates,
            *(project if position == "root" else []),
            "datasets",
            "versions",
            *arguments,
            *(project if position == "subcommand" else []),
            *flags(workspace),
            "--output",
            "json",
        )
        assert process.returncode == 2
        assert process.stdout == b""
        assert json.loads(process.stderr)["code"] == "invalid_request"
        assert server.requests == []
        assert not (directory / "b.json").exists()


@pytest.mark.parametrize("target", ["..", ".", "/", "a/..", "../.."])
def test_a_binding_out_that_names_a_directory_is_an_invalid_request_not_an_existing_file(
    workspace, certificates, target
):
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, target)
        assert process.returncode == 2
        assert process.stdout == b""
        assert json.loads(process.stderr)["code"] == "invalid_request"
        assert server.requests == []


# --- two binds of one version ---------------------------------------------------------------------


def test_two_binds_of_one_version_have_one_digest_and_differ_only_in_when_they_looked(
    workspace, certificates
):
    _, _, directory = workspace
    with TlsServer(certificates, routes()) as server:
        one = parsed(bind(server, certificates, workspace, directory / "one.json"))
        two = parsed(bind(server, certificates, workspace, directory / "two.json"))
    assert one["data"]["binding_digest"] == two["data"]["binding_digest"]
    first = json.loads((directory / "one.json").read_bytes())
    second = json.loads((directory / "two.json").read_bytes())
    assert {key for key in first if first[key] != second[key]} <= {"observed_at"}
    assert (directory / "one.json").stat().st_mode & 0o777 == 0o600


# --- what a list row says -------------------------------------------------------------------------


def test_a_list_row_carries_the_flags_that_show_and_bind_warn_about(workspace, certificates):
    partial = row(id="33333333-3333-4333-8333-333333333333", version_tag="v2", is_partial=True)
    odd = row(id="44444444-4444-4444-8444-444444444444", version_tag="v3", item_count=9)
    page = listing([row(), partial, odd])
    table = routes(**{BASE + "?page=1": body(page)})
    with TlsServer(certificates, table) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            "--output",
            "text",
            *flags(workspace),
        )
    assert process.returncode == 0, process.stderr
    lines = process.stdout.decode().splitlines()
    plain = next(line for line in lines if line.startswith("- v1 "))
    kismi = next(line for line in lines if line.startswith("- v2 "))
    odd_line = next(line for line in lines if line.startswith("- v3 "))
    assert "KISMİ" not in plain
    assert "toplam≠öğe" not in plain
    assert "KISMİ (is_partial)" in kismi
    assert "toplam≠öğe" not in kismi
    assert "toplam≠öğe" in odd_line
    assert "KISMİ" not in odd_line
    assert "tamamlandığı iddia edilmez" in process.stdout.decode()


def test_show_does_not_call_a_version_complete_when_it_only_is_not_marked_partial(
    workspace, certificates
):
    with TlsServer(certificates, routes()) as server:
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
            "--output",
            "text",
            *flags(workspace),
        )
    text = process.stdout.decode()
    assert "is_partial: hayır" in text
    assert "; tam;" not in text


def test_the_last_page_is_not_pointed_past_the_option_the_command_has(workspace, certificates):
    rows = [
        row(id=f"00000000-0000-4000-8000-{number:012d}", version_tag=f"v{number}")
        for number in range(1, 21)
    ]
    last = listing(rows, page=10000, total=300_000, has_next=True)
    table = routes(**{BASE + "?page=10000": body(last)})
    with TlsServer(certificates, table) as server:
        process = execute(
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
            "text",
            *flags(workspace),
        )
    text = process.stdout.decode()
    assert process.returncode == 0
    assert "--page 10001" not in text
    assert "en çok 10000" in text


# --- the held directory ---------------------------------------------------------------------------


class ClosingFails:
    """Fails the first ``os.close`` of one descriptor, after really closing it."""

    def __init__(self, monkeypatch):
        self.real, self.descriptor, self.failed = os.close, None, 0
        monkeypatch.setattr(os, "close", self)

    def __call__(self, descriptor):
        self.real(descriptor)
        if descriptor == self.descriptor and not self.failed:
            self.failed += 1
            raise OSError(errno.EIO, "PRIVATE-CLOSE")


def link_then_fsync_fails(monkeypatch):
    """The link lands and the directory's sync does not: the doubt of a published target."""
    real_link, real_fsync, state = os.link, os.fsync, {"linked": False}

    def link(*arguments, **keywords):
        result = real_link(*arguments, **keywords)
        state["linked"] = True
        return result

    def fsync(descriptor):
        if state["linked"]:
            raise OSError(errno.EIO, "PRIVATE-SYNC")
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "fsync", fsync)


def caught(action):
    with pytest.raises(BaseException) as error:
        action()
    return error.value


FAILED_NOTE = MESSAGES["binding_write_failed"]


@pytest.mark.parametrize(
    "interruption", [YorungeError("remote_failed"), KeyboardInterrupt(), asyncio.CancelledError()]
)
def test_a_failing_close_does_not_replace_the_error_a_binding_body_raised(
    tmp_path, monkeypatch, interruption
):
    closing = ClosingFails(monkeypatch)

    def body_():
        with binding_target(tmp_path / "b.json") as target:
            closing.descriptor = target.directory.descriptor
            raise interruption

    error = caught(body_)
    assert error is interruption
    assert closing.failed == 1
    assert FAILED_NOTE in getattr(error, "__notes__", [])  # nothing was created: true here
    assert not (tmp_path / "b.json").exists()


def test_a_failing_close_after_the_link_adds_no_note_that_contradicts_the_doubt(
    tmp_path, monkeypatch
):
    closing = ClosingFails(monkeypatch)
    link_then_fsync_fails(monkeypatch)

    def body_():
        with binding_target(tmp_path / "b.json") as target:
            closing.descriptor = target.directory.descriptor
            target.publish(held_binding())

    error = caught(body_)
    assert isinstance(error, YorungeError)
    assert error.code == "binding_write_uncertain"
    assert error.exit_code == 5
    assert closing.failed == 1
    assert FAILED_NOTE not in getattr(error, "__notes__", [])  # "not created", with a file there
    assert (tmp_path / "b.json").exists()


@pytest.mark.parametrize("publish", [False, True], ids=["nothing published", "published"])
def test_a_failing_close_after_a_clean_body_is_its_own_closed_error(tmp_path, monkeypatch, publish):
    closing = ClosingFails(monkeypatch)

    def body_():
        with binding_target(tmp_path / "b.json") as target:
            closing.descriptor = target.directory.descriptor
            if publish:
                target.publish(held_binding())

    error = caught(body_)
    assert isinstance(error, YorungeError)
    assert closing.failed == 1
    # nothing created: a failure; published: the file is whole but the held handle could not be
    # let go, which is the conservative doubt, never a silent success
    assert error.code == ("binding_write_uncertain" if publish else "binding_write_failed")
    assert (tmp_path / "b.json").exists() is publish


def full_answer(length):
    return DownloadResponse(200, None, '"v1"', "length", length)


def test_a_failing_close_does_not_replace_the_doubt_of_a_published_download(tmp_path, monkeypatch):
    data = os.urandom(50_000)
    closing = ClosingFails(monkeypatch)
    link_then_fsync_fails(monkeypatch)

    def body_():
        with open_sink(tmp_path / "w.onnx", identity_key="ab" * 32) as (sink, _):
            closing.descriptor = sink.directory.descriptor
            sink.begin(full_answer(len(data)), "full")
            sink.write(data)
            sink.complete(terminated=True)
            sink.publish(None)

    error = caught(body_)
    assert isinstance(error, YorungeError)
    assert error.code == "download_write_uncertain"
    assert error.exit_code == 5
    assert closing.failed == 1
    assert (tmp_path / "w.onnx").read_bytes() == data


def test_a_failing_close_does_not_replace_an_interrupt_in_a_download(tmp_path, monkeypatch):
    closing = ClosingFails(monkeypatch)

    def body_():
        with open_sink(tmp_path / "w.onnx", identity_key="ab" * 32) as (sink, _):
            closing.descriptor = sink.directory.descriptor
            raise KeyboardInterrupt

    assert isinstance(caught(body_), KeyboardInterrupt)
    assert closing.failed == 1


def test_a_failing_close_after_a_whole_download_does_not_undo_it(tmp_path, monkeypatch):
    data = os.urandom(50_000)
    closing = ClosingFails(monkeypatch)

    with open_sink(tmp_path / "w.onnx", identity_key="ab" * 32) as (sink, _):
        closing.descriptor = sink.directory.descriptor
        sink.begin(full_answer(len(data)), "full")
        sink.write(data)
        sink.complete(terminated=True)
        sink.publish(None)
    assert closing.failed == 1
    assert (tmp_path / "w.onnx").read_bytes() == data


# --- signals at each boundary of a bind, with a real SIGINT ---------------------------------------


def with_signal(server, certificates, workspace, point, out):
    environment = dict(os.environ, LC_ALL="C", PYTHONIOENCODING="ascii", PYTHONUTF8="0")
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-W",
            "error",
            str(SIGNAL_CONSOLE),
            "--ca",
            str(certificates[0]),
            "--port",
            str(server.port),
            "--point",
            point,
            "--",
            "datasets",
            "versions",
            "bind",
            "--dataset-id",
            DATASET,
            "--version-tag",
            "v1",
            "--binding-out",
            str(out),
            "--output",
            "json",
            *flags(workspace),
        ],
        env=environment,
        capture_output=True,
        timeout=60,
    )


# point -> (exit, code of the stderr envelope or None, the binding file exists)
BOUNDARIES = {
    "after_reads": (6, "request_cancelled", False),  # before anything is staged
    "stage_checked": (6, "request_cancelled", False),  # the stage is made, not yet linked
    "before_link": (5, "binding_write_uncertain", False),  # inside the publication: a doubt
    "after_link": (5, "binding_write_uncertain", True),
    "in_cleanup": (5, "binding_write_uncertain", True),
    "after_publish": (6, "request_cancelled", True),  # the publication is over: a plain cancel
    "writing_result": (6, "request_cancelled", True),
}


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
@pytest.mark.parametrize("point", sorted(BOUNDARIES))
def test_an_interrupt_inside_the_publication_is_a_doubt_and_after_it_a_cancel(
    workspace, certificates, point
):
    _, _, directory = workspace
    out = directory / "b.json"
    exit_code, code, published = BOUNDARIES[point]
    with TlsServer(certificates, routes()) as server:
        process = with_signal(server, certificates, workspace, point, out)
        assert process.returncode == exit_code, (process.returncode, process.stderr)
        assert json.loads(process.stderr)["code"] == code
        assert out.exists() is published
        # the stage never outlives the command (a published target keeps nothing next to it)
        assert sorted(p.name for p in directory.iterdir() if p.name.startswith(".")) == []
        if published:  # whole and private, and the rerun says so rather than writing again
            assert out.stat().st_mode & 0o777 == 0o600
            assert out.stat().st_nlink == 1
            again = bind(server, certificates, workspace, out)
            assert again.returncode == 2
            assert json.loads(again.stderr)["code"] == "binding_output_exists"


def test_the_interrupt_console_knows_the_points_this_matrix_names():
    import importlib

    sys.path.insert(0, str(SIGNAL_CONSOLE.parents[2]))
    console = importlib.import_module("tests.fixtures.version_signal_console")
    assert set(BOUNDARIES) | {"none"} == set(console.POINTS)
