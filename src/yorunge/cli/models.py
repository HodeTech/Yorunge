"""Lazy ``models download`` parser and rendering; the rules live in the API (ADR-0032 §1)."""

from __future__ import annotations

import argparse
import select
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from yorunge.cli.output import _silence_failed_descriptor, write_utf8

if TYPE_CHECKING:
    from yorunge.cli import CliResult, Parser
    from yorunge.domain.download import DownloadSummary
    from yorunge.domain.errors import YorungeError
    from yorunge.domain.models import Model

SINGLETONS = {
    "--output",
    "--non-interactive",
    "--state-dir",
    "--config",
    "--profile",
    "--version-id",
    "--model",
    "--version-tag",
    "--format",
    "--fold",
    "--sha256",
    "--timeout",
    "--weights-out",
    "--no-resume",
}

SUMMARY = (
    "Bir model sürümünün ağırlığını yeni bir dosyaya indir (ezmez, doğrulama seviyesi görünür)"
)


def _fold(value: str) -> int:
    from yorunge.domain.download import parse_fold
    from yorunge.domain.errors import YorungeError

    try:
        return parse_fold(value)
    except YorungeError:
        raise argparse.ArgumentTypeError("fold") from None


def _timeout(value: str) -> int:
    from yorunge.domain.download import parse_timeout
    from yorunge.domain.errors import YorungeError

    try:
        return parse_timeout(value)
    except YorungeError:
        raise argparse.ArgumentTypeError("timeout") from None


def _sha256(value: str) -> str:
    from yorunge.domain.download import parse_sha256
    from yorunge.domain.errors import YorungeError

    try:
        return parse_sha256(value)
    except YorungeError:
        raise argparse.ArgumentTypeError("sha256") from None


def configure(models: Parser) -> None:
    from yorunge.cli import common
    from yorunge.domain.download import (
        DEFAULT_TIMEOUT_SECONDS,
        MAX_FOLD,
        MAX_TIMEOUT_SECONDS,
        MIN_TIMEOUT_SECONDS,
    )

    common(models, context=False)
    models.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    actions = models.add_subparsers(dest="action", required=True)
    command = actions.add_parser("download", help=SUMMARY, description=SUMMARY)
    common(command, context=False)
    command.add_argument(
        "--config", type=Path, default=argparse.SUPPRESS, help="TOML profil dosyası"
    )
    command.add_argument("--profile", default=argparse.SUPPRESS, help="Profil adı")
    command.add_argument(
        "--state-dir", type=Path, default=argparse.SUPPRESS, help="Yerel durum dizini"
    )
    command.add_argument(
        "--version-id",
        default=None,
        help=(
            "Kesin model sürümü kimliği (UUID). Platform arayüzündeki model sürümü sayfasından "
            "alın; ad ya da slug çözülmez ve ilk sürüm seçilmez. --model ile birlikte verilemez."
        ),
    )
    command.add_argument(
        "--model",
        metavar="OWNER/SLUG",
        default=None,
        help=(
            "Model OWNER/SLUG; --version-tag ile birlikte verilir. Sürüm katalogdan çözülür: "
            "etiketi tam eşleşen tek sürüm kullanılır, en son ya da varsayılan sürüm seçilmez. "
            "Sahip adı olmayan modeller için --version-id kullanın."
        ),
    )
    command.add_argument(
        "--version-tag",
        metavar="TAG",
        default=None,
        help="Sürüm etiketi (tam eşleşme); --model ile birlikte verilir",
    )
    command.add_argument(
        "--format",
        dest="artifact_format",
        required=True,
        choices=("onnx", "pt", "tflite"),
        help="Ağırlık biçimi (zorunlu; sağlayıcının varsayılanı tahmin edilmez)",
    )
    command.add_argument(
        "--weights-out",
        type=Path,
        required=True,
        help=(
            "Yeni ağırlık dosyası (var olan ezilmez). Parent'ı mevcut olmalı ve üst dizin zinciri "
            "symlink içermemeli (macOS'ta /tmp ve /var/folders symlink'tir: /private/... verin)"
        ),
    )
    command.add_argument(
        "--fold",
        type=_fold,
        help=f"k-fold sürümleri için fold (0-{MAX_FOLD}); verilirse sağlayıcıya iletilir",
    )
    command.add_argument(
        "--sha256",
        type=_sha256,
        help=(
            "Bağımsız olarak bildiğiniz beklenen SHA-256 (64 küçük harf hex). Verilirse eşleşme "
            "sha256_matched seviyesini kazandırır, uyuşmazlık hedef oluşturmadan exit 7 verir; "
            "verilmezse sonuç yalnız transfer_complete'tir"
        ),
    )
    command.add_argument(
        "--timeout",
        type=_timeout,
        help=(
            f"İndirme süresi, tam saniye ({MIN_TIMEOUT_SECONDS}-{MAX_TIMEOUT_SECONDS}, "
            f"varsayılan {DEFAULT_TIMEOUT_SECONDS}). 1 GiB'lık bir dosyanın "
            f"{DEFAULT_TIMEOUT_SECONDS} sn'de inmesi yaklaşık 9,5 Mbit/s payload gerektirir"
        ),
    )
    command.add_argument(
        "--no-resume",
        action="store_true",
        help=(
            "Aynı indirmenin yarım kalmış dosyasını (bu aracın bıraktığı kanıtlanabiliyorsa) silip "
            "baştan indir; kanıtlanamayan hiçbir dosyaya dokunulmaz"
        ),
    )
    command.epilog = (
        "Yarım kalan bir indirme (güçlü ETag ve toplam boyut biliniyorsa) aynı komutla kaldığı "
        "yerden devam eder. Hedef var olan bir dosyaysa ezilmez. En çok 1 GiB iner; aşılırsa "
        "hedef oluşturulmaz. Önkoşullar: 'yorunge state init' ile hazırlanmış durum dizini, bir "
        "Platform profili ve anahtarın env değişkeni (varsayılan profilde "
        "EVREN_PLATFORM_API_KEY). Anahtar argüman değildir; kayıtlı Platform hizmetinin anahtarı "
        "sürüm adresini almak için kullanılır (etiketle seçimde ayrıca sürüm kataloğunu okumak "
        "için); dosya imzalı adresten anahtarsız indirilir. Etiketle seçimde (--model, "
        "--version-tag) sürüm katalogdan tek tam eşleşmeyle çözülür; bu yolda tam bir stage bile "
        "katalog okunmadan yayımlanmaz."
    )
    from yorunge.cli.catalog import configure_models as configure_catalog

    configure_catalog(actions)


def dispatch(args: argparse.Namespace) -> CliResult:
    from yorunge import api
    from yorunge.cli import reject_context

    if args.action in ("list", "show"):
        from yorunge.cli.catalog import dispatch_models

        return dispatch_models(args)
    from yorunge.domain.errors import YorungeError

    reject_context(args, ("project",))  # a weights download has no project; none is dropped quietly
    if selection_refused(args):
        # One way to name the version, given whole: an id, or an owner/slug with its tag. Refused
        # before any file, state or request.
        raise YorungeError("invalid_request")
    options = vars(args)
    progress = ProgressText(sys.stderr) if options.get("output", "text") == "text" else None
    shared = {
        "artifact_format": args.artifact_format,
        "weights_out": args.weights_out,
        "fold": args.fold,
        "sha256": args.sha256,
        "timeout": args.timeout,
        "no_resume": args.no_resume,
        "config": options.get("config"),
        "profile": options.get("profile"),
        "state_dir": options.get("state_dir"),
        "progress": progress if progress is not None and progress.enabled else None,
    }
    by_id = args.version_id is not None
    try:
        if by_id:
            return api.download_model_weights(args.version_id, **shared)
        return api.download_model_weights_by_tag(args.model, args.version_tag, **shared)
    finally:
        if progress is not None:
            progress.close()


TARGET_HINT = (
    "Hedefin parent'ı var olmalı ve üst dizin zinciri symlink içermemeli: macOS'ta /tmp ve "
    "/var/folders symlink'tir, gerçek yolu (/private/...) verin."
)
TIMEOUT_HINT = (
    "Bir kısmı inmişse ve sağlayıcı ETag ile toplam boyutu bildirdiyse yarım dosya saklanır; "
    "komutu yeniden çalıştırmak kaldığı yerden devam eder. Toplam süre dolduysa --timeout ile "
    "artırabilirsiniz; bağlantı ya da yanıt akışı birkaç saniye durduysa (5 sn) süreyi artırmak "
    "yardımcı olmaz, ağı kontrol edin."
)
NO_RESUME_HINT = (
    "--no-resume zaten verildi: iz bu aracın kanıtlanabilir yarım dosyası olmadığından "
    "dokunulmadı. İzi inceleyip elle kaldırın ya da başka bir hedef seçin."
)


def _mismatch_hint(error: YorungeError) -> str | None:
    """The digest that was computed (the stage is gone, so seeing it again costs a download)."""
    details = getattr(error, "details", None)
    if not isinstance(details, dict):
        return None
    computed, size = details.get("computed_sha256"), details.get("bytes")
    if type(computed) is not str or type(size) is not int:
        return None
    return (
        f"Hesaplanan SHA-256: {computed} ({size} bayt). Beklediğiniz değerle karşılaştırın; "
        "yarım dosya atıldı, yeniden denemek baştan indirir."
    )


# Each suggested command ends in ``{options}``: the profile and config the person gave, so that the
# command reads the same account as the one that failed.
SELECTION_HINT = (
    "Sürümü ya --version-id ile ya da --model OWNER/SLUG ve --version-tag birlikte verin; ikisi "
    "birden ya da yalnız biri verilemez."
)


def selection_refused(args: argparse.Namespace) -> bool:
    """Whether a download names its version in neither way, in both, or half of the tag way."""
    if getattr(args, "action", None) != "download":
        return False  # catalog reads name their models in their own ways
    by_id = getattr(args, "version_id", None) is not None
    model = getattr(args, "model", None)
    tag = getattr(args, "version_tag", None)
    by_tag = model is not None or tag is not None
    return by_id == by_tag or (by_tag and (model is None or tag is None))


STATE_HINT = (
    "Yerel durum hazır değilse 'yorunge state init' ile hazırlayın; hazırsa sahiplik ve bütünlük "
    "denetimini çalıştırın."
)
LIST_ARGUMENTS_HINT = (
    "Sayfa 1 ve üzeri bir tam sayıdır; sayfa boyutu 1 ile 100 arasında bir tam sayıdır. Görev adı "
    "1 ile 64 karakter arasında olmalı ve kenarında boşluk bulunmamalıdır."
)
CATALOG_HINTS: dict[str, str] = {
    "model_ambiguous": (
        "Aynı etiketli birden fazla sürüm var; seçim yapılmadı. Kimlikleri görmek için 'yorunge "
        "models show --service evren-platform --model OWNER/SLUG --versions{options}' çalıştırın, "
        "sonra 'yorunge models download --version-id KIMLIK --format FORMAT --weights-out "
        "DOSYA{options}' ile devam edin (FORMAT: onnx, pt veya tflite)."
    ),
    "model_task_mismatch": (
        "Model beklenen görevle eşleşmiyor. 'yorunge models show --service evren-llm --model-id "
        "KIMLIK{options}' ile görevi kontrol edin."
    ),
    "model_not_addressable": (
        "Modelin sahip adı yok; owner/slug ile adreslenemez. 'yorunge models show --service "
        "evren-platform --model-id KIMLIK --versions{options}' kullanın."
    ),
}


def error_hints(args: argparse.Namespace) -> dict[str, str | Callable[[YorungeError], str | None]]:
    """What a person is told, in text, of the errors this command meets in its own way."""
    from yorunge.cli.catalog import options_suffix

    hints: dict[str, str | Callable[[YorungeError], str | None]] = {
        "transport_timeout": TIMEOUT_HINT,
        "download_integrity_mismatch": _mismatch_hint,
        "download_target_invalid": TARGET_HINT,
    }
    if vars(args).get("no_resume") is True:
        hints["download_partial_unverified"] = NO_RESUME_HINT
    if selection_refused(args):
        hints["invalid_request"] = SELECTION_HINT
    suffix = options_suffix(args)
    hints.update({code: text.format(options=suffix) for code, text in CATALOG_HINTS.items()})
    hints["model_ambiguous"] = _ambiguity_hint(
        CATALOG_HINTS["model_ambiguous"].format(options=suffix)
    )
    hints["model_not_visible"] = _not_visible_hint(args, suffix)
    hints["state_invalid"] = STATE_HINT
    if getattr(args, "action", None) == "list":
        hints["invalid_request"] = LIST_ARGUMENTS_HINT
    return hints


def _not_visible_hint(args: argparse.Namespace, options: str) -> str:
    """The next step for a model or version the key cannot see, named for the command at hand."""
    if getattr(args, "action", None) == "download":
        return (
            "Model veya sürüm bu anahtara görünmüyor; bu kesin bir yokluk kanıtı değildir. "
            "Etiketin yazımını 'yorunge models show --service evren-platform --model OWNER/SLUG "
            f"--versions{options}' ile kontrol edin; profili ve anahtarı da kontrol edin."
        )
    service = getattr(args, "service", None) or "evren-platform"
    return (
        "Model veya sürüm bu anahtara görünmüyor; bu kesin bir yokluk kanıtı değildir. Profili ve "
        f"anahtarı kontrol edin ya da 'yorunge models list --service {service}{options}' ile "
        "arayın."
    )


def _ambiguity_hint(base: str) -> Callable[[YorungeError], str | None]:
    """The ambiguity hint, with the candidates the error carries (identity, tag, date), if any."""

    def hint(error: YorungeError) -> str | None:
        found = getattr(error, "candidates", ())
        if not found:
            return base
        rows = [
            f"  kimlik {identity}  etiket {tag}  tarih {created}"
            for identity, tag, created in found
        ]
        return "\n".join([base, "Adaylar (seçim yapılmadı):", *rows])

    return hint


def _summary_text(data: DownloadSummary, warnings: tuple[str, ...] = ()) -> str:
    from yorunge.adapters.download_engine import REPLACED_PARTIAL_WARNING

    source = data.source
    kind = f"biçim {source.format}" + ("" if source.fold is None else f", fold {source.fold}")
    rows = [
        f"Model ağırlığı indirildi: {data.output_path}",
        f"Sürüm: {source.version_id}; {kind}",
        f"Boyut: {data.bytes} bayt; SHA-256: {data.sha256}",
    ]
    if data.resolution is not None:
        resolved = data.resolution
        rows.insert(
            1,
            f"Çözülen model: {resolved.owner}/{resolved.slug} (model kimliği "
            f"{resolved.model_id}); sürüm etiketi {resolved.version_tag}. Etiketin gösterdiği "
            "sürüm kimliği katalog yanıtında gözlemlendi; sağlayıcı bunun değişmezliğini garanti "
            "etmez.",
        )
    if REPLACED_PARTIAL_WARNING in warnings:
        rows.append(
            "Önceki yarım dosya başka bir indirmeye (farklı sürüm, biçim, fold ya da hizmet "
            "hedefi) aitti; "
            "atıldı ve bu indirme baştan başladı."
        )
    if data.verification_level == "sha256_matched":
        rows.append("Doğrulama: SHA-256, verdiğiniz beklenen özetle eşleşti (sha256_matched).")
    else:
        rows.append(
            "Doğrulama: yalnız aktarım tamamlandı (transfer_complete); beklenen bir özet "
            "verilmedi, içerik doğrulanmadı. Bağımsız bir özetiniz varsa --sha256 ile verin."
        )
    if not data.resumed:
        rows.append("Aktarım: baştan indirildi.")
    elif data.resumed_from_bytes < data.bytes:
        rows.append(
            f"Aktarım: yarım kalan indirmeden {data.resumed_from_bytes} bayttan devam edildi."
        )
    elif data.resolution is not None:
        rows.append(
            "Aktarım: önceki yarım indirme tamdı; ağırlık isteği yapılmadan yayımlandı "
            "(sürüm katalogdan okundu)."
        )
    else:
        rows.append("Aktarım: önceki yarım indirme tamdı; ağ isteği yapılmadan yayımlandı.")
    rows.append(
        "Seviye yalnız indirilen baytların beklentinizle ilişkisini söyler; sağlayıcıdaki "
        "nesnenin özgünlüğünü, lisansını ya da model uygunluğunu söylemez."
    )
    return "\n".join(rows)


def text(data: Model, warnings: tuple[str, ...] = ()) -> str:
    from yorunge.domain.catalog import CatalogReading
    from yorunge.domain.download import DownloadSummary

    if isinstance(data, CatalogReading):
        from yorunge.cli.catalog import catalog_text

        return catalog_text(data)
    if isinstance(data, DownloadSummary):
        return _summary_text(data, warnings)
    raise TypeError("a download result is expected")


class ProgressText:
    """Progress on a terminal's stderr as one rewritten line; silent anywhere else."""

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream
        self._open = False
        try:
            self.enabled = bool(stream.isatty())
        except (OSError, ValueError, AttributeError):
            self.enabled = False

    def __call__(self, held: int, total: int | None) -> None:
        if not self.enabled:
            return
        amount = f"{held} / {total} bayt (%{held * 100 // total})" if total else f"{held} bayt"
        if self._write(f"\rİndiriliyor: {amount}"):
            self._open = True  # only a line that was written has to be ended

    def close(self) -> None:
        """End the line, so that whatever follows (the result, an error) starts on a new one.

        A terminal that is stopped at this very moment takes no newline (it is never waited for):
        what follows then glues onto the last report; the result is still complete and correct.
        """
        if self._open:
            self._open = False
            self._write("\n")

    def _writable(self) -> bool:
        """The terminal takes a report now: a stopped one (^S, a stalled ssh) must never be waited
        for, since the download's own deadlines cannot fire while this thread sits in ``write``."""
        try:
            descriptor = self.stream.fileno()
        except (OSError, ValueError, AttributeError):
            return True  # nothing to ask (a stream without a descriptor): the write decides
        try:
            return bool(select.select([], [descriptor], [], 0)[1])
        except (OSError, ValueError):
            return False

    def _write(self, line: str) -> bool:
        """True when the line went out; a report the terminal cannot take now is dropped."""
        if not self._writable():
            return False  # this report is dropped; the next one is tried
        try:
            write_utf8(line, self.stream)
        except (OSError, ValueError) as error:
            self.enabled = False
            # A terminal that is only full for now (non-blocking, EAGAIN) is still the terminal the
            # real error will be written to; only a terminal that is gone is cut off.
            if not isinstance(error, BlockingIOError):
                _silence_failed_descriptor(self.stream)
            return False
        return True
