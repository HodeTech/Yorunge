"""``datasets versions list|show|bind|check`` through the public API and real CLI processes.

A real loopback TLS provider answers as the canonical host; the state store, the profile config and
the key's environment variable are the user's. Each journey is shown on the wire (what was asked,
how often, with which key), on disk (the binding: private, canonical, never over an existing file)
and in the result (exit status, machine output, nothing private).
"""

import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.version_network import loopback_versions
from tests.integration.test_dataset_version_reader import (
    BASE,
    CANARY,
    DATASET,
    VERSION,
    body,
    detail,
    listing,
    row,
    splits,
)
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api
from yorunge.domain.dataset_manifest import DatasetFile, build_manifest
from yorunge.domain.dataset_version import decode_binding
from yorunge.domain.errors import YorungeError

ENV = "VERSION_SURFACE_TEST_KEY"
SECRET = "synthetic-version-surface-key-8841"
CONSOLE = Path(__file__).parents[1] / "fixtures" / "version_console.py"


def routes(**overrides):
    table = {
        BASE + "?page=1": body(listing()),
        BASE + "/v1": body(detail()),
        BASE + "/v1/splits": body(splits()),
    }
    table.update(overrides)
    return table


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    state = tmp_path / "state"
    api.initialize_state(state_dir=state)
    config = tmp_path / "config.toml"
    config.write_text(
        f'''schema_version = 1
active_profile = "test"
[profiles.test]
platform_key_env = "{ENV}"
[profiles.elsewhere]
platform_key_env = "{ENV}"
platform_url = "https://other.ssyz.org.tr/api/v1"
'''
    )
    monkeypatch.setenv(ENV, SECRET)
    return state, config, tmp_path


def manifest_file(count):
    files = tuple(
        DatasetFile(path=f"f{i}.bin", size=1, sha256=f"{i:02x}" * 32) for i in range(count)
    )
    return build_manifest(files)


def execute(server, certificates, *args, environment=None, timeout=60):
    env = dict(os.environ)
    env.update(LC_ALL="C", PYTHONIOENCODING="ascii", PYTHONUTF8="0", **(environment or {}))
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
        timeout=timeout,
    )


def parsed(process, output="json"):
    assert process.returncode == 0, process.stderr.decode("utf-8", "strict")
    value = json.loads(process.stdout.decode("utf-8", "strict"))
    if output == "ndjson":
        assert value["event"] == "result" and value["sequence"] == 1
        value = value["payload"]
    assert value["operation_id"] is None and not process.stderr
    return value


def failure(process):
    assert process.returncode != 0
    assert not process.stdout.strip() or process.stdout.strip().startswith(b"{") is False
    return json.loads(process.stderr.decode("utf-8", "strict"))


def flags(workspace):
    state, config, _ = workspace
    return ("--config", str(config), "--state-dir", str(state))


# --- list and show --------------------------------------------------------------------------------


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_list_shows_the_page_asked_for_and_nothing_private(workspace, certificates, output):
    with TlsServer(certificates, routes()) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            "--output",
            output,
            *flags(workspace),
        )
        value = parsed(process, output)
    page = value["data"]
    assert (page["kind"], page["page"], page["total"], page["has_next"]) == (
        "dataset_version_list",
        1,
        1,
        False,
    )
    assert page["items"][0]["version_tag"] == "v1" and page["items"][0]["is_frozen"] is True
    assert value["warnings"] == ["provider_metadata_only"]
    (request,) = server.requests
    assert (request.method, request.path) == ("GET", BASE + "?page=1")
    assert request.header("X-API-Key") == SECRET
    everything = process.stdout + process.stderr
    for private in (CANARY, "someone@example.test", "files.example.test", SECRET):
        assert private.encode() not in everything


def test_show_is_one_version_from_two_agreeing_reads_and_text_is_readable(workspace, certificates):
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
            *flags(workspace),
        )
    assert process.returncode == 0, process.stderr
    text = process.stdout.decode("utf-8")
    assert "v1" in text and VERSION in text and "dondurulmuş" in text
    assert "sınıf adları yazılmaz" in text
    assert [r.path for r in server.requests] == [BASE + "/v1", BASE + "/v1/splits"]
    assert CANARY not in text and SECRET not in text


def test_a_version_the_provider_does_not_have_is_not_found_and_costs_one_read(
    workspace, certificates
):
    table = routes(**{BASE + "/v9": Reply(status=404, body=b'{"detail":"nope"}')})
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
            "v9",
            "--output",
            "json",
            *flags(workspace),
        )
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "dataset_version_not_found"
    assert [r.path for r in server.requests] == [BASE + "/v9"]


@pytest.mark.parametrize(
    "arguments",
    [
        ("--page", "0"),
        ("--page", "+1"),
        ("--page", "01"),
        ("--page", " 1"),
        ("--page", "10001"),
        ("--page", "1.5"),
        ("--page", "1", "--page", "2"),
        ("--dataset-id", DATASET),
    ],
)
def test_list_refuses_a_page_that_is_not_a_plain_number_and_repeated_options(
    workspace, certificates, arguments
):
    with TlsServer(certificates, routes()) as server:
        process = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            *arguments,
            "--output",
            "json",
            *flags(workspace),
        )
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "invalid_request"
    assert server.requests == []


@pytest.mark.parametrize(
    "status,code,exit_code", [(401, "remote_access_denied", 3), (500, "remote_failed", 1)]
)
def test_a_provider_that_refuses_is_the_existing_closed_error_and_the_key_is_not_echoed(
    workspace, certificates, status, code, exit_code
):
    table = routes(**{BASE + "?page=1": body({"error": SECRET}, status=status)})
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
            "json",
            *flags(workspace),
        )
    assert process.returncode == exit_code and json.loads(process.stderr)["code"] == code
    assert SECRET.encode() not in process.stdout + process.stderr


# --- bind and check -------------------------------------------------------------------------------


def bind(server, certificates, workspace, out, *extra, output="json"):
    return execute(
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
        str(out),
        "--output",
        output,
        *extra,
        *flags(workspace),
    )


def check(server, certificates, workspace, binding, *extra, output="json"):
    return execute(
        server,
        certificates,
        "datasets",
        "versions",
        "check",
        "--binding",
        str(binding),
        "--output",
        output,
        *extra,
        *flags(workspace),
    )


def test_bind_writes_a_new_private_canonical_file_and_check_finds_it_unchanged(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out)
        summary = parsed(process)["data"]
        assert summary["kind"] == "dataset_version_bound" and summary["binding_path"] == str(out)
        info = out.lstat()
        assert stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
        binding = decode_binding(out.read_bytes())
        assert summary["binding_digest"] == binding.digest and binding.local_manifest is None
        assert binding.service.service_origin == "https://api.ssyz.org.tr"
        assert sorted(p.name for p in out.parent.iterdir() if p.name.startswith(".yorunge")) == []
        before = len(server.requests)
        outcome = parsed(check(server, certificates, workspace, out))
        assert outcome["data"]["result"] == "unchanged"
        assert outcome["data"]["binding_digest"] == binding.digest
        assert len(server.requests) - before == 2  # the detail and the splits
        for request in server.requests:
            assert request.header("X-API-Key") == SECRET and request.method == "GET"
    assert SECRET.encode() not in out.read_bytes() + process.stdout + process.stderr


def test_a_second_bind_over_the_same_name_is_refused_before_the_provider_is_asked(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    out.write_bytes(b"MINE")
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "binding_output_exists"
    assert out.read_bytes() == b"MINE" and server.requests == []


def test_bind_over_a_name_that_appears_meanwhile_does_not_overwrite_it(
    workspace, certificates, monkeypatch
):
    out = workspace[2] / "binding.json"

    def appears(record, count):
        out.write_bytes(b"THEIRS")  # the file is created while the provider is being asked
        return body(detail())

    table = routes(**{BASE + "/v1": appears})
    state, config, _ = workspace
    with TlsServer(certificates, table) as server:
        with loopback_versions(certificates[0], server.port):
            with pytest.raises(YorungeError) as error:
                api.bind_dataset_version(
                    DATASET, "v1", binding_out=out, config=config, state_dir=state
                )
    assert error.value.code == "binding_output_exists"
    assert out.read_bytes() == b"THEIRS"


def test_a_binding_name_the_report_could_not_carry_is_refused_before_the_provider_is_asked(
    workspace, certificates
):
    out = workspace[2] / "new\nline.json"  # the report is made after the link: no such file is made
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "binding_write_failed"
    assert server.requests == [] and process.stdout == b""
    assert sorted(p.name for p in out.parent.iterdir() if "line" in p.name) == []


def test_an_unfrozen_version_is_not_bound_and_no_file_is_made(workspace, certificates):
    out = workspace[2] / "binding.json"
    table = routes(**{BASE + "/v1": body(detail(is_frozen=False))})
    with TlsServer(certificates, table) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "dataset_version_not_frozen"
    assert not out.exists() and not list(out.parent.glob(".yorunge-binding-*"))


@pytest.mark.parametrize("count,relation", [(10, "count_matches"), (9, "count_differs")])
def test_bind_with_a_manifest_records_its_digest_and_how_its_file_count_relates(
    workspace, certificates, count, relation
):
    out, directory = workspace[2] / "binding.json", workspace[2]
    manifest = manifest_file(count)
    path = directory / "manifest.json"
    path.write_bytes(manifest.encoded())
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out, "--manifest", str(path))
        value = parsed(process)
    local = value["data"]["local_manifest"]
    assert local["digest"] == manifest.digest and local["relation"] == relation
    assert decode_binding(out.read_bytes()).local_manifest.relation == relation


def test_a_manifest_that_is_not_one_stops_bind_before_the_provider_is_asked(
    workspace, certificates
):
    out, directory = workspace[2] / "binding.json", workspace[2]
    (directory / "manifest.json").write_bytes(b'{"not":"a manifest"}')
    with TlsServer(certificates, routes()) as server:
        process = bind(
            server, certificates, workspace, out, "--manifest", str(directory / "manifest.json")
        )
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "manifest_invalid"
    assert server.requests == [] and not out.exists()


def test_the_binding_and_the_manifest_cannot_be_the_same_file(workspace, certificates):
    path = workspace[2] / "same.json"
    path.write_bytes(b"{}")
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, path, "--manifest", str(path))
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "invalid_request"
    assert path.read_bytes() == b"{}" and server.requests == []


def test_a_changed_version_is_exit_7_with_the_closed_list_of_what_changed(workspace, certificates):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        server.routes[BASE + "/v1"] = body(detail(item_count=11, annotated_item_count=3))
        server.routes[BASE + "/v1/splits"] = body(splits())
        process = check(server, certificates, workspace, out)
    assert process.returncode == 7
    envelope = json.loads(process.stderr)
    assert envelope["code"] == "dataset_version_changed"
    assert envelope["details"] == {
        "changed_field_count": 3,
        "changed_fields": ["annotated_item_count", "item_count", "split_total_matches_item_count"],
        "annotation_only": False,
    }
    assert not process.stdout.strip()  # a difference is an error, never a result


def test_a_version_that_is_gone_is_missing_and_exit_7(workspace, certificates):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        server.routes[BASE + "/v1"] = Reply(status=404, body=b"{}")
        process = check(server, certificates, workspace, out)
    assert process.returncode == 7
    assert json.loads(process.stderr)["code"] == "dataset_version_missing"


def test_a_binding_for_another_provider_is_state_changed_and_nothing_is_read(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        before = len(server.requests)
        process = check(server, certificates, workspace, out, "--profile", "elsewhere")
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "state_changed"
    assert len(server.requests) == before


@pytest.mark.parametrize(
    "content",
    [b"", b"{}", b"not json", b"\xff\xfe", b"x" * 20_000],
    ids=["empty", "object", "text", "bytes", "oversize"],
)
def test_a_file_that_is_not_a_binding_is_binding_invalid_and_nothing_is_asked(
    workspace, certificates, content
):
    path = workspace[2] / "binding.json"
    path.write_bytes(content)
    with TlsServer(certificates, routes()) as server:
        process = check(server, certificates, workspace, path)
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "binding_invalid"
    assert server.requests == []


def test_a_binding_that_is_a_symlink_is_not_followed(workspace, certificates):
    out = workspace[2] / "binding.json"
    link = workspace[2] / "link.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        link.symlink_to(out)
        process = check(server, certificates, workspace, link)
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "input_invalid"


def test_a_missing_binding_file_is_unreadable_not_invalid(workspace, certificates):
    with TlsServer(certificates, routes()) as server:
        process = check(server, certificates, workspace, workspace[2] / "absent.json")
    assert process.returncode == 2 and json.loads(process.stderr)["code"] == "file_unreadable"
    assert server.requests == []


# --- the Python API, in this process --------------------------------------------------------------


def test_the_api_returns_the_same_typed_results_and_validates_before_it_touches_anything(
    workspace, certificates
):
    state, config, directory = workspace
    out = directory / "binding.json"
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            listed = api.list_dataset_versions(DATASET, config=config, state_dir=state)
            shown = api.show_dataset_version(DATASET, "v1", config=config, state_dir=state)
            bound = api.bind_dataset_version(
                DATASET, "v1", binding_out=out, config=config, state_dir=state
            )
            checked = api.check_dataset_version(out, config=config, state_dir=state)
            requests = len(server.requests)
            for call in (
                lambda: api.list_dataset_versions("not-a-uuid", config=config, state_dir=state),
                lambda: api.list_dataset_versions(DATASET, page=0, config=config, state_dir=state),
                lambda: api.show_dataset_version(DATASET, "..", config=config, state_dir=state),
                lambda: api.show_dataset_version(DATASET, "a/b", config=config, state_dir=state),
                lambda: api.bind_dataset_version(
                    DATASET, "v1", binding_out="relative", config=config, state_dir=state
                ),
            ):
                with pytest.raises(YorungeError) as error:
                    call()
                assert error.value.code == "invalid_request"
            assert len(server.requests) == requests  # not one request for a refused argument
    assert listed.data.items[0].version_id == shown.data.version_id == bound.data.version_id
    assert bound.data.binding_digest == checked.data.binding_digest
    assert listed.warnings == shown.warnings == checked.warnings == ("provider_metadata_only",)
    assert checked.data.result == "unchanged" and checked.operation_id is None
    assert (shown.data.observed_at, checked.data.observed_at) != (None, None)


def test_the_api_warns_when_the_versions_split_total_is_not_its_item_count(workspace, certificates):
    state, config, directory = workspace
    skewed = {"train": 6, "val": 2, "test": 1, "unassigned": 0}
    table = routes(
        **{
            BASE + "/v1": body(detail(split_config=skewed)),
            BASE + "/v1/splits": body(splits(unassigned=0)),
        }
    )
    with TlsServer(certificates, table) as server:
        with loopback_versions(certificates[0], server.port):
            bound = api.bind_dataset_version(
                DATASET, "v1", binding_out=directory / "b.json", config=config, state_dir=state
            )
    assert bound.warnings == ("provider_metadata_only", "split_total_differs")
    assert bound.data.split_total_matches_item_count is False


def test_a_key_that_cannot_be_read_is_the_existing_credential_error_before_any_request(
    workspace, certificates, monkeypatch
):
    state, config, _ = workspace
    monkeypatch.delenv(ENV)
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            with pytest.raises(YorungeError) as error:
                api.list_dataset_versions(DATASET, config=config, state_dir=state)
    assert error.value.code == "credential_unavailable" and server.requests == []


def test_row_data_the_version_tests_share_is_what_the_provider_serves():
    # the shared fixtures of the reader tests are the provider's shapes (guards the helpers above)
    assert row()["version_tag"] == "v1" and detail()["data"]["dataset_id"] == DATASET


# --- the terminal: a closed pipe and an interrupt are local, never a claim about the provider -----


def popen(server, certificates, workspace, *args):
    return subprocess.Popen(
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "LC_ALL": "C", "PYTHONIOENCODING": "ascii"},
    )


def test_a_closed_stdout_is_a_local_output_error_after_the_read(workspace, certificates):
    with TlsServer(certificates, routes()) as server:
        process = popen(
            server,
            certificates,
            workspace,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
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
    assert json.loads(stderr)["code"] == "output_closed" and len(server.requests) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_an_interrupt_while_the_provider_is_slow_is_a_cancellation_and_prints_no_result(
    workspace, certificates
):
    table = routes(**{BASE + "?page=1": Reply(body=b"{}", header_delay=3)})
    with TlsServer(certificates, table) as server:
        process = popen(
            server,
            certificates,
            workspace,
            "datasets",
            "versions",
            "list",
            "--dataset-id",
            DATASET,
            "--output=json",
            *flags(workspace),
        )
        try:
            end = time.monotonic() + 20
            while not server.requests and time.monotonic() < end:
                time.sleep(0.02)
            assert server.requests
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=20)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert process.returncode == 6 and stdout == b""
    assert json.loads(stderr)["code"] == "request_cancelled"
    assert SECRET.encode() not in stderr
