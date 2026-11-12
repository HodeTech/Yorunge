"""Real env, filesystem, SQLite and TLS prepare/approve journeys without HTTP writes."""

import asyncio
import socket
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial

import pytest

from tests.contracts.test_platform_upload_codec import PARAMETERS, SCOPE
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.integration.test_platform_upload_reader import json_reply, project
from tests.integration.test_upload_http_budget import SECRET, session
from yorunge import api
from yorunge.adapters import upload_preparation as composition
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_input_files import UploadInputObservation
from yorunge.adapters.upload_repository import StateUploads
from yorunge.application.datasets import DatasetBudget
from yorunge.domain.credentials import (
    EnvReference,
    ResolvedCredential,
    SecretValue,
    normalize_target,
)
from yorunge.domain.dataset_upload import UploadParameters, UploadRoot, UploadStoragePolicy
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
ENV = "UPLOAD_PREPARATION_TEST_KEY"
PROJECT_PATH = f"/api/v1/projects/{SCOPE.project_id}"
STORAGE = UploadStoragePolicy(mode="proxy", origin=None)


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("prepare-tls"), names=("api.ssyz.org.tr", "localhost")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture
def prepared_input(tmp_path, monkeypatch):
    state, root = tmp_path / "state", tmp_path / "source"
    api.initialize_state(state_dir=state)
    root.mkdir()
    (root / "one.bin").write_bytes(b"original")
    with open_dataset(root, DatasetBudget()) as tree:
        manifest = tree.scan()
    monkeypatch.setenv(ENV, SECRET)
    context = Context(
        profile="test",
        project_id=SCOPE.project_id,
        account_id=SCOPE.owner.id,
        platform_url="https://api.ssyz.org.tr/api/v1",
        llm_url=Profile().llm_url,
    )
    return state, root, manifest, context, Profile(platform_key_env=ENV)


@contextmanager
def failure(code):
    with pytest.raises(YorungeError) as raised:
        yield
    assert raised.value.code == code


def routes():
    return {
        "/api/v1/auth/me": json_reply({"success": True, "data": {"id": SCOPE.owner.id}}),
        PROJECT_PATH: json_reply(project()),
    }


def runtime(data, server=None, **kwargs):
    state, _, _, context, profile = data

    def factory(key, budget):
        assert server is not None, "unexpected HTTP"
        return session(server, key, budget)[0]

    return composition.UploadPreparationRuntime(
        context, profile, state, session_factory=factory, **kwargs
    )


def prepare(value, data, **changes):
    options = dict(
        owner=SCOPE.owner,
        parameters=PARAMETERS,
        storage=STORAGE,
        admission_policy="explicit_attempt",
        cost_policy="unpriced_accepted",
        budget_micros=None,
    )
    return value.prepare(data[1], data[2], **(options | changes))


def counts(state):
    with open_existing_store(state) as store:
        return tuple(
            store.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("upload_plans", "upload_approvals", "upload_operations")
        )


def approve(value, plan, **changes):
    options = dict(acknowledge_unverified_authority=True, acknowledge_unpriced_cost=True)
    return value.approve(plan.plan_id, plan.digest, **(options | changes))


def test_prepare_approve_revoke_real_journey(prepared_input, certificates, monkeypatch, caplog):
    reads = []
    original = EnvSecretReader.read

    def read(self, reference):
        reads.append(reference)
        return original(self, reference)

    monkeypatch.setattr(EnvSecretReader, "read", read)
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input)
        assert plan.status == "attempt_ready"
        assert plan.inputs_verified
        assert plan.grant is plan.cost_bound is None
        assert not plan.executable
        assert plan.risks == ("authority_unverified", "cost_unverified")
        assert not plan.blockers
        assert plan.root.anchor == str(prepared_input[1])
        assert plan.manifest.digest == prepared_input[2].digest
        assert plan.request_limits.max_presign == 1
        assert plan.request_limits.max_upload_bytes == 8
        assert len(reads) == 1
        assert counts(prepared_input[0]) == (1, 0, 0)
        approval = approve(value, plan)
        assert approval.plan_digest == plan.digest
        assert approval.status == "approved"
        assert counts(prepared_input[0]) == (1, 1, 0)
        assert len(reads) == 2
        monkeypatch.delenv(ENV)
        (prepared_input[1] / "one.bin").unlink()
        view = value.revoke(plan.plan_id)
        assert view.approval.status == "revoked"
        assert len(reads) == 2
        assert len(server.requests) == 4
        assert all(r.method == "GET" for r in server.requests)
        assert all(r.header("X-API-Key") == SECRET for r in server.requests)
    assert SECRET not in plan.encoded().decode() + repr(value) + caplog.text


def test_the_connection_of_a_prepare_is_one_phase_of_thirty_seconds(prepared_input, certificates):
    seen = []

    def factory(key, budget):
        seen.append(budget.end - time.monotonic())
        return session(server, key, budget)[0]

    state, _, _, context, profile = prepared_input
    with TlsServer(certificates, routes()) as server:
        value = composition.UploadPreparationRuntime(
            context, profile, state, session_factory=factory
        )
        prepare(value, prepared_input)
    assert len(seen) == 1
    assert 25.0 < seen[0] <= 30.0  # the freshness rule of the reads: 30 seconds


@pytest.mark.parametrize("admission", ["verified_only", "explicit_attempt"])
def test_numeric_budget_remains_draft_without_provider_quote(
    prepared_input, certificates, admission
):
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(
            value,
            prepared_input,
            admission_policy=admission,
            cost_policy="bounded_required",
            budget_micros=200_000_000,
        )
        assert plan.status == "draft"
        assert "cost_unverified" in plan.blockers
        with failure("upload_plan_not_valid"):
            approve(value, plan)
        assert len(server.requests) == 2
        assert counts(prepared_input[0]) == (1, 0, 0)


@pytest.mark.parametrize(
    "change,code",
    [
        ({"admission_policy": "verified_only"}, "invalid_request"),
        ({"cost_policy": "bounded_required"}, "invalid_request"),
        ({"budget_micros": True}, "invalid_request"),
        (
            {"storage": UploadStoragePolicy(mode="direct", origin="https://storage.example")},
            "unsupported_combination",
        ),
        ({"parameters": PARAMETERS.model_copy(update={"name": 71})}, "invalid_request"),
    ],
)
def test_local_policy_failure_precedes_env_state_hash_http(
    prepared_input, monkeypatch, change, code
):
    value = runtime(prepared_input)

    def forbidden(*args, **kwargs):
        raise AssertionError("local rejection must precede dependency access")

    monkeypatch.setattr(composition, "open_existing_store", forbidden)
    monkeypatch.setattr(EnvSecretReader, "read", forbidden)
    monkeypatch.setattr(composition, "capture_upload_input", forbidden)
    with failure(code):
        prepare(value, prepared_input, **change)


def test_missing_store_is_not_initialized(prepared_input, tmp_path):
    data = (tmp_path / "missing", *prepared_input[1:])
    value = runtime(data)
    with failure("state_invalid"):
        prepare(value, data)
    assert not data[0].exists()


def test_hash_and_network_never_hold_sqlite_store(prepared_input, certificates, monkeypatch):
    opened = 0
    existing = composition.open_existing_store
    capture = composition.capture_upload_input

    @contextmanager
    def store(*args, **kwargs):
        nonlocal opened
        with existing(*args, **kwargs) as value:
            opened += 1
            try:
                yield value
            finally:
                opened -= 1

    def hash_input(*args, **kwargs):
        assert opened == 0
        return capture(*args, **kwargs)

    def reply(request, count):
        assert opened == 0
        # Another connection can acquire the writer lock during remote I/O.
        with open_existing_store(prepared_input[0]) as value:
            value.connection.execute("BEGIN IMMEDIATE")
            value.connection.execute("ROLLBACK")
        return routes()[request.path]

    monkeypatch.setattr(composition, "open_existing_store", store)
    monkeypatch.setattr(composition, "capture_upload_input", hash_input)
    with TlsServer(certificates, {path: reply for path in routes()}) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input)
        approve(value, plan)
    assert opened == 0


@pytest.mark.parametrize("stage", ["prepare", "approve"])
@pytest.mark.parametrize(
    "status,code",
    [
        (401, "remote_access_denied"),
        (403, "remote_access_denied"),
        (404, "invalid_response"),
        (405, "invalid_response"),
        (429, "remote_rate_limited"),
        (500, "remote_failed"),
    ],
)
def test_remote_negatives_cannot_save_plan_or_approval(
    prepared_input, certificates, stage, status, code
):
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input) if stage == "approve" else None
        server.routes[PROJECT_PATH] = Reply(status=status, body=b"private-untrusted-body")
        with failure(code):
            if plan is None:
                prepare(value, prepared_input)
            else:
                approve(value, plan)
        assert counts(prepared_input[0]) == (int(plan is not None), 0, 0)
        assert all(r.method == "GET" for r in server.requests)


@pytest.mark.parametrize("stage", ["prepare", "approve"])
@pytest.mark.parametrize("race", ["credential", "reset", "clock", "files"])
def test_remote_window_change_rejects_final_mutation(prepared_input, certificates, stage, race):
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input) if stage == "approve" else None

        def change(request, count):
            if race == "files":
                (prepared_input[1] / "one.bin").write_bytes(b"modified")
            elif race == "reset":
                preview = api.preview_identity_reset(state_dir=prepared_input[0]).data
                api.reset_identity(preview.digest, state_dir=prepared_input[0])
            elif race == "clock":
                with open_existing_store(prepared_input[0]) as store:
                    store.connection.execute(
                        "UPDATE cache_clock SET clock_generation=clock_generation+1"
                    )
            else:
                with open_existing_store(prepared_input[0]) as store:
                    StateCredentialRegistry(store).observe(
                        ResolvedCredential(
                            EnvReference(service_id="evren-platform", name=ENV),
                            normalize_target(prepared_input[3].platform_url),
                            SecretValue("rotated-private-key"),
                        )
                    )
            return routes()[PROJECT_PATH]

        server.routes[PROJECT_PATH] = change
        with failure("input_changed" if race == "files" else "state_changed"):
            prepare(value, prepared_input) if plan is None else approve(value, plan)
        assert counts(prepared_input[0]) == (int(plan is not None), 0, 0)


@pytest.mark.parametrize("mode", ["digest", "ack", "extra_ack", "duplicate", "input"])
def test_approve_preflight_rejects_without_new_http(prepared_input, certificates, mode):
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input)
        if mode == "duplicate":
            approve(value, plan)
        if mode == "input":
            (prepared_input[1] / "one.bin").write_bytes(b"new-data")
        before = len(server.requests)
        expected = {
            "digest": "upload_plan_not_valid",
            "ack": "approval_required",
            "extra_ack": "invalid_request",
            "duplicate": "operation_conflict",
            "input": "input_changed",
        }[mode]
        with failure(expected):
            if mode == "digest":
                value.approve(plan.plan_id, "0" * 64)
            else:
                approve(
                    value,
                    plan,
                    **(
                        {"acknowledge_unverified_authority": False}
                        if mode == "ack"
                        else {"acknowledge_unpriced_cost": 1}
                        if mode == "extra_ack"
                        else {}
                    ),
                )
        assert len(server.requests) == before


def test_async_loop_and_cross_thread_reject_before_dependencies(prepared_input, monkeypatch):
    value = runtime(prepared_input)

    def forbidden(*args, **kwargs):
        raise AssertionError("owner gate must run first")

    monkeypatch.setattr(composition, "open_existing_store", forbidden)
    monkeypatch.setattr(EnvSecretReader, "read", forbidden)

    async def inside():
        with failure("invalid_request"):
            prepare(value, prepared_input)
        with failure("invalid_request"):
            runtime(prepared_input)

    asyncio.run(inside())
    result = []

    def worker():
        try:
            prepare(value, prepared_input)
        except YorungeError as error:
            result.append(error.code)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert result == ["invalid_request"]


def test_commit_rechecks_preparation_freshness(prepared_input, certificates, monkeypatch):
    class Clock:
        value = datetime.now(UTC)

        def now(self):
            return self.value

        def monotonic(self):
            return time.monotonic()

    clock = Clock()
    original = StateUploads._preparation_check

    def delayed(plan, check, stamp, gate):
        original(plan, check, stamp, gate)
        clock.value += timedelta(seconds=31)

    monkeypatch.setattr(StateUploads, "_preparation_check", staticmethod(delayed))
    with TlsServer(certificates, routes()) as server:
        with failure("upload_plan_not_valid"):
            prepare(runtime(prepared_input, server, clock=clock), prepared_input)
    assert counts(prepared_input[0]) == (0, 0, 0)


@pytest.mark.parametrize("part", ["name", "account", "project"])
def test_selected_literal_in_local_fields_never_reaches_http_or_plan(
    prepared_input, certificates, monkeypatch, part
):
    data = prepared_input
    changes = {}
    if part == "name":
        changes["parameters"] = PARAMETERS.model_copy(update={"name": SECRET})
    elif part == "account":
        data = (*data[:3], data[3].model_copy(update={"account_id": SECRET}), data[4])
    else:
        monkeypatch.setenv(ENV, SCOPE.project_id)
    with TlsServer(certificates, routes()) as server:
        with failure("invalid_request"):
            prepare(runtime(data, server), data, **changes)
        assert not server.requests
        assert counts(data[0]) == (0, 0, 0)


def test_env_is_resolved_once_and_not_replaced_during_http(
    prepared_input, certificates, monkeypatch
):
    def replace_env(request, count):
        monkeypatch.setenv(ENV, "new-parent-env-key")
        return routes()[request.path]

    with TlsServer(certificates, routes() | {"/api/v1/auth/me": replace_env}) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input)
        assert all(record.header("X-API-Key") == SECRET for record in server.requests)
        before = len(server.requests)
        with failure("state_changed"):
            approve(value, plan)
        assert len(server.requests) == before
        assert counts(prepared_input[0]) == (1, 0, 0)


@pytest.mark.parametrize("bad", ["missing", "other", "profile_mismatch"])
def test_context_rejections_precede_secret_and_hash(prepared_input, monkeypatch, bad):
    context, profile = prepared_input[3:]
    if bad == "missing":
        context = context.model_copy(update={"project_id": None})
    elif bad == "other":
        context = context.model_copy(update={"platform_url": "https://other.example/api/v1"})
        profile = profile.model_copy(update={"platform_url": context.platform_url})
    else:
        profile = profile.model_copy(update={"platform_url": "https://other.example/api/v1"})
    data = (*prepared_input[:3], context, profile)

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid target before env/state/hash")

    monkeypatch.setattr(EnvSecretReader, "read", forbidden)
    monkeypatch.setattr(composition, "open_existing_store", forbidden)
    with failure(
        {
            "missing": "invalid_request",
            "other": "unsupported_combination",
            "profile_mismatch": "state_changed",
        }[bad]
    ):
        prepare(runtime(data), data)


def test_local_revoke_does_not_load_context_or_env(prepared_input, certificates, monkeypatch):
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input)
        approve(value, plan)
        before = len(server.requests)

        def forbidden(*args, **kwargs):
            raise AssertionError("revoke is local")

        monkeypatch.setattr(EnvSecretReader, "read", forbidden)
        view = composition.revoke_upload_approval(plan.plan_id, prepared_input[0])
        assert view.approval.status == "revoked"
        assert len(server.requests) == before


def test_latched_namespace_preflight_returns_same_operation_before_hash_or_http(
    prepared_input, certificates, monkeypatch
):
    with TlsServer(certificates, routes()) as server:
        value = runtime(prepared_input, server)
        plan = prepare(value, prepared_input)
        approve(value, plan)
        bound, scope = value._bind(plan.scope.owner)
        inputs = composition.capture_upload_input(
            prepared_input[1],
            prepared_input[2],
            bound.credential.secret,
            end=time.monotonic() + 900,
        )
        owned, reader = value._http(bound, scope, plan.request_limits, time.monotonic() + 30)
        with owned:
            check = owned.exchange(
                lambda client: reader.current(client, plan, inputs, action="create_private_dataset")
            )
        with open_existing_store(prepared_input[0]) as store:
            repository = StateUploads(store, bound)
            record = repository.admit(plan.plan_id, check)
            repository.arm(
                record.operation_id,
                record.lease,
                check,
                "create",
                None,
                total_end=time.monotonic() + 900,
            )
        before = len(server.requests)

        def forbidden(*args, **kwargs):
            raise AssertionError("latched namespace before hash")

        monkeypatch.setattr(composition, "capture_upload_input", forbidden)
        with pytest.raises(YorungeError) as raised:
            prepare(value, prepared_input)
        assert raised.value.code == "operation_conflict"
        assert raised.value.operation_id == record.operation_id
        assert len(server.requests) == before


@pytest.mark.parametrize("seconds,code", [(901, "upload_plan_not_valid"), (-1, "state_changed")])
@pytest.mark.parametrize("phase", ["recheck", "before_get"])
def test_clock_change_during_last_recheck_is_controlled_before_plan_seal(
    prepared_input, certificates, monkeypatch, seconds, code, phase
):
    class Clock:
        value = datetime.now(UTC)

        def now(self):
            return self.value

        def monotonic(self):
            return time.monotonic()

    clock = Clock()
    original = UploadInputObservation.recheck

    def changed(self):
        original(self)
        clock.value += timedelta(seconds=seconds)

    if phase == "recheck":
        monkeypatch.setattr(UploadInputObservation, "recheck", changed)
    else:
        observe = composition.ObservedUploadReader.preparation

        async def later(self, client):
            clock.value += timedelta(seconds=seconds)
            return await observe(self, client)

        monkeypatch.setattr(composition.ObservedUploadReader, "preparation", later)
    with TlsServer(certificates, routes()) as server:
        with failure(code):
            prepare(runtime(prepared_input, server, clock=clock), prepared_input)
        assert len(server.requests) == 2
        assert all(record.method == "GET" for record in server.requests)
    assert counts(prepared_input[0]) == (0, 0, 0)


def test_combined_plan_wire_preflight_rejects_legal_long_metadata_before_http(
    prepared_input, monkeypatch
):
    # Model-level long-path fixture: Darwin cannot create this 4,080-byte path.
    # Actual credential/SQLite phases run; this test claims no native Linux I/O.
    root = UploadRoot(anchor="/" + "/".join(["é" * 127] * 16), device=1, inode=1)
    parameters = UploadParameters(
        name="é" * 128,
        modality="MULTIMODAL",
        visibility="private",
        contributions_enabled=False,
        license="é" * 64,
        tags=tuple(str(index) + "x" * 127 for index in range(10)),
    )
    observed = composition.capture_upload_input(
        prepared_input[1], prepared_input[2], SecretValue(SECRET), end=time.monotonic() + 900
    )
    inputs = replace(observed, root=root)
    context = prepared_input[3].model_copy(update={"profile": "x" * 128})
    data = (*prepared_input[:3], context, prepared_input[4])
    monkeypatch.setattr(composition, "capture_upload_input", lambda *args, **kwargs: inputs)
    rejected_call = partial(prepare, runtime(data), data, parameters=parameters)
    with pytest.raises(YorungeError) as raised:
        rejected_call()
    assert raised.value.code == "invalid_request"
    assert raised.value.exit_code == 2
    assert raised.value.__context__ is raised.value.__cause__ is None
    assert counts(data[0]) == (0, 0, 0)


@pytest.mark.parametrize("size", [16383, 16384, 16385])
def test_seal_wire_exact_boundary_has_controlled_rejection(prepared_input, size):
    # Use the independent literal manifest and canonical plan shape to choose
    # a legal root whose encoded plan is exactly at the wire boundary.
    from pathlib import Path

    from tests.contracts.test_platform_upload_codec import PLAN
    from yorunge.application.upload_policy import UploadPreparationV2
    from yorunge.domain.dataset_manifest import DatasetManifest

    manifest = DatasetManifest.model_validate_json(
        (Path(__file__).parents[1] / "fixtures" / "dataset-manifest-v1.json").read_bytes()
    )
    parameters = UploadParameters(
        name="é" * 128,
        modality="MULTIMODAL",
        visibility="private",
        contributions_enabled=False,
        license="é" * 64,
        tags=tuple(str(index) + "x" * 127 for index in range(10)),
    )
    root = UploadRoot(anchor="/" + "/".join(["é" * 127] * 16), device=1, inode=1)
    # Shorter ASCII tags tune one byte at a time without crossing field bounds.
    work = PLAN.cost_work().model_copy(
        update={
            "scope": PLAN.scope.model_copy(update={"profile": "x" * 128}),
            "root": root,
            "parameters": parameters,
        }
    )
    work = type(work).model_validate_json(work.encoded())
    request = UploadPreparationV2(
        plan_id=PLAN.plan_id,
        work=work,
        manifest=manifest,
        admission_policy="explicit_attempt",
        cost_policy="unpriced_accepted",
        budget_micros=None,
        inputs_verified=True,
        grant=None,
        cost_bound=None,
        prepared_at=PLAN.prepared_at,
    )
    # Adjust using a test-only raw decoder seam to count the actual producer's
    # bytes; the real final _seal below uses the strict production decoder.
    from unittest.mock import patch

    with patch.object(type(PLAN), "model_validate_json", side_effect=lambda payload: payload):
        encoded = composition.prepare_upload_v2(request)
    excess = len(encoded) - size
    assert 127 < excess < 254
    tuned = parameters.model_copy(
        update={
            "tags": (
                parameters.tags[0][:1],
                parameters.tags[1][: -(excess - 127)],
                *parameters.tags[2:],
            )
        }
    )
    work = type(work).model_validate_json(work.model_copy(update={"parameters": tuned}).encoded())
    request = replace(request, work=work)
    if size <= 16384:
        result = composition._seal(request)
        assert len(result.encoded()) == size
    else:
        with pytest.raises(YorungeError) as raised:
            composition._seal(request)
        assert raised.value.code == "invalid_request"
        assert raised.value.__context__ is raised.value.__cause__ is None
