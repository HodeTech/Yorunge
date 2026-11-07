"""The resume report over a real interrupted upload: real files, real store, a TLS provider.

The source is made by the product itself: the original workflow runs against the provider until the
provider's lost answer stops it, so its journal is exactly what a real interruption leaves. The
provider's items are then changed to make each class and each blocker of the report.
"""

import hashlib
import json
import socket
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_http_budget import SECRET, session
from tests.integration.test_upload_original import approved, factory, loader
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import upload_files_original
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.domain.errors import OperationError, YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(
        tmp_path_factory.mktemp("upload-resume-tls"), names=("localhost", "api.ssyz.org.tr")
    )


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


def lose_confirm_of(provider, name, *, remembered=True):
    """The provider answers the confirm of ``name`` with a lost response.

    ``remembered`` says whether it kept the item (the confirm took effect) or not (it did not).
    """
    original = provider.confirm

    def confirm(request, count):
        if json.loads(request.body)["items"][0]["filename"] != name:
            return original(request, count)
        if remembered:
            answer = original(request, count)
            return Reply(status=answer.status, body=answer.body, truncate_at=3)
        return Reply(status=201, body=b'{"private":"response-lost"}', truncate_at=3)

    provider.confirm = confirm


def interrupted(data, server):
    """Run the original upload until the lost answer stops it; the operation it leaves."""
    plan = approved(data, server)
    with pytest.raises(OperationError) as stopped:
        upload_files_original(plan.plan_id, data[0], loader(data), session_factory=factory(server))
    assert stopped.value.code == "operation_uncertain"
    return stopped.value.operation_id


def resume_runtime(data, server=None, **kwargs):
    state, _, _, context, profile = data

    def build(key, budget):
        assert server is not None, "unexpected HTTP"
        return session(server, key, budget)[0]

    return UploadResumeRuntime(context, profile, state, session_factory=build, **kwargs)


def world(data):
    """Three files; the provider loses the answer to the confirm of the second."""
    data = many(data)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "two.bin")
    return data, provider


def test_a_report_classifies_the_files_of_an_interrupted_upload(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        before = len(server.requests)
        report = resume_runtime(data, server).resume(source, accept_unverified_read=True)
        counts = report.observation.class_counts
        assert (counts.confirmed, counts.observed, counts.pending_clean) == (1, 1, 1)
        assert counts.pending_uncertain == 0 and report.eligible
        assert report.recommended_action == "prepare" and report.blockers == ()
        assert (report.observation.send_files, report.plan_id) == (1, None)
        assert all(r.method == "GET" for r in server.requests[before:])


TABLES = ("upload_namespaces", "upload_manifests", "upload_plans", "upload_approvals")
TABLES += ("upload_operations", "upload_controls", "upload_stage_intents", "upload_stage_receipts")
TABLES += ("upload_verifications",)


def rows(state):
    with open_existing_store(state) as store:
        return [
            store.connection.execute(f"SELECT * FROM {t} ORDER BY 1,2").fetchall() for t in TABLES
        ]


def item(name, *, size=1, sha=None):
    return {
        "id": str(uuid4()),
        "dataset_id": DATASET,
        "original_filename": name,
        "file_size_bytes": size,
        "sha256_hash": sha or hashlib.sha256(name.encode()).hexdigest(),
    }


def serve_items(provider, items, *, page=128, total=None):
    """The provider lists ``items`` in pages: one route per cursor, as the product follows them."""
    base = f"/api/v1/datasets/{DATASET}/items?limit=128"
    pages = [items[i : i + page] for i in range(0, len(items), page)] or [[]]
    for number, found in enumerate(pages):
        following = f"c{number + 1}" if number + 1 < len(pages) else None
        path = base if number == 0 else f"{base}&cursor=c{number}"
        provider.route_table[path] = lambda request, count, found=found, following=following: reply(
            {
                "items": found,
                "total": len(items) if total is None else total,
                "next_cursor": following,
            }
        )


def reported(data, server, source, **flags):
    return resume_runtime(data, server).resume(source, accept_unverified_read=True, **flags)


# --- what each file is --------------------------------------------------------------------------


def test_a_confirm_that_took_no_effect_is_uncertain_and_asks_for_the_acknowledgement(
    prepared_input, certificates
):
    data = many(prepared_input)
    provider = UploadProvider(SCOPE.owner.id, SCOPE.project_id)
    lose_confirm_of(provider, "two.bin", remembered=False)
    with TlsServer(certificates, provider.routes()) as server:
        report = reported(data, server, interrupted(data, server))
        counts = report.observation.class_counts
        assert (counts.confirmed, counts.pending_uncertain, counts.pending_clean) == (1, 1, 1)
        assert report.observation.send_files == 2 and report.observation.unconfirmed_ack_required
        assert report.eligible and report.recommended_action == "prepare"
        assert [e.file_class for e in report.observation.examples] == ["pending_uncertain"]
        assert [e.paths for e in report.observation.examples] == [("two.bin",)]


PROBLEMS = {
    "a confirmed file the provider no longer has": (
        lambda provider: provider.confirmed.pop("one.bin"),
        "drift_missing",
        ("one.bin",),
    ),
    "a file the provider holds with other content": (
        lambda provider: provider.confirmed["one.bin"].update(file_size_bytes=999),
        "conflict",
        ("one.bin",),
    ),
    "a file whose content sits under another name": (
        lambda provider: provider.confirmed.update(
            {"copy.bin": item("copy.bin", size=8, sha=provider.confirmed["one.bin"]["sha256_hash"])}
        ),
        "conflict",
        ("one.bin",),
    ),
    "an item the manifest does not list": (
        lambda provider: provider.confirmed.update({"stray.bin": item("stray.bin")}),
        "extra_remote",
        None,
    ),
    "an item without a hash": (
        lambda provider: provider.confirmed["two.bin"].update(sha256_hash=None),
        "inventory_unreliable",
        None,
    ),
}


@pytest.mark.parametrize("problem", PROBLEMS.values(), ids=PROBLEMS)
def test_each_problem_of_the_remote_state_is_a_blocker_with_its_class(
    prepared_input, certificates, problem
):
    change, blocker, example = problem
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        change(provider)
        report = reported(data, server, source)
        assert blocker in report.blockers and not report.eligible
        assert report.recommended_action == "none" and report.observation is not None
        if example is not None:
            assert example in [e.paths for e in report.observation.examples]
        assert report.plan_id is None


def test_a_listing_of_more_than_a_thousand_items_is_too_large_and_unreliable(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        serve_items(provider, [item(f"extra-{n:04d}.bin") for n in range(1_100)])
        report = reported(data, server, source)
        assert {"inventory_too_large", "inventory_unreliable"} <= set(report.blockers)
        assert report.observation.class_counts.confirmed == 0  # nothing is claimed of a cut listing


def test_a_listing_whose_total_moves_is_unreliable(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        serve_items(provider, list(provider.confirmed.values()), total=99)
        report = reported(data, server, source)
        assert "inventory_unreliable" in report.blockers and not report.eligible


# --- what stands in the way before the files are looked at --------------------------------------


def test_a_dataset_the_project_does_not_list_is_unobserved_and_nothing_is_classified(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        provider.linked = False  # the project no longer lists the dataset
        before = len(server.requests)
        report = reported(data, server, source)
        assert report.blockers == ("membership_unobserved",) and report.observation is None
        assert report.dataset_id == DATASET and report.recommended_action == "none"
        assert not any(r.path.endswith("/items?limit=128") for r in server.requests[before:])


def test_a_folder_that_changed_is_a_blocker_beside_an_observation(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        (data[1] / "one.bin").write_bytes(b"changed after the interruption")
        report = reported(data, server, source)
        assert "local_changed" in report.blockers and report.observation is not None
        assert report.recommended_action == "none"


@pytest.mark.parametrize(
    "route,status,code",
    [
        ("my-role", 403, "remote_access_denied"),
        ("my-role", 503, "remote_failed"),
        ("my-role", 429, "remote_rate_limited"),
        ("items", 503, "remote_failed"),
        ("items", 429, "remote_rate_limited"),
    ],
)
def test_a_provider_that_refuses_or_fails_is_an_error_of_the_report_not_a_blocker(
    prepared_input, certificates, route, status, code
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        failing = {
            "my-role": f"/api/v1/datasets/{DATASET}/my-role",
            "items": f"/api/v1/datasets/{DATASET}/items?limit=128",
        }[route]
        provider.route_table[failing] = Reply(status=status, body=b"{}")
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == code


# --- what a report does and does not do ---------------------------------------------------------


def test_a_report_writes_nothing_locally_and_asks_the_provider_only_to_read(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        stored, before = rows(data[0]), len(server.requests)
        counters = (provider.create_calls, provider.link_calls, provider.presign_calls)
        counters += (provider.put_calls, provider.confirm_calls)
        report = reported(data, server, source)
        assert report.eligible and rows(data[0]) == stored
        found = server.requests[before:]
        assert all(r.method == "GET" for r in found) and 5 <= len(found) <= 512
        assert counters == (
            provider.create_calls,
            provider.link_calls,
            provider.presign_calls,
            provider.put_calls,
            provider.confirm_calls,
        )
        encoded = report.encoded().decode()
        for secret in (SECRET, SCOPE.owner.id, SCOPE.project_id, str(data[1])):
            assert secret not in encoded


def test_the_unverified_read_must_be_chosen_before_the_provider_is_read(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        before = len(server.requests)
        with pytest.raises(YorungeError) as error:
            resume_runtime(data, server).resume(source, accept_unverified_read=False)
        assert error.value.code == "approval_required" and len(server.requests) == before
