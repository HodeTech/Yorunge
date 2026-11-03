"""Streaming sink and observed counters have independent byte and cleanup oracles."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.fixtures.http_server import certificate
from tests.fixtures.upload_native_client import flow
from tests.fixtures.upload_native_control import server
from tests.fixtures.upload_native_data import (
    KEY,
    KEY_ENV,
    canonical,
    fixture,
    write_config,
    write_fixture,
)
from tests.fixtures.upload_native_server import StreamingProvider
from tests.fixtures.upload_network import Connection, CountedResponse, CountingStream, Metrics
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from yorunge import api


def prepared(directory, label):
    directory.mkdir()
    write_fixture(directory / "source", directory / "manifest.json", fixture(label))
    write_config(directory / "config.toml")
    api.initialize_state(state_dir=directory / "state")
    return directory


def test_fixed_warm_data_matches_manifest_and_no_clobber(tmp_path):
    expected = fixture("warm")
    work = prepared(tmp_path / "work", "warm")
    for file in expected["files"]:
        body = (work / "source" / file["path"]).read_bytes()
        index = int(file["path"][5:8])
        assert len(body) == file["size"]
        assert body == bytes((offset + 17 * index) % 256 for offset in range(len(body)))
        assert hashlib.sha256(body).hexdigest() == file["sha256"]
    content = {key: value for key, value in expected.items() if key != "digest"}
    assert hashlib.sha256(canonical(content)).hexdigest() == expected["digest"]
    with pytest.raises(FileExistsError):
        write_fixture(work / "source", work / "manifest.json", expected)


def test_sink_rejects_a_consistent_but_wrong_client_hash_before_put():
    provider = StreamingProvider(fixture("warm"))
    provider.created = provider.linked = True
    row = fixture("warm")["files"][0]
    request = SimpleNamespace(
        body=json.dumps(
            {
                "files": [
                    {"filename": row["path"], "file_size": row["size"], "sha256_hash": "0" * 64}
                ]
            }
        ).encode()
    )
    with pytest.raises(AssertionError):
        provider.presign(request, 1)
    assert provider.presign_calls == provider.put_calls == 0 and not provider.objects


def test_worker_rejects_editable_install_before_network(tmp_path):
    from tests.fixtures.upload_native_control import ROOT

    provenance = tmp_path / "source.json"
    provenance.write_text(json.dumps({"source_sha256": {}, "locked_runtime": {}}))
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "tests/fixtures/upload_native_client.py"),
            "--ca",
            str(tmp_path / "absent.pem"),
            "--port",
            "1",
            "--warm-port",
            "2",
            "--prefix",
            sys.prefix,
            "--provenance",
            str(provenance),
            "--work",
            str(tmp_path / "absent"),
            "--warm",
            str(tmp_path / "also-absent"),
        ],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0 and not result.stdout
    assert b"product import escaped the selected installed environment" in result.stderr
    assert not (tmp_path / "absent").exists()


def test_separate_streaming_sink_public_flow_observes_closed_bounded_resources(
    tmp_path, monkeypatch
):
    from tests.fixtures.upload_network import loopback_upload

    cert = certificate(tmp_path / "cert", names=("api.ssyz.org.tr",))
    work = prepared(tmp_path / "work", "warm")
    monkeypatch.setenv(KEY_ENV, KEY)
    metrics = Metrics()
    with server(tmp_path / "server", cert, "warm") as ready:
        assert ready["pid"] != os.getpid()
        with loopback_upload(cert[0], ready["port"], metrics):
            result = flow(work)
    assert result.data.operation_status == "succeeded"
    observed = metrics.summary()
    assert observed["source_bytes"] == observed["confirmed_bytes"] == 1_048_576
    assert observed["confirmed_files"] == 3 and observed["max_source_chunk_bytes"] <= 1_048_576
    assert 1 <= observed["peak_sources"] <= 2
    assert 1 <= observed["peak_connections"] <= 2
    assert 1 <= observed["peak_puts"] <= 2
    assert observed["open_sources"] == observed["open_connections"] == 0
    assert observed["active_requests"] == observed["active_puts"] == 0
    assert len(observed["sessions"]) == 3
    assert len(observed["put_seconds"]) == 3
    assert all(0 < elapsed <= 120 for elapsed in observed["put_seconds"])
    assert len(observed["request_seconds"]) == sum(
        row["read_attempts"] + row["effect_attempts"] for row in observed["sessions"]
    )
    found = json.loads((tmp_path / "server/stdout.json").read_bytes())
    assert found["received"] == fixture("warm")["files"]
    assert 0 < found["max_read_bytes"] <= 65_536 and found["errors"] == 0
    assert found["presign_calls"] == found["put_calls"] == found["confirm_calls"] == 3
    assert found["create_calls"] == found["link_calls"] == 1
    assert found["requests"]["POST"] == 8 and found["requests"]["PUT"] == 3
    assert found["active_requests"] == 0 and found["peak_active_requests"] <= 2
    assert (tmp_path / "server/stderr.txt").read_bytes() == b""


@pytest.mark.parametrize("kind", ["connection", "response"])
def test_failed_close_cannot_claim_released_resource(kind):
    metrics = Metrics()

    async def fail():
        raise OSError("synthetic close failure")

    if kind == "connection":
        wrapped = CountingStream(SimpleNamespace(aclose=fail), Connection(metrics))
    else:
        metrics.request_started(True)
        wrapped = CountedResponse(SimpleNamespace(aclose=fail), metrics, True)
    close = wrapped.aclose()
    with pytest.raises(OSError):
        asyncio.run(close)
    assert metrics.open_connections == (kind == "connection")
    assert metrics.active_requests == (kind == "response")
