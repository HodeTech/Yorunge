"""Local use cases; credential access requires an explicit service check."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from yorunge.adapters.files import load_config, load_recipe, load_saved_plan, validate
from yorunge.application.planning import build_plan, capability_records, resolve_selection
from yorunge.domain.credentials import CredentialCheck, ServiceId
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import (
    CapabilityView,
    Configuration,
    Context,
    Execution,
    Identifier,
    Model,
    Plan,
    Profile,
    Recipe,
    Result,
    Task,
)
from yorunge.domain.state import StateInfo


class Request(Model):
    profile: Identifier | None = None
    project: Identifier | None = None
    task: Task | None = None
    tool: Identifier | None = None
    execution: Execution | None = None


class CredentialRequest(Request):
    service_id: ServiceId


def initialize_state(*, state_dir: Path | None = None) -> Result[StateInfo]:
    """Explicitly create/validate the local state; never reads service credentials."""
    import sys

    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    if sys.platform not in ("darwin", "linux"):
        raise YorungeError("state_unsupported")
    from yorunge.adapters.state import open_store

    with open_store(state_dir) as store:
        return Result[StateInfo](data=store.verify())


def _context(
    config: Path | None, request: Request, recipe: Recipe | None
) -> tuple[Context, Profile]:
    if config is not None and not isinstance(config, Path):
        raise YorungeError("invalid_request")
    if config is None:
        config = Path.home() / ".config" / "yorunge" / "config.toml"
        try:
            exists = config.exists()
        except (OSError, ValueError):
            raise YorungeError("file_unreadable") from None
        if not exists:
            configuration = Configuration(
                schema_version=1, active_profile="default", profiles={"default": Profile()}
            )
        else:
            configuration = load_config(config)
    else:
        configuration = load_config(config)
    name = request.profile or (recipe.profile if recipe else None) or configuration.active_profile
    if name not in configuration.profiles:
        raise YorungeError("profile_not_found")
    selected = configuration.profiles[name]
    project = request.project or (recipe.project if recipe else None) or selected.project_id
    return Context(
        profile=name,
        project_id=project,
        account_id=selected.account_id,
        platform_url=selected.platform_url,
        llm_url=selected.llm_url,
    ), selected


def show_context(
    *, config: Path | None = None, profile: str | None = None, project: str | None = None
) -> Result[Context]:
    request = validate(Request, {"profile": profile, "project": project}, "invalid_request")
    context, _ = _context(config, request, None)
    return Result[Context](data=context)


def check_credential(
    service_id: str,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
) -> Result[CredentialCheck]:
    """Check only the selected env reference; never authenticates or persists identity."""
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.application.credentials import resolve_credential

    request = validate(
        CredentialRequest,
        {"service_id": service_id, "profile": profile, "project": project},
        "invalid_request",
    )
    context, selected = _context(config, request, None)
    resolved = resolve_credential(selected, request.service_id, EnvSecretReader())
    return Result[CredentialCheck](
        data=CredentialCheck(
            service_id=resolved.reference.service_id,
            **resolved.target.model_dump(),
            profile=context.profile,
            account_id=context.account_id,
            project_id=context.project_id,
        )
    )


def _resolve(
    *,
    config: Path | None,
    recipe: Path | None,
    profile: str | None,
    project: str | None,
    task: str | None,
    tool: str | None,
    execution: str | None,
) -> tuple[Context, Profile, Request, Recipe]:
    if recipe is not None and not isinstance(recipe, Path):
        raise YorungeError("invalid_request")
    request = validate(
        Request,
        {
            "profile": profile,
            "project": project,
            "task": task,
            "tool": tool,
            "execution": execution,
        },
        "invalid_request",
    )
    spec = load_recipe(recipe) if recipe is not None else None
    selected_task = request.task or (spec.task if spec else None)
    if selected_task is None:
        raise YorungeError("invalid_request")
    if spec is None:
        spec = Recipe(schema_version=1, task=selected_task)
    elif selected_task != spec.task:
        try:
            spec = Recipe.model_validate({**spec.model_dump(), "task": selected_task})
        except ValidationError:
            raise YorungeError("unsupported_combination") from None
    if selected_task not in ("llm.train",) and spec.training is not None:
        raise YorungeError("unsupported_combination")
    context, selected_profile = _context(config, request, spec)
    return context, selected_profile, request, spec


def inspect_capabilities(
    *,
    task: str | None = None,
    config: Path | None = None,
    recipe: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    execution: str | None = None,
) -> Result[CapabilityView]:
    context, selected_profile, request, spec = _resolve(
        config=config,
        recipe=recipe,
        profile=profile,
        project=project,
        task=task,
        tool=tool,
        execution=execution,
    )
    selection = resolve_selection(
        spec.task, selected_profile, spec, request.tool, request.execution
    )
    return Result[CapabilityView](
        data=CapabilityView(
            context=context,
            selection=selection,
            records=capability_records(context, selection),
        )
    )


def prepare_plan(
    *,
    task: str | None = None,
    config: Path | None = None,
    recipe: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    execution: str | None = None,
) -> Result[Plan]:
    context, selected_profile, request, spec = _resolve(
        config=config,
        recipe=recipe,
        profile=profile,
        project=project,
        task=task,
        tool=tool,
        execution=execution,
    )
    selection = resolve_selection(
        spec.task, selected_profile, spec, request.tool, request.execution
    )
    plan = build_plan(context, selection, spec)
    return Result[Plan](data=plan, warnings=("offline_draft_not_executable",))


def load_plan(path: Path) -> Result[Plan]:
    """Validate a saved Plan JSON object without consulting the current profile."""
    if not isinstance(path, Path):
        raise YorungeError("invalid_request")
    plan = load_saved_plan(path)
    try:
        expected = build_plan(plan.context, plan.selection, plan.recipe)
        if expected != plan:
            raise YorungeError("invalid_plan")
    except YorungeError:
        raise YorungeError("invalid_plan") from None
    return Result[Plan](data=plan, warnings=("offline_draft_not_executable",))
