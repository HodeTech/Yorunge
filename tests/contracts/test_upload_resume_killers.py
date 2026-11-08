"""Texts and projections of the resume surface that no test of the step pinned (P02-3i R1-B).

Each test names the mutant it kills: the next step of every recommended action, the observation
lines, the quota boundary, the hint of every error a `resume` meets, and the summary text of a
continuation that has files whose last confirm may or may not have landed.
"""

import io
import json
from pathlib import Path

import pytest

from yorunge.cli.output import OutputRenderer
from yorunge.cli.upload import (
    RESUME_ERROR_HINTS,
    _quota_lines,
    _resume_text,
    _summary_text,
)
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_public import DatasetUploadSummaryV3
from yorunge.domain.upload_resume_report import (
    DatasetUploadResumeReport,
    QuotaCounters,
    ResumeExamples,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
SOURCE = "00000000-0000-4000-8000-000000000009"
OTHER = "00000000-0000-4000-8000-0000000000cc"


def golden(name):
    return DatasetUploadResumeReport.model_validate_json(
        (FIXTURES / f"dataset-continuation-resume-report-v1-{name}.json").read_bytes()
    )


def unobserved(**changes):
    return golden("unobserved").model_copy(update=changes)


# --- the next step of every recommended action -----------------------------------------------


def test_a_report_that_recommends_reconcile_leads_to_reconcile():
    report = unobserved(
        blockers=("reconcile_available",), recommended_action="reconcile", observation=None
    )
    text = _resume_text(report)
    assert (
        f"Uzlaştır: yorunge datasets upload reconcile --operation-id {SOURCE} "
        "--accept-unverified-read"
    ) in text
    assert "Hazırla:" not in text and "devam komutu yok" not in text


def test_a_report_that_recommends_waiting_says_to_wait():
    report = unobserved(
        blockers=("source_active",),
        recommended_action="wait",
        observation=None,
        related_operation_id=OTHER,
    )
    text = _resume_text(report)
    assert "Bekle: lease bitince raporu yeniden alın." in text
    assert "Hazırla:" not in text and "devam komutu yok" not in text


# --- the observation lines ------------------------------------------------------------------


def test_the_unconfirmed_warning_and_every_example_are_shown():
    eligible = golden("eligible")
    observation = eligible.observation.model_copy(
        update={
            "examples": (
                ResumeExamples(file_class="pending_uncertain", paths=("a.txt", "b.txt", "c.txt")),
                ResumeExamples(file_class="drift_missing", paths=("d.txt",)),
            )
        }
    )
    text = _resume_text(eligible.model_copy(update={"observation": observation}))
    assert "Uyarı: bazı dosyaların son onay (confirm) isteği sunucuya ulaşmış olabilir" in text
    assert "Örnek (belirsiz (son onay isteği gitmiş olabilir)): a.txt, b.txt, c.txt" in text
    assert "Örnek (kaybolmuş): d.txt" in text
    quiet = observation.model_copy(update={"unconfirmed_ack_required": False})
    assert "Uyarı: bazı dosyaların" not in _resume_text(
        eligible.model_copy(update={"observation": quiet})
    )


# --- the quota line --------------------------------------------------------------------------


def test_an_attempt_that_exactly_fits_is_not_full_and_one_more_is():
    report = golden("eligible")
    fits = report.model_copy(
        update={
            "quota_used": QuotaCounters(plans=127, operations=127, files=4093, payload_bytes=1000),
            "quota_added": QuotaCounters(plans=1, operations=1, files=3, payload_bytes=100),
        }
    )
    assert not any("Kota dolu" in line for line in _quota_lines(fits))
    over = fits.model_copy(
        update={"quota_used": fits.quota_used.model_copy(update={"files": 4094})}
    )
    assert any("Kota dolu" in line and "dosya" in line for line in _quota_lines(over))
    bytes_over = fits.model_copy(
        update={
            "quota_used": fits.quota_used.model_copy(
                update={"payload_bytes": 16 * 1024 * 1024 - 99}
            )
        }
    )
    # the payload is an upper bound (the sealed plan has its true size): "near", not "full"
    lines = _quota_lines(bytes_over)
    assert not any("Kota dolu" in line for line in lines)
    assert any("Kota sınırda" in line for line in lines)


# --- the hints for the errors a resume meets ----------------------------------------------------


@pytest.mark.parametrize(
    "code,word",
    [
        ("state_changed", "--config ve --profile"),
        ("state_busy", "meşgul"),
        ("upload_plan_not_valid", "plan penceresi"),
        ("invalid_request", "seçenekleri yardımla"),
        ("invalid_response", "CON"),
        ("approval_required", "--accept-unverified-read"),
    ],
)
def test_each_error_a_resume_meets_has_its_hint_in_text_and_none_in_machine_output(code, word):
    error = YorungeError(code)
    text = io.StringIO()
    OutputRenderer(
        "text",
        stderr=text,
        stdout=io.StringIO(),
        upload_guidance=True,
        error_hints=RESUME_ERROR_HINTS,
    ).error(error)
    assert error.message in text.getvalue() and RESUME_ERROR_HINTS[code] in text.getvalue()
    assert word in RESUME_ERROR_HINTS[code]
    machine = io.StringIO()
    OutputRenderer(
        "json",
        stderr=machine,
        stdout=io.StringIO(),
        upload_guidance=True,
        error_hints=RESUME_ERROR_HINTS,
    ).error(error)
    assert RESUME_ERROR_HINTS[code] not in machine.getvalue()
    assert json.loads(machine.getvalue())["code"] == code


# --- the summary text of a continuation ---------------------------------------------------------


def continuation(**changes):
    value = DatasetUploadSummaryV3.model_validate_json(
        (FIXTURES / "dataset-continuation-summary-v3.json").read_bytes()
    )
    return value.model_copy(update=changes)


def test_a_plan_with_unconfirmed_files_says_so_and_names_the_flag_of_the_approval():
    plan = continuation(
        uncertain_files=1,
        continuation_files=2,
        operation_id=None,
        operation_status=None,
        approval_status=None,
        approval_expires_at=None,
    )
    lines = "\n".join(_summary_text(plan))
    assert "Gönderilecek dosyalardan 1 tanesinin son onay isteği gitmiş olabilir" in lines
    assert "--accept-unconfirmed-effects ekleyin" in lines
    quiet = "\n".join(_summary_text(plan.model_copy(update={"uncertain_files": 0})))
    assert "belirsiz" not in quiet and "--accept-unconfirmed-effects" not in quiet
