"""Pre-HTTP content eligibility, lifecycle priority and unchanged legacy history."""

import json
import shutil
import time
from datetime import timedelta
from functools import partial
from types import SimpleNamespace

import pytest

from tests.contracts.test_platform_upload_codec import PARAMETERS, SCOPE
from tests.fixtures.http_server import TlsServer
from tests.fixtures.upload_provider import UploadProvider
from tests.integration.test_upload_cli import execute
from tests.integration.test_upload_http_budget import SECRET
from tests.integration.test_upload_original import factory, loader
from tests.integration.test_upload_preparation import ENV, approve, counts, prepare, runtime
from tests.integration.test_upload_preparation import certificates as certificates
from tests.integration.test_upload_preparation import loopback_only as loopback_only
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_public_api import public_inputs as public_inputs
from yorunge import api
from yorunge.adapters import upload_original, upload_preparation
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.datasets import DatasetBudget
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import MESSAGES, OperationError, YorungeError


def duplicated(inputs):
    data, artifact, config = inputs
    (data[1] / "private-duplicate-name-canary.bin").write_bytes(b"original")
    with open_dataset(data[1], DatasetBudget()) as tree:
        manifest = tree.scan()
    artifact.write_bytes(manifest.encoded())
    return (*data[:2], manifest, *data[3:]), artifact, config


def legacy(inputs, server, monkeypatch, *, approved=False, terminal=False, running=False):
    """Seed the real journal exactly as the writer before ADR-0028 could do.

    Only the new eligibility check is bypassed while constructing historical
    data. Current calls below always run with the real check restored.
    """
    data = inputs[0]
    with monkeypatch.context() as old:
        old.setattr(upload_preparation, "require_distinct_upload_content", lambda _: None)
        old.setattr(upload_original, "require_distinct_upload_content", lambda _: None)
        value = runtime(data, server)
        plan = prepare(value, data)
        if approved or terminal or running:
            approve(value, plan)
        if terminal or running:
            action = (
                upload_original.run_upload_original
                if terminal
                else upload_original.create_link_original
            )
            record = action(
                plan.plan_id, data[0], loader(data), session_factory=factory(server)
            ).record
            assert record.status == ("succeeded" if terminal else "running")
    return plan


def assert_duplicate(error):
    assert error.code == "upload_duplicate_content"
    assert error.exit_code == 2
    envelope = error.envelope()
    assert envelope["operation_id"] is None
    assert envelope["details"] == {}
    assert envelope["message"] == MESSAGES["upload_duplicate_content"]


@pytest.mark.parametrize("output", ["text", "json", "ndjson"])
def test_public_api_and_cli_duplicate_rejection_has_no_http_or_plan(
    public_inputs, certificates, output
):
    data, artifact, config = duplicated(public_inputs)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        with pytest.raises(YorungeError) as rejected:
            api.prepare_dataset_upload(
                data[1],
                manifest=artifact,
                owner=SCOPE.owner,
                parameters=PARAMETERS,
                project=SCOPE.project_id,
                admission_policy="explicit_attempt",
                unpriced=True,
                config=config,
                profile="test",
                state_dir=data[0],
            )
        assert_duplicate(rejected.value)
        process = execute(
            server,
            "datasets",
            "upload",
            "plan",
            str(data[1]),
            "--manifest",
            str(artifact),
            "--name",
            PARAMETERS.name,
            "--owner-user",
            SCOPE.owner.id,
            "--project",
            SCOPE.project_id,
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
            "--output",
            output,
        )
        assert process.returncode == 2
        assert not process.stdout
        assert MESSAGES["upload_duplicate_content"] in process.stderr.decode("utf-8")
        if output != "text":
            value = json.loads(process.stderr)
            # Before a stream opens, both machine modes use the safe error envelope.
            assert value == rejected.value.envelope()
        assert not server.requests
    assert counts(data[0]) == (0, 0, 0)
    for sentinel in (
        b"private-duplicate-name-canary",
        data[2].files[0].sha256.encode(),
        str(data[1]).encode(),
        SECRET.encode(),
    ):
        assert sentinel not in process.stdout + process.stderr
    with open_existing_store(data[0]) as store:
        assert store.connection.execute("SELECT count(*) FROM upload_namespaces").fetchone()[0] == 0


@pytest.mark.parametrize("action", ["approve", "start"])
def test_saved_duplicate_rejects_before_context_env_hash_and_business_writes(
    public_inputs, certificates, monkeypatch, action
):
    inputs = duplicated(public_inputs)
    data, _, config = inputs
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    with TlsServer(certificates, provider.routes()) as server:
        plan = legacy(inputs, server, monkeypatch, approved=action == "start")
        before = len(server.requests), counts(data[0])
        config.unlink()
        shutil.rmtree(data[1])
        monkeypatch.delenv(ENV)
        with open_existing_store(data[0]) as store:
            bindings = tuple(store.connection.execute("SELECT * FROM credential_bindings"))
        if action == "approve":
            invoke = partial(
                api.approve_dataset_upload,
                plan.plan_id,
                plan.digest,
                accept_unverified_authority=True,
                accept_unpriced_cost=True,
                config=config,
                state_dir=data[0],
            )
        else:
            invoke = partial(
                api.start_dataset_upload, plan.plan_id, config=config, state_dir=data[0]
            )
        with pytest.raises(YorungeError) as rejected:
            invoke()
        assert_duplicate(rejected.value)
        assert (len(server.requests), counts(data[0])) == before
        with open_existing_store(data[0]) as store:
            assert tuple(store.connection.execute("SELECT * FROM credential_bindings")) == bindings
            assert StateUploads(store).show(plan_id=plan.plan_id).operation is None


@pytest.mark.parametrize("case", ["digest", "ack", "expired", "approved", "start-unapproved"])
def test_lifecycle_errors_precede_duplicate_eligibility(
    public_inputs, certificates, monkeypatch, case
):
    inputs = duplicated(public_inputs)
    data = inputs[0]
    with TlsServer(
        certificates, UploadProvider(SCOPE.owner.id, SCOPE.project_id).routes()
    ) as server:
        plan = legacy(inputs, server, monkeypatch, approved=case == "approved")
        before = len(server.requests)
        clock = SimpleNamespace(
            now=lambda: instant(plan.expires_at) + timedelta(seconds=1), monotonic=time.monotonic
        )
        if case == "start-unapproved":
            invoke = partial(api.start_dataset_upload, plan.plan_id, state_dir=data[0])
        else:
            invoke = partial(
                upload_preparation.read_approval_input,
                plan.plan_id,
                "0" * 64 if case == "digest" else plan.digest,
                case != "ack",
                True,
                data[0],
                clock if case == "expired" else runtime(data).clock,
            )
        with pytest.raises(YorungeError) as raised:
            invoke()
        assert (
            raised.value.code
            == {
                "digest": "upload_plan_not_valid",
                "ack": "approval_required",
                "expired": "upload_plan_not_valid",
                "approved": "operation_conflict",
                "start-unapproved": "approval_required",
            }[case]
        )
        assert len(server.requests) == before


def test_new_prepare_input_change_precedes_duplicate_rule(public_inputs, certificates):
    data, _, _ = duplicated(public_inputs)
    (data[1] / "one.bin").write_bytes(b"changed!")
    with TlsServer(
        certificates, UploadProvider(SCOPE.owner.id, SCOPE.project_id).routes()
    ) as server:
        value = runtime(data, server)
        with pytest.raises(YorungeError) as raised:
            prepare(value, data)
        assert raised.value.code == "input_changed"
        assert not server.requests


@pytest.mark.parametrize("terminal", [False, True])
def test_duplicate_history_and_local_commands_survive_without_inputs(
    public_inputs, certificates, monkeypatch, terminal
):
    inputs = duplicated(public_inputs)
    data, artifact, config = inputs
    with TlsServer(
        certificates, UploadProvider(SCOPE.owner.id, SCOPE.project_id).routes()
    ) as server:
        plan = legacy(inputs, server, monkeypatch, terminal=terminal, running=not terminal)
        before = len(server.requests)
        with open_existing_store(data[0]) as store:
            encoded = StateUploads(store).show(plan_id=plan.plan_id).operation.encoded()
        shutil.rmtree(data[1])
        artifact.unlink()
        config.unlink()
        monkeypatch.delenv(ENV)
        if terminal:
            shown = api.start_dataset_upload(plan.plan_id, state_dir=data[0]).data
            assert shown.operation_status == "succeeded"
        else:
            with pytest.raises(OperationError) as existing:
                api.start_dataset_upload(plan.plan_id, state_dir=data[0])
            assert existing.value.code == "operation_uncertain"
            shown = api.show_dataset_upload(plan_id=plan.plan_id, state_dir=data[0]).data
            assert shown.operation_id == existing.value.operation_id
        assert api.show_dataset_upload(plan_id=plan.plan_id, state_dir=data[0]).data == shown
        assert api.list_dataset_uploads(plan_id=plan.plan_id, state_dir=data[0]).data.uploads == (
            shown,
        )
        assert api.review_dataset_upload(plan.plan_id, state_dir=data[0]).data.summary == shown
        revoked = api.revoke_dataset_upload(plan.plan_id, state_dir=data[0]).data
        assert revoked.approval_status == "revoked"
        with open_existing_store(data[0]) as store:
            assert StateUploads(store).show(plan_id=plan.plan_id).operation.encoded() == encoded
            assert store.verify().store_schema_version == 7
        assert len(server.requests) == before
