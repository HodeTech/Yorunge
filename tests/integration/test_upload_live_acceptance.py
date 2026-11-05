"""Synthetic TLS acceptance-runner tests; never a real account or installed-runtime claim."""

import hashlib
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import PARAMETERS, SCOPE
from tests.fixtures.http_server import Reply, TlsServer
from tests.fixtures.upload_network import loopback_upload
from tests.fixtures.upload_provider import DATASET, UploadProvider
from tests.integration.test_upload_file_workflow import certificates as certificates
from tests.integration.test_upload_file_workflow import loopback_only as loopback_only
from yorunge import api
from yorunge.domain.errors import OperationError, YorungeError

ROOT = Path(__file__).resolve().parents[2]


def inputs(tmp_path):
    root = tmp_path.resolve()
    config, credentials = root / "config.toml", root / "credentials.json"
    config.write_text("""schema_version = 1
active_profile = "pilot"
[profiles.pilot]
platform_url = "https://api.ssyz.org.tr/api/v1"
platform_key_env = "PILOT_PLATFORM_KEY"
""")
    credentials.write_text(json.dumps({"PILOT_PLATFORM_KEY": "synthetic-pilot-selected-key"}))
    for path in (config, credentials):
        path.chmod(0o600)
    return SimpleNamespace(
        config=config,
        credentials=credentials,
        workspace=root / "pilot",
        wheel=root / "unused.whl",
        project=SCOPE.project_id,
        accept_live_unpriced_write=True,
    )


def provenance_seam(helper, monkeypatch, wheel_changed=False):
    """Only isolated wheel provenance is a double; all API/state/HTTP/effects are real."""
    namespace = helper["run"].__globals__
    driver = runpy.run_path(str(ROOT / "scripts/benchmark-upload.py"))
    snapshots = []

    def wheel_snapshot(*args):
        snapshots.append(None)
        return {
            "metadata_sha256": {},
            "sha256": "changed" if wheel_changed and len(snapshots) > 1 else "original",
        }

    driver["WHEEL"]["snapshot"] = wheel_snapshot
    original = runpy.run_path

    def load(path):
        if path.endswith("upload_native_client.py"):
            return {"provenance": lambda *args: None}
        if path.endswith("benchmark-upload.py"):
            return driver
        return original(path)

    monkeypatch.setitem(namespace, "runpy", SimpleNamespace(run_path=load))
    monkeypatch.setitem(
        namespace, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=True), prefix=sys.prefix)
    )


@pytest.mark.parametrize("outcome", ["success", "partial_put", "wheel_changed"])
def test_real_api_graph_receipt_and_no_retry_workspace(
    tmp_path, certificates, monkeypatch, outcome
):
    helper = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
    args = inputs(tmp_path)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id, name="yorunge-acceptance-pilot")
    if outcome == "partial_put":
        provider.fail_put_name = "first.png"
    if outcome == "success":
        original_put = provider.put

        def echoed_put(request, count):
            response = original_put(request, count)
            return Reply(
                body=json.dumps(
                    {
                        "success": True,
                        "size": len(request.body),
                        "sha256_hash": hashlib.sha256(request.body).hexdigest(),
                    }
                ).encode(),
                status=response.status,
            )

        provider.put = echoed_put
    provenance_seam(helper, monkeypatch, wheel_changed=outcome == "wheel_changed")
    monkeypatch.setenv("PILOT_PLATFORM_KEY", "prior-env-value")
    with (
        TlsServer(certificates, provider.routes()) as server,
        loopback_upload(server.certificates[0], server.port),
    ):
        if outcome == "partial_put":
            with pytest.raises(OperationError) as stopped:
                helper["run"](args)
            receipt = json.loads((args.workspace / "receipt.json").read_bytes())
            assert receipt["reason_code"] == stopped.value.reason_code
            assert receipt["reason_code"] != "operation_uncertain"
            assert any(
                row["kind"] == "put" and row["http_status"] == 503
                for row in receipt["counters"]["control_responses"]
            )
        elif outcome == "wheel_changed":
            with pytest.raises(ValueError, match="wheel changed"):
                helper["run"](args)
            identity = json.loads((args.workspace / "operation-identity.json").read_bytes())
            current = api.show_dataset_upload(
                operation_id=identity["operation_id"], state_dir=args.workspace / "state"
            ).data
            assert current.operation_status == "succeeded"
            assert provider.confirm_calls == 2
        else:
            value = helper["run"](args)
            assert value["outcome"] == "metadata_succeeded"
            assert "same_hash_different_names" not in value
            assert value["fixture_file_count"] == 2
            assert value["distinct_content_hashes"] is True
            assert value["fixture_bytes"] == 158
            actual = value["counters"]["actual"]
            assert actual["read_requests"] == actual["read_attempts"] == 23
            assert actual["effect_attempts"] == 8
            assert actual["upload_bytes"] == 158
            assert value["counters"]["open_reservations"] == 0
            puts = [row for row in value["counters"]["control_responses"] if row["kind"] == "put"]
            assert {row["file_index"] for row in puts} == {0, 1}
            assert all(row["typed_accepted"] is True for row in puts)
            assert all(
                row["shape"]["root"]["matches_expected"]["sha256_hash"] is True for row in puts
            )
        count = len(server.requests)
        with pytest.raises(ValueError):
            helper["run"](args)
        assert len(server.requests) == count
        assert provider.create_calls == provider.link_calls == 1
    import os

    assert os.environ["PILOT_PLATFORM_KEY"] == "prior-env-value"
    receipt = (args.workspace / "receipt.json").read_bytes()
    assert provider.owner_id.encode() not in receipt
    assert SCOPE.project_id.encode() not in receipt
    assert b"synthetic-pilot-selected-key" not in receipt
    assert b"yorunge-acceptance-pilot" not in receipt
    assert json.loads(receipt)["outcome"] == (
        "metadata_succeeded" if outcome == "success" else "incomplete"
    )
    expected = {
        "first.png": "8f7eb0f9bebe51f1f6aceaf60bbb8e99a845b88e77cb86e0aaf66df9bb0b21aa",
        "different.png": "2ba82df1c51676319e2542bec023cc95fd9d594cc70b0d6b60cdaa9bafb77fd9",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((args.workspace / "source" / name).read_bytes()).hexdigest() == digest
    assert not (args.workspace / "source" / "same-content.png").exists()


def test_link_decoder_failure_retains_closed_trace_without_accepting_or_replaying(
    tmp_path, certificates, monkeypatch
):
    helper = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
    args = inputs(tmp_path)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id, name="yorunge-acceptance-pilot")
    provider.link_reply = Reply(
        body=json.dumps(
            {
                "message": "private-link-message-canary",
            }
        ).encode()
    )
    provenance_seam(helper, monkeypatch)
    with (
        TlsServer(certificates, provider.routes()) as server,
        loopback_upload(server.certificates[0], server.port),
    ):
        with pytest.raises(OperationError) as stopped:
            helper["run"](args)
        assert stopped.value.reason_code == "invalid_response"
        assert provider.create_calls == provider.link_calls == 1
        assert provider.confirm_calls == 0
        raw = (args.workspace / "receipt.json").read_bytes()
    trace = json.loads(raw)["counters"]["control_responses"]
    assert [row["kind"] for row in trace] == ["create", "project_link"]
    assert trace[0]["typed_accepted"] is True
    assert trace[1]["typed_accepted"] is False
    assert trace[1]["transport_2xx_accepted"] is True
    assert trace[1]["shape"]["root"]["matches_expected"] == {}
    assert b"private-link-message-canary" not in raw
    assert DATASET.encode() not in raw
    assert provider.owner_id.encode() not in raw


def test_no_consent_and_nonprivate_credential_files_fail_before_any_workspace(tmp_path):
    helper = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
    args = inputs(tmp_path)
    args.accept_live_unpriced_write = False
    with pytest.raises(ValueError):
        helper["run"](args)
    assert not args.workspace.exists()
    args.credentials.chmod(0o644)
    with pytest.raises(ValueError, match="private bounded"):
        helper["credential"](args.config, args.credentials)


def test_private_file_and_config_target_do_not_open_another_account_target(tmp_path):
    helper = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
    args = inputs(tmp_path)
    args.config.write_text(args.config.read_text().replace("api.ssyz.org.tr", "other.example"))
    with pytest.raises(ValueError, match="canonical Platform"):
        helper["credential"](args.config, args.credentials)
    alias = tmp_path / "alias"
    alias.symlink_to(args.credentials)
    with pytest.raises(ValueError, match="symlinks"):
        helper["private_file"](alias)


@pytest.mark.parametrize("failure", ["RuntimeError", "KeyboardInterrupt", "SystemExit"])
def test_pilot_main_stops_without_rendering_private_exception_chain(failure):
    import subprocess

    code = """
import builtins,runpy,sys
helper=runpy.run_path(sys.argv[1])
kind=getattr(builtins,sys.argv[2])
def failed(args):
    raise kind('private-exception-canary')
helper['main'].__globals__['run']=failed
sys.argv=['pilot','--project','00000000-0000-4000-8000-000000000004']
for option in ('config','credentials','workspace','wheel'):
    sys.argv.extend(['--'+option,'unused'])
raise SystemExit(helper['main']())
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            code,
            str(ROOT / "scripts/upload_live_acceptance.py"),
            failure,
        ],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert result.stdout == b""
    assert b"private-exception-canary" not in result.stderr
    assert b"Traceback" not in result.stderr
    assert b"Pilot stopped." in result.stderr


def test_frozen_three_pngs_remain_a_local_duplicate_negative(tmp_path, certificates, monkeypatch):
    helper = runpy.run_path(str(ROOT / "scripts/upload_live_acceptance.py"))
    assert len(helper["SELECTED_IMAGES"]) == len(set(helper["SELECTED_IMAGES"].values())) == 2
    frozen = runpy.run_path(str(helper["FROZEN"]))["fixtures"]()
    assert len(frozen) == 3
    assert len({hashlib.sha256(body).hexdigest() for _, body in frozen}) == 2
    args = inputs(tmp_path)
    args.workspace.mkdir()
    source = args.workspace / "source"
    source.mkdir()
    for name, body in frozen:
        (source / name).write_bytes(body)
    artifact, state = args.workspace / "manifest.json", args.workspace / "state"
    api.inspect_dataset(source, manifest_out=artifact)
    api.initialize_state(state_dir=state)
    monkeypatch.setenv("PILOT_PLATFORM_KEY", "synthetic-pilot-selected-key")
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with (
        TlsServer(certificates, provider.routes()) as server,
        loopback_upload(server.certificates[0], server.port),
    ):
        with pytest.raises(YorungeError) as rejected:
            api.prepare_dataset_upload(
                source,
                manifest=artifact,
                owner=SCOPE.owner,
                parameters=PARAMETERS,
                project=SCOPE.project_id,
                admission_policy="explicit_attempt",
                unpriced=True,
                config=args.config,
                state_dir=state,
            )
        assert rejected.value.code == "upload_duplicate_content"
        assert not server.requests
        assert api.list_dataset_uploads(state_dir=state).data.uploads == ()
