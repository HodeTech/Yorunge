"""``datasets versions list|show|bind|check`` through the public API and real CLI processes.

A real loopback TLS provider answers as the canonical host; the state store, the profile config and
the key's environment variable are the user's. Each journey is shown on the wire (what was asked,
how often, with which key), on disk (the binding: private, canonical, never over an existing file)
and in the result (exit status, machine output, nothing private).
"""

import asyncio
import json
import os
import shlex
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate
from tests.fixtures.version_network import HOSTS, loopback_versions
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
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api
from yorunge.domain.dataset_manifest import DatasetFile, build_manifest
from yorunge.domain.dataset_version import decode_binding
from yorunge.domain.errors import MESSAGES, YorungeError

ENV = "VERSION_SURFACE_TEST_KEY"
SECRET = "synthetic-version-surface-key-8841"
CONSOLE = Path(__file__).parents[1] / "fixtures" / "version_console.py"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("version-surface-tls"), names=(*HOSTS, "localhost"))


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


def execute(server, certificates, *args, environment=None, timeout=60, cwd=None):
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
        cwd=cwd,
    )


def parsed(process, output="json"):
    assert process.returncode == 0, process.stderr.decode("utf-8", "strict")
    value = json.loads(process.stdout.decode("utf-8", "strict"))
    if output == "ndjson":
        assert value["event"] == "result"
        assert value["sequence"] == 1
        value = value["payload"]
    assert value["operation_id"] is None
    assert not process.stderr
    return value


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
    assert page["items"][0]["version_tag"] == "v1"
    assert page["items"][0]["is_frozen"] is True
    assert value["warnings"] == ["provider_metadata_only"]
    (request,) = server.requests
    assert (request.method, request.path) == ("GET", BASE + "?page=1")
    assert request.header("X-API-Key") == SECRET
    everything = process.stdout + process.stderr
    for private in (CANARY, "someone@example.test", "files.example.test", SECRET):
        assert private.encode() not in everything


def versions_list(server, certificates, workspace, *extra, output="json"):
    return execute(
        server,
        certificates,
        "datasets",
        "versions",
        "list",
        "--dataset-id",
        DATASET,
        "--output",
        output,
        *extra,
        *flags(workspace),
    )


def test_list_page_two_asks_for_page_two_and_says_where_the_next_one_is(workspace, certificates):
    third = row(id="33333333-3333-4333-8333-333333333333", version_tag="v3")
    fourth = row(id="44444444-4444-4444-8444-444444444444", version_tag="v4")
    table = routes(
        **{
            BASE + "?page=2": body(
                listing([third, fourth], page=2, page_size=2, total=5, has_next=True)
            )
        }
    )
    with TlsServer(certificates, table) as server:
        as_json = versions_list(server, certificates, workspace, "--page", "2")
        as_text = versions_list(server, certificates, workspace, "--page", "2", output="text")
    page = parsed(as_json)["data"]
    assert (page["page"], page["page_size"], page["total"], page["has_next"]) == (2, 2, 5, True)
    assert [request.path for request in server.requests] == [BASE + "?page=2"] * 2
    text = as_text.stdout.decode("utf-8")
    assert as_text.returncode == 0
    assert not as_text.stderr
    assert "sayfa 2, toplam 5 sürüm" in text
    assert "v3" in text
    assert "v4" in text
    assert "Sonraki sayfa var (--page 3)." in text
    assert "provider" not in text.casefold()


def test_a_page_past_the_end_is_an_honest_empty_page_in_every_mode(workspace, certificates):
    table = routes(
        **{BASE + "?page=99": body(listing([], page=99, page_size=20, total=1, has_next=False))}
    )
    with TlsServer(certificates, table) as server:
        as_text = versions_list(server, certificates, workspace, "--page", "99", output="text")
        as_json = versions_list(server, certificates, workspace, "--page", "99")
    assert as_text.returncode == 0
    assert "Bu sayfada sürüm yok." in as_text.stdout.decode()
    page = parsed(as_json)["data"]
    assert (page["items"], page["total"], page["has_next"]) == ([], 1, False)


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
    assert "v1" in text
    assert VERSION in text
    assert "dondurulmuş" in text
    assert "sınıf adları yazılmaz" in text
    assert [r.path for r in server.requests] == [BASE + "/v1", BASE + "/v1/splits"]
    assert CANARY not in text
    assert SECRET not in text


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
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"
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
    assert process.returncode == exit_code
    assert json.loads(process.stderr)["code"] == code
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
        assert summary["kind"] == "dataset_version_bound"
        assert summary["binding_path"] == str(out)
        info = out.lstat()
        assert stat.S_IMODE(info.st_mode) == 0o600
        assert info.st_nlink == 1
        binding = decode_binding(out.read_bytes())
        assert summary["binding_digest"] == binding.digest
        assert binding.local_manifest is None
        assert binding.service.service_origin == "https://api.ssyz.org.tr"
        assert sorted(p.name for p in out.parent.iterdir() if p.name.startswith(".yorunge")) == []
        before = len(server.requests)
        outcome = parsed(check(server, certificates, workspace, out))
        assert outcome["data"]["result"] == "unchanged"
        assert outcome["data"]["binding_digest"] == binding.digest
        assert len(server.requests) - before == 2  # the detail and the splits
        for request in server.requests:
            assert request.header("X-API-Key") == SECRET
            assert request.method == "GET"
    assert SECRET.encode() not in out.read_bytes() + process.stdout + process.stderr


def test_bind_in_text_says_where_the_binding_is_how_to_check_it_and_claims_nothing_more(
    workspace, certificates
):
    out = workspace[2] / "my binding.json"  # a space: the printed command must stay quotable
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out, output="text")
    text = process.stdout.decode("utf-8")
    assert process.returncode == 0
    assert not process.stderr
    assert f"Sürüm bağı kaydedildi: {out}" in text
    assert "Digest: " in text
    (command,) = [line for line in text.splitlines() if line.startswith("Denetle: ")]
    assert shlex.split(command.removeprefix("Denetle: ")) == [
        "yorunge",
        "datasets",
        "versions",
        "check",
        "--binding",
        str(out),
    ]
    assert "Özel --config/--profile/--state-dir kullandıysanız" in text
    assert "Yalnız sağlayıcı metadata'sı" in text
    assert "üyelik" in text
    assert SECRET not in text


def test_bind_in_ndjson_is_one_result_event(workspace, certificates):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out, output="ndjson")
        value = parsed(process, "ndjson")
    assert value["data"]["kind"] == "dataset_version_bound"
    assert value["data"]["binding_digest"] == decode_binding(out.read_bytes()).digest
    assert value["warnings"] == ["provider_metadata_only"]


def test_a_relative_binding_path_is_made_absolute_once_and_check_reads_it_the_same_way(
    workspace, certificates
):
    here = workspace[2].resolve()
    with TlsServer(certificates, routes()) as server:
        made = execute(
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
            "binding.json",
            "--output",
            "json",
            *flags(workspace),
            cwd=here,
        )
        assert parsed(made)["data"]["binding_path"] == str(here / "binding.json")
        checked = execute(
            server,
            certificates,
            "datasets",
            "versions",
            "check",
            "--binding",
            "binding.json",
            "--output",
            "text",
            *flags(workspace),
            cwd=here,
        )
    assert checked.returncode == 0
    assert "Değişmedi: v1" in checked.stdout.decode()
    assert (here / "binding.json").is_file()


def test_a_second_bind_over_the_same_name_is_refused_before_the_provider_is_asked(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    out.write_bytes(b"MINE")
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "binding_output_exists"
    assert out.read_bytes() == b"MINE"
    assert server.requests == []


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
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "binding_write_failed"
    assert server.requests == []
    assert process.stdout == b""
    assert sorted(p.name for p in out.parent.iterdir() if "line" in p.name) == []


def test_a_version_the_provider_does_not_have_is_not_found_for_bind_too_and_nothing_is_written(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    table = routes(**{BASE + "/v1": Reply(status=404, body=b"{}")})
    with TlsServer(certificates, table) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "dataset_version_not_found"
    assert not out.exists()
    assert not list(out.parent.glob(".yorunge-binding-*"))


def test_a_plain_bind_says_only_that_it_is_provider_metadata(workspace, certificates):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        value = parsed(bind(server, certificates, workspace, out))
    assert value["warnings"] == ["provider_metadata_only"]
    assert value["data"]["is_partial"] is False
    assert value["data"]["split_total_matches_item_count"]


def test_a_partial_version_is_bound_with_its_flag_in_the_result_too(workspace, certificates):
    out = workspace[2] / "binding.json"
    table = routes(**{BASE + "/v1": body(detail(is_partial=True))})
    with TlsServer(certificates, table) as server:
        value = parsed(bind(server, certificates, workspace, out))
    assert value["data"]["is_partial"] is True
    assert decode_binding(out.read_bytes()).is_partial


def test_the_binding_names_the_provider_of_the_active_profile_not_the_default_one(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, out, "--profile", "elsewhere")
        parsed(process)
        (request, *_) = server.requests
    held = decode_binding(out.read_bytes())
    assert held.service.service_origin == "https://other.ssyz.org.tr"
    assert request.header("Host").startswith("other.ssyz.org.tr")


def test_a_provider_that_is_slower_than_the_budget_ends_the_command_and_writes_nothing(
    workspace, certificates, monkeypatch
):
    from yorunge.adapters import dataset_version_api

    out = workspace[2] / "binding.json"
    monkeypatch.setattr(dataset_version_api, "VERSION_SECONDS", 1.0)
    # The delay is far past the 1 s budget, so the command can only end by its own deadline; only
    # the call is timed (leaving the server waits for its handler, which says nothing of the call).
    table = routes(**{BASE + "/v1": body(detail(), header_delay=6.0)})
    state, config, _ = workspace
    with TlsServer(certificates, table) as server:
        with loopback_versions(certificates[0], server.port):
            began = time.monotonic()
            with pytest.raises(YorungeError) as error:
                api.bind_dataset_version(
                    DATASET, "v1", binding_out=out, config=config, state_dir=state
                )
            elapsed = time.monotonic() - began
    assert error.value.code == "transport_timeout"
    assert elapsed < 4.5
    assert not out.exists()
    assert not list(out.parent.glob(".yorunge-binding-*"))


def test_an_unfrozen_version_is_not_bound_and_no_file_is_made(workspace, certificates):
    out = workspace[2] / "binding.json"
    table = routes(**{BASE + "/v1": body(detail(is_frozen=False))})
    with TlsServer(certificates, table) as server:
        process = bind(server, certificates, workspace, out)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "dataset_version_not_frozen"
    assert not out.exists()
    assert not list(out.parent.glob(".yorunge-binding-*"))


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
    assert local["digest"] == manifest.digest
    assert local["relation"] == relation
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
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "manifest_invalid"
    assert server.requests == []
    assert not out.exists()


def test_the_binding_and_the_manifest_cannot_be_the_same_file(workspace, certificates):
    path = workspace[2] / "same.json"
    path.write_bytes(b"{}")
    with TlsServer(certificates, routes()) as server:
        process = bind(server, certificates, workspace, path, "--manifest", str(path))
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "invalid_request"
    assert path.read_bytes() == b"{}"
    assert server.requests == []


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


@pytest.mark.parametrize("output", ["ndjson", "text"])
def test_a_difference_is_an_error_envelope_and_never_a_result_in_every_mode(
    workspace, certificates, output
):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        server.routes[BASE + "/v1"] = body(detail(item_count=11, annotated_item_count=3))
        process = check(server, certificates, workspace, out, output=output)
    assert process.returncode == 7
    assert not process.stdout.strip()  # no event before the verdict
    if output == "ndjson":
        assert json.loads(process.stderr)["code"] == "dataset_version_changed"
    else:
        # the person reads the catalog's sentence, not the closed code the machine envelope carries
        assert b"dataset_version_changed" not in process.stderr
        assert MESSAGES["dataset_version_changed"] in process.stderr.decode("utf-8")


def test_an_unchanged_version_is_a_result_in_text_and_ndjson(workspace, certificates):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        as_text = check(server, certificates, workspace, out, output="text")
        as_events = check(server, certificates, workspace, out, output="ndjson")
    assert as_text.returncode == 0
    assert "Değişmedi: v1" in as_text.stdout.decode()
    assert "bayt eşliği" in as_text.stdout.decode()
    assert not as_text.stderr
    assert parsed(as_events, "ndjson")["data"]["result"] == "unchanged"


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


def test_a_binding_for_another_provider_tells_a_person_which_options_to_give_in_text_only(
    workspace, certificates
):
    out = workspace[2] / "binding.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        as_text = check(
            server, certificates, workspace, out, "--profile", "elsewhere", output="text"
        )
        as_json = check(server, certificates, workspace, out, "--profile", "elsewhere")
    message = as_text.stderr.decode()
    assert as_text.returncode == 2
    assert "--config, --profile ve --state-dir" in message
    assert "--config, --profile" not in as_json.stderr.decode()  # the envelope is what it was


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
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "binding_invalid"
    assert server.requests == []


def test_a_binding_that_is_a_symlink_is_not_followed(workspace, certificates):
    out = workspace[2] / "binding.json"
    link = workspace[2] / "link.json"
    with TlsServer(certificates, routes()) as server:
        parsed(bind(server, certificates, workspace, out))
        link.symlink_to(out)
        process = check(server, certificates, workspace, link)
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "input_invalid"


def test_a_missing_binding_file_is_unreadable_not_invalid(workspace, certificates):
    with TlsServer(certificates, routes()) as server:
        process = check(server, certificates, workspace, workspace[2] / "absent.json")
    assert process.returncode == 2
    assert json.loads(process.stderr)["code"] == "file_unreadable"
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
    assert checked.data.result == "unchanged"
    assert checked.operation_id is None
    assert (shown.data.observed_at, checked.data.observed_at) != (None, None)


def test_the_arguments_about_where_the_caller_stands_are_judged_before_any_file_is_read(
    workspace, certificates
):
    state, config, directory = workspace
    missing = directory / "no-such-manifest.json"
    out = directory / "binding.json"
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            for call in (
                lambda: api.bind_dataset_version(
                    DATASET, "v1", binding_out=out, manifest=missing, config=config, state_dir="s"
                ),
                lambda: api.check_dataset_version(missing, config=config, state_dir="s"),
                lambda: api.list_dataset_versions(DATASET, config=config, state_dir="s"),
            ):
                with pytest.raises(YorungeError) as error:
                    call()
                assert error.value.code == "invalid_request"  # not file_unreadable
            out.write_bytes(b"MINE")

            async def inside():
                return api.bind_dataset_version(
                    DATASET, "v1", binding_out=out, config=config, state_dir=state
                )

            inside_value = inside()
            with pytest.raises(YorungeError) as inside_a_loop:
                asyncio.run(inside_value)
            # The running loop is refused first, whatever the target says.
            assert inside_a_loop.value.code == "invalid_request"
    assert server.requests == []
    assert out.read_bytes() == b"MINE"


def test_an_os_error_of_the_read_phase_of_bind_is_not_called_a_write_failure(
    workspace, certificates, monkeypatch
):
    from yorunge.adapters.http_session import HttpSession

    state, config, directory = workspace
    out = directory / "binding.json"

    def exhausted(self):
        raise OSError(24, "PRIVATE-DETAIL-OF-THE-OS")

    monkeypatch.setattr(HttpSession, "__enter__", exhausted)
    with TlsServer(certificates, routes()) as server:
        with loopback_versions(certificates[0], server.port):
            with pytest.raises(YorungeError) as error:
                api.bind_dataset_version(
                    DATASET, "v1", binding_out=out, config=config, state_dir=state
                )
    assert error.value.code == "file_unreadable"
    assert "PRIVATE-DETAIL" not in repr(error.value.envelope())
    assert error.value.__context__ is None
    assert not out.exists()
    assert not list(out.parent.glob(".yorunge-binding-*"))


def test_the_project_option_is_not_a_versions_option_since_a_read_of_versions_needs_none(
    workspace, certificates
):
    with TlsServer(certificates, routes()) as server:
        process = versions_list(server, certificates, workspace, "--project", "alpha")
    assert process.returncode == 2
    assert server.requests == []


def test_the_messages_of_a_changed_version_and_an_invalid_binding_say_what_to_do():
    assert "--output json" in MESSAGES["dataset_version_changed"]
    assert "bayt bayt aynı" in MESSAGES["binding_invalid"]


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
    assert error.value.code == "credential_unavailable"
    assert server.requests == []


def test_row_data_the_version_tests_share_is_what_the_provider_serves():
    # the shared fixtures of the reader tests are the provider's shapes (guards the helpers above)
    assert row()["version_tag"] == "v1"
    assert detail()["data"]["dataset_id"] == DATASET


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
    assert json.loads(stderr)["code"] == "output_closed"
    assert len(server.requests) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal contract")
def test_an_interrupt_while_the_provider_is_slow_is_a_cancellation_and_prints_no_result(
    workspace, certificates
):
    # The interrupt ends the wait at once; the delay only has to outlast a slow test machine.
    table = routes(**{BASE + "?page=1": Reply(body=b"{}", header_delay=30)})
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
    assert process.returncode == 6
    assert stdout == b""
    assert json.loads(stderr)["code"] == "request_cancelled"
    assert SECRET.encode() not in stderr
