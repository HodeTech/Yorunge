"""Lazy upload parser and user-facing rendering; all business rules live in the API."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

from yorunge.cli.output import write_utf8

if TYPE_CHECKING:
    from yorunge.application.upload_progress import UploadProgress
    from yorunge.cli import Parser
    from yorunge.domain.models import Model, Result
    from yorunge.domain.upload_public import (
        DatasetUploadsPage,
        DatasetUploadSummary,
        UploadIntentReview,
    )

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
    "--accept-unverified-read",
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
        "start": "İlk aktarımı bir kez başlat; mevcut işi tekrar göndermez",
        "list": "Yerel plan ve iş özetlerini göster",
        "show": "Plan veya operation ID ile kayıtlı özeti göster",
        "reconcile": "Aynı işi yalnız uzak okumayla uzlaştır",
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
    else:
        command.add_argument("--plan-id", required=True)
        if action == "approve":
            command.add_argument(
                "--confirm", required=True, help="İncelenen planın tam SHA-256 digest’i"
            )
            command.add_argument("--accept-unverified-authority", action="store_true")
            command.add_argument("--accept-unpriced-cost", action="store_true")


def _plan_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("root", type=Path)
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--name", required=True)
    command.add_argument("--project", required=True)
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
        "--admission-policy", choices=("verified-only", "explicit-attempt"), default="verified-only"
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
) -> Result[DatasetUploadSummary] | Result[UploadIntentReview] | Result[DatasetUploadsPage]:
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
        return api.show_dataset_upload(
            plan_id=args.plan_id, operation_id=args.operation_id, state_dir=state
        )
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
            **context,
        )
    if action == "reconcile":
        return api.reconcile_dataset_upload(
            args.operation_id, accept_unverified_read=args.accept_unverified_read, **context
        )
    from yorunge.application.upload_progress import observe_upload

    progress = ProgressText(sys.stderr) if options.get("output", "text") == "text" else None
    with observe_upload(progress if progress is not None and progress.enabled else None):
        return api.start_dataset_upload(args.plan_id, **context)


def operation_id(data: Model) -> str | None:
    from yorunge.domain.upload_public import DatasetUploadSummary, UploadIntentReview

    if isinstance(data, DatasetUploadSummary):
        return data.operation_id
    return data.summary.operation_id if isinstance(data, UploadIntentReview) else None


def text(data: Model) -> str:
    from yorunge.domain.upload_public import (
        DatasetUploadsPage,
        DatasetUploadSummary,
        UploadIntentReview,
    )

    if isinstance(data, UploadIntentReview):
        return _review_text(data)
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
    if not isinstance(data, DatasetUploadSummary):
        raise TypeError("upload result type required")
    return "\n".join(_summary_text(data))


def _summary_text(data: DatasetUploadSummary) -> list[str]:
    lines = [
        f"Plan: {data.plan_id}",
        f"Digest: {data.plan_digest}",
        f"Plan durumu: {PLAN_STATES[data.plan_status]}",
    ]
    if data.legacy_history_only:
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
        lines.append("Dosya metadata eşliği doğrulandı; uzak byte’lar indirilip hash’lenmedi.")
    if not data.authority_verified:
        lines.append("Yazma yetkisi doğrulanmış sayılmaz.")
    else:
        lines.append("Başlangıç yazma yetkisi kanıtı tarihsel olarak doğrulandı.")
    lines.extend(_cost_text(data))
    if data.risks:
        lines.append("Riskler: " + "; ".join(RISKS[risk] for risk in data.risks))
    if data.blockers:
        lines.append("Engeller: " + "; ".join(BLOCKERS[blocker] for blocker in data.blockers))
    lines.extend(_next_text(data))
    return lines


def _next_text(data: DatasetUploadSummary) -> list[str]:
    if data.operation_id is not None:
        if data.operation_status == "unknown":
            return [
                f"İncele: yorunge datasets upload show --operation-id {data.operation_id}",
                "Eksik aşamaları yeniden göndermeyin; uygun kaydı salt okumayla uzlaştırın.",
            ]
        return []
    lines = [f"İncele: yorunge datasets upload review --plan-id {data.plan_id}"]
    if data.legacy_history_only or data.blockers:
        return lines
    if data.approval_status is None:
        command = (
            f"Onay: yorunge datasets upload approve --plan-id {data.plan_id} "
            f"--confirm {data.plan_digest}"
        )
        if "authority_unverified" in data.risks:
            command += " --accept-unverified-authority"
        if data.cost_policy == "unpriced_accepted":
            command += " --accept-unpriced-cost"
        lines.append(command)
    elif data.approval_status == "approved":
        lines.append(f"Başlat: yorunge datasets upload start --plan-id {data.plan_id}")
    lines.append("Özel --config/--state-dir kullandıysanız aynı seçenekleri koruyun.")
    return lines


def _credits(micros: int) -> str:
    whole, fraction = divmod(micros, 1_000_000)
    return f"{whole}.{fraction:06d}"


def _cost_text(data: DatasetUploadSummary) -> list[str]:
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
    lines.extend(
        (
            f"İlk başlatma maliyet üst sınırı: {_credits(bound.maximum_micros)} CR",
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
            f"Manifest: {data.manifest.digest}",
            f"Yükleme hedefi: {data.storage.origin or 'Platform API'}",
            f"Plan bitişi: {data.expires_at}",
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
        except (OSError, UnicodeError, ValueError):
            self.enabled = False
