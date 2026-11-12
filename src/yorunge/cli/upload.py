"""Lazy upload parser and user-facing rendering; all business rules live in the API."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

from yorunge.cli.output import _silence_failed_descriptor, write_utf8

if TYPE_CHECKING:
    from yorunge.adapters.upload_public import ResumeHint
    from yorunge.application.upload_progress import UploadProgress
    from yorunge.cli import Parser
    from yorunge.domain.errors import YorungeError
    from yorunge.domain.models import Model, Result
    from yorunge.domain.upload_public import (
        DatasetUploadsPage,
        DatasetUploadSummary,
        DatasetUploadSummaryV3,
        UploadIntentReview,
        UploadSummary,
    )
    from yorunge.domain.upload_resume_report import DatasetUploadResumeReport

LOCAL = {"list", "show", "review", "revoke"}
SINGLETONS = {
    "--output",
    "--non-interactive",
    "--state-dir",
    "--config",
    "--profile",
    "--project",
    "--manifest",
    "--name",
    "--owner-user",
    "--owner-org",
    "--modality",
    "--storage-origin",
    "--budget-cr",
    "--unpriced",
    "--admission-policy",
    "--plan-id",
    "--operation-id",
    "--confirm",
    "--accept-unverified-authority",
    "--accept-unpriced-cost",
    "--accept-unconfirmed-effects",
    "--accept-unverified-read",
    "--prepare",
    "--limit",
    "--cursor",
    "--license",
}

PLAN_STATES = {"draft": "taslak", "prepared": "hazır", "attempt_ready": "açık denemeye hazır"}
OPERATION_STATES = {
    "admitted": "henüz gönderilmedi",
    "running": "devam ediyor",
    "unknown": "belirsiz",
    "succeeded": "metadata doğrulaması tamamlandı",
    "failed": "başarısız",
    "cancelled": "yerel olarak sonlandırıldı",
}
RISKS = {"authority_unverified": "yetki doğrulanmadı", "cost_unverified": "fiyat doğrulanmadı"}
BLOCKERS = {
    "authority_unverified": "yetki kanıtı eksik",
    "cost_unverified": "fiyat üst sınırı eksik",
    "cost_exceeds_budget": "maliyet üst sınırı bütçeyi aşıyor",
    "inputs_unverified": "içerik doğrulanmadı",
}


def configure(upload: Parser) -> None:
    from yorunge.cli import common

    common(upload, context=False)
    upload.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    actions = upload.add_subparsers(dest="upload_action", required=True)
    descriptions = {
        "plan": "Güncel dosyaları kontrol et; private oluşturma planını kaydet",
        "review": "Onaydan önce seçilmiş hedefi ve içeriği yerel incele",
        "approve": "Tam digest ve gerekli risk seçimleriyle onayla",
        "revoke": "Yerel onayı geri al; verilmiş isteği geri çekmez",
        "start": "Planı bir kez başlat (özgün ya da devam planı); mevcut işi tekrar göndermez",
        "list": "Yerel plan ve iş özetlerini göster",
        "show": "Plan veya operation ID ile kayıtlı özeti göster",
        "reconcile": "Aynı işi yalnız uzak okumayla uzlaştır",
        "resume": "Yarım kalan aktarımın ne gerektirdiğini raporla; --prepare planı kaydeder",
    }
    for action, description in descriptions.items():
        command = actions.add_parser(action, help=description, description=description)
        common(command, context=False)
        command.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
        if action not in LOCAL:
            command.add_argument("--config", type=Path, default=argparse.SUPPRESS)
            command.add_argument("--profile", default=argparse.SUPPRESS)
        _arguments(command, action)


def _arguments(command: argparse.ArgumentParser, action: str) -> None:
    if action == "plan":
        _plan_arguments(command)
    elif action == "list":
        command.add_argument("--plan-id")
        command.add_argument("--limit", type=int, default=50)
        command.add_argument("--cursor")
    elif action == "show":
        identity = command.add_mutually_exclusive_group(required=True)
        identity.add_argument("--operation-id")
        identity.add_argument("--plan-id")
    elif action == "reconcile":
        command.add_argument("--operation-id", required=True)
        command.add_argument("--accept-unverified-read", action="store_true")
    elif action == "resume":
        _resume_arguments(command)
    else:
        command.add_argument("--plan-id", required=True)
        if action == "approve":
            command.add_argument(
                "--confirm", required=True, help="İncelenen planın tam SHA-256 digest’i"
            )
            command.add_argument("--accept-unverified-authority", action="store_true")
            command.add_argument("--accept-unpriced-cost", action="store_true")
            command.add_argument(
                "--accept-unconfirmed-effects",
                action="store_true",
                help="Yalnız devam planı: son onay isteği gitmiş olabilecek dosyaların yeniden "
                "gönderilmesini kabul et (geri alınamaz: aynı adlı kopya oluşabilir ve sonraki "
                "devamları engeller; önce lease süresinin dolmasını ve sonra da bir süre bekleyin)",
            )


def _resume_arguments(command: argparse.ArgumentParser) -> None:
    command.epilog = (
        "Varsayılan salt okuma raporudur: yerel plan yazmaz, uzak yazma yapmaz ve devam edilsin "
        "ya da edilemesin exit 0 verir (neden her engelin satırında yazılıdır). Dataset’in "
        "okunması reconcile ile aynı açık seçimi ister (--accept-unverified-read). --prepare "
        "aynı gözlemi yapar ve engel yoksa devam planını kaydeder; engel varsa hata verir. Plan "
        "sonra review, approve ve start ile ilerler."
    )
    command.add_argument("--operation-id", required=True, help="Yarım kalan kaynak işin kimliği")
    command.add_argument(
        "--accept-unverified-read",
        action="store_true",
        help="Dataset’i doğrulanmamış açık okuma denemesiyle okumayı kabul et",
    )
    command.add_argument(
        "--prepare",
        action="store_true",
        help="Engel yoksa devam planını yerel olarak kaydet (yalnız yerel yazma)",
    )
    command.add_argument(
        "--accept-unconfirmed-effects",
        action="store_true",
        help="Yalnız --prepare ile: son onay isteği gitmiş olabilecek dosyaların yeniden "
        "gönderilmesini kabul et (geri alınamaz: aynı adlı kopya oluşabilir ve sonraki "
        "devamları engeller; önce lease süresinin dolmasını ve sonra da bir süre bekleyin)",
    )


def _plan_arguments(command: argparse.ArgumentParser) -> None:
    command.epilog = (
        "Gizli dosyalar dahil en çok 128 dosya; dosya başına 500.000.000 byte, toplam 1 GiB. "
        "Her PUT en çok 120 s: 500 MB için kesintisiz en az 33,34 Mbit/s gerekir; "
        "daha yavaş aktarım belirsiz kalabilir, otomatik resume yoktur. "
        "Plan/onay/ilk çalıştırma bütçesi ayrı ayrı en çok 900 s. "
        "Kalıcı store kotası: 128 plan/iş, 4.096 dosya ve 16 MiB rezerv; "
        "taslak ve geçmiş kayıtlar otomatik silinmez."
    )
    command.add_argument("root", type=Path, help="Gizli dosyalar dahil taranacak yerel kök")
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--name", required=True)
    command.add_argument(
        "--project", default=argparse.SUPPRESS, help="Açık proje kimliği (zorunlu)"
    )
    owner = command.add_mutually_exclusive_group(required=True)
    owner.add_argument("--owner-user")
    owner.add_argument("--owner-org")
    command.add_argument(
        "--modality", choices=("VISION", "AUDIO", "NLP", "MULTIMODAL", "MEDICAL"), required=True
    )
    command.add_argument("--license")
    command.add_argument("--tag", action="append", default=[])
    command.add_argument(
        "--storage-origin", help="Direct origin; mevcut Platform profili desteklemez"
    )
    command.add_argument(
        "--admission-policy",
        choices=("verified-only", "explicit-attempt"),
        default="verified-only",
        help="Varsayılan verified-only kanıt ister; explicit-attempt ayrı açık risk seçimidir",
    )
    cost = command.add_mutually_exclusive_group(required=True)
    cost.add_argument(
        "--budget-cr", help="CR tutarı; en çok altı kesir hanesi, fiyat kanıtı gerekir"
    )
    cost.add_argument(
        "--unpriced", action="store_true", help="CR tavanı uygulanmaz; açık deneme gerekir"
    )


def _plan(args: argparse.Namespace) -> Result[DatasetUploadSummary]:
    from yorunge import api
    from yorunge.domain.dataset_upload import UploadOwner, UploadParameters
    from yorunge.domain.dataset_upload_v2 import AdmissionPolicy
    from yorunge.domain.errors import YorungeError

    if "project" not in vars(args):
        raise YorungeError("invalid_request")
    owner = parameters = None
    try:
        if len(args.tag) != len(set(args.tag)):
            raise ValueError("duplicate tag")
        owner = UploadOwner(
            kind="user" if args.owner_user is not None else "organization",
            id=args.owner_user if args.owner_user is not None else args.owner_org,
        )
        parameters = UploadParameters(
            name=args.name,
            modality=args.modality,
            visibility="private",
            contributions_enabled=False,
            license=args.license,
            tags=tuple(sorted(args.tag)),
        )
    except ValueError:
        pass
    if owner is None or parameters is None:
        raise YorungeError("invalid_request")
    return api.prepare_dataset_upload(
        args.root,
        manifest=args.manifest,
        owner=owner,
        parameters=parameters,
        project=args.project,
        budget_cr=args.budget_cr,
        unpriced=args.unpriced,
        admission_policy=cast("AdmissionPolicy", args.admission_policy.replace("-", "_")),
        storage_origin=args.storage_origin,
        config=vars(args).get("config"),
        profile=vars(args).get("profile"),
        state_dir=vars(args).get("state_dir"),
    )


def dispatch(
    args: argparse.Namespace,
) -> (
    Result[DatasetUploadSummary]
    | Result[UploadSummary]
    | Result[UploadIntentReview]
    | Result[DatasetUploadsPage]
    | Result[DatasetUploadResumeReport]
):
    from yorunge import api
    from yorunge.cli import reject_context

    options, action = vars(args), args.upload_action
    state = options.get("state_dir")
    if action in LOCAL:
        reject_context(args, ("config", "profile", "project"))
    elif action != "plan":
        reject_context(args, ("project",))
    if action == "plan":
        return _plan(args)
    if action == "list":
        return api.list_dataset_uploads(
            plan_id=args.plan_id, limit=args.limit, cursor=args.cursor, state_dir=state
        )
    if action == "show":
        return _show(args, state)
    if action == "review":
        return api.review_dataset_upload(args.plan_id, state_dir=state)
    if action == "revoke":
        return api.revoke_dataset_upload(args.plan_id, state_dir=state)
    context = {name: options.get(name) for name in ("config", "profile", "state_dir")}
    if action == "approve":
        return api.approve_dataset_upload(
            args.plan_id,
            args.confirm,
            accept_unverified_authority=args.accept_unverified_authority,
            accept_unpriced_cost=args.accept_unpriced_cost,
            accept_unconfirmed_effects=args.accept_unconfirmed_effects,
            **context,
        )
    if action == "reconcile":
        return api.reconcile_dataset_upload(
            args.operation_id, accept_unverified_read=args.accept_unverified_read, **context
        )
    if action == "resume":
        return api.resume_dataset_upload(
            args.operation_id,
            prepare=args.prepare,
            accept_unverified_read=args.accept_unverified_read,
            accept_unconfirmed_effects=args.accept_unconfirmed_effects,
            **context,
        )
    from yorunge.application.upload_progress import observe_upload

    with observe_upload(_progress_sink(options.get("output", "text"))):
        return api.start_dataset_upload(args.plan_id, **context)


def _show(args: argparse.Namespace, state: Path | None) -> Result[UploadSummary]:
    from yorunge import api

    shown = api.show_dataset_upload(
        plan_id=args.plan_id, operation_id=args.operation_id, state_dir=state
    )
    if vars(args).get("output", "text") == "text" and shown.data.operation_status in HINTED:
        # What the journal alone says of continuing: only the text of an operation that is
        # unknown, or still "running" (a killed process leaves it so) uses it; the summary
        # itself does not change.
        from yorunge.adapters.upload_public import resume_hint

        assert shown.data.operation_id is not None
        args.resume_hint = resume_hint(state, shown.data.operation_id)
    return shown


def _progress_sink(output: str) -> ProgressText | None:
    """The progress line of a text-output start: only where stderr is a terminal."""
    progress = ProgressText(sys.stderr) if output == "text" else None
    return progress if progress is not None and progress.enabled else None


def operation_id(data: Model) -> str | None:
    from yorunge.domain.upload_public import (
        DatasetUploadSummary,
        DatasetUploadSummaryV3,
        UploadIntentReview,
    )
    from yorunge.domain.upload_resume_report import DatasetUploadResumeReport

    if isinstance(data, DatasetUploadResumeReport):
        return data.source_operation_id  # the report is about the source it was asked for
    if isinstance(data, DatasetUploadSummary | DatasetUploadSummaryV3):
        return data.operation_id
    return data.summary.operation_id if isinstance(data, UploadIntentReview) else None


def text(data: Model, hint: ResumeHint | None = None) -> str:
    from yorunge.domain.upload_public import (
        DatasetUploadsPage,
        DatasetUploadSummary,
        DatasetUploadSummaryV3,
        UploadIntentReview,
    )
    from yorunge.domain.upload_resume_report import DatasetUploadResumeReport

    if isinstance(data, UploadIntentReview):
        return _review_text(data)
    if isinstance(data, DatasetUploadResumeReport):
        return _resume_text(data)
    if isinstance(data, DatasetUploadsPage):
        rows = [
            f"{p.plan_id}  {p.operation_id or '-'}  "
            + (
                OPERATION_STATES[p.operation_status]
                if p.operation_status is not None
                else PLAN_STATES[p.plan_status]
            )
            for p in data.uploads
        ]
        rows.insert(0, "Plan ID  İş ID  Durum")
        if not data.uploads:
            rows.append("Kayıtlı upload yok.")
        if data.next_cursor is not None:
            rows.append(f"Sonraki sayfa: --cursor {data.next_cursor}")
        return "\n".join(rows)
    if not isinstance(data, DatasetUploadSummary | DatasetUploadSummaryV3):
        raise TypeError("upload result type required")
    return "\n".join(_summary_text(data, hint))


def _continuation_text(data: DatasetUploadSummaryV3) -> list[str]:
    """What makes a continuation what it is: whose remainder it sends, and how much."""
    lines = [
        f"Devam: {data.continuation_of} işinin kalanını gönderir; {data.continuation_files} dosya "
        f"gönderilir, {data.remote_present_files} dosya Platform’da zaten görülüyor."
    ]
    if data.uncertain_files:
        lines.append(
            f"Gönderilecek dosyalardan {data.uncertain_files} tanesinin son onay isteği gitmiş "
            "olabilir (belirsiz); onay bunun için ayrı bir seçim ister."
        )
    return lines


def _summary_text(data: UploadSummary, hint: ResumeHint | None = None) -> list[str]:
    from yorunge.domain.upload_public import DatasetUploadSummaryV3

    lines = [
        f"Plan: {data.plan_id}",
        f"Digest: {data.plan_digest}",
        f"Plan durumu: {PLAN_STATES[data.plan_status]}",
    ]
    if isinstance(data, DatasetUploadSummaryV3):
        lines.extend(_continuation_text(data))
    elif data.legacy_history_only:
        lines.append("Tarihsel kayıt; yeni yazma kapalı.")
    if data.approval_status is not None:
        lines.append(
            f"Onay: {'kaydedildi' if data.approval_status == 'approved' else 'geri alındı'} "
            f"(bitiş: {data.approval_expires_at})"
        )
    if data.operation_id is not None:
        assert data.operation_status is not None
        lines.extend(
            (f"İş: {data.operation_id}", f"Durum: {OPERATION_STATES[data.operation_status]}")
        )
    if data.dataset_id is not None:
        lines.append(f"Veri seti: {data.dataset_id}")
    if data.verification_level == "metadata":
        lines.append(
            "Veri setinin bütün dosyalarının metadata eşliği doğrulandı; uzak byte’lar "
            "indirilip hash’lenmedi."
            if isinstance(data, DatasetUploadSummaryV3)
            else "Dosya metadata eşliği doğrulandı; uzak byte’lar indirilip hash’lenmedi."
        )
    if not data.authority_verified:
        lines.append("Yazma yetkisi doğrulanmış sayılmaz.")
    else:
        lines.append("Başlangıç yazma yetkisi kanıtı tarihsel olarak doğrulandı.")
    lines.extend(_cost_text(data))
    if data.risks:
        lines.append("Riskler: " + "; ".join(RISKS[risk] for risk in data.risks))
    if data.blockers:
        lines.append("Engeller: " + "; ".join(BLOCKERS[blocker] for blocker in data.blockers))
    lines.extend(_next_text(data, hint))
    return lines


def _next_text(data: UploadSummary, hint: ResumeHint | None = None) -> list[str]:
    if data.operation_id is not None:
        if data.operation_status == "unknown":
            return _unknown_text(data, hint)
        # A process that was killed leaves its operation "running" until the lease lapses: the
        # journal tells who is in the way (a live lease) or that the report can be taken.
        return _continue_text(data, hint) if data.operation_status == "running" else []
    lines = [f"İncele: yorunge datasets upload review --plan-id {data.plan_id}"]
    if data.legacy_history_only or data.blockers:
        if data.blockers:
            lines.append(
                "Engeller kapanmadan onay veya aktarım başlamaz. Mevcut Platform profili "
                "yetki/fiyat kanıtı üretmez; verified-only bu eksiklerle taslak kalır. "
                "Doğrulanmamış deneme ayrı explicit-attempt ve maliyet seçimi gerektirir."
            )
        return lines
    lines.extend(_approval_text(data))
    lines.append("Özel --config/--profile/--state-dir kullandıysanız aynı seçenekleri koruyun.")
    return lines


def explained_blockers(names: Sequence[str]) -> tuple[str, ...]:
    """The blockers a person is told about, each only where its advice can still help.

    A record that is over has no proof left to take (``reconcile_available``), and a listing that
    is too large is not one to take again later (``inventory_unreliable``).
    """
    held = tuple(names)
    silenced = {
        "reconcile_available": "source_terminal" in held,
        "inventory_unreliable": "inventory_too_large" in held,
    }
    return tuple(name for name in held if not silenced.get(name, False))


def _continue_text(data: UploadSummary, hint: ResumeHint | None) -> list[str]:
    """How to go on from an unknown operation, as far as its own journal can tell."""
    if hint is None:
        return []
    identity = data.operation_id
    if not hint.blockers:
        return [
            f"Devam için: yorunge datasets upload resume --operation-id {identity} "
            "--accept-unverified-read",
            "Bu bir salt okuma raporudur: ne kaldığını gösterir, hiçbir şey göndermez, "
            "plan ya da upload kaydı yazmaz; --prepare ile devam planı kaydedilir.",
        ]
    lines = ["Devam şu an mümkün değil (yerel kayda göre):"]
    for name in explained_blockers(hint.blockers):
        reason, step = BLOCKER_TEXT[name]
        lines.extend((f"- {name}: {reason}", f"  Sonraki adım: {step}"))
    if hint.related_operation_id is not None:
        lines.append(
            f"Devamı: {hint.related_operation_id} — yorunge datasets upload show "
            f"--operation-id {hint.related_operation_id}"
        )
    return lines


def _unknown_text(data: UploadSummary, hint: ResumeHint | None = None) -> list[str]:
    lines = [
        f"İncele: yorunge datasets upload show --operation-id {data.operation_id}",
        "Aynı --state-dir ve uzlaştırmada aynı --config/--profile seçimini koruyun.",
        "Eksik aşamaları yeni plan/ad/store ile yeniden göndermeyin.",
    ]
    if data.dataset_id is None:
        lines.append(
            "Dataset ID kaydedilmedi; Platform’da private kaynak oluşmuş olabilir. "
            "Adından ID tahmin edilmez; otomatik kurtarma veya silme yapılmaz."
        )
    elif hint is None or not hint.blockers or "reconcile_available" in hint.blockers:
        # The general advice; when the journal itself says that `reconcile` would be refused (a
        # continuation stands, the record is over), the blocks below say what to do instead.
        lines.extend(
            (
                "Yalnız tam accepted grafiği ve create kanıtı olan uygun kayıt için salt okuma: "
                f"yorunge datasets upload reconcile --operation-id {data.operation_id}",
                "Doğrulanmamış okuma gerekiyorsa --accept-unverified-read ayrı açık seçimdir; "
                "eksik receipt okuma ile doldurulmaz.",
            )
        )
    lines.extend(_continue_text(data, hint))
    return lines


def _approval_text(data: UploadSummary) -> list[str]:
    from yorunge.domain.upload_public import DatasetUploadSummaryV3

    lines = []
    if data.approval_status is None:
        command = (
            f"Onay: yorunge datasets upload approve --plan-id {data.plan_id} "
            f"--confirm {data.plan_digest}"
        )
        if "authority_unverified" in data.risks:
            lines.append(
                "Yetki riskini kabul ediyorsanız onaya ayrıca "
                "--accept-unverified-authority ekleyin."
            )
        if data.cost_policy == "unpriced_accepted":
            lines.append(
                "Sayısal CR tavanı olmamasını kabul ediyorsanız ayrıca "
                "--accept-unpriced-cost ekleyin."
            )
        if isinstance(data, DatasetUploadSummaryV3) and data.uncertain_files:
            lines.append(
                "Son onay isteği gitmiş olabilecek dosyaların yeniden gönderilmesini kabul "
                "ediyorsanız ayrıca --accept-unconfirmed-effects ekleyin (aynı adlı kopya "
                "oluşabilir; kopya varsa sonraki devamlar `conflict` ile engellenir ve kopya "
                "yalnız Platform arayüzünde silinebilir)."
            )
        lines.append(command)
    elif data.approval_status == "approved":
        lines.append(f"Başlat: yorunge datasets upload start --plan-id {data.plan_id}")
    else:
        lines.append("Bu planın onayı geri alındı; aynı plan yeniden onaylanmaz.")
    return lines


def _credits(micros: int) -> str:
    whole, fraction = divmod(micros, 1_000_000)
    return f"{whole}.{fraction:06d}"


def _cost_text(data: UploadSummary) -> list[str]:
    lines = []
    if data.budget_micros is not None:
        lines.append(f"CR bütçesi: {_credits(data.budget_micros)} CR")
    if data.cost_policy == "unpriced_accepted":
        lines.append("CR tavanı uygulanmaz.")
    bound = data.cost_bound
    if bound is None:
        lines.append("Fiyat doğrulanmadı; bilinmeyen ücret sıfır değildir.")
        if data.cost_policy == "bounded_required":
            lines.append("Bütçe, güncel fiyat üst sınırı olmadan yürütme izni vermez.")
        return lines
    scope = "Devam başlatma" if data.schema_version == 3 else "İlk başlatma"
    lines.extend(
        (
            f"{scope} maliyet üst sınırı: {_credits(bound.maximum_micros)} CR",
            f"Ücret dönemi: {bound.charge_period_start} — {bound.charge_period_end}",
            "Dönem sonrası depolama: "
            + ("bilinmiyor" if bound.post_period_storage == "unknown" else "ek ücret yok"),
        )
    )
    return lines


def _review_text(data: UploadIntentReview) -> str:
    chosen = data.parameters
    lines = _summary_text(data.summary)
    lines.extend(
        (
            f"Seçilen hedef: {data.target.service_origin}{data.target.api_base_path}",
            f"Profil: {data.target.profile}",
            f"Seçilen sahip: {data.selected_owner.kind} {data.selected_owner.id}",
            f"Seçilen proje: {data.selected_project_id}",
            f"Yerel kök: {data.root}",
            f"İstenen ad: {chosen.name}",
            f"Tür: {chosen.modality}; görünürlük: private; katkılar: kapalı",
            f"Dosyalar: {data.manifest.file_count}; toplam: {data.manifest.total_bytes} byte",
            *_selection_text(data),
            f"Manifest: {data.manifest.digest}",
            f"Yükleme hedefi: {data.storage.origin or 'Platform API'}",
            f"Plan bitişi: {data.expires_at}",
            "Gizli dosyalar da dahildir; dosya adlarını onaydan önce yerel manifestten inceleyin.",
            "Sınırlar: 128 dosya; dosya başına 500.000.000 byte; toplam 1 GiB; PUT başına 120 s.",
            "500 MB için kesintisiz en az 33,34 Mbit/s gerekir; timeout otomatik resume üretmez.",
            "Bu seçilmiş niyettir; sağlayıcı kimlik veya izin doğrulaması değildir.",
        )
    )
    if data.request_limits is not None:
        limits = data.request_limits
        effects = limits.max_create + limits.max_project_link + limits.max_presign
        effects += limits.max_put + limits.max_confirm
        lines.append(
            f"Uzak sınırlar: {effects} yazma denemesi; "
            f"{limits.max_read_requests} okuma/{limits.max_read_attempts} deneme"
        )
    if chosen.license is not None:
        lines.append(f"Lisans: {chosen.license}")
    if chosen.tags:
        lines.append("Etiketler: " + ", ".join(chosen.tags))
    return "\n".join(lines)


UNCONFIRMED_WARNING = (
    "Uyarı: bazı dosyaların son onay (confirm) isteği sunucuya ulaşmış olabilir. Yeniden "
    "göndermek aynı adlı bir kopya yaratabilir; kopya varsa sonraki her devam `conflict` ile "
    "engellenir ve kopya yalnız Platform arayüzünde silinebilir.",
    "Kabul etmeden önce kaynağın lease süresi (en çok 150 sn) dolduktan sonra da bir süre "
    "bekleyin: sunucuda geç kalmış bir commit sınırsız gecikebilir. Yeniden gönderilen "
    "dosyaların önceki yüklemelerinden yetim nesneler kalabilir (silinmez, saklama maliyeti "
    "bilinmiyor).",
)
ORPHAN_NOTE = (
    "Yeniden gönderilen dosyalar yeni nesne anahtarıyla yüklenir; önceki presign/PUT’tan kalan "
    "yetim nesneler silinmez ve saklama maliyeti bilinmiyor."
)
HINTED = ("unknown", "running")  # the operations whose `show` text may point at `resume`

# For each closed blocker of a resume report, one sentence of why and one of what to do next: the
# JSON carries only the names, so this is the whole explanation a person gets.
BLOCKER_TEXT: dict[str, tuple[str, str]] = {
    "source_active": (
        "Kaynak iş ya da devamı hâlâ çalışıyor (lease dolmadı).",
        "Lease bitince raporu yeniden alın; çalışan işe show --operation-id ile bakın.",
    ),
    "source_ineligible": (
        "Kaynak devam için uygun değil: henüz hiçbir şey göndermemiş ya da doğrulanmamış "
        "okumaya izin vermeyen (verified-only) bir kaynak.",
        "Devam yok; hiçbir şey göndermemiş bir devamsa kaynağının kimliğiyle resume verin, "
        "bekleyen kaynağı lease dolunca reconcile --operation-id --accept-unverified-read "
        "sonlandırır, sonra yeni plan kurun.",
    ),
    "source_superseded": (
        "Bu kaynağın iptal edilmemiş bir devamı zaten var.",
        "Devamın kimliğiyle show --operation-id çalıştırın; belirsizse onun için resume "
        "--operation-id verin, başarıyla bittiyse devam gerekmez.",
    ),
    "source_terminal": (
        "Kaynak iş sona ermiş (başarılı, başarısız ya da iptal edilmiş).",
        "Başarıyla bittiyse devam gerekmez; iptal edildiyse yeni plan kurulabilir; başarısızsa "
        "nedenini Platform’da inceleyin, yeni plan reddedilen yazmayı aşmaz.",
    ),
    "reconcile_available": (
        "Kaynağın bütün aşamaları kayıtlı; yalnız metadata kanıtı eksik.",
        "reconcile --operation-id ve --accept-unverified-read ile salt okuma kanıtı alın; "
        "invalid_response alırsanız öğeler kayıtla uyuşmuyordur, Platform arayüzünde inceleyin.",
    ),
    "create_unknown": (
        "Platform’daki veri setinin kimliği kaydedilmedi: create hiç gönderilmemiş ya da sonucu "
        "bilinmiyor.",
        "Platform arayüzünde inceleyin (otomatik kurtarma ya da silme yoktur); create "
        "gönderildiyse aynı adlı yeni plan reddedilir, farklı adlı plan ikinci bir veri seti "
        "yaratabilir.",
    ),
    "membership_unobserved": (
        "Veri setinin kaynağın oluşturduğu private veri seti olduğu ve projede tek kez "
        "göründüğü doğrulanamadı.",
        "Platform arayüzünde veri setini ve proje bağını kontrol edip raporu yeniden alın.",
    ),
    "known_negative": (
        "Kayıtlı zincirde bilinen olumsuz bir sonuç (reddedilmiş makbuz) var.",
        "Devam desteklenmez; Platform’daki durumu inceleyin, yeni plan reddedilen yazmayı aşmaz.",
    ),
    "drift_missing": (
        "Daha önce kabul edilmiş bir dosya Platform’da artık görünmüyor.",
        "Platform arayüzünde veri setini inceleyin; kaybolan dosyayı ürün kendiliğinden "
        "yeniden göndermez.",
    ),
    "conflict": (
        "Platform’da manifestle uyuşmayan bir öğe var: aynı adlı ama içeriği farklı, kopya ya da "
        "aynı içerik başka adda.",
        "Platform arayüzünde öğeyi silin ya da adını değiştirin.",
    ),
    "extra_remote": (
        "Veri setinde manifestte olmayan öğeler var.",
        "Platform arayüzünde fazla öğeleri inceleyin; ürün onları silmez.",
    ),
    "inventory_unreliable": (
        "Platform’un öğe listesi tutarlı bir bütün oluşturmuyor.",
        "Biraz sonra raporu yeniden alın; sürerse Platform’da inceleyin.",
    ),
    "inventory_too_large": (
        "Veri setinde 1.024’ten fazla öğe var; devam bu büyüklükte desteklenmez.",
        "Uzak durumu Platform arayüzünden inceleyin.",
    ),
    "local_changed": (
        "Yerel klasör ya da manifest, plandaki gibi değil.",
        "Klasörü yüklemedeki haline getirip raporu yeniden alın; değişmiş bir klasör bu işin "
        "devamı değil, ayrı bir ekleme işidir.",
    ),
}
CLASS_TEXT = {
    "pending_uncertain": "belirsiz (son onay isteği gitmiş olabilir)",
    "drift_missing": "kaybolmuş",
    "conflict": "çakışan",
    "inventory_unreliable": "güvenilmez listede",
}


def _conflict_hint(error: YorungeError) -> str | None:
    """Another operation stands in the way (the source's live continuation, or its own reader)."""
    identity = getattr(error, "operation_id", None)
    if identity is None:
        return None
    return (
        "Kaynak iş ya da devamı hâlâ çalışıyor ya da lease'i dolmadı (en çok 150 sn). Önce o işin "
        f"raporunu alın: yorunge datasets upload resume --operation-id {identity} "
        "--accept-unverified-read; --prepare'i raporun uygun dediği iş için verin."
    )


# The errors a `resume` meets in its own way: what a person does about each (the closed code and
# the fixed message stay as they are; this is added to the text output of that command alone).
RESUME_ERROR_HINTS: dict[str, str | Callable[[YorungeError], str | None]] = {
    "state_changed": (
        "Yerel durum rapor hazırlanırken değişti (anahtar döndürülmüş ya da saat izi "
        "değişmiş olabilir); aynı --config ve --profile ile komutu yeniden çalıştırın."
    ),
    "operation_conflict": _conflict_hint,
    "state_invalid": (
        "Bu kayıt devam ettirilemiyor: eski (v1) bir kayıt yalnız tarihtir (show --operation-id "
        "durumunu söyler); v1 değilse yerel durum geçersizdir, sahiplik ve bütünlük "
        "denetimini çalıştırın."
    ),
    "input_changed": (
        "Klasör ya da manifest plandakinden farklı: klasörü yüklemedeki haline getirip komutu "
        "yeniden verin; değişmiş bir klasör bu işin devamı değil, ayrı bir ekleme işidir."
    ),
    "state_busy": "Yerel durum deposu meşgul; çalışan başka bir komut bitince yeniden deneyin.",
    "upload_plan_not_valid": (
        "Gözlem sürerken plan penceresi doldu ya da saat geriye gitti; komutu yeniden çalıştırın."
    ),
    "invalid_request": (
        "Manifest’teki bir dosya yolu kullanılan anahtarla aynı olduğu için rapor "
        "gösterilemiyor ya da bir seçenek geçersiz; seçenekleri yardımla karşılaştırın."
    ),
    "invalid_response": (
        "Platform’un yanıtı beklenen biçimde değil ya da yerel yol kurallarına uymayan adlı bir "
        "öğe (örneğin CON, a., dosya:adı) var; öğe adı sorunluysa Platform arayüzünde öğeyi "
        "silin ya da adını değiştirin, değilse biraz sonra yeniden deneyin."
    ),
    "approval_required": (
        "Eksik açık seçim: dataset’in okunması için --accept-unverified-read; belirsiz "
        "dosyalarla --prepare için ayrıca --accept-unconfirmed-effects (geri alınamaz sonucu "
        "raporun uyarısından okuyun)."
    ),
}
QUOTA_TEXT = {"plans": "plan", "operations": "iş", "files": "dosya", "payload_bytes": "bayt"}


# What a continuation adds to the local record is exact for plans, operations and files and an
# upper bound for the payload (the plan is sealed at its true size when it is prepared).
CERTAIN_QUOTA = ("plans", "operations", "files")


def _quota_over(data: DatasetUploadResumeReport) -> tuple[list[str], list[str]]:
    """The limits this attempt would pass: for certain, and only by its upper bound."""
    from yorunge.domain.dataset_upload import (
        MAX_TRANSFER_FILES,
        MAX_TRANSFER_OPERATIONS,
        MAX_TRANSFER_PAYLOAD_BYTES,
        MAX_TRANSFER_PLANS,
    )

    limits = {
        "plans": MAX_TRANSFER_PLANS,
        "operations": MAX_TRANSFER_OPERATIONS,
        "files": MAX_TRANSFER_FILES,
        "payload_bytes": MAX_TRANSFER_PAYLOAD_BYTES,
    }
    used, added = data.quota_used, data.quota_added
    over = [
        name for name, limit in limits.items() if getattr(used, name) + getattr(added, name) > limit
    ]
    return (
        [QUOTA_TEXT[name] for name in over if name in CERTAIN_QUOTA],
        [QUOTA_TEXT[name] for name in over if name not in CERTAIN_QUOTA],
    )


def _quota_lines(data: DatasetUploadResumeReport) -> list[str]:
    from yorunge.domain.dataset_upload import (
        MAX_TRANSFER_FILES,
        MAX_TRANSFER_OPERATIONS,
        MAX_TRANSFER_PAYLOAD_BYTES,
        MAX_TRANSFER_PLANS,
    )

    used, added = data.quota_used, data.quota_added
    lines = [
        f"Yerel kayıt kotası: kullanılan {used.plans}/{MAX_TRANSFER_PLANS} plan, "
        f"{used.operations}/{MAX_TRANSFER_OPERATIONS} iş, {used.files}/{MAX_TRANSFER_FILES} dosya, "
        f"{used.payload_bytes}/{MAX_TRANSFER_PAYLOAD_BYTES} bayt; bu deneme ekler: "
        f"{added.plans} plan, {added.operations} iş, {added.files} dosya, en çok "
        f"{added.payload_bytes} bayt."
    ]
    certain, possible = _quota_over(data)
    if certain:
        lines.append(
            "Kota dolu: bu deneme yerel kaydın şu sınırını aşar: "
            + ", ".join(certain)
            + ". Kayıtlar otomatik silinmez; plan kaydedilemez (hazırlama "
            "upload_capacity_exceeded verir)."
        )
    elif possible:
        lines.append(
            "Kota sınırda: bu denemenin en çok eklediği bayt kalan payload kotasını aşabilir; "
            "hazırlama planın gerçek boyutunu denetler ve aşarsa upload_capacity_exceeded verir."
        )
    return lines


def _observation_lines(data: DatasetUploadResumeReport) -> list[str]:
    observation = data.observation
    if observation is None:
        if "membership_unobserved" in data.blockers:
            return [
                "Dataset’in dosya listesi okunmadı: kimliği ve proje bağı doğrulanamadığı için "
                "rapor yerel kayda ve bu yoklamaya dayanır."
            ]
        return ["Uzak durum okunmadı: rapor yalnız yerel kayda dayanır."]
    counts = observation.class_counts
    lines = [
        f"Dosya sınıfları: onaylı {counts.confirmed}, uzakta gözlenen {counts.observed}, "
        f"gönderilmemiş {counts.pending_clean}, belirsiz {counts.pending_uncertain}, "
        f"kaybolmuş {counts.drift_missing}, çakışan {counts.conflict}, "
        f"güvenilmez listede {counts.inventory_unreliable}.",
        (
            f"Gönderilecek (yalnız bilgi; engeller sürdüğü için plan kurulamaz): "
            f"{observation.send_files} dosya, {observation.send_bytes} bayt."
            if data.blockers
            else f"Gönderilecek: {observation.send_files} dosya, {observation.send_bytes} bayt."
        ),
    ]
    if observation.unconfirmed_ack_required:
        lines.extend(UNCONFIRMED_WARNING)
        lines.append("Plan ve onay bunun için ayrı bir seçim ister (--accept-unconfirmed-effects).")
    for example in observation.examples:
        lines.append(f"Örnek ({CLASS_TEXT[example.file_class]}): " + ", ".join(example.paths))
    return lines


def _resume_next_lines(data: DatasetUploadResumeReport) -> list[str]:
    lines = []
    identity = data.source_operation_id
    if data.plan_id is not None:
        lines.append(f"İncele: yorunge datasets upload review --plan-id {data.plan_id}")
        lines.append("Onay ve başlatma review çıktısındaki komutlarla sürer (approve, start).")
    elif data.recommended_action == "prepare" and _quota_over(data)[0]:
        lines.append(
            "Şu an hazırlanamaz: yerel kayıt kotası dolu (kayıtlar otomatik silinmez; hazırlama "
            "upload_capacity_exceeded verir)."
        )
    elif data.recommended_action == "prepare":
        lines.append(
            f"Hazırla: yorunge datasets upload resume --operation-id {identity} "
            "--accept-unverified-read --prepare"
        )
        if data.observation is not None and data.observation.unconfirmed_ack_required:
            lines.append(
                "Belirsiz dosyalar için --prepare’a ayrıca --accept-unconfirmed-effects eklemek "
                "gerekir; önce yukarıdaki uyarıyı okuyun."
            )
    elif data.recommended_action == "reconcile":
        lines.append(
            f"Uzlaştır: yorunge datasets upload reconcile --operation-id {identity} "
            "--accept-unverified-read"
        )
    elif data.recommended_action == "wait":
        lines.append("Bekle: lease bitince raporu yeniden alın.")
    else:
        lines.append(
            "Bu rapordan sonra çalıştırılacak bir devam komutu yok; engellerin adımlarına bakın."
        )
    lines.append("Özel --config/--profile/--state-dir kullandıysanız aynı seçenekleri koruyun.")
    return lines


def _resume_text(data: DatasetUploadResumeReport) -> str:
    lines = [
        f"Devam raporu — kaynak iş: {data.source_operation_id}",
        f"Veri seti: {data.dataset_id or 'kaydedilmedi (create sonucu bilinmiyor)'}",
        f"Manifest: {data.file_count} dosya; gözlem zamanı: {data.observed_at}",
    ]
    if data.plan_id is not None:
        lines.append(f"Devam planı kaydedildi: {data.plan_id} (digest: {data.plan_digest})")
    elif data.eligible:
        lines.append(
            "Devam edilebilir"
            + (" (yerel kayıt kotası hariç)" if _quota_over(data)[0] else "")
            + "; plan kaydedilmedi (salt okuma raporu)."
        )
    else:
        lines.append("Devam edilemiyor: engeller kapanmadan plan kaydedilmez.")
    for blocker in explained_blockers(data.blockers):
        reason, step = BLOCKER_TEXT[blocker]
        lines.extend((f"- {blocker}: {reason}", f"  Sonraki adım: {step}"))
    if data.related_operation_id is not None:
        lines.append(f"İlgili iş: {data.related_operation_id}")
    lines.extend(_observation_lines(data))
    lines.extend(_quota_lines(data))
    lines.extend(_resume_next_lines(data))
    lines.append(
        "Yalnız sağlayıcı metadata’sı gözlendi; dosya içeriği ya da baytları doğrulanmadı."
        if data.observation is not None
        else "Dosya içeriği ya da baytları doğrulanmadı."
    )
    return "\n".join(lines)


def _selection_text(data: UploadIntentReview) -> tuple[str, ...]:
    """A continuation sends only some of the manifest's files: which count and how many bytes."""
    limits = data.request_limits
    if data.summary.schema_version != 3 or limits is None:
        return ()
    present = data.manifest.file_count - limits.max_presign
    return (
        f"Bu devamda gönderilecek: {limits.max_presign} dosya, {limits.max_upload_bytes} byte"
        + (" (manifestin geri kalanı Platform’da zaten görülüyor)." if present > 0 else "."),
        *((ORPHAN_NOTE,) if limits.max_presign else ()),
    )


class ProgressText:
    def __init__(self, stream: TextIO) -> None:
        self.stream, self._last = stream, float("-inf")
        try:
            self.enabled = bool(stream.isatty())
        except (OSError, ValueError, AttributeError):
            self.enabled = False

    def __call__(self, progress: UploadProgress) -> None:
        now = time.monotonic()
        if not self.enabled or now - self._last < 0.1:
            return
        self._last = now
        try:
            write_utf8(
                f"İş {progress.operation_id} | Taşımaya verilen: "
                f"{progress.source_bytes}/{progress.total_bytes} byte | "
                f"Onaylı: {progress.confirmed_files}/{progress.total_files} dosya, "
                f"{progress.confirmed_bytes} byte\n",
                self.stream,
            )
        except (OSError, ValueError):
            self.enabled = False
            _silence_failed_descriptor(self.stream)
