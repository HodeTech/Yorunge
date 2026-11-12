"""The resume report over a real interrupted upload: real files, real store, a TLS provider.

The source is made by the product itself: the original workflow runs against the provider until the
provider's lost answer stops it, so its journal is exactly what a real interruption leaves. The
provider's items are then changed to make each class and each blocker of the report.
"""

import hashlib
import json
import logging
import socket
import traceback
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import SCOPE
from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from tests.fixtures.upload_provider import DATASET, UploadProvider, reply
from tests.integration.test_upload_file_workflow import many
from tests.integration.test_upload_http_budget import SECRET, session
from tests.integration.test_upload_original import approved, factory, loader
from tests.integration.test_upload_preparation import ENV
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from yorunge.adapters.state import open_existing_store
from yorunge.adapters.upload_original import upload_files_original
from yorunge.adapters.upload_resume import UploadResumeRuntime
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.upload_resume_report import (
    ResumeClassCounts,
    continuation_added_payload_bytes,
)

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
    loader_value = loader(data)
    factory_value = factory(server)
    with pytest.raises(OperationError) as stopped:
        upload_files_original(plan.plan_id, data[0], loader_value, session_factory=factory_value)
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
        assert counts.pending_uncertain == 0
        assert report.eligible
        assert report.recommended_action == "prepare"
        assert report.blockers == ()
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


DETAIL = "/api/v1/datasets/test-user/test-dataset"
MEMBERS = f"/api/v1/projects/{SCOPE.project_id}/datasets"
READS = {
    "me": "/api/v1/auth/me",
    "project": f"/api/v1/projects/{SCOPE.project_id}",
    "owned": "/api/v1/datasets?page=1&page_size=20&scope=owned",
    "detail": DETAIL,
    "membership": MEMBERS,
    "role": f"/api/v1/datasets/{DATASET}/my-role",
    "items": f"/api/v1/datasets/{DATASET}/items?limit=128",
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
        assert report.observation.send_files == 2
        assert report.observation.unconfirmed_ack_required
        assert report.eligible
        assert report.recommended_action == "prepare"
        assert [e.file_class for e in report.observation.examples] == ["pending_uncertain"]
        assert [e.paths for e in report.observation.examples] == [("two.bin",)]


def classes(**counted):
    """The class counts of a report: the ones named, and nothing in the others."""
    return ResumeClassCounts(
        **{name: counted.get(name, 0) for name in ResumeClassCounts.model_fields}
    )


# What each problem of the remote state makes of the three files (``one.bin`` confirmed, ``two.bin``
# kept by the provider though its answer was lost, the third not sent): the blockers in their closed
# order, the class counts, and the paths the report names. An item no file of the manifest is never
# named or counted. Under an unreliable listing no file is claimed, so every file is that class.
PROBLEMS = {
    "a confirmed file the provider no longer has": (
        lambda provider: provider.confirmed.pop("one.bin"),
        ("drift_missing",),
        classes(observed=1, pending_clean=1, drift_missing=1),
        [("drift_missing", ("one.bin",))],
    ),
    "a file the provider holds with other content": (
        lambda provider: provider.confirmed["one.bin"].update(file_size_bytes=999),
        ("conflict",),
        classes(observed=1, pending_clean=1, conflict=1),
        [("conflict", ("one.bin",))],
    ),
    "a file whose content sits under another name": (
        lambda provider: provider.confirmed.update(
            {"copy.bin": item("copy.bin", size=8, sha=provider.confirmed["one.bin"]["sha256_hash"])}
        ),
        ("conflict", "extra_remote"),
        classes(observed=1, pending_clean=1, conflict=1),
        [("conflict", ("one.bin",))],
    ),
    "an item the manifest does not list": (
        lambda provider: provider.confirmed.update({"stray.bin": item("stray.bin")}),
        ("extra_remote",),
        classes(confirmed=1, observed=1, pending_clean=1),
        [],
    ),
    "an item without a hash": (
        lambda provider: provider.confirmed["two.bin"].update(sha256_hash=None),
        ("inventory_unreliable",),
        classes(inventory_unreliable=3),
        [("inventory_unreliable", ("one.bin", "two.bin", "ölçüm.bin"))],
    ),
    "an identity listed under two names": (
        lambda provider: provider.confirmed["two.bin"].update(
            id=provider.confirmed["one.bin"]["id"]
        ),
        ("inventory_unreliable",),
        classes(inventory_unreliable=3),
        [("inventory_unreliable", ("one.bin", "two.bin", "ölçüm.bin"))],
    ),
}


@pytest.mark.parametrize("problem", PROBLEMS.values(), ids=PROBLEMS)
def test_each_problem_of_the_remote_state_is_a_blocker_with_its_class(
    prepared_input, certificates, problem
):
    change, blockers, counts, examples = problem
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        change(provider)
        report = reported(data, server, source)
        assert report.blockers == blockers
        assert not report.eligible
        assert report.recommended_action == "none"
        assert report.plan_id is None
        found = report.observation
        assert found.class_counts == counts
        assert [(e.file_class, e.paths) for e in found.examples] == examples
        # What would be sent is what the provider does not hold: the one file left (nine bytes).
        seen_sent = (found.send_files, found.send_bytes)
        assert seen_sent == ((1, len(b"different")) if counts.pending_clean else (0, 0))
        assert not found.unconfirmed_ack_required
        encoded = report.encoded().decode()
        assert "stray.bin" not in encoded
        assert "copy.bin" not in encoded  # never named


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


def test_a_listing_whose_cursor_comes_back_is_unreliable(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        base = READS["items"]
        have = list(provider.confirmed.values())
        again = {"items": [], "total": len(have), "next_cursor": "c1"}
        provider.route_table[base] = lambda request, count: reply({**again, "items": have})
        provider.route_table[base + "&cursor=c1"] = lambda request, count: reply(again)
        before = len(server.requests)
        report = reported(data, server, source)
        assert "inventory_unreliable" in report.blockers
        assert not report.eligible
        # The loop is cut at the second visit of the cursor, not followed.
        assert sum(r.path.startswith(base) for r in server.requests[before:]) == 2


def test_a_listing_whose_total_moves_is_unreliable(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        serve_items(provider, list(provider.confirmed.values()), total=99)
        report = reported(data, server, source)
        assert "inventory_unreliable" in report.blockers
        assert not report.eligible


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
        assert report.blockers == ("membership_unobserved",)
        assert report.observation is None
        assert report.dataset_id == DATASET
        assert report.recommended_action == "none"
        asked = [r.path for r in server.requests[before:]]
        assert not any(path.endswith(("/items?limit=128", "/my-role")) for path in asked)


def test_a_folder_that_changed_is_a_blocker_beside_an_observation(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        (data[1] / "one.bin").write_bytes(b"changed after the interruption")
        report = reported(data, server, source)
        assert "local_changed" in report.blockers
        assert report.observation is not None
        assert report.recommended_action == "none"


FAILURES = {
    401: "remote_access_denied",
    403: "remote_access_denied",
    429: "remote_rate_limited",
    500: "remote_failed",
    503: "remote_failed",
}


@pytest.mark.parametrize("read", READS)
def test_a_provider_that_refuses_or_fails_is_an_error_of_the_report_not_a_blocker(
    prepared_input, certificates, read
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        for status, code in FAILURES.items():
            provider.route_table[READS[read]] = Reply(status=status, body=b"{}")
            with pytest.raises(YorungeError) as error:
                reported(data, server, source)
            assert error.value.code == code, (read, status)


def test_a_key_of_another_account_is_an_error_not_a_report(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        other = {"id": "00000000-0000-4000-8000-000000000999"}
        provider.route_table[READS["me"]] = reply(other)
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "invalid_response"


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
        assert report.eligible
        assert rows(data[0]) == stored
        found = server.requests[before:]
        assert all(r.method == "GET" for r in found)
        assert len(found) == len(READS)
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
        resume_runtime_value = resume_runtime(data, server)
        with pytest.raises(YorungeError) as error:
            resume_runtime_value.resume(source, accept_unverified_read=False)
        assert error.value.code == "approval_required"
        assert len(server.requests) == before


def drifted(**changes):
    """The provider shows the dataset with ``changes``, in its detail and in the owned list."""

    def change(provider):
        provider.route_table[DETAIL] = reply({**provider.dataset(), **changes})
        listed = {**provider.dataset(), "owner_username": "test-user", "slug": "test-dataset"}
        listed.pop("contributions_enabled")
        provider.route_table[READS["owned"]] = reply([{**listed, **changes}])

    return change


def drifted_detail(**changes):
    """... only in its detail (the owned list still shows it as it was)."""

    def change(provider):
        provider.route_table[DETAIL] = reply({**provider.dataset(), **changes})

    return change


NOT_THE_BASELINE = {
    "a detail of another owner": lambda provider: setattr(provider, "wrong_detail_owner", True),
    "a detail that is gone": lambda provider: provider.route_table.update(
        {DETAIL: Reply(status=404, body=b"{}")}
    ),
    "a detail that is gone for good": lambda provider: provider.route_table.update(
        {DETAIL: Reply(status=410, body=b"{}")}
    ),
    "an owned list that no longer shows the dataset": lambda provider: provider.route_table.update(
        {READS["owned"]: reply([])}
    ),
    "a dataset that was renamed": drifted(name="renamed-since"),
    "a dataset that was shared": drifted(visibility="public"),
    "a dataset that became unlisted": drifted(visibility="unlisted"),
    "a dataset that now takes contributions": drifted_detail(contributions_enabled=True),
}


@pytest.mark.parametrize("change", NOT_THE_BASELINE.values(), ids=NOT_THE_BASELINE)
def test_a_dataset_that_is_not_the_baseline_is_unobserved_and_never_listed(
    prepared_input, certificates, change
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        change(provider)
        before = len(server.requests)
        report = reported(data, server, source)
        assert report.blockers == ("membership_unobserved",)
        assert report.observation is None
        assert report.recommended_action == "none"
        assert report.dataset_id == DATASET
        asked = [r.path for r in server.requests[before:]]
        assert not any(path.endswith(("/items?limit=128", "/my-role")) for path in asked)


MALFORMED_DATASET = {
    "a visibility the platform does not document": drifted(visibility="secret"),
    "a visibility that is not text": drifted(visibility=7),
    "a contribution flag that is not a boolean": drifted_detail(contributions_enabled="true"),
}


@pytest.mark.parametrize("change", MALFORMED_DATASET.values(), ids=MALFORMED_DATASET)
def test_a_dataset_the_platform_describes_in_words_it_does_not_have_is_an_error(
    prepared_input, certificates, change
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        change(provider)
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "invalid_response"


def test_a_dataset_not_shown_to_be_the_baseline_still_reports_all_the_report_knows(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        (data[1] / "one.bin").write_bytes(b"changed after the interruption")
        provider.linked = False
        report = reported(data, server, source)
        # Both stand together, in the closed order of the blockers.
        assert report.blockers == ("membership_unobserved", "local_changed")
        assert report.observation is None
        assert report.dataset_id == DATASET
        # The store's counters and what an attempt would add (for all three files: none is chosen).
        assert (report.quota_used.plans, report.quota_used.operations) == (1, 1)
        assert report.quota_added.payload_bytes == continuation_added_payload_bytes(3)
        assert report.quota_added.plans == report.quota_added.operations == 1


def test_an_error_that_is_not_about_the_folder_is_never_reported_as_a_changed_folder(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)

        def timed_out(*arguments, **keywords):
            raise YorungeError("execution_timeout")

        monkeypatch.setattr("yorunge.adapters.upload_resume.capture_upload_input", timed_out)
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "execution_timeout"


def test_a_key_that_reads_like_a_path_of_the_manifest_is_refused_though_the_folder_is_gone(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        # The folder is not there, so its capture stops before the manifest is read against the key.
        data[1].rename(data[1].parent / "moved-away")
        monkeypatch.setenv(ENV, "one.bin")
        before = len(server.requests)
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "invalid_request"
        assert len(server.requests) == before
        assert "one.bin" not in str(error.value) + repr(error.value)


CANARY = "PRIVATE-PROVIDER-CANARY"
SAYS = {
    "an html page for the dataset": (DETAIL, 200),
    "an html page for the project's datasets": (MEMBERS, 200),
    "an html page for the items": (READS["items"], 200),
    "a failure of the role": (READS["role"], 500),
    "a failure of the dataset": (DETAIL, 500),
}


@pytest.mark.parametrize("route,status", SAYS.values(), ids=SAYS)
def test_nothing_the_provider_says_reaches_the_error_the_traceback_or_the_log(
    prepared_input, certificates, caplog, route, status
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        body = f"<html>{CANARY} {SECRET}</html>".encode()
        provider.route_table[route] = Reply(status=status, body=body)
        with caplog.at_level(logging.DEBUG), pytest.raises(YorungeError) as error:
            reported(data, server, source)
    shown = "".join(traceback.format_exception(error.value)) + repr(error.value) + caplog.text
    assert CANARY not in shown
    assert SECRET not in shown


def test_a_key_that_may_not_upload_to_the_dataset_is_refused_by_the_report(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        provider.upload_allowed = False  # the role no longer lists the upload permission
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "remote_access_denied"


def test_a_transport_that_breaks_while_describing_the_dataset_is_an_error_not_a_blocker(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        provider.route_table[DETAIL] = Reply(status=200, body=b'{"id":"x"}', truncate_at=3)
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "transport_failed"


MALFORMED = {
    "an html page instead of the dataset": (DETAIL, Reply(status=200, body=b"<html>portal</html>")),
    "an empty body instead of the dataset": (DETAIL, Reply(status=200, body=b"")),
    "an array instead of the dataset": (DETAIL, Reply(status=200, body=b"[[],[]]")),
    "a redirect instead of the dataset": (
        DETAIL,
        Reply(status=302, body=b"", headers=(("Location", "/elsewhere"),)),
    ),
    "an html page instead of the project's datasets": (MEMBERS, Reply(body=b"<html>portal</html>")),
    "more datasets than a project's list may hold": (
        MEMBERS,
        reply([{"id": str(uuid4())} for _ in range(129)]),
    ),
}


@pytest.mark.parametrize("answer", MALFORMED.values(), ids=MALFORMED)
def test_a_malformed_answer_about_the_dataset_is_an_error_not_a_missing_dataset(
    prepared_input, certificates, answer
):
    route, found = answer
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        provider.route_table[route] = found
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == "invalid_response"


def test_a_well_formed_answer_about_another_dataset_is_a_missing_one(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        other = {**provider.dataset(), "id": "00000000-0000-4000-8000-0000000000bb"}
        provider.route_table[DETAIL] = reply(other)
        report = reported(data, server, source)
        assert report.blockers == ("membership_unobserved",)
        assert report.observation is None


def test_a_read_that_fails_for_a_moment_is_asked_again_once(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        items = f"/api/v1/datasets/{DATASET}/items?limit=128"
        provider.route_table[items] = Reply(status=503, body=b"{}")
        before = sum(r.path == items for r in server.requests)
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        # A transient answer is retried once by the transport; the report is then the error.
        assert error.value.code == "remote_failed"
        assert sum(r.path == items for r in server.requests) - before == 2


def test_a_folder_that_was_moved_away_is_a_changed_folder_to_the_report_and_unreadable_to_prepare(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        data[1].rename(data[1].parent / "moved-away")
        report = reported(data, server, source)
        assert "local_changed" in report.blockers
        assert report.observation is not None
        with pytest.raises(YorungeError) as error:
            reported(data, server, source, prepare=True)
        assert error.value.code == "file_unreadable"
