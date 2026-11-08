"""What a person reads of a resume report and of a refused continuation.

The JSON names the blockers; these tests pin the words: every blocker has exactly one sentence of
reason and one of next step, the report says what it observed and what it did not, the quota line
says when the local record cannot take another attempt, and the next command is the one the
recommended action names.
"""

import io
import json
from pathlib import Path

import pytest

from yorunge.cli.output import OutputRenderer
from yorunge.cli.upload import BLOCKER_TEXT, CLASS_TEXT, _resume_text
from yorunge.domain.errors import OperationError
from yorunge.domain.upload_resume import BLOCKERS, ContinuationNotPossible
from yorunge.domain.upload_resume_report import DatasetUploadResumeReport

FIXTURES = Path(__file__).parents[1] / "fixtures"
SOURCE = "00000000-0000-4000-8000-000000000009"


def golden(name):
    return DatasetUploadResumeReport.model_validate_json(
        (FIXTURES / f"dataset-continuation-resume-report-v1-{name}.json").read_bytes()
    )


def test_every_blocker_has_one_sentence_of_reason_and_one_of_next_step():
    assert set(BLOCKER_TEXT) == set(BLOCKERS)
    for name, (reason, step) in BLOCKER_TEXT.items():
        for sentence in (reason, step):
            assert sentence.endswith(".") and "\n" not in sentence, name
            assert ". " not in sentence, f"{name}: one sentence, not two"
            assert len(sentence) < 200, name
        assert reason != step


def test_every_class_a_person_has_to_act_on_has_a_word():
    from yorunge.domain.upload_resume_report import PROBLEM_CLASSES

    assert set(CLASS_TEXT) == set(PROBLEM_CLASSES)


def test_the_text_of_an_eligible_report_with_unconfirmed_files_leads_to_prepare():
    text = _resume_text(golden("eligible"))
    assert f"Devam raporu — kaynak iş: {SOURCE}" in text
    assert "Devam edilebilir; plan kaydedilmedi (salt okuma raporu)." in text
    assert "Gönderilecek: 2 dosya, 8 bayt." in text
    assert "belirsiz 1" in text and "--accept-unconfirmed-effects" in text
    assert "Örnek (belirsiz (son onay isteği gitmiş olabilir)): ölçüm.txt" in text
    assert (
        f"Hazırla: yorunge datasets upload resume --operation-id {SOURCE} "
        "--accept-unverified-read --prepare --accept-unconfirmed-effects"
    ) in text
    assert "Engeller" not in text and "- " not in text.split("Dosya sınıfları")[0]
    assert text.rstrip().endswith("baytları doğrulanmadı.")
    assert "Özel --config/--profile/--state-dir" in text


def test_the_text_of_a_blocked_report_says_why_and_what_next_and_offers_no_command():
    text = _resume_text(golden("blocked"))
    reason, step = BLOCKER_TEXT["drift_missing"]
    assert "Devam edilemiyor" in text
    assert f"- drift_missing: {reason}\n  Sonraki adım: {step}" in text
    assert "Örnek (kaybolmuş): a.txt" in text
    assert "Hazırla:" not in text and "Uzlaştır:" not in text
    assert "devam komutu yok" in text


def test_the_text_of_a_report_that_read_nothing_says_so():
    text = _resume_text(golden("unobserved"))
    assert "Veri seti: kaydedilmedi (create sonucu bilinmiyor)" in text
    assert "Uzak durum okunmadı: rapor yalnız yerel kayda dayanır." in text
    assert "Dosya sınıfları" not in text and "- create_unknown:" in text


def test_a_report_with_a_plan_leads_to_the_review_not_to_another_prepare():
    report = golden("eligible")
    planned = report.model_copy(
        update={
            "plan_id": "00000000-0000-4000-8000-0000000000b1",
            "plan_digest": "a" * 64,
        }
    )
    text = _resume_text(planned)
    assert "Devam planı kaydedildi: 00000000-0000-4000-8000-0000000000b1 (digest: " in text
    assert "İncele: yorunge datasets upload review --plan-id 00000000" in text
    assert "Hazırla:" not in text


def test_the_quota_line_says_when_the_local_record_cannot_take_another_attempt():
    report = golden("eligible")
    assert "Kota dolu" not in _resume_text(report)
    full = report.model_copy(
        update={"quota_used": report.quota_used.model_copy(update={"plans": 128})}
    )
    text = _resume_text(full)
    assert "kullanılan 128/128 plan" in text
    assert "Kota dolu: bu deneme yerel kaydın şu sınırını aşar: plan." in text
    assert "Kayıtlar otomatik silinmez" in text


def test_the_related_operation_of_a_waiting_source_is_named():
    report = golden("blocked").model_copy(
        update={
            "blockers": ("source_superseded",),
            "related_operation_id": "00000000-0000-4000-8000-0000000000cc",
            "observation": None,
        }
    )
    text = _resume_text(report)
    assert "İlgili iş: 00000000-0000-4000-8000-0000000000cc" in text
    assert "- source_superseded:" in text


@pytest.mark.parametrize("names", [("source_terminal",), ("source_terminal", "local_changed")])
def test_a_refused_continuation_is_explained_in_the_text_error_output(names):
    error = ContinuationNotPossible(names, SOURCE)
    block = OutputRenderer._blockers_text(error.blockers, SOURCE)
    for name in names:
        reason, step = BLOCKER_TEXT[name]
        assert f"- {name}: {reason}\n  Sonraki adım: {step}" in block
    assert block.endswith(
        f"Rapor: yorunge datasets upload resume --operation-id {SOURCE} --accept-unverified-read"
    )


# --- an error that names another operation than the one asked about ------------------------------

OTHER = "00000000-0000-4000-8000-0000000000cc"


def rendered(output, error, *, requested):
    stderr = io.StringIO()
    renderer = OutputRenderer(
        output,
        stderr=stderr,
        stdout=io.StringIO(),
        upload_guidance=True,
        requested_operation_id=requested,
    )
    renderer.error(error)
    return stderr.getvalue()


def test_an_error_about_a_related_operation_says_it_is_not_the_one_asked_about():
    text = rendered("text", OperationError("operation_conflict", OTHER), requested=SOURCE)
    assert f"İş: {OTHER}" in text
    assert f"İstediğiniz iş {SOURCE} değil; yukarıdaki iş ona bağlı" in text
    assert f"İncele: yorunge datasets upload show --operation-id {OTHER}" in text


@pytest.mark.parametrize("code", ["state_invalid", "operation_not_found", "operation_uncertain"])
def test_only_a_conflict_is_described_as_belonging_to_the_operation_asked_about(code):
    # another code naming another row (a broken row of the store, say) is not "its continuation"
    text = rendered("text", OperationError(code, OTHER), requested=SOURCE)
    assert f"İş: {OTHER}" in text and "İstediğiniz iş" not in text


@pytest.mark.parametrize("requested", [SOURCE, SOURCE.upper(), None])
def test_an_error_about_the_asked_operation_or_without_one_has_no_such_line(requested):
    text = rendered("text", OperationError("operation_conflict", SOURCE), requested=requested)
    assert f"İş: {SOURCE}" in text and "İstediğiniz iş" not in text


@pytest.mark.parametrize("output", ["json", "ndjson"])
def test_the_machine_error_never_carries_the_line(output):
    text = rendered(output, OperationError("operation_conflict", OTHER), requested=SOURCE)
    envelope = json.loads(text.splitlines()[0])
    assert envelope["operation_id"] == OTHER and "İstediğiniz" not in text
