"""A provider that misbehaves in ways the report must bound, name or refuse; never trust.

Its time bounds are tested scaled down (the phase and the listing may take one second here, thirty
in the product) so that a body dripped one byte at a time is cut where the budget says without the
test waiting for it.
"""

import time

import pytest

from tests.fixtures.http_server import Reply, TlsServer
from tests.integration.test_upload_http_budget import session
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    READS,
    interrupted,
    item,
    reported,
    serve_items,
    world,
)
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from yorunge.adapters.platform_upload_reader import PHASE_SECONDS, ObservedUploadReader
from yorunge.adapters.upload_resume import (
    LISTING_SECONDS,
    OBSERVATION_SECONDS,
    UploadResumeRuntime,
)
from yorunge.domain.errors import YorungeError

ROLE = b'{"role":"owner","permissions":["read","upload"]}'
LISTING = b'{"items":[],"total":0,"next_cursor":null}'


def test_the_phases_of_the_observation_are_thirty_seconds_and_the_whole_a_minute():
    assert PHASE_SECONDS == LISTING_SECONDS == 30.0
    assert OBSERVATION_SECONDS == 60.0


DRIP = "yorunge.adapters.upload_resume."
PHASE = "yorunge.adapters.platform_upload_reader.PHASE_SECONDS"


@pytest.mark.parametrize(
    "bound,seconds,read,body,code",
    [
        (PHASE, 1.0, "role", ROLE, "transport_timeout"),
        (DRIP + "LISTING_SECONDS", 1.0, "items", LISTING, "transport_timeout"),
        (DRIP + "OBSERVATION_SECONDS", 2.0, "role", ROLE, "execution_timeout"),
        (DRIP + "OBSERVATION_SECONDS", 2.0, "items", LISTING, "execution_timeout"),
    ],
    ids=["baseline phase", "listing", "whole, in the baseline", "whole, in the listing"],
)
def test_a_body_that_is_dripped_is_cut_where_the_budget_ends(
    prepared_input, certificates, monkeypatch, bound, seconds, read, body, code
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        monkeypatch.setattr(bound, seconds)
        provider.route_table[READS[read]] = Reply(body=body, chunk_size=1, chunk_delay=0.5)
        began = time.monotonic()
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        assert error.value.code == code
        assert time.monotonic() - began < 10  # the body alone would have taken over twenty seconds


def test_each_time_bound_of_the_observation_is_its_named_constant(
    prepared_input, certificates, monkeypatch
):
    """The bounds are the constants, not numbers near them: seen at the three places they are used.

    A bound twice as long would still cut a body dripped for over twenty seconds, so this asks the
    deadlines themselves, without waiting for anything.
    """
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)  # the upload itself keeps its own bounds
        monkeypatch.setattr(PHASE, 7.0)
        monkeypatch.setattr(DRIP + "LISTING_SECONDS", 11.0)
        monkeypatch.setattr(DRIP + "OBSERVATION_SECONDS", 18.0)
        seen = {}
        original_get = ObservedUploadReader._get
        original_inventory = ObservedUploadReader.inventory

        async def get(self, client, kind, endpoint, end, query=()):
            seen.setdefault("phase", end - time.monotonic())
            return await original_get(self, client, kind, endpoint, end, query)

        async def inventory(self, client, dataset_id, *, deadline):
            seen["listing"] = deadline - time.monotonic()
            return await original_inventory(self, client, dataset_id, deadline=deadline)

        monkeypatch.setattr(ObservedUploadReader, "_get", get)
        monkeypatch.setattr(ObservedUploadReader, "inventory", inventory)

        def build(key, budget):
            seen["budget"] = budget.end - time.monotonic()
            return session(server, key, budget)[0]

        state, _, _, context, profile = data
        UploadResumeRuntime(context, profile, state, session_factory=build).resume(
            source, accept_unverified_read=True
        )
        assert 5.5 < seen["phase"] <= 7.0, seen
        assert 9.5 < seen["listing"] <= 11.0, seen
        assert 16.5 < seen["budget"] <= 18.0, seen


def test_the_observation_is_made_under_a_read_only_budget(prepared_input, certificates):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        budgets = []

        def build(key, budget):
            budgets.append(budget)
            return session(server, key, budget)[0]

        state, _, _, context, profile = data
        runtime = UploadResumeRuntime(context, profile, state, session_factory=build)
        before = len(server.requests)
        runtime.resume(source, accept_unverified_read=True)
        assert len(budgets) == 1
        # Every request the server saw is a read the budget counted once (no retry was needed), and
        # none of the effects was asked for: the counters stand well inside the read-only limits.
        counters, asked = budgets[0].snapshot(), len(server.requests) - before
        assert counters.read_requests == counters.read_attempts == asked
        assert asked == len(READS)
        assert counters.effect_attempts == 0  # each read, once
        assert counters.create_requests == counters.project_link_requests == 0
        assert counters.presign_requests == counters.put_requests == counters.confirm_requests == 0
        with pytest.raises(YorungeError) as error:
            budgets[0].reserve("create")  # a request that is not a read is not admitted at all
        assert error.value.code == "invalid_request"


@pytest.mark.parametrize("name", ["CON", "a.", "a\\b", "../x", "x" * 256])
def test_an_item_no_upload_of_the_product_could_have_made_is_an_invalid_answer(
    prepared_input, certificates, name
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        serve_items(provider, [*provider.confirmed.values(), item(name)])
        with pytest.raises(YorungeError) as error:
            reported(data, server, source)
        # The path rules decide what an item is: a listing with an item outside them is not
        # classified (it is not an extra item), and the same answer is refused wherever it is read.
        assert error.value.code == "invalid_response"
