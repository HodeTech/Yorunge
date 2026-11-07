"""What a report and a plan say of the store's quota, and that an attempt which fits is accepted.

The refusal of an attempt the store cannot hold is tested with the prepare tests; here the bounds
are set to exactly what the attempt needs, so a comparison off by one is found on both sides.
"""

from datetime import UTC, datetime

import pytest

from tests.fixtures.http_server import TlsServer
from tests.integration.test_upload_preparation import prepared_input as prepared_input
from tests.integration.test_upload_resume_observation import (
    certificates as certificates,
)
from tests.integration.test_upload_resume_observation import (
    interrupted,
    reported,
    rows,
    world,
)
from tests.integration.test_upload_resume_observation import (
    loopback_only as loopback_only,
)
from tests.integration.test_upload_resume_prepare import prepared, saved
from yorunge.domain.capabilities import instant
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_resume_report import continuation_added_payload_bytes

LIMITS = "yorunge.adapters.upload_resume.MAX_TRANSFER_"


def test_an_attempt_that_fits_the_plan_and_operation_bounds_exactly_is_accepted(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        used = reported(data, server, source).quota_used
        monkeypatch.setattr(LIMITS + "PLANS", used.plans + 1)
        monkeypatch.setattr(LIMITS + "OPERATIONS", used.operations + 1)
        assert prepared(data, server, source).plan_id is not None


def test_an_attempt_that_fits_the_file_and_payload_bounds_exactly_is_accepted(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        first = prepared(data, server, source)  # what one attempt adds, as the report states it
        used = reported(data, server, source).quota_used
        monkeypatch.setattr(LIMITS + "FILES", used.files + 3)
        monkeypatch.setattr(
            LIMITS + "PAYLOAD_BYTES", used.payload_bytes + first.quota_added.payload_bytes
        )
        assert prepared(data, server, source).plan_id is not None


def test_an_attempt_a_byte_over_the_payload_bound_is_refused_and_writes_nothing(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        first = prepared(data, server, source)
        used = reported(data, server, source).quota_used
        added = first.quota_added.payload_bytes  # the same attempt again: one byte too much
        monkeypatch.setattr(LIMITS + "PAYLOAD_BYTES", used.payload_bytes + added - 1)
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            prepared(data, server, source)
        assert error.value.code == "upload_capacity_exceeded" and rows(data[0]) == stored


def test_the_file_bound_counts_every_file_of_the_manifest_not_only_those_that_are_sent(
    prepared_input, certificates, monkeypatch
):
    data, provider = world(prepared_input)  # three files, one left to send
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        used = reported(data, server, source).quota_used
        monkeypatch.setattr(LIMITS + "FILES", used.files + 2)  # room for the one, not for the three
        stored = rows(data[0])
        with pytest.raises(YorungeError) as error:
            prepared(data, server, source)
        assert error.value.code == "upload_capacity_exceeded" and rows(data[0]) == stored


def test_the_payload_a_report_and_a_plan_add_is_the_formula_and_the_observation_is_dated(
    prepared_input, certificates
):
    data, provider = world(prepared_input)
    with TlsServer(certificates, provider.routes()) as server:
        source = interrupted(data, server)
        asked: list[datetime] = []
        provider.on_request = lambda: asked.append(datetime.now(UTC))
        report = reported(data, server, source)
        sending = report.observation.send_files
        # Three files; the report states the most an attempt that sends ``sending`` of them adds.
        assert report.quota_added.payload_bytes == continuation_added_payload_bytes(3, sending)
        assert instant(report.observed_at) >= asked[-1]  # dated once the dataset had been read
        done = prepared(data, server, source)
        plan = saved(data, done.plan_id).plan
        assert done.quota_added.payload_bytes == continuation_added_payload_bytes(
            3, sending, len(plan.encoded())
        )
