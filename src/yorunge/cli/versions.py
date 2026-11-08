"""Lazy ``datasets versions`` parser and rendering; the rules live in the API (ADR-0033)."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yorunge.cli import CliResult, Parser
    from yorunge.domain.dataset_version import (
        DatasetVersionBound,
        DatasetVersionCheck,
        DatasetVersionList,
        DatasetVersionObservation,
        SplitCounts,
    )
    from yorunge.domain.models import Model

SINGLETONS = {
    "--output",
    "--non-interactive",
    "--state-dir",
    "--config",
    "--profile",
    "--dataset-id",
    "--version-tag",
    "--page",
    "--binding-out",
    "--manifest",
    "--binding",
}

MAX_PAGE = 10_000

DESCRIPTIONS = {
    "list": "Veri setinin sürümlerinden bir sayfa göster (salt okuma)",
    "show": "Bir sürümü detay ve bölme sayılarıyla göster (salt okuma)",
    "bind": "Dondurulmuş bir sürümü yeni bir bağ dosyasına değişmez referans yap",
    "check": "Bağ dosyasının sağlayıcıdaki sürümle hâlâ aynı olduğunu denetle (salt okuma)",
}


# What a person is told, in text, of the one error this command family meets in its own way (the
# closed message and the machine envelope stay as they are).
ERROR_HINTS = {
    "state_changed": (
        "Çoğunlukla bağ başka bir profil ya da hizmetle yazılmıştır: bağı yazarken kullandığınız "
        "--config, --profile ve --state-dir seçimini verin."
    ),
}


def _page(value: str) -> int:
    """A page number: decimal ASCII digits, no sign, no space, no leading zero, 1-10 000."""
    if re.fullmatch(r"[1-9]\d{0,4}", value, re.ASCII) is None or int(value) > MAX_PAGE:
        raise argparse.ArgumentTypeError("page")
    return int(value)


def configure(versions: Parser) -> None:
    from yorunge.cli import common

    common(versions, context=False)
    versions.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    actions = versions.add_subparsers(dest="versions_action", required=True)
    for action, description in DESCRIPTIONS.items():
        command = actions.add_parser(action, help=description, description=description)
        common(command, context=False)
        command.add_argument(
            "--config", type=Path, default=argparse.SUPPRESS, help="TOML profil dosyası"
        )
        command.add_argument("--profile", default=argparse.SUPPRESS, help="Profil adı")
        command.add_argument(
            "--state-dir", type=Path, default=argparse.SUPPRESS, help="Yerel durum dizini"
        )
        if action != "check":
            command.add_argument("--dataset-id", required=True, help="Veri seti kimliği (UUID)")
        if action in ("show", "bind"):
            command.add_argument("--version-tag", required=True, help="Sürüm etiketi")
        if action == "list":
            command.add_argument("--page", type=_page, default=1, help="Sayfa (1-10000)")
        if action == "bind":
            command.add_argument(
                "--binding-out",
                type=Path,
                required=True,
                help="Yeni bağ dosyası (var olan ezilmez)",
            )
            command.add_argument(
                "--manifest", type=Path, help="Yerel Manifest v1 dosyası (sayı eşliği için)"
            )
        if action == "check":
            command.add_argument("--binding", type=Path, required=True, help="Bağ dosyası")


def dispatch(args: argparse.Namespace) -> CliResult:
    from yorunge import api
    from yorunge.cli import reject_context

    # No version command has a project: one given at the root is refused, not dropped.
    reject_context(args, ("project",))
    options = vars(args)
    context = {name: options.get(name) for name in ("config", "profile")}
    shared = {**context, "state_dir": options.get("state_dir")}
    action = args.versions_action
    if action == "list":
        return api.list_dataset_versions(args.dataset_id, page=args.page, **shared)
    if action == "show":
        return api.show_dataset_version(args.dataset_id, args.version_tag, **shared)
    if action == "bind":
        return api.bind_dataset_version(
            args.dataset_id,
            args.version_tag,
            binding_out=args.binding_out,
            manifest=args.manifest,
            **shared,
        )
    return api.check_dataset_version(args.binding, **shared)


def _splits(counts: SplitCounts) -> str:
    return (
        f"train {counts.train}, val {counts.val}, test {counts.test}, atanmamış {counts.unassigned}"
    )


def _yes(value: bool, yes: str, no: str) -> str:
    return yes if value else no


def _list_text(data: DatasetVersionList) -> str:
    rows = [f"Veri seti {data.dataset_id}: sayfa {data.page}, toplam {data.total} sürüm."]
    for item in data.items:
        flags = _yes(item.is_partial, "; KISMİ (is_partial)", "") + _yes(
            item.split_total_matches_item_count, "", "; toplam≠öğe"
        )
        rows.append(
            f"- {item.version_tag} ({item.version_id}): "
            f"{_yes(item.is_frozen, 'dondurulmuş', 'DONDURULMAMIŞ')}; "
            f"{item.item_count} öğe ({_splits(item.split_counts)}){flags}; "
            f"oluşturma {item.created_at}"
        )
    if not data.items:
        rows.append("Bu sayfada sürüm yok.")
    if data.has_next and data.page < MAX_PAGE:
        rows.append(f"Sonraki sayfa var (--page {data.page + 1}).")
    elif data.has_next:
        rows.append(
            f"Sonraki sayfa var ama --page en çok {MAX_PAGE} olabilir; bu komut daha ileri gidemez."
        )
    rows.append("Yalnız sağlayıcı metadata'sı ve tek sayfa; sürümlerin tamamlandığı iddia edilmez.")
    return "\n".join(rows)


def _show_text(data: DatasetVersionObservation) -> str:
    rows = [
        f"Sürüm: {data.version_tag} ({data.version_id})",
        f"Veri seti: {data.dataset_id}",
        (
            f"Durum: {_yes(data.is_frozen, 'dondurulmuş', 'DONDURULMAMIŞ')}; "
            f"{_yes(data.is_partial, 'KISMİ (is_partial)', 'is_partial: hayır')}; "
            f"export {_yes(data.is_export_ready, 'hazır', 'hazır değil')}"
        ),
        f"Öğe: {data.item_count} ({_splits(data.split_counts)})",
        (
            f"Etiketli öğe: {data.annotated_item_count}; toplam etiket: "
            f"{data.total_annotation_count}; sınıf: {data.class_count}"
        ),
        f"Oluşturma: {data.created_at}; gözlem: {data.observed_at}",
    ]
    if not data.split_total_matches_item_count:
        rows.append("Uyarı: bölme sayıları toplamı öğe sayısından farklı.")
    rows.append("Yalnız sağlayıcı metadata'sı; sınıf adları yazılmaz, içerik doğrulanmadı.")
    return "\n".join(rows)


def _bound_text(data: DatasetVersionBound) -> str:
    rows = [
        f"Sürüm bağı kaydedildi: {data.binding_path}",
        f"Sürüm: {data.version_tag} ({data.version_id}); veri seti {data.dataset_id}",
        f"Digest: {data.binding_digest}",
    ]
    if data.local_manifest is not None:
        relation = _yes(
            data.local_manifest.relation == "count_matches",
            "dosya sayısı sürümün öğe sayısıyla aynı; üyelik kanıtı değildir",
            "DOSYA SAYISI sürümün öğe sayısından FARKLI",
        )
        rows.append(f"Yerel Manifest: {data.local_manifest.digest} ({relation})")
    if not data.split_total_matches_item_count:
        rows.append("Uyarı: sürümün bölme sayıları toplamı öğe sayısından farklı.")
    if data.is_partial:
        rows.append("Uyarı: sağlayıcı bu sürümü kısmi (is_partial) işaretlemiş; anlamı bilinmiyor.")
    rows.extend(
        (
            "Denetle: "
            + shlex.join(
                ("yorunge", "datasets", "versions", "check", "--binding", data.binding_path)
            ),
            "Özel --config/--profile/--state-dir kullandıysanız aynı seçenekleri koruyun.",
            "Digest kendi kendine hash'tir (imza değil); kullanmadan önce check edin.",
            "Yalnız sağlayıcı metadata'sı; içerik, üyelik ya da model uygunluğu söylenmez.",
        )
    )
    return "\n".join(rows)


def _check_text(data: DatasetVersionCheck) -> str:
    return (
        f"Değişmedi: {data.version_tag} ({data.version_id}) bağdaki ile aynı.\n"
        f"Bağ digest'i: {data.binding_digest}; gözlem: {data.observed_at}\n"
        "Yalnız sağlayıcı metadata'sı karşılaştırıldı; bayt eşliği, üyelik ya da model uygunluğu "
        "söylenmez."
    )


def text(data: Model) -> str:
    from yorunge.domain.dataset_version import (
        DatasetVersionBound,
        DatasetVersionCheck,
        DatasetVersionList,
        DatasetVersionObservation,
    )

    if isinstance(data, DatasetVersionList):
        return _list_text(data)
    if isinstance(data, DatasetVersionObservation):
        return _show_text(data)
    if isinstance(data, DatasetVersionBound):
        return _bound_text(data)
    if isinstance(data, DatasetVersionCheck):
        return _check_text(data)
    raise TypeError("a version result is expected")
