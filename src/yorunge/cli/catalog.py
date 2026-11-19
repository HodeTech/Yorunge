"""``models list|show`` and ``datasets list``: arguments, the call and the text view (P02-4e).

The rules live in ``yorunge.api`` and the catalog adapter. This module reads the arguments,
refuses every combination that cannot mean anything before any request is made, and writes a
plain text view. Provider text is shown through the catalog's own cleaning; identifiers are shown
as the provider sent them, with the same cleaning applied for the terminal only. A command the
text suggests repeats the profile and config the user gave, so it reads the same account.
"""

from __future__ import annotations

import argparse
import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yorunge.cli import CliResult
    from yorunge.domain.catalog import CatalogReading, LlmListing
    from yorunge.domain.errors import YorungeError
    from yorunge.domain.models import Result

PLATFORM = "evren-platform"
LLM = "evren-llm"
SERVICES = (PLATFORM, LLM)
LIST_SUMMARY = "Erişebildiğiniz modellerin bir sayfasını göster (salt okuma)"
SHOW_SUMMARY = "Bir modeli, sürümlerini ya da bir LLM modelini göster (salt okuma)"
DATASETS_SUMMARY = "Veri setlerinin bir sayfasını göster (salt okuma; kapsam K4 ile teyit edilir)"
PROFILE_SINGLETONS = {"--config", "--profile"}
LIST_SINGLETONS = {"--service", "--page", "--page-size", "--task"}
SHOW_SINGLETONS = {"--service", "--model", "--model-id", "--versions", "--task"}
SINGLETONS = (
    PROFILE_SINGLETONS | LIST_SINGLETONS | SHOW_SINGLETONS | {"--output", "--non-interactive"}
)
NO_OWNER = "(sahip adı yok)"
COMPLETENESS = {
    "complete": "tam liste",
    "partial": "kısmi: sonraki sayfa var",
    "last_page": "son sayfa: önceki sayfalar gösterilmedi",
    "unknown": "tamlık kanıtlanamadı",
}


def _count(value: str) -> int:
    """A page number or size as the user wrote it: digits only, and never too large to read."""
    if not value.isascii() or not value.isdigit():
        raise argparse.ArgumentTypeError("count")
    try:
        return int(value)
    except ValueError:  # the integer text limit: far beyond any page the catalog can hold
        raise argparse.ArgumentTypeError("count") from None


def _profile_options(parser: argparse.ArgumentParser) -> None:
    from pathlib import Path

    parser.add_argument("--config", type=Path, default=None, help="TOML profil dosyası")
    parser.add_argument("--profile", default=None, help="Profil adı (yoksa aktif profil)")


def configure_models(actions: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from yorunge.cli import common

    listing = actions.add_parser("list", help=LIST_SUMMARY, description=LIST_SUMMARY)
    common(listing, context=False)
    _profile_options(listing)
    listing.add_argument("--service", required=True, choices=SERVICES, help="Hangi hizmet")
    listing.add_argument("--page", type=_count, default=None, help="Sayfa (Platform; varsayılan 1)")
    listing.add_argument(
        "--page-size", type=_count, default=None, help="Sayfa boyutu (Platform; varsayılan 20)"
    )
    listing.add_argument("--task", default=None, help="LLM görevine göre istemci tarafı süzme")

    showing = actions.add_parser("show", help=SHOW_SUMMARY, description=SHOW_SUMMARY)
    common(showing, context=False)
    _profile_options(showing)
    showing.add_argument("--service", required=True, choices=SERVICES, help="Hangi hizmet")
    showing.add_argument("--model", default=None, help="Platform: OWNER/SLUG")
    showing.add_argument(
        "--model-id", default=None, help="Model kimliği (Platform: yalnız --versions ile; LLM)"
    )
    showing.add_argument(
        "--versions", action="store_true", default=False, help="Platform: sürüm listesini de göster"
    )
    showing.add_argument("--task", default=None, help="LLM: beklenen görev (eşleşmezse hata)")


def configure_datasets(actions: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from yorunge.cli import common

    listing = actions.add_parser("list", help=DATASETS_SUMMARY, description=DATASETS_SUMMARY)
    common(listing, context=False)
    _profile_options(listing)
    listing.add_argument("--page", type=_count, default=None, help="Sayfa (varsayılan 1)")
    listing.add_argument(
        "--page-size", type=_count, default=None, help="Sayfa boyutu (varsayılan 20)"
    )


def options_suffix(args: argparse.Namespace) -> str:
    """The profile and config the user gave, in the form a suggested command repeats them."""
    parts = []
    if getattr(args, "config", None) is not None:
        parts.append(f" --config {shlex.quote(str(args.config))}")
    if getattr(args, "profile", None) is not None:
        parts.append(f" --profile {shlex.quote(args.profile)}")
    return "".join(parts)


def _invalid() -> YorungeError:
    from yorunge.domain.errors import YorungeError

    return YorungeError("invalid_request")


def _split_model(value: str) -> tuple[str, str]:
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise _invalid()
    return parts[0], parts[1]


def dispatch_models(args: argparse.Namespace) -> CliResult:
    from yorunge.cli import reject_context

    reject_context(args, ("state_dir", "project"))  # a catalog read has no state and no project
    if args.action == "list":
        return _list(args)
    return _show(args)


def _list(args: argparse.Namespace) -> CliResult:
    from yorunge import api
    from yorunge.domain.catalog import task_argument

    if args.service == PLATFORM:
        if args.task is not None:
            raise _invalid()
        page = 1 if args.page is None else args.page
        size = 20 if args.page_size is None else args.page_size
        return api.list_platform_models(
            page=page, page_size=size, config=args.config, profile=args.profile
        )
    if args.page is not None or args.page_size is not None:
        raise _invalid()
    # The task is checked before the list is requested: a bad argument never reaches the network.
    task = None if args.task is None else task_argument(args.task)
    result = api.list_llm_models(config=args.config, profile=args.profile)
    if task is None:
        return result
    return _filter_by_task(result, task)


def _filter_by_task(result: Result[CatalogReading[LlmListing]], task: str) -> CliResult:
    """A client-side filter: the same list the key sees, with its completeness unchanged.

    The filter is recorded only when the provider listed something to filter; an empty provider
    list stays an empty list, whatever task was asked for.
    """
    from yorunge.domain.catalog import CatalogReading, LlmListing
    from yorunge.domain.models import Result

    reading = result.data
    provider_models = reading.data.models
    kept = tuple(model for model in provider_models if model.task == task)
    filtered = CatalogReading[LlmListing](
        observed_from=reading.observed_from,
        observed_until=reading.observed_until,
        data=LlmListing(models=kept, task_filter=task if provider_models else None),
    )
    return Result[CatalogReading[LlmListing]](data=filtered, warnings=result.warnings)


def _show(args: argparse.Namespace) -> CliResult:
    from yorunge import api

    if args.service == PLATFORM:
        if args.task is not None:
            raise _invalid()
        if args.model is not None and args.model_id is not None:
            raise _invalid()
        if args.model is not None:
            owner, slug = _split_model(args.model)
            return api.show_platform_model(
                owner, slug, versions=args.versions, config=args.config, profile=args.profile
            )
        # The owner-less route lists the versions of a model by its identifier, and only that.
        if args.model_id is None or not args.versions:
            raise _invalid()
        return api.list_platform_versions(args.model_id, config=args.config, profile=args.profile)
    if args.model is not None or args.versions or args.model_id is None:
        raise _invalid()
    return api.show_llm_model(
        args.model_id, task=args.task, config=args.config, profile=args.profile
    )


def dispatch_datasets(args: argparse.Namespace) -> CliResult:
    from yorunge import api
    from yorunge.cli import reject_context

    reject_context(args, ("state_dir", "project"))
    page = 1 if args.page is None else args.page
    size = 20 if args.page_size is None else args.page_size
    return api.list_platform_datasets(
        page=page, page_size=size, config=args.config, profile=args.profile
    )


# --- text ---------------------------------------------------------------------------------------


def _s(value: object, limit: int | None = None) -> str:
    """Provider text for the terminal: the catalog's cleaning, bounded by the display limit."""
    from yorunge.domain.catalog import NAME_LIMIT, text

    if value is None:
        return "-"
    return text(value if isinstance(value, str) else str(value), limit or NAME_LIMIT) or "-"


def _id(value: object) -> str:
    """An identifier as the provider sent it: cleaned for the terminal, never shortened.

    The codec already bounds identifiers to the raw limit, and refuses edge whitespace, so the
    display limit is the same bound and nothing is trimmed.
    """
    from yorunge.domain.catalog import IDENTITY_LIMIT

    return _s(value, IDENTITY_LIMIT)


def _window(reading: CatalogReading[object]) -> str:
    return f"Gözlem: {reading.observed_from} – {reading.observed_until}"


def catalog_text(reading: CatalogReading[object], options: str = "") -> str:
    """The text view of one reading; ``options`` is what the suggested commands must repeat."""
    from yorunge.domain.catalog import (
        DatasetPage,
        LlmListing,
        LlmModel,
        PlatformModelDetail,
        PlatformModelPage,
        VersionListing,
    )

    data = reading.data
    if isinstance(data, PlatformModelPage):
        lines = _platform_page(data, options)
    elif isinstance(data, PlatformModelDetail):
        lines = _platform_detail(data, options)
    elif isinstance(data, VersionListing):
        lines = _versions(data, None, options)
    elif isinstance(data, LlmListing):
        lines = _llm_listing(data)
    elif isinstance(data, LlmModel):
        lines = _llm_model(data)
    elif isinstance(data, DatasetPage):
        lines = _dataset_page(data, options)
    else:
        raise TypeError("a catalog reading is expected")
    lines.append(_window(reading))
    return "\n".join(lines)


def _number(value: int | None) -> str:
    return "-" if value is None else str(value)


def _platform_page(page: object, options: str) -> list[str]:
    from yorunge.domain.catalog import PlatformModelPage

    assert isinstance(page, PlatformModelPage)
    lines = [
        f"Platform modelleri — sayfa {page.page}, sayfa boyutu {page.page_size}, "
        f"toplam {page.total} kayıt; {COMPLETENESS[page.completeness]}."
    ]
    if not page.models:
        lines.append("Bu anahtara görünen model yok; bu kesin bir yokluk kanıtı değildir.")
    for model in page.models:
        owner = _id(model.owner_username) if model.owner_username is not None else NO_OWNER
        lines.append(
            f"  {owner}/{_id(model.slug)}  {_s(model.name)}  {_s(model.modality)}  "
            f"sürüm {model.versions_count}  kimlik {_id(model.model_id)}"
        )
    if any(model.owner_username is None for model in page.models):
        lines.append(
            "Sahip adı olmayan modeller için kimlikle: yorunge models show --service "
            f"{PLATFORM} --model-id KIMLIK --versions{options}"
        )
    if page.completeness == "partial":
        lines.append(
            f"Sonraki sayfa: yorunge models list --service {PLATFORM} "
            f"--page {page.page + 1} --page-size {page.page_size}{options}"
        )
    return lines


def _platform_detail(detail: object, options: str) -> list[str]:
    from yorunge.domain.catalog import TEXT_LIMIT, PlatformModelDetail

    assert isinstance(detail, PlatformModelDetail)
    model = detail.model
    owner = _id(model.owner_username) if model.owner_username is not None else NO_OWNER
    lines = [
        f"{owner}/{_id(model.slug)} — {_s(model.name)}",
        f"  kimlik: {_id(model.model_id)}",
        f"  görünürlük: {_s(model.visibility)}; aşama: {_s(model.stage)}; "
        f"modalite: {_s(model.modality)}",
        f"  lisans: {_s(model.license) if model.license is not None else 'belirtilmemiş'}",
        f"  sürüm sayısı: {model.versions_count}",
    ]
    if model.description is not None:
        lines.append(f"  açıklama: {_s(model.description, TEXT_LIMIT)}")
    if detail.versions is not None:
        lines.extend(_versions(detail.versions, _id(model.slug), options))
    return lines


def _versions(listing: object, slug: str | None, options: str) -> list[str]:
    from yorunge.domain.catalog import VersionListing

    assert isinstance(listing, VersionListing)
    heading = f"Sürümler ({COMPLETENESS[listing.completeness]}):"
    if slug is None:
        heading = (
            "Sürümler, model kimliğiyle ("
            + COMPLETENESS[listing.completeness]
            + "; sahip adı olmadığı için etiketle çözüm yapılmaz):"
        )
    lines = [f"  {heading}"]
    if not listing.versions:
        lines.append("    (sürüm yok)")
    for version in listing.versions:
        formats = [
            name
            for name, present in (
                ("weights", version.has_weights),
                ("onnx", version.has_onnx),
                ("tflite", version.has_tflite),
            )
            if present
        ]
        lines.append(
            f"    {_id(version.version_tag)}  kimlik {_id(version.version_id)}  "
            f"biçim: {', '.join(formats) or 'bilinmiyor'}  {_s(version.created_at)}"
        )
    lines.append(
        "  İndirme (sürüm kimliğiyle): yorunge models download --version-id KIMLIK "
        f"--format onnx|pt|tflite --weights-out DOSYA{options}"
    )
    return lines


def _llm_listing(listing: object) -> list[str]:
    from yorunge.domain.catalog import LlmListing

    assert isinstance(listing, LlmListing)
    heading = "LLM modelleri (bu anahtara görünenler; listede olmaması kesin yokluk değildir)"
    if listing.task_filter is not None:
        heading += f"; görev süzmesi: {_s(listing.task_filter)} (istemci tarafı)"
    lines = [heading + ":"]
    if not listing.models:
        if listing.task_filter is not None:
            lines.append(
                f"  görev {_s(listing.task_filter)} ile eşleşen model yok; süzme olmadan "
                "listeleyerek diğer görevlere bakın."
            )
        else:
            lines.append("  (görünen model yok)")
    for model in listing.models:
        modalities = ", ".join(_s(item) for item in model.modalities or ()) or "-"
        context = "-" if model.context_length is None else str(model.context_length)
        lines.append(
            f"  {_id(model.model_id)}  görev {_s(model.task)}  bağlam {context}  "
            f"modalite {modalities}"
        )
    return lines


def _llm_model(model: object) -> list[str]:
    from yorunge.domain.catalog import LlmModel

    assert isinstance(model, LlmModel)
    lines = [
        f"{_id(model.model_id)} — görev {_s(model.task)}",
        f"  modaliteler: {', '.join(_s(item) for item in model.modalities or ()) or '-'}",
        f"  bağlam: {_number(model.context_length)}; "
        f"en çok çıktı: {_number(model.default_max_output_tokens)}",
        f"  hassasiyet: {_s(model.precision) if model.precision is not None else '-'}",
    ]
    if model.pricing is None:
        lines.append("  fiyat: bilinmiyor")
    else:
        price = model.pricing
        lines.append(
            f"  fiyat: girdi {price.prompt_token_price} / çıktı {price.completion_token_price} "
            f"{_s(price.currency) if price.currency is not None else ''}; ücretsiz tarih: "
            f"{_s(price.free_until) if price.free_until is not None else 'yok'} "
            "(bilgi; maliyet kapısı değildir)"
        )
    return lines


def _dataset_page(page: object, options: str) -> list[str]:
    from yorunge.domain.catalog import DatasetPage

    assert isinstance(page, DatasetPage)
    lines = [
        f"Veri setleri — sayfa {page.page}, sayfa boyutu {page.page_size}; "
        f"{COMPLETENESS[page.completeness]}; kapsam: teyit edilmedi."
    ]
    if not page.datasets:
        lines.append("  (bu sayfada veri seti yok)")
    for dataset in page.datasets:
        owner = _id(dataset.owner_username) if dataset.owner_username is not None else NO_OWNER
        lines.append(
            f"  {owner}/{_id(dataset.slug)}  {_s(dataset.name)}  {_s(dataset.modality)}  "
            f"öğe {dataset.item_count}  {_s(dataset.visibility)}  kimlik {_id(dataset.dataset_id)}"
        )
    if page.completeness == "partial":
        lines.append(
            f"Sonraki sayfa: yorunge datasets list --page {page.page + 1} "
            f"--page-size {page.page_size}{options}"
        )
    return lines
