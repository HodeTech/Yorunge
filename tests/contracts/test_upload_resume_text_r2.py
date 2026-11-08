"""What round two of P02-3i pinned about the words a person is given.

Every sentence of advice here was wrong, vacuous or unpinned once: a person is told to run a
command the state refuses, to wait for what has already happened, to take a report again that can
never change, or to re-send what ADR-0031 §3 says is irreversible without hearing so.
"""

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from yorunge.adapters.upload_public import ResumeHint
from yorunge.cli import main
from yorunge.cli.output import OutputRenderer
from yorunge.cli.upload import (
    BLOCKER_TEXT,
    ORPHAN_NOTE,
    RESUME_ERROR_HINTS,
    UNCONFIRMED_WARNING,
    _continue_text,
    _quota_lines,
    _resume_next_lines,
    _resume_text,
    _selection_text,
    _summary_text,
    _unknown_text,
    explained_blockers,
)
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.upload_public import DatasetUploadSummary
from yorunge.domain.upload_resume import BLOCKERS
from yorunge.domain.upload_resume_report import DatasetUploadResumeReport

SOURCE = "00000000-0000-4000-8000-000000000009"
OTHER = "00000000-0000-4000-8000-0000000000cc"


# --- which blockers a person is told about --------------------------------------------------------


@pytest.mark.parametrize(
    "held,told",
    [
        (("source_terminal", "reconcile_available"), ("source_terminal",)),
        (("reconcile_available",), ("reconcile_available",)),  # alone it is the next step
        (
            ("extra_remote", "inventory_unreliable", "inventory_too_large"),
            ("extra_remote", "inventory_too_large"),
        ),
        (("inventory_unreliable",), ("inventory_unreliable",)),  # alone, taking it again helps
        (("source_active",), ("source_active",)),
        ((), ()),
        (
            (
                "source_terminal",
                "reconcile_available",
                "inventory_unreliable",
                "inventory_too_large",
            ),
            ("source_terminal", "inventory_too_large"),
        ),
    ],
)
def test_a_blocker_is_explained_only_where_its_advice_can_still_help(held, told):
    assert explained_blockers(held) == told
    assert set(told) <= set(BLOCKERS)


def test_the_error_block_of_a_refused_prepare_explains_the_same_blockers_as_the_report():
    # the third place a person reads the blockers: the stderr of `resume --prepare`
    block = OutputRenderer._blockers_text(("source_terminal", "reconcile_available"), SOURCE)
    assert "- source_terminal:" in block and "reconcile_available" not in block
    block = OutputRenderer._blockers_text(
        ("extra_remote", "inventory_unreliable", "inventory_too_large"), SOURCE
    )
    assert "- inventory_too_large:" in block and "Biraz sonra raporu yeniden alın" not in block
    assert block.endswith(
        f"Rapor: yorunge datasets upload resume --operation-id {SOURCE} --accept-unverified-read\n"
        "Özel --config/--profile/--state-dir kullandıysanız aynı seçenekleri koruyun."
    )


def test_the_show_hint_of_a_source_with_a_continuation_does_not_send_a_person_to_reconcile():
    summary = SimpleNamespace(
        operation_id=SOURCE, dataset_id="00000000-0000-4000-8000-000000000909"
    )
    superseded = ResumeHint(("source_superseded",), OTHER)
    lines = "\n".join(_unknown_text(summary, superseded))
    assert "reconcile --operation-id" not in lines  # that command is refused for this source
    assert f"Devamı: {OTHER}" in lines and "source_superseded" in lines
    # the general advice stays for a source nobody has continued (or one whose proof is missing)
    for hint in (None, ResumeHint((), None), ResumeHint(("reconcile_available",), None)):
        assert f"reconcile --operation-id {SOURCE}" in "\n".join(_unknown_text(summary, hint))


def test_a_terminal_source_is_not_told_to_reconcile_in_the_show_hint():
    summary = SimpleNamespace(operation_id=SOURCE, dataset_id=None)
    lines = "\n".join(
        _continue_text(summary, ResumeHint(("source_terminal", "reconcile_available"), None))
    )
    assert "source_terminal" in lines and "reconcile_available" not in lines


# --- the sentences of the blockers ---------------------------------------------------------------


def test_the_sentences_that_round_one_corrected_stay_corrected():
    conflict = " ".join(BLOCKER_TEXT["conflict"])
    assert "aynı adlı ama içeriği farklı" in conflict and "kopya" in conflict
    assert "aynı içerik başka adda" in conflict  # three causes, not the first of them
    assert "--accept-unverified-read" in BLOCKER_TEXT["reconcile_available"][1]
    ineligible = BLOCKER_TEXT["source_ineligible"][1]
    assert "kaynağının kimliğiyle resume verin" in ineligible  # a continuation that sent nothing
    assert (
        "reconcile --operation-id --accept-unverified-read" in ineligible
    )  # what ends a waiting one
    assert "lease dolunca yerel olarak iptal edilir" not in ineligible  # nothing cancels by itself
    create = BLOCKER_TEXT["create_unknown"]
    assert "hiç gönderilmemiş ya da sonucu bilinmiyor" in create[0]
    assert "aynı adlı yeni plan reddedilir" in create[1] and "ikinci bir veri seti" in create[1]
    assert "yeni plan kurulabilir" not in create[1]  # a create intent claims the name


def test_the_consent_names_the_irreversible_consequence_and_the_wait_that_helps():
    warning = " ".join(UNCONFIRMED_WARNING)
    for phrase in (
        "aynı adlı bir kopya yaratabilir",
        "`conflict` ile engellenir",
        "yalnız Platform arayüzünde silinebilir",
        "yetim nesneler",
        "dolduktan sonra da bir süre bekleyin",  # waiting for the lease alone proves nothing
        "sınırsız gecikebilir",
    ):
        assert phrase in warning, phrase
    assert "yetim nesneler" in ORPHAN_NOTE


def _review(files, bytes_, total):
    return SimpleNamespace(
        summary=SimpleNamespace(schema_version=3),
        request_limits=SimpleNamespace(max_presign=files, max_upload_bytes=bytes_),
        manifest=SimpleNamespace(file_count=total),
    )


def test_the_note_about_orphan_objects_is_given_only_where_something_is_sent_again():
    sending = _selection_text(_review(2, 9, 3))
    assert sending[0] == (
        "Bu devamda gönderilecek: 2 dosya, 9 byte (manifestin geri kalanı Platform’da zaten "
        "görülüyor)."
    )
    assert sending[1:] == (ORPHAN_NOTE,)
    everything = _selection_text(_review(3, 9, 3))
    assert everything[0] == "Bu devamda gönderilecek: 3 dosya, 9 byte." and everything[1:] == (
        ORPHAN_NOTE,
    )
    check_only = _selection_text(_review(0, 0, 3))  # M = 0: a check of the dataset, nothing sent
    assert len(check_only) == 1 and "yetim" not in check_only[0]
    assert (
        _selection_text(
            SimpleNamespace(request_limits=None, summary=SimpleNamespace(schema_version=2))
        )
        == ()
    )


# --- the hints of the errors a resume meets ------------------------------------------------------


def test_a_conflict_with_another_operation_names_the_report_that_leads_out():
    hint = RESUME_ERROR_HINTS["operation_conflict"]
    assert callable(hint)
    text = hint(OperationError("operation_conflict", OTHER))
    assert text is not None
    assert f"resume --operation-id {OTHER} --accept-unverified-read" in text
    assert "en çok 150 sn" in text and "show" not in text
    assert hint(YorungeError("operation_conflict")) is None  # nothing to name: nothing added


def test_the_other_resume_errors_say_what_a_person_does():
    hints = RESUME_ERROR_HINTS
    legacy = hints["state_invalid"]
    assert isinstance(legacy, str)
    assert "eski (v1)" in legacy and "yalnız tarihtir" in legacy and "show --operation-id" in legacy
    assert "bütünlük denetimini" in legacy  # and the other cause of the same code stays covered
    changed = hints["input_changed"]
    assert isinstance(changed, str)
    assert "yüklemedeki haline getirip" in changed and "ayrı bir ekleme işidir" in changed
    approval = hints["approval_required"]
    assert isinstance(approval, str)
    assert "--accept-unverified-read" in approval and "--accept-unconfirmed-effects" in approval
    assert "verin" not in approval  # a person who gave the first is not told to give it again


# --- the help ------------------------------------------------------------------------------------


def _help(capsys, *path):
    with pytest.raises(SystemExit) as stop:
        main([*path, "--help"])
    assert stop.value.code == 0
    return " ".join(capsys.readouterr().out.split())  # argparse wraps lines: compare words


def test_the_help_of_resume_names_where_the_reasons_are_and_what_the_consent_costs(capsys):
    text = _help(capsys, "datasets", "upload", "resume")
    assert "neden her engelin satırında yazılıdır" in text
    assert "--accept-unconfirmed-effects" in text
    assert "aynı adlı kopya oluşabilir ve sonraki devamları engeller" in text
    assert "lease süresinin dolmasını ve sonra da bir süre bekleyin" in text


def test_the_help_of_approve_names_what_the_consent_costs(capsys):
    text = _help(capsys, "datasets", "upload", "approve")
    assert "--accept-unconfirmed-effects" in text
    assert "geri alınamaz" in text and "aynı adlı kopya oluşabilir" in text
    assert "lease süresinin dolmasını ve sonra da bir süre bekleyin" in text


def test_the_help_of_start_says_it_starts_either_family_of_plan(capsys):
    text = _help(capsys, "datasets", "upload")
    assert "Planı bir kez başlat (özgün ya da devam planı)" in text


# --- what round two's mutation run found nobody pinning -------------------------------------------

FIXTURES = Path(__file__).parents[1] / "fixtures"


def golden(name):
    return DatasetUploadResumeReport.model_validate_json(
        (FIXTURES / f"dataset-continuation-resume-report-v1-{name}.json").read_bytes()
    )


def run(*arguments):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["datasets", "upload", *arguments, "--output", "json"])
    return code, out.getvalue(), err.getvalue()


def original_plan_without_approval():
    value = DatasetUploadSummary.model_validate_json(
        (FIXTURES / "dataset-upload-summary-v2.json").read_bytes()
    )
    return value.model_copy(
        update={
            "approval_status": None,
            "approval_expires_at": None,
            "operation_id": None,
            "operation_status": None,
            "dataset_id": None,
            "verification_level": "none",
            "authority_verified": False,
        }
    )


def test_the_approval_hint_of_an_original_plan_never_speaks_of_unconfirmed_effects():
    # the shared hint was rewritten for continuations; the original side must stay as it was
    text = "\n".join(_summary_text(original_plan_without_approval()))
    assert "Onay: yorunge datasets upload approve --plan-id" in text
    assert "--accept-unconfirmed-effects" not in text


def test_a_report_without_unconfirmed_files_does_not_ask_for_the_unconfirmed_flag():
    report = golden("eligible")
    quiet = report.model_copy(
        update={
            "observation": report.observation.model_copy(update={"unconfirmed_ack_required": False})
        }
    )
    text = _resume_text(quiet)
    assert "Hazırla: yorunge datasets upload resume" in text
    assert "--accept-unconfirmed-effects" not in text and "yetim" not in text


def test_an_exhausted_operation_quota_is_a_certain_limit_like_the_plan_quota():
    report = golden("eligible")
    full = report.model_copy(
        update={"quota_used": report.quota_used.model_copy(update={"operations": 128})}
    )
    assert any("Kota dolu" in line and "iş" in line for line in _quota_lines(full))
    assert "Hazırla:" not in "\n".join(_resume_next_lines(full))


@pytest.mark.parametrize("verb", ["resume", "reconcile"])
def test_a_repeated_unverified_read_flag_is_a_usage_error_before_any_state(tmp_path, verb):
    absent = tmp_path / "absent"
    code, out, err = run(
        verb,
        "--operation-id",
        str(uuid4()),
        "--accept-unverified-read",
        "--accept-unverified-read",
        "--state-dir",
        str(absent),
    )
    assert code == 2 and out == "" and json.loads(err)["code"] == "invalid_request"
    assert not absent.exists()


@pytest.mark.parametrize("verb", ["resume", "approve", "start", "reconcile"])
def test_the_root_level_project_is_refused_by_every_verb_that_takes_a_plan_or_a_source(
    tmp_path, verb
):
    extra = {
        "resume": ["--operation-id", str(uuid4())],
        "reconcile": ["--operation-id", str(uuid4())],
        "approve": ["--plan-id", str(uuid4()), "--confirm", "0" * 64],
        "start": ["--plan-id", str(uuid4())],
    }[verb]
    absent = tmp_path / "absent"
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(
            ["--project", str(uuid4()), "datasets", "upload", verb, *extra]
            + ["--state-dir", str(absent), "--output", "json"]
        )
    assert code == 2 and json.loads(err.getvalue())["code"] == "invalid_request"
    assert not absent.exists()


def test_the_error_details_of_a_refusal_carry_no_capacity_kind():
    from yorunge.domain.streams import ContinuationErrorDetails

    with pytest.raises(ValueError):
        ContinuationErrorDetails(
            reason_code="continuation_not_possible",
            capacity_kind="store",
            blockers=("source_terminal",),
        )


def test_the_flag_relation_of_resume_is_judged_before_the_store_and_names_the_source(tmp_path):
    from yorunge import api

    identity, root = str(uuid4()), tmp_path / "absent"
    with pytest.raises(YorungeError) as raised:
        api.resume_dataset_upload(
            identity, accept_unverified_read=True, accept_unconfirmed_effects=True, state_dir=root
        )
    assert raised.value.code == "invalid_request"
    assert getattr(raised.value, "operation_id", None) == identity
    assert not root.exists()


def rendered(output, error, *, requested):
    stderr = io.StringIO()
    OutputRenderer(
        output,
        stderr=stderr,
        stdout=io.StringIO(),
        upload_guidance=True,
        requested_operation_id=requested,
    ).error(error)
    return stderr.getvalue()


def test_the_comparison_of_operation_ids_in_the_error_text_ignores_the_case():
    # a canonical id is lower case, but a caller's spelling must not make a related operation look
    # like another one: hex letters, so that upper() really differs
    asked = "00000000-0000-4000-8000-0000000000ab"
    named = OperationError("operation_conflict", asked)
    for requested in (asked, asked.upper()):
        text = rendered("text", named, requested=requested)
        assert "İstediğiniz iş" not in text, requested
