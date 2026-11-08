"""What round two (reviewer B) of P02-3q found no test noticing: each test names a mutant it kills.

The refusals of `link()`, the guards of the shared argument helpers and of the small-file reader,
the options before the action, the lines of the text renderer that nothing asserted, and the real
close of the directory handle of a target.
"""

import contextlib
import errno
import io
import os
import re
import stat
import sys
from pathlib import Path

import pytest

from tests.fixtures.http_server import TlsServer
from tests.integration.test_binding_files import binding
from tests.integration.test_binding_files import place as place
from tests.integration.test_dataset_version_reader import BASE, DATASET, body, detail
from tests.integration.test_dataset_version_surface import (
    bind,
    execute,
    flags,
    routes,
)
from tests.integration.test_dataset_version_surface import certificates as certificates
from tests.integration.test_dataset_version_surface import workspace as workspace
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api
from yorunge.adapters import artifact_publisher, small_files
from yorunge.adapters.binding_files import binding_target
from yorunge.adapters.command_arguments import absolute, judge_ground
from yorunge.adapters.small_files import read_regular_file
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import is_reportable_path

DOCUMENTED = (
    errno.EPERM,
    errno.EACCES,
    errno.EROFS,
    errno.ENOTSUP,
    errno.EOPNOTSUPP,
    errno.ENOSYS,
    errno.EMLINK,
    errno.EXDEV,
    errno.ENOSPC,
    errno.EDQUOT,
    errno.ENAMETOOLONG,
    errno.ELOOP,
    errno.ENOTDIR,
    errno.ENOENT,
)


def text_of(process):
    assert process.returncode == 0, process.stderr
    return process.stdout.decode("utf-8")


# --- link(): what the kernel refuses without making anything, and what it leaves in doubt ---------


def test_the_errors_of_link_that_mean_nothing_was_made_are_exactly_the_documented_ones():
    assert artifact_publisher.LINK_REFUSED == frozenset(DOCUMENTED)


@pytest.mark.parametrize("number", DOCUMENTED, ids=[errno.errorcode[n] for n in DOCUMENTED])
def test_each_documented_refusal_of_link_is_a_definite_failure_and_leaves_nothing(
    place, monkeypatch, number
):
    def refuse(*arguments, **keywords):
        raise OSError(number, "PRIVATE")

    monkeypatch.setattr(artifact_publisher.os, "link", refuse)
    with pytest.raises(YorungeError) as error:
        with binding_target(place / "binding.json") as target:
            target.publish(binding())
    assert (error.value.code, error.value.exit_code) == ("binding_write_failed", 2)
    assert list(place.iterdir()) == []


@pytest.mark.parametrize("number", [errno.EIO, errno.ETIMEDOUT, errno.ESTALE, errno.EBUSY])
def test_any_other_error_of_link_stays_uncertain(place, monkeypatch, number):
    def fail(*arguments, **keywords):
        raise OSError(number, "PRIVATE")

    monkeypatch.setattr(artifact_publisher.os, "link", fail)
    with pytest.raises(YorungeError) as error:
        with binding_target(place / "binding.json") as target:
            target.publish(binding())
    assert (error.value.code, error.value.exit_code) == ("binding_write_uncertain", 5)


# --- the shared argument helpers and the small-file reader ----------------------------------------


def test_an_absolute_path_does_not_need_the_working_directory(tmp_path, monkeypatch):
    here = tmp_path.resolve() / "gone"
    here.mkdir()
    monkeypatch.chdir(here)
    here.rmdir()  # the shell this runs in was deleted
    target = tmp_path.resolve() / "binding.json"
    assert absolute(target) == target
    with pytest.raises(YorungeError) as error:
        absolute(Path("relative.json"))
    assert error.value.code == "input_invalid"


def test_the_platform_is_judged_with_the_other_arguments_before_any_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(YorungeError) as error:
        judge_ground(None)
    assert error.value.code == "state_unsupported"
    missing = tmp_path.resolve() / "no-such-binding.json"
    with pytest.raises(YorungeError) as error:
        api.check_dataset_version(missing)
    assert error.value.code == "state_unsupported"  # not file_unreadable
    with pytest.raises(YorungeError) as error:
        api.bind_dataset_version(
            DATASET, "v1", binding_out=tmp_path.resolve() / "b.json", manifest=missing
        )
    assert error.value.code == "state_unsupported"
    assert not os.path.exists(missing)


def test_the_small_file_reader_refuses_a_platform_without_descriptor_relative_calls(
    place, monkeypatch
):
    (place / "a.json").write_bytes(b"{}")
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(YorungeError) as error:
        read_regular_file(place / "a.json", limit=10, oversize="binding_invalid")
    assert error.value.code == "input_unsupported"


@pytest.mark.parametrize("parent", ["..", "new\nline", "a\x00b"])
def test_a_parent_the_chain_walk_refuses_is_input_invalid(place, parent):
    path = Path(str(place) + "/" + parent + "/a.json")
    with pytest.raises(YorungeError) as error:
        read_regular_file(path, limit=10, oversize="binding_invalid")
    assert error.value.code == "input_invalid"


def test_an_oversize_file_is_refused_before_a_byte_of_it_is_read(place, monkeypatch):
    path = place / "big.json"
    with path.open("wb") as handle:
        handle.truncate(10 * 1024**2)  # sparse

    def forbidden(*arguments):
        raise AssertionError("read")

    monkeypatch.setattr(small_files.os, "read", forbidden)
    with pytest.raises(YorungeError) as error:
        read_regular_file(path, limit=100, oversize="binding_invalid")
    assert error.value.code == "binding_invalid"


# --- the command line: options before the action, a project, no action ----------------------------


def test_the_shared_options_are_accepted_before_the_action_too():
    from yorunge.cli import parser

    arguments = parser().parse_args(
        [
            "datasets",
            "versions",
            "--state-dir",
            "/s",
            "--output",
            "json",
            "--non-interactive",
            "list",
            "--dataset-id",
            DATASET,
        ]
    )
    assert (arguments.state_dir, arguments.output, arguments.non_interactive) == (
        Path("/s"),
        "json",
        True,
    )


def test_the_project_option_is_refused_before_the_action_too(monkeypatch):
    from yorunge.cli import main

    def reached(*arguments, **keywords):
        raise AssertionError("the parser let --project through to the use case")

    monkeypatch.setattr(api, "list_dataset_versions", reached)
    for position in (
        ["datasets", "versions", "--project", "alpha", "list", "--dataset-id", DATASET],
        ["datasets", "versions", "list", "--dataset-id", DATASET, "--project", "alpha"],
    ):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            assert main(["--output", "json", *position]) == 2


def test_a_versions_command_without_an_action_is_a_usage_error_not_a_crash():
    from yorunge.cli import main

    error = io.StringIO()
    with contextlib.redirect_stderr(error), contextlib.redirect_stdout(io.StringIO()):
        assert main(["--output", "json", "datasets", "versions"]) == 2
    assert "invalid_request" in error.getvalue()
    assert "Traceback" not in error.getvalue()


# --- the text of list, show and bind: lines nothing asserted --------------------------------------


def test_the_text_of_list_and_show_give_the_split_counts_and_list_closes_with_its_scope(
    workspace, certificates
):
    with TlsServer(certificates, routes()) as server:
        listed = text_of(
            execute(
                server,
                certificates,
                "datasets",
                "versions",
                "list",
                "--dataset-id",
                DATASET,
                *flags(workspace),
            )
        )
        shown = text_of(
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
    assert "(train 6, val 2, test 1, atanmamış 1)" in listed
    assert "(train 6, val 2, test 1, atanmamış 1)" in shown
    assert listed.rstrip().endswith("sürümlerin tamamlandığı iddia edilmez.")


def test_the_text_of_show_says_whether_the_export_is_ready(workspace, certificates):
    def shown(table):
        with TlsServer(certificates, table) as server:
            return text_of(
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

    not_ready = shown(routes())
    ready = shown(routes(**{BASE + "/v1": body(detail(is_export_ready=True))}))
    assert "export hazır değil" in not_ready
    assert "export hazır değil" not in ready
    assert "export hazır" in ready


def test_the_text_of_bind_says_the_digest_is_a_self_hash_and_to_check_before_use(
    workspace, certificates
):
    out = workspace[2] / "b.json"
    with TlsServer(certificates, routes()) as server:
        text = text_of(bind(server, certificates, workspace, out, output="text"))
    assert "Digest kendi kendine hash'tir (imza değil); kullanmadan önce check edin." in text


# --- a path that can be reported: the whole bidirectional range and what lies next to it ----------


@pytest.mark.parametrize("codepoint", [*range(0x202A, 0x202F), *range(0x2066, 0x206A)])
def test_every_bidirectional_override_and_isolate_is_refused_in_a_reportable_path(codepoint):
    assert not is_reportable_path("/tmp/a" + chr(codepoint) + "b.json")


@pytest.mark.parametrize("codepoint", [0x2029, 0x202F, 0x2065, 0x206A, 0x200E, 0x200F])
def test_the_characters_next_to_the_bidirectional_ranges_are_not_refused(codepoint):
    assert is_reportable_path("/tmp/a" + chr(codepoint) + "b.json")


# --- the directory handle of a target and the files around a binding ------------------------------


@pytest.mark.parametrize("how", ["published", "nothing published", "error in flight"])
def test_the_directory_descriptor_of_a_target_is_closed_in_the_os_on_every_path(place, how):
    held = None
    try:
        with binding_target(place / "binding.json") as target:
            held = target.directory.descriptor
            if how == "published":
                target.publish(binding())
            elif how == "error in flight":
                raise YorungeError("remote_failed")
    except YorungeError:
        pass
    with pytest.raises(OSError) as error:
        os.fstat(held)
    assert error.value.errno == errno.EBADF


def test_a_target_that_cannot_be_one_opens_no_directory_handle(place):
    (place / "real").mkdir()
    before = len(os.listdir("/dev/fd"))
    for bad in (
        place / "real" / "new\nline.json",
        place / "real" / "tab\there.json",
        place / "real" / ("x" * 4097),
        place / "real" / "a‮b.json",
    ):
        with pytest.raises(YorungeError):
            with binding_target(bad):
                raise AssertionError("the block must not be entered")
    assert len(os.listdir("/dev/fd")) == before


def test_a_binding_is_synced_to_disk_before_and_after_it_is_linked(place, monkeypatch):
    """The binding writer's own `_sync` (a copy of the base's) could be emptied unnoticed."""
    seen = []
    real = os.fsync

    def spy(descriptor):
        seen.append("file" if stat.S_ISREG(os.fstat(descriptor).st_mode) else "directory")
        return real(descriptor)

    monkeypatch.setattr(os, "fsync", spy)
    with binding_target(place / "binding.json") as target:
        target.publish(binding())
    assert seen.count("file") == 2
    assert seen.count("directory") == 1


def test_the_stage_of_a_binding_is_exactly_prefix_random_suffix(place, monkeypatch):
    names = []
    real = artifact_publisher.ArtifactPublisher._publish_link

    def spy(self):
        names.extend(p.name for p in place.iterdir())
        return real(self)

    monkeypatch.setattr(artifact_publisher.ArtifactPublisher, "_publish_link", spy)
    with binding_target(place / "b.json") as target:
        target.publish(binding())
    assert len(names) == 1
    assert re.fullmatch(r"\.yorunge-binding-[0-9a-f]{32}\.tmp", names[0])
