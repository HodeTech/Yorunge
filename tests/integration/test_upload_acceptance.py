"""Public CLI recovery before first ID and maximum normal-file upload acceptance."""

import hashlib
import json
import shutil
import signal
import subprocess
import time

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import UploadProvider
from tests.integration.test_upload_cli import approved_cli, command, execute, result
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.datasets import DatasetBudget


def inventory(inputs, count):
    data, artifact, config = inputs
    (data[1] / "one.bin").unlink()
    for index in range(count):
        (data[1] / f"file-{index:03}.bin").write_bytes(index.to_bytes(2, "big"))
    with open_dataset(data[1], DatasetBudget()) as tree:
        manifest = tree.scan()
    artifact.write_bytes(manifest.encoded())
    return (*data[:2], manifest, *data[3:]), artifact, config


@pytest.mark.parametrize("boundary", ["admission", "create-intent"])
def test_cli_sigkill_before_first_id_is_recovered_by_documented_local_commands(
    public_inputs, certificates, monkeypatch, boundary
):
    data, artifact, config = public_inputs
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    ready = config.parent / "checkpoint.ready"
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved_cli(server, public_inputs)
        args = command(
            server,
            "datasets",
            "upload",
            "start",
            "--plan-id",
            plan["plan_id"],
            "--config",
            str(config),
            "--state-dir",
            str(data[0]),
            "--output=json",
        )
        separator = args.index("--")
        args[separator:separator] = ["--checkpoint", boundary, "--ready", str(ready)]
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            end = time.monotonic() + 20
            while not ready.exists() and process.poll() is None and time.monotonic() < end:
                time.sleep(0.01)
            assert ready.exists(), "child did not reach its committed boundary"
            assert ready.read_bytes() == b"paused\n"
            process.kill()
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == -signal.SIGKILL
            assert not stdout
            assert not stderr  # The user has never received the operation ID.
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
        assert provider.create_calls == provider.link_calls == provider.put_calls == 0
        count = len(server.requests)
        config.unlink()
        artifact.unlink()
        shutil.rmtree(data[1])
        monkeypatch.delenv(ENV)
        local = ("--state-dir", str(data[0]), "--output=json")
        shown = result(
            execute(server, "datasets", "upload", "show", "--plan-id", plan["plan_id"], *local),
            "json",
        )
        page = result(
            execute(server, "datasets", "upload", "list", "--plan-id", plan["plan_id"], *local),
            "json",
        )
        assert page["uploads"] == [shown]
        assert page["next_cursor"] is None
        assert shown["operation_id"] is not None
        assert shown["operation_status"] == ("admitted" if boundary == "admission" else "running")
        with open_existing_store(data[0]) as store:
            view = StateUploads(store).show(operation_id=shown["operation_id"])
            before = view.operation.encoded()
            assert len(view.intents) == (0 if boundary == "admission" else 1)
            assert not view.receipts
            assert view.operation.dataset_id is None
        repeated = execute(
            server, "datasets", "upload", "start", "--plan-id", plan["plan_id"], *local
        )
        failure = json.loads(repeated.stderr)
        assert repeated.returncode == (2 if boundary == "admission" else 5)
        assert failure["operation_id"] == shown["operation_id"]
        assert not repeated.stdout
        assert failure["code"] == (
            "operation_conflict" if boundary == "admission" else "operation_uncertain"
        )
        assert len(server.requests) == count
        with open_existing_store(data[0]) as store:
            view = StateUploads(store).show(operation_id=shown["operation_id"])
            assert view.operation.encoded() == before
            assert not view.receipts
            assert store.verify().store_schema_version == 7


def test_real_cli_maximum_file_inventory_has_complete_distinct_graph(public_inputs, certificates):
    inputs = inventory(public_inputs, 128)
    data, _, config = inputs
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = approved_cli(server, inputs)
        process = execute(
            server,
            "datasets",
            "upload",
            "start",
            "--plan-id",
            plan["plan_id"],
            "--config",
            str(config),
            "--state-dir",
            str(data[0]),
            "--output=json",
            timeout=300,
        )
        shown = result(process, "json")
        assert shown["operation_status"] == "succeeded"
        assert shown["verification_level"] == "metadata"
        assert not shown["authority_verified"]
        assert not shown["remote_bytes_verified"]
        assert provider.create_calls == provider.link_calls == 1
        assert provider.presign_calls == provider.put_calls == provider.confirm_calls == 128
        assert len(provider.objects) == len(provider.confirmed) == 128
        assert len({row["id"] for row in provider.confirmed.values()}) == 128
        keys = set()
        for file in data[2].files:
            selected = provider.presigns[file.path]
            key = selected["object_key"]
            assert key not in keys
            keys.add(key)
            actual = provider.objects[key]
            assert len(actual) == file.size
            assert hashlib.sha256(actual).hexdigest() == file.sha256
            remote = provider.confirmed[file.path]
            assert remote["original_filename"] == file.path
            assert remote["file_size_bytes"] == file.size
            assert remote["sha256_hash"] == file.sha256
        assert len({row["sha256_hash"] for row in provider.confirmed.values()}) == 128
        with open_existing_store(data[0]) as store:
            view = StateUploads(store).show(operation_id=shown["operation_id"])
            assert len(view.intents) == len(view.receipts) == 2 + 3 * 128
            assert all(receipt.result == "accepted" for receipt in view.receipts)
            for index in range(128):
                assert {i.kind for i in view.intents if i.file_index == index} == {
                    "presign",
                    "put",
                    "confirm",
                }
            assert view.verification is not None
            assert len(view.verification.files) == 128
            for observed, file in zip(view.verification.files, data[2].files, strict=True):
                assert observed.path_digest == hashlib.sha256(file.path.encode("utf-8")).hexdigest()
                assert (observed.size_bytes, observed.sha256) == (file.size, file.sha256)
                assert observed.item_id == provider.confirmed[file.path]["id"]
            assert store.verify().store_schema_version == 7
        count = len(server.requests)
        found = result(
            execute(
                server,
                "datasets",
                "upload",
                "start",
                "--plan-id",
                plan["plan_id"],
                "--state-dir",
                str(data[0]),
                "--output=json",
            ),
            "json",
        )
        assert found == shown
        assert len(server.requests) == count


def test_cli_file_129_is_rejected_before_http_or_saved_plan(public_inputs, certificates):
    data, artifact, config = inventory(public_inputs, 129)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        process = execute(
            server,
            "datasets",
            "upload",
            "plan",
            str(data[1]),
            "--manifest",
            str(artifact),
            "--name",
            "sample",
            "--project",
            SCOPE.project_id,
            "--owner-user",
            SCOPE.owner.id,
            "--modality",
            "VISION",
            "--unpriced",
            "--admission-policy",
            "explicit-attempt",
            "--config",
            str(config),
            "--profile",
            "test",
            "--state-dir",
            str(data[0]),
            "--output=json",
        )
        assert process.returncode == 2
        assert not process.stdout
        assert json.loads(process.stderr)["code"] == "input_budget_exceeded"
        assert not server.requests
        with open_existing_store(data[0]) as store:
            assert store.connection.execute("SELECT count(*) FROM upload_plans").fetchone()[0] == 0
            assert (
                store.connection.execute("SELECT count(*) FROM upload_operations").fetchone()[0]
                == 0
            )
            assert store.verify().store_schema_version == 7
