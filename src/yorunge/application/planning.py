from __future__ import annotations

from urllib.parse import urlsplit

from yorunge.domain.errors import YorungeError
from yorunge.domain.models import (
    LLM_TASKS,
    TOOL_IDS,
    Capability,
    Context,
    Execution,
    Plan,
    Profile,
    Recipe,
    Scope,
    Selection,
    SelectionSource,
    Support,
    Task,
)


def resolve_selection(
    task: Task,
    profile: Profile,
    recipe: Recipe,
    tool: str | None,
    execution: Execution | None,
) -> Selection:
    selected_tool: str | None
    tool_source: SelectionSource
    if tool is not None:
        selected_tool, tool_source = tool, "request"
    elif recipe.tool is not None:
        selected_tool, tool_source = recipe.tool.id, "recipe"
    elif task in profile.tools.defaults:
        selected_tool, tool_source = profile.tools.defaults[task], "profile"
    elif task in LLM_TASKS:
        selected_tool, tool_source = "forgelm", "product_default"
    else:
        selected_tool, tool_source = None, "native"

    backend: Execution
    backend_source: SelectionSource
    if execution is not None:
        backend, backend_source = execution, "request"
    elif recipe.execution is not None:
        backend, backend_source = recipe.execution.backend, "recipe"
    else:
        backend = "evren-managed" if task == "vision.train.managed" else "local"
        backend_source = "product_default"
    return Selection(
        task=task,
        tool=selected_tool,
        tool_source=tool_source,
        execution=backend,
        execution_source=backend_source,
    )


def scope_for(context: Context, selection: Selection) -> Scope:
    if selection.execution == "local" and selection.task in LLM_TASKS:
        return Scope(
            service_id="local",
            service_origin=None,
            api_base_path=None,
            account_id=None,
            project_id=context.project_id,
            tool=selection.tool,
            execution=selection.execution,
        )
    llm = selection.task == "llm.chat"
    parts = urlsplit(context.llm_url if llm else context.platform_url)
    host = f"[{parts.hostname}]" if ":" in (parts.hostname or "") else parts.hostname
    return Scope(
        service_id="evren-llm" if llm else "evren-platform",
        service_origin=f"https://{host}",
        api_base_path=parts.path or "/",
        account_id=context.account_id,
        project_id=context.project_id,
        tool=selection.tool,
        execution=selection.execution,
    )


def combination_error(selection: Selection) -> str | None:
    if selection.task not in LLM_TASKS:
        expected = "evren-managed" if selection.task == "vision.train.managed" else "local"
        if selection.tool is not None or selection.execution != expected:
            return "unsupported_combination"
    elif selection.execution == "evren-managed":
        return "unsupported_combination"
    elif selection.tool not in TOOL_IDS:
        return "tool_unavailable"
    return None


def capability_records(context: Context, selection: Selection) -> tuple[Capability, ...]:
    scope = scope_for(context, selection)
    records: list[Capability] = []

    def add(identifier: str, support: Support, reason: str, message: str) -> None:
        records.append(
            Capability(
                capability_id=identifier,
                task=selection.task,
                scope=scope,
                support=support,
                reason_code=reason,
                message=message,
                evidence="local_policy"
                if support in ("supported", "unsupported")
                else "not_verified",
            )
        )

    add(
        "planning.offline",
        "supported",
        "offline_planner_implemented",
        "Yerel seçim ve plan şeması çözümlenebilir; yürütme yetkisi vermez.",
    )
    problem = combination_error(selection)
    if problem:
        add(
            "task.execution",
            "unsupported",
            problem,
            "Bu görev, araç ve ortam birleşimi için yürütme tanımlı değil.",
        )
        return tuple(records)
    if selection.tool is not None:
        add(
            "tool.adapter",
            "unsupported",
            "adapter_not_implemented",
            "Seçim korundu; bu sürümde araç adaptörü yok, görev çalıştırılamaz.",
        )
    else:
        add(
            "service.task",
            "unknown",
            "service_not_verified",
            "Uzak hizmet ve hesap yeteneği bu çevrimdışı sorguda doğrulanmadı.",
        )
    if selection.execution == "evren-workspace":
        add(
            "runtime.access",
            "unknown",
            "runtime_access_unverified",
            "Genel kullanıcı çalışma ortamı sözleşmesi ve erişimi doğrulanmadı.",
        )
    if scope.service_id != "local":
        add(
            "authorization.scope",
            "unknown",
            "authorization_not_verified",
            "Sır okunmadı; hizmet kimliği ve izin kapsamı doğrulanmadı.",
        )
        if context.project_id is None and selection.task != "llm.chat":
            add(
                "context.project",
                "requires_access",
                "project_selection_required",
                "Uzak görev öncesinde açık proje seçimi gerekiyor.",
            )
    return tuple(records)


def build_plan(context: Context, selection: Selection, recipe: Recipe) -> Plan:
    problem = combination_error(selection)
    if problem == "tool_unavailable":
        raise YorungeError("tool_unavailable")
    if problem:
        raise YorungeError("unsupported_combination")
    records = capability_records(context, selection)
    blockers = tuple(record.reason_code for record in records if record.support != "supported")
    # A valid draft records unresolved execution and input bindings explicitly.
    plan = Plan(
        context=context,
        selection=selection,
        recipe=recipe,
        capabilities=records,
        blockers=(*blockers, "inputs_not_verified", "execution_not_implemented"),
        digest="0" * 64,
    )
    return plan.model_copy(update={"digest": plan.computed_digest()})
