"""Real mandatory provider GETs, typed unknown authority, and current local inputs."""

import asyncio
import hashlib
import json
import logging
import shutil
import socket
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from tests.contracts.test_platform_upload_codec import DATASET, PARAMETERS, PLAN, SCOPE
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.integration.test_upload_http_budget import budget, credential, session
from yorunge.adapters.dataset_files import open_dataset
from yorunge.adapters.platform_upload_reader import ObservedUploadReader
from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.adapters.upload_input_files import capture_upload_input
from yorunge.application.datasets import DatasetBudget
from yorunge.domain.capabilities import canonical, timestamp
from yorunge.domain.dataset_upload import UploadOwner, manifest_reference
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.platform_upload import ProviderDataset

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
NOW = datetime(2026, 11, 2, 11, tzinfo=UTC)
PROJECT_PATH = f"/api/v1/projects/{SCOPE.project_id}"
OWNED_PATH = "/api/v1/datasets?page=1&page_size=128&scope=owned"
DETAIL_PATH = "/api/v1/datasets/sample-user/sample-dataset"
ROLE_PATH = f"/api/v1/datasets/{DATASET}/my-role"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-reader-tls"), names=("localhost", "api.ssyz.org.tr")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def json_reply(value, **changes):
    return Reply(body=json.dumps(value, ensure_ascii=False).encode(), **changes)


def project(scope=SCOPE):
    return {
        "id": scope.project_id,
        "owner_id": scope.owner.id,
        "org_id": None if scope.owner.kind == "user" else scope.owner.id,
        "visibility": "private",
    }


def dataset(scope=SCOPE, **changes):
    return {
        "id": DATASET,
        "name": PARAMETERS.name,
        "modality": PARAMETERS.modality,
        "visibility": "private",
        "contributions_enabled": False,
        "owner_id": scope.owner.id,
        "org_id": None if scope.owner.kind == "user" else scope.owner.id,
        **changes,
    }


def routes(scope=SCOPE, **changes):
    values = {
        "/api/v1/auth/me": json_reply({"success": True, "data": {"id": scope.owner.id}}),
        PROJECT_PATH: json_reply(project(scope)),
        OWNED_PATH: json_reply(
            [{**dataset(scope), "owner_username": "sample-user", "slug": "sample-dataset"}]
        ),
        DETAIL_PATH: json_reply(dataset(scope)),
        PROJECT_PATH + "/datasets": json_reply([{"id": DATASET}]),
        ROLE_PATH: json_reply({"role": "owner", "permissions": ["read", "upload"]}),
    }
    values.update(changes)
    return values


def current_input(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "file.bin").write_bytes(b"content")
    with open_dataset(root, DatasetBudget()) as tree:
        manifest = tree.scan()
    key = credential()
    observed = capture_upload_input(root, manifest, key.secret, end=time.monotonic() + 900)
    body = PLAN.model_dump(mode="json", exclude={"digest"})
    body.update(
        root=observed.root.model_dump(mode="json"),
        manifest=manifest_reference(manifest).model_dump(mode="json"),
    )
    body["request_limits"].update(
        max_presign=1, max_put=1, max_confirm=1, max_upload_bytes=manifest.total_bytes
    )
    plan = DatasetUploadPlanV2.model_validate_json(
        canonical({**body, "digest": hashlib.sha256(canonical(body)).hexdigest()})
    )
    return plan, observed, key


def reader(key, value, scope=SCOPE, clock=lambda: NOW):
    return ObservedUploadReader(scope, key, value, utc_clock=clock)


def test_real_preparation_is_two_reads_not_a_grant_or_cost(certificates, caplog):
    key, value = credential(), budget(readonly=True)
    source = reader(key, value)
    with TlsServer(certificates, routes()) as server:
        owned, instances = session(server, key, value)
        with caplog.at_level(logging.DEBUG), owned:
            check = owned.exchange(source.preparation)
        assert [record.path for record in server.requests] == ["/api/v1/auth/me", PROJECT_PATH]
        assert all(record.method == "GET" for record in server.requests)
        assert instances[0]._slots._value == 2 and not instances[0]._responses
    assert check.outcome == "not_exposed" and check.grant is None and check.error_code is None
    assert check.action == "create_private_dataset" and check.dataset_id is None
    assert check.checked_at == timestamp(NOW) and check.scope == SCOPE
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 2
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0
    assert key.secret.reveal() not in repr(check) + caplog.text


@pytest.mark.parametrize(
    "action,count",
    [("create_private_dataset", 2), ("link_project", 4), ("upload_created_dataset", 6)],
)
def test_real_current_proof_binds_full_input_and_exact_expected_dataset(
    tmp_path, certificates, action, count
):
    plan, inputs, key = current_input(tmp_path)
    value = budget()
    source = reader(key, value)
    baseline = None if action == "create_private_dataset" else ProviderDataset(**dataset())
    with TlsServer(certificates, routes()) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.current(
                    client, plan, inputs, action=action, expected_dataset=baseline
                )
            )
        assert len(server.requests) == count and all(
            record.method == "GET" for record in server.requests
        )
    assert check.saved_plan_id == plan.plan_id and check.saved_plan_digest == plan.digest
    assert check.work_digest == plan.cost_work().digest() and check.inputs_verified
    assert (
        check.baseline_grant
        is check.baseline_cost_bound
        is check.supplemental_grant
        is check.supplemental_cost_bound
        is None
    )
    assert check.authorization.outcome == "not_exposed" and check.authorization.grant is None
    check.require_current(
        plan,
        now=timestamp(NOW),
        action=action,
        dataset_id=None if baseline is None else baseline.id,
    )
    assert (check.upload_observation is not None) is (action == "upload_created_dataset")
    assert value.snapshot().read_requests == count and value.snapshot().effect_attempts == 0


@pytest.mark.parametrize("endpoint", ["/api/v1/auth/me", PROJECT_PATH, ROLE_PATH])
@pytest.mark.parametrize(
    "status,outcome,code",
    [
        (401, "denied", "remote_access_denied"),
        (403, "denied", "remote_access_denied"),
        (404, "invalid", "invalid_response"),
        (405, "invalid", "invalid_response"),
        (302, "invalid", "invalid_response"),
        (429, "unavailable", "remote_rate_limited"),
        (500, "unavailable", "remote_failed"),
        (503, "unavailable", "remote_failed"),
    ],
)
def test_mandatory_statuses_never_become_absent_authority(
    tmp_path, certificates, endpoint, status, outcome, code
):
    plan, inputs, key = current_input(tmp_path)
    value, values = budget(), routes()
    values[endpoint] = Reply(status=status, body=b"PRIVATE-ERROR-BODY")
    source = reader(key, value)
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.current(
                    client,
                    plan,
                    inputs,
                    action="upload_created_dataset",
                    expected_dataset=ProviderDataset(**dataset()),
                )
            )
        assert all(record.method == "GET" for record in server.requests)
        assert value.snapshot().read_attempts == len(server.requests)
    assert (check.authorization.outcome, check.authorization.error_code) == (outcome, code)
    assert check.authorization.grant is None and check.upload_observation is None
    assert value.snapshot().effect_attempts == value.snapshot().response_pending == 0
    assert "PRIVATE-ERROR-BODY" not in check.model_dump_json()


@pytest.mark.parametrize(
    "fault",
    [
        "no_upload",
        "duplicate_permission",
        "role_false",
        "missing_context",
        "wrong_project_owner",
        "public_project",
        "secret_metadata",
        "duplicate_json",
        "nonfinite_json",
        "invalid_utf8",
        "false_success",
    ],
)
def test_mandatory_schema_and_known_negative_are_closed(tmp_path, certificates, fault):
    plan, inputs, key = current_input(tmp_path)
    value, values = budget(), routes()
    target = ROLE_PATH
    response = {"role": "owner", "permissions": ["read"]}
    if fault == "duplicate_permission":
        response["permissions"] = ["upload", "upload"]
    elif fault == "role_false":
        response["role"] = False
    elif fault == "missing_context":
        target, response = PROJECT_PATH, {"id": SCOPE.project_id}
    elif fault == "wrong_project_owner":
        target, response = (
            PROJECT_PATH,
            project() | {"owner_id": "00000000-0000-4000-8000-000000000099"},
        )
    elif fault == "public_project":
        target, response = PROJECT_PATH, project() | {"visibility": "public"}
    elif fault == "secret_metadata":
        response = {
            "role": "owner",
            "permissions": ["upload"],
            "ignored": {"value": key.secret.reveal()},
        }
    elif fault == "false_success":
        response = {"success": False, "data": {"role": "owner", "permissions": ["upload"]}}
    values[target] = json_reply(response)
    raws = {
        "duplicate_json": b'{"role":"owner","role":"owner","permissions":["upload"]}',
        "nonfinite_json": b'{"role":"owner","permissions":["upload"],"extra":NaN}',
        "invalid_utf8": b"\xff",
    }
    if fault in raws:
        values[target] = Reply(body=raws[fault])
    source = reader(key, value)
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.current(
                    client,
                    plan,
                    inputs,
                    action="upload_created_dataset",
                    expected_dataset=ProviderDataset(**dataset()),
                )
            )
    assert check.authorization.outcome == ("denied" if fault == "no_upload" else "invalid")
    assert check.authorization.error_code == (
        "remote_access_denied" if fault == "no_upload" else "invalid_response"
    )
    assert check.upload_observation is None and check.authorization.grant is None


def test_read_authorization_does_not_require_local_files_or_upload_permission(
    tmp_path, certificates
):
    _, inputs, key = current_input(tmp_path)
    shutil.rmtree(inputs.root.anchor)
    value, values = budget(readonly=True), routes()
    values[ROLE_PATH] = Reply(status=403)
    source = reader(key, value)
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.read_authorization(
                    client, ProviderDataset(**dataset()), PARAMETERS
                )
            )
        assert len(server.requests) == 5 and ROLE_PATH not in [
            record.path for record in server.requests
        ]
    assert (
        check.action == "read_created_dataset"
        and check.outcome == "not_exposed"
        and check.grant is None
    )


@pytest.mark.parametrize("field", ["org_id", "owner_id"])
def test_full_historical_owner_pair_is_checked_even_when_selected_owner_matches(
    certificates, field
):
    key, value = credential(), budget()
    scope = SCOPE
    expected = dataset()
    changed = "00000000-0000-4000-8000-000000000088"
    if field == "owner_id":
        scope = SCOPE.model_copy(
            update={"owner": UploadOwner(kind="organization", id=SCOPE.owner.id)}
        )
        expected = dataset(scope)
    baseline = ProviderDataset(**expected)
    values = routes(scope)
    values[DETAIL_PATH] = json_reply(expected | {field: changed})
    source = reader(key, value, scope)
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.read_authorization(client, baseline, PARAMETERS)
            )
    assert check.outcome == "invalid" and check.error_code == "invalid_response"


def test_file_change_during_mandatory_reads_does_not_yield_verified_inputs(tmp_path, certificates):
    plan, inputs, key = current_input(tmp_path)
    value, values = budget(), routes()

    def mutate(record, count):
        (tmp_path / "source" / "file.bin").write_bytes(b"CONTENT")
        return json_reply(project())

    values[PROJECT_PATH] = mutate
    source = reader(key, value)
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(
                lambda client: source.current(client, plan, inputs, action="create_private_dataset")
            )
        assert failure.value.code == "input_changed" and len(server.requests) == 2
    assert value.snapshot().effect_attempts == 0


def test_first_observation_timestamp_is_not_refreshed_at_probe_end(certificates):
    key, value, calls = credential(), budget(), []

    def clock():
        result = NOW if not calls else NOW + timedelta(seconds=31)
        calls.append(result)
        return result

    source = reader(key, value, clock=clock)
    with TlsServer(certificates, routes()) as server:
        owned, _ = session(server, key, value)
        with owned, pytest.raises(YorungeError) as failure:
            owned.exchange(source.preparation)
        assert failure.value.code == "upload_plan_not_valid" and len(server.requests) == 2
    assert value.snapshot().response_pending == 0


def test_changed_read_identity_keeps_historical_expected_dataset_immutable(certificates):
    key, value = credential(), budget(readonly=True)
    changed = SCOPE.model_copy(
        update={
            "identity_epoch": str(uuid.uuid4()),
            "clock_generation": SCOPE.clock_generation + 1,
            "credential_id": str(uuid.uuid4()),
        }
    )
    source = reader(key, value, changed)
    baseline = ProviderDataset(**dataset())
    before = baseline.encoded()
    with TlsServer(certificates, routes()) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.read_authorization(client, baseline, PARAMETERS)
            )
    assert check.scope == changed and check.scope != SCOPE
    assert baseline.encoded() == before and check.grant is None


@pytest.mark.parametrize("fault", ["expired", "scope", "input", "grant", "cost"])
def test_invalid_saved_plan_or_input_is_rejected_before_http(tmp_path, fault):
    from tests.contracts.test_upload_policy_v2 import grant_for
    from yorunge.application.upload_policy import UploadPreparationV2, prepare_upload_v2
    from yorunge.domain.upload_costs import UploadCostBoundV2

    plan, inputs, key = current_input(tmp_path)
    value, scope, now = budget(), SCOPE, NOW
    if fault == "expired":
        now += timedelta(seconds=901)
    elif fault == "scope":
        scope = SCOPE.model_copy(update={"clock_generation": SCOPE.clock_generation + 1})
    elif fault == "input":
        (tmp_path / "source" / "file.bin").write_bytes(b"CONTENT")
    else:
        cost = None
        if fault == "cost":
            payload = json.loads(
                (
                    Path(__file__).parents[1] / "fixtures/dataset-upload-cost-bound-v2.json"
                ).read_bytes()
            )
            payload.update(
                work_digest=plan.cost_work().digest(), scope=plan.scope.model_dump(mode="json")
            )
            cost = UploadCostBoundV2.model_validate_json(canonical(payload))
        plan = prepare_upload_v2(
            UploadPreparationV2(
                plan_id=plan.plan_id,
                work=plan.cost_work(),
                manifest=inputs.manifest,
                admission_policy="explicit_attempt",
                cost_policy="unpriced_accepted",
                budget_micros=None,
                inputs_verified=True,
                grant=grant_for(plan.cost_work(), "full") if fault == "grant" else None,
                cost_bound=cost,
                prepared_at=timestamp(NOW),
            )
        )
    source = reader(key, value, scope, clock=lambda: now)
    calls = []

    async def handler(wire):
        calls.append(wire)
        return httpx.Response(200, content=b"{}")

    async def run():
        async with UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(YorungeError) as failure:
                await source.current(client, plan, inputs, action="create_private_dataset")
            assert failure.value.code == (
                "input_changed" if fault == "input" else "upload_plan_not_valid"
            )

    asyncio.run(run())
    assert calls == [] and value.snapshot().read_requests == 0


@pytest.mark.parametrize("fault", ["short_missing", "cross_page_duplicate", "all_128_pages"])
def test_owned_lookup_is_bounded_exact_id_and_detects_observed_duplicates(fault):
    key, value = credential(), budget(readonly=True)
    source = reader(key, value)
    count = [0]

    async def handler(wire):
        count[0] += 1
        path = wire.url.path
        if path == "/api/v1/auth/me":
            result = {"success": True, "data": {"id": SCOPE.owner.id}}
        elif path == f"/api/v1/projects/{SCOPE.project_id}":
            result = project()
        else:
            assert path == "/api/v1/datasets"
            page = int(wire.url.params["page"])
            assert 1 <= page <= 128 and wire.url.params["page_size"] == "128"
            result = [
                {"id": str(uuid.UUID(int=1000 + (page - 1) * 128 + index))} for index in range(128)
            ]
            if fault == "short_missing":
                result.pop()
            if fault == "cross_page_duplicate" and page == 2:
                result = [
                    {"id": str(uuid.UUID(int=1000))},
                    {**dataset(), "owner_username": "sample-user", "slug": "sample-dataset"},
                ]
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(result).encode()))

    async def run():
        async with UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(handler)
        ) as client:
            return await source.read_authorization(client, ProviderDataset(**dataset()), PARAMETERS)

    check = asyncio.run(run())
    assert check.outcome == "invalid" and check.error_code == "invalid_response"
    assert count[0] == {"short_missing": 3, "cross_page_duplicate": 4, "all_128_pages": 130}[fault]
    assert value.snapshot().read_attempts == count[0] and value.snapshot().response_pending == 0


def test_owned_found_on_later_page_uses_only_returned_safe_username_slug():
    key, value = credential(), budget(readonly=True)
    source = reader(key, value)
    paths = []

    async def handler(wire):
        paths.append(str(wire.url))
        if wire.url.path == "/api/v1/datasets" and wire.url.params["page"] == "1":
            result = [{"id": str(uuid.UUID(int=1000 + index))} for index in range(128)]
        elif wire.url.path == "/api/v1/datasets":
            result = [{**dataset(), "owner_username": "sample-user", "slug": "sample-dataset"}]
        elif wire.url.path == "/api/v1/auth/me":
            result = {"success": True, "data": {"id": SCOPE.owner.id}}
        elif wire.url.path == f"/api/v1/projects/{SCOPE.project_id}":
            result = project()
        elif wire.url.path == f"/api/v1/projects/{SCOPE.project_id}/datasets":
            result = [{"id": DATASET}]
        else:
            assert wire.url.path == DETAIL_PATH
            result = dataset()
        return httpx.Response(200, stream=httpx.ByteStream(json.dumps(result).encode()))

    async def run():
        async with UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(handler)
        ) as client:
            return await source.read_authorization(client, ProviderDataset(**dataset()), PARAMETERS)

    check = asyncio.run(run())
    assert check.outcome == "not_exposed" and len(paths) == 6
    assert not any(path.split("?")[0].endswith(f"/datasets/{DATASET}") for path in paths)


def test_wrong_client_budget_and_local_secret_are_rejected_without_reads():
    key, value = credential(), budget()
    bad_scope = SCOPE.model_copy(update={"profile": key.secret.reveal()})
    with pytest.raises(YorungeError) as failure:
        reader(key, value, bad_scope)
    assert failure.value.code == "invalid_request"
    source = reader(key, value)
    calls = []

    async def handler(wire):
        calls.append(wire)
        return httpx.Response(200, content=b"{}")

    async def run():
        other = budget()
        async with UploadHttpxTransport(
            key, other, transport=httpx.MockTransport(handler)
        ) as client:
            with pytest.raises(YorungeError) as failure:
                await source.preparation(client)
            assert failure.value.code == "invalid_request"

    asyncio.run(run())
    assert calls == [] and value.snapshot().read_requests == 0


def test_new_negative_keeps_source_timeout_code_without_refreshing_a_positive():
    key, value, times = (
        credential(),
        budget(),
        iter([NOW, NOW + timedelta(seconds=31), NOW + timedelta(seconds=31)]),
    )
    source = reader(key, value, clock=lambda: next(times))

    async def handler(wire):
        raise httpx.ReadTimeout("PRIVATE-TIMEOUT-CANARY", request=wire)

    async def run():
        async with UploadHttpxTransport(
            key, value, transport=httpx.MockTransport(handler)
        ) as client:
            return await source.preparation(client)

    check = asyncio.run(run())
    assert check.outcome == "unavailable" and check.error_code == "transport_timeout"
    assert check.checked_at == timestamp(NOW + timedelta(seconds=31))
    assert check.grant is None and "PRIVATE-TIMEOUT-CANARY" not in check.model_dump_json()
    assert value.snapshot().read_attempts == 1 and value.snapshot().response_pending == 0


def test_oversized_mandatory_raw_response_is_invalid_and_keeps_consumed_quota(certificates):
    key, value, values = credential(), budget(), routes()
    values["/api/v1/auth/me"] = Reply(body=b"x" * (1_048_576 + 1))
    source = reader(key, value)
    with TlsServer(certificates, values) as server:
        owned, instances = session(server, key, value)
        with owned:
            check = owned.exchange(source.preparation)
        assert len(server.requests) == 1
        assert instances[0]._slots._value == 2 and not instances[0]._responses
    assert check.outcome == "invalid" and check.error_code == "invalid_response"
    assert value.snapshot().read_requests == value.snapshot().read_attempts == 1
    assert value.snapshot().response_bytes <= 1_048_576 and value.snapshot().response_pending == 0


@pytest.mark.parametrize("organization_owner", [False, True])
def test_reported_owner_fields_are_preserved_without_principal_inference(
    certificates, organization_owner
):
    key, value = credential(), budget()
    org = "00000000-0000-4000-8000-000000000077"
    scope = (
        SCOPE.model_copy(update={"owner": UploadOwner(kind="organization", id=org)})
        if organization_owner
        else SCOPE
    )
    expected = dataset(scope, owner_id=SCOPE.owner.id, org_id=org)
    baseline = ProviderDataset(**expected)
    values = routes(scope)
    values["/api/v1/auth/me"] = json_reply({"success": True, "data": {"id": SCOPE.owner.id}})
    values[PROJECT_PATH] = json_reply(project(scope) | {"owner_id": SCOPE.owner.id, "org_id": org})
    values[OWNED_PATH] = json_reply(
        [{**expected, "owner_username": "sample-user", "slug": "sample-dataset"}]
    )
    values[DETAIL_PATH] = json_reply(expected)
    source = reader(key, value, scope)
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned:
            check = owned.exchange(
                lambda client: source.read_authorization(client, baseline, PARAMETERS)
            )
    assert check.outcome == "not_exposed" and check.grant is None
    assert check.scope.owner == scope.owner and baseline.org_id == org


@pytest.mark.parametrize("advance", [1, 2])
def test_final_metadata_recheck_cannot_return_evidence_older_than_30_seconds(
    tmp_path, certificates, monkeypatch, advance
):
    from yorunge.adapters.upload_input_files import UploadInputObservation

    plan, inputs, key = current_input(tmp_path)
    value, now, checks = budget(), [NOW], [0]
    original = UploadInputObservation.recheck

    def recheck(observation):
        original(observation)
        checks[0] += 1
        if checks[0] == 2:
            now[0] += timedelta(seconds=advance)

    monkeypatch.setattr(UploadInputObservation, "recheck", recheck)
    values = routes()

    def delayed_context(record, count):
        now[0] += timedelta(seconds=29)
        return json_reply(project())

    values[PROJECT_PATH] = delayed_context
    source = reader(key, value, clock=lambda: now[0])
    with TlsServer(certificates, values) as server:
        owned, _ = session(server, key, value)
        with owned:
            if advance == 2:
                with pytest.raises(YorungeError) as failure:
                    owned.exchange(
                        lambda client: source.current(
                            client, plan, inputs, action="create_private_dataset"
                        )
                    )
                assert failure.value.code == "upload_plan_not_valid"
            else:
                check = owned.exchange(
                    lambda client: source.current(
                        client, plan, inputs, action="create_private_dataset"
                    )
                )
                assert check.checked_at == timestamp(NOW)
                check.require_current(
                    plan, now=timestamp(now[0]), action="create_private_dataset", dataset_id=None
                )
        assert len(server.requests) == 2
    assert checks[0] == 2 and value.snapshot().effect_attempts == 0
