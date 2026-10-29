"""Lightweight parser; application and schema imports happen after metadata commands."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, TypeAlias, TypeVar, cast, overload

from yorunge import __version__
from yorunge.cli.output import OutputRenderer, write_utf8

if TYPE_CHECKING:
    from yorunge.domain.capabilities import CachedCapabilityView
    from yorunge.domain.configuration import ConfigUpdate, DoctorReport, ProfilesView
    from yorunge.domain.credentials import CredentialCheck, CredentialObservation
    from yorunge.domain.execution import (
        ExecutionApprovalState,
        ExecutionPlans,
        ExecutionPlanView,
        ExecutionValidity,
        ForgottenExecutionPlan,
    )
    from yorunge.domain.maintenance import Preview as MaintenancePreview
    from yorunge.domain.maintenance import Snapshot as IdentitySnapshot
    from yorunge.domain.models import CapabilityView, Context, Model, Plan, Result
    from yorunge.domain.operations import JobsPage, JobView
    from yorunge.domain.state import StateInfo

    CliResult: TypeAlias = (
        Result[Plan]
        | Result[Context]
        | Result[CapabilityView]
        | Result[CredentialCheck]
        | Result[CredentialObservation]
        | Result[StateInfo]
        | Result[MaintenancePreview]
        | Result[ConfigUpdate]
        | Result[ProfilesView]
        | Result[DoctorReport]
        | Result[CachedCapabilityView]
        | Result[ExecutionPlanView]
        | Result[ExecutionPlans]
        | Result[ExecutionValidity]
        | Result[ExecutionApprovalState]
        | Result[ForgottenExecutionPlan]
        | Result[JobsPage]
        | Result[JobView]
    )


class UsageError(Exception):
    pass


N = TypeVar("N")


class Parser(argparse.ArgumentParser):
    _configure: Callable[[Parser], None] | None = None

    def _ensure_configured(self) -> None:
        configure = self._configure
        if configure is not None:
            self._configure = None
            configure(self)

    @overload
    def parse_known_args(
        self, args: Sequence[str] | None = None, namespace: None = None
    ) -> tuple[argparse.Namespace, list[str]]: ...

    @overload
    def parse_known_args(self, args: Sequence[str] | None, namespace: N) -> tuple[N, list[str]]: ...

    @overload
    def parse_known_args(self, *, namespace: N) -> tuple[N, list[str]]: ...

    def parse_known_args(
        self, args: Sequence[str] | None = None, namespace: object | None = None
    ) -> tuple[object, list[str]]:
        self._ensure_configured()
        return super().parse_known_args(args, namespace)

    def format_help(self) -> str:
        self._ensure_configured()
        return super().format_help()

    def error(self, message: str) -> NoReturn:
        # argparse's message may contain arbitrary user input, including a credential.
        raise UsageError

    def _print_message(self, message: str, file: object | None = None) -> None:
        if message:
            from typing import TextIO, cast

            # argparse supplies the intended stream explicitly. A missing
            # stdout is a delivery failure, not a reason to print help to stderr.
            write_utf8(message, cast(TextIO, file))


def common(parser: argparse.ArgumentParser, *, context: bool = True) -> None:
    parser.allow_abbrev = False
    parser.add_argument(
        "--output",
        choices=("text", "json", "ndjson"),
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

    def add(name: str, help: str, configure: Callable[[Parser], None]) -> None:
        command = commands.add_parser(name, help=help)
        command._configure = configure

    add("init", "İlk config'i no-clobber oluştur", common)
    add("doctor", "Yerel ayar ve state tanılaması; sır okumaz", _doctor_options)
    add("context", "Yerel profil bağlamı", _context_options)
    add("state", "Yerel kimlik durumunu yönet", _state_options)
    add("capabilities", "Sınırlı çevrimdışı yetenek görünümü", _capability_options)
    add("plan", "Çevrimdışı plan; yürütme başlatmaz", _plan_options)
    add("train", "LLM eğitim planı (eğitim çalıştırmaz)", _train_options)
    add("jobs", "Son yerel iş kayıtlarını göster; uzak durumu sorgulamaz", _jobs_options)
    return root


def _doctor_options(doctor: Parser) -> None:
    common(doctor)
    doctor.add_argument("--state-dir", type=Path)


def _jobs_options(jobs: Parser) -> None:
    common(jobs, context=False)
    jobs.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    actions = jobs.add_subparsers(dest="action", required=True)
    for name in ("list", "show"):
        command = actions.add_parser(name)
        common(command, context=False)
        command.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
        if name == "show":
            command.add_argument("--operation-id", required=True)
        else:
            command.add_argument("--status")
            command.add_argument("--plan-id")
            command.add_argument("--limit", type=int, default=50)
            command.add_argument("--cursor")


def _jobs_singletons(arguments: Sequence[str]) -> None:
    seen: set[str] = set()
    singleton = {
        "--output",
        "--non-interactive",
        "--state-dir",
        "--status",
        "--plan-id",
        "--limit",
        "--cursor",
        "--operation-id",
    }
    for argument in arguments:
        option = argument.split("=", 1)[0]
        if option in singleton:
            if option in seen:
                raise UsageError
            seen.add(option)


def _context_options(context: Parser) -> None:
    common(context)
    context_actions = context.add_subparsers(dest="action", required=True)
    show = context_actions.add_parser("show")
    common(show)
    for action in ("profiles", "use-profile", "set-project", "clear-project"):
        management = context_actions.add_parser(action)
        common(management)
        if action == "use-profile":
            management.add_argument("name")
        elif action == "set-project":
            management.add_argument("project_id")
    credential = context_actions.add_parser(
        "credential", help="Seçilen hizmetin env sırrını kontrol et"
    )
    common(credential)
    credential.add_argument("--service", required=True, choices=("evren-platform", "evren-llm"))
    identity = context_actions.add_parser("identity", help="Seçilen sır gözleminin yerel kimliği")
    common(identity)
    identity.add_argument("--service", required=True, choices=("evren-platform", "evren-llm"))
    identity.add_argument("--state-dir", type=Path)


def _state_options(state: Parser) -> None:
    common(state, context=False)
    state.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    state_actions = state.add_subparsers(dest="action", required=True)
    state_init = state_actions.add_parser("init")
    common(state_init, context=False)
    state_init.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    for name in ("reset", "restore", "recover"):
        maintenance = state_actions.add_parser(name, help="Önizle; digest ile açıkça uygula")
        common(maintenance, context=False)
        maintenance.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
        maintenance.add_argument("--confirm", help="Güncel önizleme digest'i")
        if name == "restore":
            maintenance.add_argument("--backup", required=True, type=Path)


def _capability_options(capabilities: Parser) -> None:
    planning_options(capabilities)
    cache_modes = capabilities.add_mutually_exclusive_group()
    cache_modes.add_argument("--cached", action="store_true", help="Açık stateful önbellek okuması")
    cache_modes.add_argument(
        "--refresh", action="store_true", help="Uygulanan yerel kanıtı yenile; uzak keşif yok"
    )
    capabilities.add_argument("--state-dir", type=Path)


def _plan_options(plan: Parser) -> None:
    common(plan)
    actions = plan.add_subparsers(dest="action", required=True)
    planning_options(actions.add_parser("prepare", help="Sabit seçimleri ve engelleri hazırla"))
    saved = actions.add_parser("show", help="Kaydedilmiş planı doğrula ve göster")
    common(saved, context=False)
    saved.add_argument("--plan", required=True, type=Path, help="Plan nesnesi içeren JSON dosyası")
    execution_plan = actions.add_parser("execution", help="Ayrı kalıcı execution planı; yürütmez")
    execution_plan._configure = execution_options


def _train_options(train: Parser) -> None:
    common(train)
    train_plan = train.add_subparsers(dest="action", required=True).add_parser("plan")
    planning_options(train_plan, task=False)


def execution_options(execution_plan: argparse.ArgumentParser) -> None:
    common(execution_plan)
    execution_actions = execution_plan.add_subparsers(dest="execution_action", required=True)
    for name in ("prepare", "list", "show", "validate", "approve", "revoke", "forget"):
        command = execution_actions.add_parser(name)
        if name == "prepare":
            planning_options(command)
            command.add_argument("--input-root", type=Path)
        else:
            common(command, context=name in ("validate", "approve"))
        command.add_argument("--state-dir", type=Path)
        if name in ("show", "validate", "approve", "revoke", "forget"):
            command.add_argument("--plan-id", required=True)
        if name in ("approve", "forget"):
            command.add_argument("--confirm", help="Tam plan digest'i; eksik/yanlış ise çıkış 4")
        if name == "list":
            command.add_argument("--limit", type=int, default=50)
            command.add_argument("--cursor")


def jobs_text_result(data: Model) -> str:
    from yorunge.domain.operations import JobsPage, JobView

    warning = "Yerel geçmiş: son kayıt güncel uzak durumu yansıtmayabilir; uzlaştırma yapılmadı."
    if isinstance(data, JobsPage):
        lines = [warning]
        lines.extend(
            f"{job.operation_id} {job.task}: {job.status} "
            f"(execution: {job.execution_status}; delivery: {job.delivery_status})"
            for job in data.jobs
        )
        if not data.jobs:
            lines.append("Kayıtlı iş yok.")
        if data.next_cursor is not None:
            lines.append(f"Sonraki cursor: {data.next_cursor}")
        return "\n".join(lines)
    if isinstance(data, JobView):
        job = data.operation
        lines = [
            warning,
            f"İş: {job.operation_id}\nGörev: {job.task}\nDurum: {job.status}",
            f"Execution: {job.execution_status}\nDelivery: {job.delivery_status}",
            f"Plan: {job.plan_id}\nDigest: {job.plan_digest}",
            f"Son yerel kayıt: {job.updated_at}",
        ]
        lines.extend(
            f"Attempt {item.number}: {item.attempt_id} {item.status}; "
            f"neden: {item.reason_code or '-'}"
            for item in data.attempts
        )
        if data.outcome is not None:
            lines.append(
                f"Sonuç: {data.outcome.recorded_at}; neden: {data.outcome.reason_code or '-'}"
            )
        return "\n".join(lines)
    raise TypeError("unsupported jobs result type")


def text_result(data: Model) -> str:
    from yorunge.domain.models import CapabilityView, Context, Plan

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

    return local_text_result(data)


def local_text_result(data: Model) -> str:
    from yorunge.domain.capabilities import CachedCapabilityView
    from yorunge.domain.configuration import ConfigUpdate, DoctorReport, ProfilesView
    from yorunge.domain.credentials import CredentialCheck, CredentialObservation
    from yorunge.domain.maintenance import LegacyMaintenancePreview, MaintenancePreview
    from yorunge.domain.state import StateInfo

    execution = execution_text_result(data)
    if execution is not None:
        return execution
    if isinstance(data, CachedCapabilityView):
        return "\n".join(
            f"{r.key.capability_id}: {r.effective_support} ({r.freshness}) — {r.message}"
            for r in data.records
        )
    if isinstance(data, ConfigUpdate):
        return (
            f"Config kaydedildi: {data.config_path}\nAktif profil: {data.active_profile}\n"
            f"Seçili profil projesi: {data.project_id or 'seçilmedi'}\n"
            f"Backup: {data.backup_path or 'ilk oluşturma'}"
        )
    if isinstance(data, ProfilesView):
        return "\n".join(("* " if item.active else "  ") + item.name for item in data.profiles)
    if isinstance(data, DoctorReport):
        return "\n".join(f"{item.name}: {item.status} ({item.code or '-'})" for item in data.checks)
    if isinstance(data, (MaintenancePreview, LegacyMaintenancePreview)):
        return maintenance_text(data)
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
    raise TypeError("unsupported result type")


def execution_text_result(data: Model) -> str | None:
    from yorunge.domain.execution import (
        ExecutionApprovalState,
        ExecutionPlans,
        ExecutionPlanView,
        ExecutionValidity,
        ForgottenExecutionPlan,
    )

    if isinstance(data, ExecutionApprovalState):
        return (
            f"Plan: {data.plan_id}\nOnay etkin: {data.effective}\n"
            f"Durum: {data.record.status if data.record else 'none'}\nYürütme başlatılmaz."
        )
    if isinstance(data, ForgottenExecutionPlan):
        return f"Yerel plan unutuldu: {data.plan_id}\nUzak iş iptali değildir."
    if isinstance(data, ExecutionPlanView):
        return execution_plan_text(data)
    if isinstance(data, ExecutionValidity):
        return (
            f"Geçerli: {data.valid}\n"
            f"Onay etkin: {data.approval.effective if data.approval else False}\n"
            f"Nedenler: {', '.join(data.reasons) or '-'}"
        )
    if isinstance(data, ExecutionPlans):
        return "\n".join(
            f"{p.plan_id} {p.digest} {p.task} ({p.status}; onay kaydı: {p.approval_status})"
            for p in data.plans
        ) + (f"\nSonraki cursor: {data.next_cursor}" if data.next_cursor else "")
    return None


def execution_plan_text(data: ExecutionPlanView) -> str:
    plan = data.plan
    approval_status = (
        data.approval.record.status if data.approval and data.approval.record else "none"
    )
    return (
        f"Execution planı: {plan.plan_id}\nDigest: {plan.digest}\n"
        f"Hazırlık: {plan.status}; güncel geçerlilik: "
        f"{data.validity.valid if data.validity else 'denetlenmedi'}\n"
        f"Onay kaydı: {approval_status}; "
        "show güncel onay doğrulaması yapmaz.\n"
        f"Engeller: {', '.join(plan.assessment.blockers) or '-'}\nYürütme başlatılmaz."
    )


def maintenance_text(data: MaintenancePreview) -> str:
    lines = [f"İşlem: {data.action}", f"Onay digest: {data.digest}"]
    if data.current:
        lines.extend(maintenance_counts("Mevcut", data.current))
    if data.source:
        lines.extend(maintenance_counts("Snapshot", data.source))
    if data.cache_invalidated:
        lines.append("Capability cache geçersizleşir.")
    if data.history_may_be_lost:
        lines.append("Snapshot sonrası credential, plan ve onay geçmişi kaybolabilir.")
    else:
        lines.append("Mevcut credential, plan ve onay geçmişi korunur.")
    lines.append("Yeni kimlik alanı açılır; eski kimlikler, planlar ve onaylar geçersizleşir.")
    if data.schema_version == 3:
        lines.extend(
            (
                "Operation, attempt ve terminal sonuç geçmişi korunur.",
                "Gönderim öncesi işler cancelled; gönderilmiş olabilecek işler unknown olur.",
                "Önceden arm edilmiş dış çağrının durduğu garanti edilmez.",
            )
        )
    return "\n".join(lines)


def maintenance_counts(label: str, snapshot: IdentitySnapshot) -> tuple[str, ...]:
    from yorunge.domain.maintenance import IdentitySnapshot as OperationSnapshot

    common = (
        f"{label} credential bağı: {snapshot.binding_count}",
        f"{label} plan: {snapshot.plan_count}",
        f"{label} onay: {snapshot.approval_count}",
    )
    if isinstance(snapshot, OperationSnapshot):
        return (
            *common,
            f"{label} operation: {snapshot.operation_count}",
            f"{label} attempt: {snapshot.attempt_count}",
            f"{label} terminal olmayan operation: {snapshot.nonterminal_operation_count}",
            f"{label} unknown operation: {snapshot.unknown_operation_count}",
        )
    return common


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    # Error format is known even when parsing fails before reaching --output.
    machine_output = any(
        arg in ("--output=json", "--output=ndjson")
        or (arg == "--output" and args_list[i + 1 : i + 2] in (["json"], ["ndjson"]))
        for i, arg in enumerate(args_list)
    )
    renderer = OutputRenderer("json" if machine_output else "text")
    try:
        args = parser().parse_args(args_list)
        if args.command == "jobs":
            _jobs_singletons(args_list)
    except UsageError:
        from yorunge.domain.errors import YorungeError

        return renderer.error(YorungeError("invalid_request"))
    except KeyboardInterrupt:
        from yorunge.domain.errors import YorungeError

        return renderer.error(YorungeError("request_cancelled"))
    except (OSError, ValueError) as error:
        return renderer.error(renderer.output_failure(error))

    from yorunge.domain.errors import YorungeError

    renderer = OutputRenderer(vars(args).get("output", "text"))
    try:
        result = dispatch(args)
    except YorungeError as error:
        return renderer.error(error)
    except KeyboardInterrupt:
        return renderer.error(YorungeError("request_cancelled"))
    except (OSError, UnicodeError):
        return renderer.error(YorungeError("file_unreadable"))

    try:
        text = None
        if renderer.output == "text":
            text = (
                jobs_text_result(result.data)
                if args.command == "jobs"
                else text_result(result.data)
            )
        renderer.result(cast("Result[Model]", result), text=text)
        return 0
    except YorungeError as error:
        return renderer.error(error)
    except KeyboardInterrupt:
        return renderer.error(YorungeError("request_cancelled"))
    except (OSError, UnicodeError) as error:
        return renderer.error(renderer.output_failure(error))


def reject_context(args: argparse.Namespace, names: tuple[str, ...]) -> None:
    from yorunge.domain.errors import YorungeError

    if any(vars(args).get(name) is not None for name in names):
        raise YorungeError("invalid_request")


def state_result(args: argparse.Namespace) -> Result[StateInfo] | Result[MaintenancePreview]:
    from yorunge import api

    reject_context(args, ("config", "profile", "project"))
    state_dir = vars(args).get("state_dir")
    if args.action == "init":
        return api.initialize_state(state_dir=state_dir)
    if args.action == "reset":
        return (
            api.reset_identity(args.confirm, state_dir=state_dir)
            if args.confirm is not None
            else api.preview_identity_reset(state_dir=state_dir)
        )
    if args.action == "restore":
        return (
            api.restore_state(args.backup, args.confirm, state_dir=state_dir)
            if args.confirm is not None
            else api.preview_state_restore(args.backup, state_dir=state_dir)
        )
    return (
        api.recover_state(args.confirm, state_dir=state_dir)
        if args.confirm is not None
        else api.preview_state_recovery(state_dir=state_dir)
    )


def context_result(args: argparse.Namespace) -> CliResult:
    from yorunge import api

    options = vars(args)
    context_options = {name: options.get(name) for name in ("config", "profile", "project")}
    if args.action in ("profiles", "use-profile"):
        reject_context(args, ("profile", "project"))
    if args.action in ("set-project", "clear-project"):
        reject_context(args, ("project",))
    if args.action == "profiles":
        return api.list_profiles(config=options.get("config"))
    if args.action == "use-profile":
        return api.activate_profile(args.name, config=options.get("config"))
    if args.action == "set-project":
        return api.set_project(
            args.project_id, config=options.get("config"), profile=options.get("profile")
        )
    if args.action == "clear-project":
        return api.clear_project(config=options.get("config"), profile=options.get("profile"))
    if args.action == "identity":
        return api.observe_credential(args.service, state_dir=args.state_dir, **context_options)
    if args.action == "credential":
        return api.check_credential(args.service, **context_options)
    return api.show_context(**context_options)


def dispatch(args: argparse.Namespace) -> CliResult:
    from yorunge import api

    options = vars(args)
    if args.command == "state":
        return state_result(args)
    if args.command == "jobs":
        reject_context(args, ("config", "profile", "project"))
        if args.action == "show":
            return api.show_job(args.operation_id, state_dir=options.get("state_dir"))
        return api.list_jobs(
            status=args.status,
            plan_id=args.plan_id,
            limit=args.limit,
            cursor=args.cursor,
            state_dir=options.get("state_dir"),
        )
    if args.command == "context":
        return context_result(args)
    if args.command == "plan" and args.action == "execution":
        return execution_result(args)
    if args.command == "plan" and args.action == "show":
        reject_context(args, ("config", "profile", "project"))
        return api.load_plan(args.plan)
    context_options = {name: options.get(name) for name in ("config", "profile", "project")}
    if args.command == "init":
        return api.initialize_config(**context_options)
    if args.command == "doctor":
        return api.diagnose_local(state_dir=args.state_dir, **context_options)
    return planning_result(args)


def planning_result(args: argparse.Namespace) -> CliResult:
    from yorunge import api

    options = vars(args)
    context_options = {name: options.get(name) for name in ("config", "profile", "project")}
    task = "llm.train" if args.command == "train" else options.get("task")
    if args.command == "capabilities":
        if args.cached or args.refresh:
            return api.query_capabilities(
                **context_options,
                task=task,
                recipe=args.recipe,
                tool=args.tool,
                execution=args.execution,
                refresh=args.refresh,
                state_dir=args.state_dir,
            )
        if args.state_dir is not None:
            from yorunge.domain.errors import YorungeError

            raise YorungeError("invalid_request")
    use_case = api.inspect_capabilities if args.command == "capabilities" else api.prepare_plan
    return use_case(
        **context_options, task=task, recipe=args.recipe, tool=args.tool, execution=args.execution
    )


def execution_result(args: argparse.Namespace) -> CliResult:
    from yorunge import api

    options = vars(args)
    action = args.execution_action
    if action in ("list", "show", "revoke", "forget"):
        reject_context(args, ("config", "profile", "project"))
        if action == "list":
            return api.list_execution_plans(
                limit=args.limit, cursor=args.cursor, state_dir=args.state_dir
            )
        if action == "revoke":
            return api.revoke_execution_approval(args.plan_id, state_dir=args.state_dir)
        if action == "forget":
            return api.forget_execution_plan(args.plan_id, args.confirm, state_dir=args.state_dir)
        return api.show_execution_plan(args.plan_id, state_dir=args.state_dir)
    context = {name: options.get(name) for name in ("config", "profile", "project")}
    if action == "approve":
        return api.approve_execution_plan(
            args.plan_id, args.confirm, state_dir=args.state_dir, **context
        )
    if action == "validate":
        return api.validate_execution_plan(args.plan_id, state_dir=args.state_dir, **context)
    return api.prepare_execution_plan(
        task=args.task,
        recipe=args.recipe,
        tool=args.tool,
        execution=args.execution,
        input_root=args.input_root,
        state_dir=args.state_dir,
        **context,
    )
