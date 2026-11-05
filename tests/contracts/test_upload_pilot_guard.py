"""Cross-invocation pilot limits add restrictions without bypassing production gates."""

import asyncio
import runpy
import time

import pytest

from tests.contracts.test_upload_evidence import ROOT
from yorunge.application.upload_budget import UploadBudget
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_costs import UploadRequestLimits


@pytest.fixture
def guard():
    return runpy.run_path(str(ROOT / "scripts/upload_pilot_guard.py"))["PilotGuard"]()


def limits():
    return UploadRequestLimits(
        max_create=1,
        max_project_link=1,
        max_presign=3,
        max_put=3,
        max_confirm=3,
        max_read_requests=512,
        max_read_attempts=1024,
        max_control_request_bytes=4_194_304,
        max_control_response_bytes=16_777_216,
        max_upload_bytes=237,
    )


def test_global_read_limit_spans_new_budget_instances_and_restores_methods(guard):
    original = UploadBudget.reserve
    with guard.install():
        for _ in range(40):
            budget = UploadBudget(limits(), end=time.monotonic() + 900, read_only=True)
            assert budget.end <= guard.end
            reservation = budget.reserve("read")
            reservation.finish()
        budget = UploadBudget(limits(), end=time.monotonic() + 30, read_only=True)
        with pytest.raises(YorungeError) as failure:
            budget.reserve("read")
        assert failure.value.code == "upload_limit_exceeded"
    assert UploadBudget.reserve is original
    value = guard.snapshot()
    assert value["claims"]["read"] == 40
    assert value["actual"]["read_attempts"] == 0
    assert value["open_reservations"] == value["response_pending"] == 0


def test_response_pending_and_consumed_bytes_share_global_pre_network_limit(guard):
    async def exchange():
        with guard.install():
            budget = UploadBudget(limits(), end=time.monotonic() + 30, read_only=True)
            reservations = [budget.reserve("read") for _ in range(16)]
            with pytest.raises(YorungeError) as failure:
                budget.reserve("read")
            assert failure.value.code == "upload_limit_exceeded"
            current = reservations.pop()
            current.begin()
            current.attempt()
            current.response(1024)
            current.finish()
            extra = budget.reserve("read", response_bytes=1_047_552)
            with pytest.raises(YorungeError) as failure:
                budget.reserve("read", response_bytes=1)
            assert failure.value.code == "upload_limit_exceeded"
            for reservation in (*reservations, extra):
                reservation.finish()

    asyncio.run(exchange())
    assert guard.snapshot()["response_pending"] == 0
    assert guard.snapshot()["actual"]["response_bytes"] == 1024


@pytest.mark.parametrize(
    "kind,maximum", [("create", 1), ("project_link", 1), ("presign", 2), ("put", 2), ("confirm", 2)]
)
def test_effect_limit_spans_invocations_even_when_unstarted_claim_is_released(guard, kind, maximum):
    with guard.install():
        budget = UploadBudget(limits(), end=time.monotonic() + 30, read_only=False)
        for _ in range(maximum):
            budget.reserve(kind, response_bytes=65_536).finish()
        other = UploadBudget(limits(), end=time.monotonic() + 30, read_only=False)
        with pytest.raises(YorungeError) as failure:
            other.reserve(kind)
        assert failure.value.code == "upload_limit_exceeded"


def test_selected_image_bytes_are_capped_before_any_attempt(guard):
    with guard.install():
        budget = UploadBudget(limits(), end=time.monotonic() + 30, read_only=False)
        with pytest.raises(YorungeError) as failure:
            budget.reserve("put", upload_bytes=159)
        assert failure.value.code == "upload_limit_exceeded"
        assert budget.snapshot().effect_attempts == budget.snapshot().upload_bytes == 0
        assert guard.snapshot()["open_reservations"] == 0


def test_guard_preserves_production_readonly_and_deadline_rejection(guard):
    original = UploadBudget.__init__
    with guard.install():
        budget = UploadBudget(limits(), end=time.monotonic() + 30, read_only=True)
        with pytest.raises(YorungeError) as failure:
            budget.reserve("create")
        assert failure.value.code == "invalid_request"
    assert UploadBudget.__init__ is original
    guard.end = time.monotonic() - 1
    current_limits, end = limits(), time.monotonic() + 30
    with guard.install(), pytest.raises(YorungeError) as failure:
        UploadBudget(current_limits, end=end, read_only=False)

    assert failure.value.code == "execution_timeout"
