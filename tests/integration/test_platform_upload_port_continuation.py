"""A continuation through the port: its files alone, no create or link, a confirm that counts on.

The records are the lifecycle fixture's: a real store, a real admitted continuation and the arms its
repository commits. Presign and confirm travel over real TLS; the PUT receipt is the fixture's, as
there is no local folder behind the fixture's manifest.
"""

import json
import socket
import time
from urllib.parse import quote

import pytest

from tests.fixtures.continuation_history import DATASET_ID
from tests.fixtures.continuation_lifecycle import tick
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.integration.test_upload_http_budget import session
from yorunge.adapters.platform_upload_port import ObservedUploadPort
from yorunge.adapters.state import open_store
from yorunge.adapters.upload_store import read_any_view
from yorunge.application.http_transport import HttpCredential
from yorunge.application.upload_budget import UploadBudget
from yorunge.domain.capabilities import timestamp
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import UploadRequestLimits

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)
RAW_KEY = "objects/provider-resource-canary-31807"
API = f"/api/v1/datasets/{DATASET_ID}/upload/"


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-continuation-port-tls"),
        names=("localhost", "api.ssyz.org.tr"),
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def port_of(lifecycle, plan, *, value=None):
    bound = lifecycle.bound
    key = HttpCredential(
        "X-API-Key",
        bound.credential.secret,
        target=bound.credential.target,
        service_id="evren-platform",
    )
    value = value or UploadBudget(plan.request_limits, end=time.monotonic() + 60, read_only=False)
    port = ObservedUploadPort(
        plan, lifecycle.manifest, plan.scope, bound, key, value, utc_clock=lifecycle.clock.now
    )
    return port, key, value


def reply(value, **changes):
    return Reply(body=json.dumps(value).encode(), **changes)


def presigned(context, key=RAW_KEY):
    return {
        "presigned_urls": [
            {
                "filename": context.file.path,
                "sha256_hash": context.file.sha256,
                "file_size": context.file.size,
                "client_uid": context.client_uid,
                "object_key": key,
                "upload_url": f"/datasets/{DATASET_ID}/upload/put?key={quote(key, safe='')}",
            }
        ],
        "duplicates": [],
    }


def confirmed(count):
    return {"created": 1, "actual_count": count, "batch_duplicates": 0}


def saved(lifecycle, record, outcome):
    with open_store(lifecycle.root_dir, timeout=60) as store:
        return lifecycle.repository(store).receipt(
            record.operation_id, record.lease, outcome.receipt
        )


def put_of(lifecycle, record, plan, context):
    """The test's own PUT receipt for a file (no folder stands behind the fixture's manifest)."""
    lifecycle.arm(plan, record, "put", context.file_index)
    tick(lifecycle)
    with open_store(lifecycle.root_dir, timeout=60) as store:
        intent = read_any_view(store.connection, plan.plan_id).intents[-1]
        lifecycle.repository(store).receipt(
            record.operation_id,
            record.lease,
            StageReceipt(
                schema_version=1,
                intent_id=intent.intent_id,
                recorded_at=timestamp(lifecycle.clock.value),
                result="accepted",
                dataset_id=DATASET_ID,
                object_key=context.local_binding,  # what the presign receipt named
                sent_bytes=context.file.size,
                sent_sha256=context.file.sha256,
            ),
        )
    tick(lifecycle)


def presigned_and_put(lifecycle, plan, record, port, owned, index):
    """File ``index`` presigned over TLS, then put (by the fixture): the upload to confirm."""
    context = next(c for c in port.files(record.operation_id, DATASET_ID) if c.file_index == index)
    arm = lifecycle.arm(plan, record, "presign", index)
    outcome = owned.exchange(lambda client: port.prepare_presign(context).execute(client, arm))
    assert outcome.upload is not None
    saved(lifecycle, record, outcome)
    tick(lifecycle)
    put_of(lifecycle, record, plan, context)
    return outcome.upload


# --- what the port holds ------------------------------------------------------------------------


def test_a_continuations_contexts_are_its_selected_files_of_its_own_dataset(lifecycle):
    plan, record = lifecycle.admitted()
    port, _, _ = port_of(lifecycle, plan)
    found = port.files(record.operation_id, DATASET_ID)
    assert [c.file_index for c in found] == [1, 2] == list(plan.continuation.file_indices)
    assert {c.dataset_id for c in found} == {DATASET_ID}
    other = "00000000-0000-4000-8000-0000000000aa"
    with pytest.raises(YorungeError) as error:
        port.files(record.operation_id, other)
    assert error.value.code == "invalid_request"


def test_a_continuation_that_sends_nothing_has_no_contexts(lifecycle):
    plan, record = lifecycle.admitted(indices=())
    port, _, _ = port_of(lifecycle, plan)
    assert port.files(record.operation_id, DATASET_ID) == ()


def test_a_continuation_has_no_create_and_no_link_and_asks_the_budget_for_neither(lifecycle):
    plan, record = lifecycle.admitted()
    port, _, value = port_of(lifecycle, plan)
    before = value.snapshot()
    with pytest.raises(YorungeError) as error:
        port.prepare_create(record.operation_id)
    assert error.value.code == "invalid_request"
    with pytest.raises(YorungeError) as error:
        port.prepare_link(record.operation_id, DATASET_ID)
    assert error.value.code == "invalid_request"
    assert value.snapshot() == before


def test_the_budget_of_a_port_is_the_plans_own_limits(lifecycle):
    plan, _ = lifecycle.admitted()
    other = plan.request_limits.model_copy(update={"max_upload_bytes": 1})
    wrong = UploadBudget(other, end=time.monotonic() + 60, read_only=False)
    with pytest.raises(YorungeError) as error:
        port_of(lifecycle, plan, value=wrong)
    assert error.value.code == "invalid_request"
    original = UploadRequestLimits(
        max_create=1,
        max_project_link=1,
        max_presign=2,
        max_put=2,
        max_confirm=2,
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4 * 1_048_576,
        max_control_response_bytes=16 * 1_048_576,
        max_upload_bytes=plan.request_limits.max_upload_bytes,
    )
    # An original upload's limits are not a continuation's, whatever their numbers.
    with pytest.raises(YorungeError) as error:
        port_of(
            lifecycle,
            plan,
            value=UploadBudget(original, end=time.monotonic() + 60, read_only=False),
        )
    assert error.value.code == "invalid_request"


def test_a_file_context_of_another_port_is_not_one_of_this_ones(lifecycle):
    plan, record = lifecycle.admitted()
    port, _, _ = port_of(lifecycle, plan)
    port.files(record.operation_id, DATASET_ID)
    other, _, _ = port_of(lifecycle, plan)
    foreign = other.files(record.operation_id, DATASET_ID)[0]
    with pytest.raises(YorungeError) as error:
        port.prepare_presign(foreign)
    assert error.value.code == "invalid_request"


# --- the effects, over TLS, with the arms the repository committed ------------------------------


def test_the_requests_the_port_binds_are_the_ones_the_repository_armed(lifecycle, certificates):
    """A presign and a confirm armed by the repository are accepted by the port: same digest.

    The intent the repository commits carries a digest of the request, computed from the plan's
    own binding (its dataset); the port refuses an arm whose digest is not the one it computes
    from the context. Both being right, a continuation's requests are the same on both sides.
    """
    plan, record = lifecycle.admitted()
    port, key, value = port_of(lifecycle, plan)
    context = port.files(record.operation_id, DATASET_ID)[0]
    routes = {API + "presign": reply(presigned(context)), API + "confirm": reply(confirmed(1))}
    with TlsServer(certificates, routes) as server:
        owned, _ = session(server, key, value)
        with owned:
            upload = presigned_and_put(lifecycle, plan, record, port, owned, 1)
            arm = lifecycle.arm(plan, record, "confirm", 1)
            done = owned.exchange(
                lambda client: port.prepare_confirm(upload, confirmed_count=1).execute(client, arm)
            )
            assert done.receipt.result == "accepted"
    assert [r.path for r in server.requests] == [API + "presign", API + "confirm"]
    assert all(r.method == "POST" for r in server.requests)
    assert value.snapshot().effect_attempts == 2


@pytest.mark.parametrize("reported", [1, 2])
def test_a_confirm_into_a_dataset_that_held_a_file_may_report_either_count(
    lifecycle, certificates, reported
):
    # Files 1 and 2 of three are sent: the dataset held one before. The first confirm is the
    # operation's own first (count 1) and the dataset's second (count 2); both are the same event.
    plan, record = lifecycle.admitted()
    assert plan.continuation.remote_present_count == 1
    port, key, value = port_of(lifecycle, plan)
    context = port.files(record.operation_id, DATASET_ID)[0]
    routes = {
        API + "presign": reply(presigned(context)),
        API + "confirm": reply(confirmed(reported)),
    }
    with TlsServer(certificates, routes) as server:
        owned, _ = session(server, key, value)
        with owned:
            upload = presigned_and_put(lifecycle, plan, record, port, owned, 1)
            arm = lifecycle.arm(plan, record, "confirm", 1)
            done = owned.exchange(
                lambda client: port.prepare_confirm(upload, confirmed_count=1).execute(client, arm)
            )
    assert done.receipt.result == "accepted"


@pytest.mark.parametrize("reported", [0, 3, 4, 128])
def test_a_confirm_that_reports_neither_count_is_not_an_accepted_receipt(
    lifecycle, certificates, reported
):
    plan, record = lifecycle.admitted()
    port, key, value = port_of(lifecycle, plan)
    context = port.files(record.operation_id, DATASET_ID)[0]
    routes = {
        API + "presign": reply(presigned(context)),
        API + "confirm": reply(confirmed(reported)),
    }
    with TlsServer(certificates, routes) as server:
        owned, _ = session(server, key, value)
        with owned:
            upload = presigned_and_put(lifecycle, plan, record, port, owned, 1)
            arm = lifecycle.arm(plan, record, "confirm", 1)
            with pytest.raises(YorungeError) as error:
                owned.exchange(
                    lambda client: port.prepare_confirm(upload, confirmed_count=1).execute(
                        client, arm
                    )
                )
    assert error.value.code == "invalid_response"
    with open_store(lifecycle.root_dir, timeout=60) as store:
        view = read_any_view(store.connection, plan.plan_id)
    confirm = [i for i in view.intents if i.kind == "confirm"]
    assert len(confirm) == 1  # the intent was committed, so the effect is uncertain...
    accepted_ids = {r.intent_id for r in view.receipts if r.result == "accepted"}
    assert confirm[0].intent_id not in accepted_ids  # ...and no receipt claims it took effect


# --- each count is judged on its own ------------------------------------------------------------


def confirm_of(owned, port, upload, place, arm):
    """The outcome of one confirm sent with ``arm`` (arguments, so that a loop binds nothing)."""
    return owned.exchange(
        lambda client: port.prepare_confirm(upload, confirmed_count=place).execute(client, arm)
    )


def two_confirms(lifecycle, certificates, first, second):
    """Files 1 and 2 of three (the dataset held one) confirmed, the provider counting ``first``
    and ``second``; the outcomes of the confirms, the second being an error when it is refused."""
    plan, record = lifecycle.admitted()
    assert plan.continuation.remote_present_count == 1
    port, key, value = port_of(lifecycle, plan)
    by_name = {c.file.path: c for c in port.files(record.operation_id, DATASET_ID)}
    answers = iter([first, second])

    def presign(request, count):
        context = by_name[json.loads(request.body)["files"][0]["filename"]]
        return reply(presigned(context, f"{RAW_KEY}-{context.file_index}"))

    routes = {
        API + "presign": presign,
        API + "confirm": lambda request, count: reply(confirmed(next(answers))),
    }
    outcomes = []
    with TlsServer(certificates, routes) as server:
        owned, _ = session(server, key, value)
        with owned:
            for index, place in ((1, 1), (2, 2)):
                upload = presigned_and_put(lifecycle, plan, record, port, owned, index)
                arm = lifecycle.arm(plan, record, "confirm", index)
                try:
                    outcome = confirm_of(owned, port, upload, place, arm)
                except YorungeError as error:
                    outcomes.append(error)
                    break
                saved(lifecycle, record, outcome)
                tick(lifecycle)
                outcomes.append(outcome)
    return outcomes


@pytest.mark.parametrize(
    "first,second",
    [(1, 2), (2, 3), (1, 3), (2, 2)],
    ids=[
        "the operation's counts",
        "the dataset's counts",
        "the operation's, then the dataset's",
        "the dataset's, then the operation's",
    ],
)
def test_each_confirm_is_accepted_for_either_count_whatever_the_one_before_reported(
    lifecycle, certificates, first, second
):
    # Base 1: the first confirm may report 1 or 2, the second 2 or 3. The count is a secondary
    # alarm and what a provider's count means is unobserved, so the two are not tied together.
    outcomes = two_confirms(lifecycle, certificates, first, second)
    assert [o.receipt.result for o in outcomes] == ["accepted", "accepted"]


@pytest.mark.parametrize("first,second", [(1, 1), (2, 4), (1, 0), (2, 128)])
def test_a_second_count_that_is_neither_of_its_two_is_refused(
    lifecycle, certificates, first, second
):
    outcomes = two_confirms(lifecycle, certificates, first, second)
    assert len(outcomes) == 2 and outcomes[0].receipt.result == "accepted"
    assert isinstance(outcomes[1], YorungeError) and outcomes[1].code == "invalid_response"
