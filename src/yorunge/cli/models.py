"""Lazy ``models download`` parser and rendering; the rules live in the API (ADR-0032 §1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from yorunge.cli.output import _silence_failed_descriptor, write_utf8

if TYPE_CHECKING:
    from yorunge.cli import CliResult, Parser
    from yorunge.domain.download import DownloadSummary
    from yorunge.domain.models import Model

SINGLETONS = {
    "--output",
    "--non-interactive",
    "--state-dir",
    "--config",
    "--profile",
    "--version-id",
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
        required=True,
        help=(
            "Kesin model sürümü kimliği (UUID). Platform arayüzündeki model sürümü sayfasından "
            "alın; ad ya da slug çözülmez ve ilk sürüm seçilmez."
        ),
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
        help="Yeni ağırlık dosyası (var olan ezilmez; parent'ı mevcut olmalı)",
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
        "yerden devam eder. Hedef var olan bir dosyaysa ezilmez. Anahtar argüman değildir; "
        "kayıtlı Platform hizmetinin anahtarı yalnız sürüm adresini almak için kullanılır, "
        "dosya imzalı adresten anahtarsız indirilir."
    )


def dispatch(args: argparse.Namespace) -> CliResult:
    from yorunge import api

    options = vars(args)
    progress = ProgressText(sys.stderr) if options.get("output", "text") == "text" else None
    try:
        return api.download_model_weights(
            args.version_id,
            artifact_format=args.artifact_format,
            weights_out=args.weights_out,
            fold=args.fold,
            sha256=args.sha256,
            timeout=args.timeout,
            no_resume=args.no_resume,
            config=options.get("config"),
            profile=options.get("profile"),
            state_dir=options.get("state_dir"),
            progress=progress if progress is not None and progress.enabled else None,
        )
    finally:
        if progress is not None:
            progress.close()


def _summary_text(data: DownloadSummary) -> str:
    source = data.source
    kind = f"biçim {source.format}" + ("" if source.fold is None else f", fold {source.fold}")
    rows = [
        f"Model ağırlığı indirildi: {data.output_path}",
        f"Sürüm: {source.version_id}; {kind}",
        f"Boyut: {data.bytes} bayt; SHA-256: {data.sha256}",
    ]
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
    else:
        rows.append("Aktarım: önceki yarım indirme tamdı; ağ isteği yapılmadan yayımlandı.")
    rows.append(
        "Seviye yalnız indirilen baytların beklentinizle ilişkisini söyler; sağlayıcıdaki "
        "nesnenin özgünlüğünü, lisansını ya da model uygunluğunu söylemez."
    )
    return "\n".join(rows)


def text(data: Model) -> str:
    from yorunge.domain.download import DownloadSummary

    if isinstance(data, DownloadSummary):
        return _summary_text(data)
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
        self._write(f"\rİndiriliyor: {amount}")
        self._open = True

    def close(self) -> None:
        """End the line, so that whatever follows (the result, an error) starts on a new one."""
        if self._open:
            self._open = False
            self._write("\n")

    def _write(self, line: str) -> None:
        try:
            write_utf8(line, self.stream)
        except (OSError, ValueError):
            self.enabled = False
            _silence_failed_descriptor(self.stream)
