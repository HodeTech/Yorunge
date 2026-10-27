"""Lightweight parser; application and schema imports happen after metadata commands."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from yorunge import __version__

if TYPE_CHECKING:
    from yorunge.domain.models import CapabilityView, Context, Model, Plan, Result


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse's message may contain arbitrary user input, including a credential.
        raise UsageError


def common(parser: argparse.ArgumentParser, *, context: bool = True) -> None:
    parser.allow_abbrev = False
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default=argparse.SUPPRESS,
        help="Sonuç biçimi (varsayılan: text)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Etkileşimsiz çalış (bu sürüm zaten soru sormaz)",
    )
    if context:
        parser.add_argument(
            "--config", type=Path, default=argparse.SUPPRESS, help="TOML profil dosyası"
        )
        parser.add_argument("--profile", default=argparse.SUPPRESS, help="Profil adı")
        parser.add_argument("--project", default=argparse.SUPPRESS, help="Açık proje kimliği")


def planning_options(parser: argparse.ArgumentParser, *, task: bool = True) -> None:
    common(parser)
    parser.add_argument("--recipe", type=Path, help="Sınırlı v1 YAML reçetesi")
    if task:
        parser.add_argument("--task", help="Görev kimliği; reçetedeki seçimi geçersiz kılar")
    parser.add_argument("--tool", help="Açık araç kimliği; sessiz fallback yapılmaz")
    parser.add_argument("--execution", help="local, evren-managed veya evren-workspace")


def parser() -> Parser:
    root = Parser(prog="yorunge", description="Yörünge — çevrimdışı bağlam ve plan hazırlığı")
    root.add_argument("--version", action="version", version=f"yorunge {__version__}")
    common(root)
    commands = root.add_subparsers(dest="command", required=True)
    context = commands.add_parser("context", help="Yerel profil bağlamı")
    common(context)
    context_actions = context.add_subparsers(dest="action", required=True)
    show = context_actions.add_parser("show")
    common(show)
    credential = context_actions.add_parser(
        "credential", help="Seçilen hizmetin env sırrını kontrol et"
    )
    common(credential)
    credential.add_argument("--service", required=True, choices=("evren-platform", "evren-llm"))
    identity = context_actions.add_parser("identity", help="Seçilen sır gözleminin yerel kimliği")
    common(identity)
    identity.add_argument("--service", required=True, choices=("evren-platform", "evren-llm"))
    identity.add_argument("--state-dir", type=Path)
    state = commands.add_parser("state", help="Yerel kimlik durumunu yönet")
    common(state, context=False)
    state.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    state_init = state.add_subparsers(dest="action", required=True).add_parser("init")
    common(state_init, context=False)
    state_init.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    capabilities = commands.add_parser("capabilities", help="Sınırlı çevrimdışı yetenek görünümü")
    planning_options(capabilities)
    plan = commands.add_parser("plan", help="Çevrimdışı plan; yürütme başlatmaz")
    common(plan)
    actions = plan.add_subparsers(dest="action", required=True)
    planning_options(actions.add_parser("prepare", help="Sabit seçimleri ve engelleri hazırla"))
    saved = actions.add_parser("show", help="Kaydedilmiş planı doğrula ve göster")
    common(saved, context=False)
    saved.add_argument("--plan", required=True, type=Path, help="Plan nesnesi içeren JSON dosyası")
    train = commands.add_parser("train", help="LLM eğitim planı (eğitim çalıştırmaz)")
    common(train)
    train_plan = train.add_subparsers(dest="action", required=True).add_parser("plan")
    planning_options(train_plan, task=False)
    return root


def text_result(data: Model) -> str:
    from yorunge.domain.credentials import CredentialCheck, CredentialObservation
    from yorunge.domain.models import CapabilityView, Context, Plan
    from yorunge.domain.state import StateInfo

    if isinstance(data, StateInfo):
        return f"Yerel durum hazır.\nKimlik alanı: {data.identity_epoch}"

    if isinstance(data, CredentialObservation):
        return (
            f"Hizmet: {data.service_id}\nKimlik: {data.identity.credential_id}\n"
            f"Nesil: {data.identity.credential_revision}\nUzak erişim doğrulanmadı."
        )
    if isinstance(data, CredentialCheck):
        return (
            f"Hizmet: {data.service_id}\nProfil: {data.profile}\n"
            "Sır mevcut; uzak erişim doğrulanmadı."
        )
    if isinstance(data, Context):
        return (
            f"Profil: {data.profile}\nProje: {data.project_id or 'seçilmedi'}\n"
            "Uzak erişim doğrulanmadı."
        )
    if isinstance(data, CapabilityView):
        rows = [f"Görev: {data.selection.task}; araç: {data.selection.tool or 'native'}"]
        rows.extend(f"{r.support}: {r.message}" for r in data.records)
        return "\n".join(rows)
    if isinstance(data, Plan):
        return (
            f"Çevrimdışı taslak: {data.selection.task}\n"
            f"Araç: {data.selection.tool or 'native'} ({data.selection.tool_source})\n"
            f"Ortam: {data.selection.execution}\nDigest: {data.digest}\n"
            f"Engeller: {', '.join(data.blockers)}\n"
            "Plan hazırlandı; yürütülemez. Eğitim veya uzak işlem başlatılmadı."
        )
    raise TypeError("unsupported result type")


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    # Error format is known even when parsing fails before reaching --output.
    json_output = any(
        arg == "--output=json" or (arg == "--output" and args_list[i + 1 : i + 2] == ["json"])
        for i, arg in enumerate(args_list)
    )
    try:
        args = parser().parse_args(args_list)
    except UsageError:
        from yorunge.domain.errors import YorungeError

        error = YorungeError("invalid_request")
        print(
            json.dumps(error.envelope(), ensure_ascii=False) if json_output else error.message,
            file=sys.stderr,
        )
        return error.exit_code

    from yorunge import api
    from yorunge.domain.errors import YorungeError

    options = vars(args)
    json_output = options.get("output", "text") == "json"
    from yorunge.domain.credentials import CredentialCheck, CredentialObservation
    from yorunge.domain.state import StateInfo

    result: (
        Result[Plan]
        | Result[Context]
        | Result[CapabilityView]
        | Result[CredentialCheck]
        | Result[CredentialObservation]
        | Result[StateInfo]
    )
    try:
        if args.command == "state":
            if any(options.get(name) is not None for name in ("config", "profile", "project")):
                raise YorungeError("invalid_request")
            result = api.initialize_state(state_dir=options.get("state_dir"))
        elif args.command == "plan" and args.action == "show":
            if any(options.get(name) is not None for name in ("config", "profile", "project")):
                raise YorungeError("invalid_request")
            result = api.load_plan(args.plan)
        else:
            context_options = {name: options.get(name) for name in ("config", "profile", "project")}
            if args.command == "context":
                if args.action == "identity":
                    result = api.observe_credential(
                        args.service, state_dir=args.state_dir, **context_options
                    )
                elif args.action == "credential":
                    result = api.check_credential(args.service, **context_options)
                else:
                    result = api.show_context(**context_options)
            else:
                task = "llm.train" if args.command == "train" else options.get("task")
                use_case = (
                    api.inspect_capabilities if args.command == "capabilities" else api.prepare_plan
                )
                result = use_case(
                    **context_options,
                    task=task,
                    recipe=args.recipe,
                    tool=args.tool,
                    execution=args.execution,
                )
        print(result.model_dump_json() if json_output else text_result(result.data))
        return 0
    except YorungeError as error:
        print(
            json.dumps(error.envelope(), ensure_ascii=False) if json_output else error.message,
            file=sys.stderr,
        )
        return error.exit_code
