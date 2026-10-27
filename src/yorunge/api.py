"""Local use cases; credential access requires an explicit service check."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from yorunge.adapters.files import load_config, load_recipe, load_saved_plan, validate
from yorunge.application.planning import build_plan, capability_records, resolve_selection
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
    ServiceId,
    Task,
)

if TYPE_CHECKING:
    from yorunge.domain.capabilities import CachedCapabilityView
    from yorunge.domain.configuration import ConfigUpdate, Diagnostic, DoctorReport, ProfilesView
    from yorunge.domain.credentials import CredentialCheck, CredentialObservation
    from yorunge.domain.maintenance import MaintenancePreview
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

    from yorunge.domain.state import StateInfo

    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    if sys.platform not in ("darwin", "linux"):
        raise YorungeError("state_unsupported")
    from yorunge.adapters.state import open_store

    with open_store(state_dir) as store:
        return Result[StateInfo](data=store.verify())


def preview_identity_reset(*, state_dir: Path | None = None) -> Result[MaintenancePreview]:
    from yorunge.adapters.maintenance import preview_reset
    from yorunge.domain.maintenance import MaintenancePreview

    return Result[MaintenancePreview](data=preview_reset(state_dir))


def reset_identity(confirmation: str, *, state_dir: Path | None = None) -> Result[StateInfo]:
    from yorunge.adapters.maintenance import reset
    from yorunge.domain.state import StateInfo

    return Result[StateInfo](data=reset(state_dir, confirmation))


def preview_state_restore(
    backup_dir: Path, *, state_dir: Path | None = None
) -> Result[MaintenancePreview]:
    from yorunge.adapters.maintenance import preview_restore
    from yorunge.domain.maintenance import MaintenancePreview

    return Result[MaintenancePreview](
        data=preview_restore(backup_dir, state_dir),
        warnings=("restore_discards_post_backup_history",),
    )


def restore_state(
    backup_dir: Path, confirmation: str, *, state_dir: Path | None = None
) -> Result[StateInfo]:
    from yorunge.adapters.maintenance import restore
    from yorunge.domain.state import StateInfo

    return Result[StateInfo](
        data=restore(backup_dir, state_dir, confirmation),
        warnings=("restore_discards_post_backup_history",),
    )


def preview_state_recovery(*, state_dir: Path | None = None) -> Result[MaintenancePreview]:
    from yorunge.adapters.maintenance import preview_recovery
    from yorunge.domain.maintenance import MaintenancePreview

    return Result[MaintenancePreview](data=preview_recovery(state_dir))


def recover_state(confirmation: str, *, state_dir: Path | None = None) -> Result[StateInfo]:
    from yorunge.adapters.maintenance import recover
    from yorunge.domain.state import StateInfo

    return Result[StateInfo](
        data=recover(state_dir, confirmation), warnings=("restore_discards_post_backup_history",)
    )


def _configuration(config: Path | None) -> tuple[Configuration, bool]:
    if config is not None and not isinstance(config, Path):
        raise YorungeError("invalid_request")
    exists = True
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
    return configuration, exists


def _context(
    config: Path | None, request: Request, recipe: Recipe | None
) -> tuple[Context, Profile]:
    configuration, _ = _configuration(config)
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


def initialize_config(
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
) -> Result[ConfigUpdate]:
    from yorunge.adapters.configuration import initialize
    from yorunge.domain.configuration import ConfigUpdate

    request = validate(Request, {"profile": profile, "project": project}, "invalid_request")
    return Result[ConfigUpdate](
        data=initialize(config, request.profile or "default", request.project)
    )


def list_profiles(*, config: Path | None = None) -> Result[ProfilesView]:
    from yorunge.domain.configuration import ProfileSummary, ProfilesView

    configuration, exists = _configuration(config)
    return Result[ProfilesView](
        data=ProfilesView(
            config_exists=exists,
            active_profile=configuration.active_profile,
            profiles=tuple(
                ProfileSummary(
                    name=name,
                    active=name == configuration.active_profile,
                    account_id=value.account_id,
                    project_id=value.project_id,
                )
                for name, value in configuration.profiles.items()
            ),
        )
    )


def activate_profile(name: str, *, config: Path | None = None) -> Result[ConfigUpdate]:
    from yorunge.adapters.configuration import update
    from yorunge.application.configuration import activate
    from yorunge.domain.configuration import ConfigUpdate

    request = validate(Request, {"profile": name}, "invalid_request")
    if request.profile is None:
        raise YorungeError("invalid_request")
    return Result[ConfigUpdate](data=update(config, request.profile, activate))


def set_project(
    project: str,
    *,
    config: Path | None = None,
    profile: str | None = None,
) -> Result[ConfigUpdate]:
    from yorunge.adapters.configuration import update
    from yorunge.application.configuration import project_selection
    from yorunge.domain.configuration import ConfigUpdate

    request = validate(Request, {"profile": profile, "project": project}, "invalid_request")
    if request.project is None:
        raise YorungeError("invalid_request")
    return Result[ConfigUpdate](
        data=update(
            config,
            request.profile,
            lambda value, name: project_selection(value, name, request.project),
        )
    )


def clear_project(
    *,
    config: Path | None = None,
    profile: str | None = None,
) -> Result[ConfigUpdate]:
    from yorunge.adapters.configuration import update
    from yorunge.application.configuration import project_selection
    from yorunge.domain.configuration import ConfigUpdate

    request = validate(Request, {"profile": profile}, "invalid_request")
    return Result[ConfigUpdate](
        data=update(
            config,
            request.profile,
            lambda value, name: project_selection(value, name, None),
        )
    )


def _missing_config(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except (OSError, ValueError):
        pass
    return False


def _diagnostic_configuration(config: Path | None) -> tuple[Configuration, bool]:
    configuration, exists = _configuration(config)
    if not exists:
        try:
            if (Path.home() / ".config/yorunge/config.toml").is_symlink():
                raise YorungeError("file_unreadable")
        except OSError:
            raise YorungeError("file_unreadable") from None
    return configuration, exists


def diagnose_local(
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[DoctorReport]:
    from yorunge.adapters.diagnostics import check_state
    from yorunge.adapters.local_files import require_local_files
    from yorunge.domain.configuration import Diagnostic, DoctorReport

    request = validate(Request, {"profile": profile, "project": project}, "invalid_request")
    if (config is not None and not isinstance(config, Path)) or (
        state_dir is not None and not isinstance(state_dir, Path)
    ):
        raise YorungeError("invalid_request")
    require_local_files()
    checks = _config_diagnostics(config, request)
    checks.extend(check_state(state_dir))
    checks.append(Diagnostic(name="remote_access", status="not_checked"))
    return Result[DoctorReport](
        data=DoctorReport(
            checks=tuple(checks),
            issue_count=sum(item.status in ("missing", "invalid", "busy") for item in checks),
        )
    )


def _config_diagnostics(config: Path | None, request: Request) -> list[Diagnostic]:
    from yorunge.domain.configuration import Diagnostic

    checks: list[Diagnostic] = []
    try:
        configuration, exists = _diagnostic_configuration(config)
        checks.append(Diagnostic(name="configuration", status="ok" if exists else "missing"))
        name = request.profile or configuration.active_profile
        if name not in configuration.profiles:
            raise YorungeError("profile_not_found")
        selected = configuration.profiles[name]
        checks.extend(
            (
                Diagnostic(name="profile", status="ok"),
                Diagnostic(
                    name="platform_reference",
                    status="ok" if selected.platform_key_env else "missing",
                ),
                Diagnostic(
                    name="llm_reference", status="ok" if selected.llm_key_env else "missing"
                ),
            )
        )
    except YorungeError as error:
        if error.code == "profile_not_found":
            checks.append(Diagnostic(name="profile", status="invalid", code=error.code))
        else:
            missing = error.code == "file_unreadable" and _missing_config(config)
            checks.append(
                Diagnostic(
                    name="configuration",
                    status="missing" if missing else "invalid",
                    code=error.code,
                )
            )
            checks.append(Diagnostic(name="profile", status="not_checked"))
        checks.extend(
            (
                Diagnostic(name="platform_reference", status="not_checked"),
                Diagnostic(name="llm_reference", status="not_checked"),
            )
        )
    return checks


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
    from yorunge.domain.credentials import CredentialCheck

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


def observe_credential(
    service_id: str,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[CredentialObservation]:
    """Persist one selected env snapshot; does not verify remote authentication."""
    from yorunge.adapters.identity import StateCredentialRegistry
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.adapters.state import open_store, state_directory
    from yorunge.application.credentials import bind_credential, resolve_credential
    from yorunge.domain.credentials import CredentialObservation

    request = validate(
        CredentialRequest,
        {"service_id": service_id, "profile": profile, "project": project},
        "invalid_request",
    )
    root = state_directory(state_dir)
    context, selected = _context(config, request, None)
    resolved = resolve_credential(selected, request.service_id, EnvSecretReader())
    with open_store(root) as store:
        bound = bind_credential(context, resolved, StateCredentialRegistry(store))
        return Result[CredentialObservation](
            data=CredentialObservation(
                service_id=resolved.reference.service_id,
                **resolved.target.model_dump(),
                profile=context.profile,
                account_id=context.account_id,
                project_id=context.project_id,
                identity=bound.identity,
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


def query_capabilities(
    *,
    task: str | None = None,
    config: Path | None = None,
    recipe: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    execution: str | None = None,
    refresh: bool = False,
    state_dir: Path | None = None,
) -> Result[CachedCapabilityView]:
    """Explicit stateful query. No caller evidence, producer or authorization input."""
    import time

    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    query_started = time.monotonic()
    if type(refresh) is not bool or (state_dir is not None and not isinstance(state_dir, Path)):
        raise YorungeError("invalid_request")
    from yorunge.adapters.capability_cache import StateCache
    from yorunge.adapters.identity import StateCredentialRegistry
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.adapters.state import open_store
    from yorunge.application.capabilities import LocalPolicyProducer, current_policy_result
    from yorunge.application.credentials import bind_credential, resolve_credential
    from yorunge.domain.capabilities import (
        CachedCapabilityView,
        CapabilityKey,
        CapabilityScopeV2,
        ExecutionBinding,
        ModelBinding,
        ToolBinding,
    )
    from yorunge.domain.credentials import normalize_target

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
    offline = capability_records(context, selection)
    remote = next(
        (
            r.scope.service_id
            for r in offline
            if r.capability_id != "planning.offline" and r.scope.service_id != "local"
        ),
        None,
    )
    remaining = 5.0 - (time.monotonic() - query_started)
    if remaining <= 0:
        raise YorungeError("state_busy")
    with open_store(state_dir, timeout=remaining) as store:
        identity = None
        if remote in ("evren-platform", "evren-llm"):
            name = (
                selected_profile.platform_key_env
                if remote == "evren-platform"
                else selected_profile.llm_key_env
            )
            if name is not None:
                resolved = resolve_credential(selected_profile, remote, EnvSecretReader())
                identity = bind_credential(
                    context, resolved, StateCredentialRegistry(store)
                ).identity
        cache = StateCache(store, bindings=(identity,) if identity else ())
        stamp = cache.stamp()
        records = []
        for old in offline:
            local = old.capability_id == "planning.offline" or old.scope.service_id == "local"
            service = "local" if local else old.scope.service_id
            target = (
                None
                if local
                else normalize_target(
                    context.llm_url if service == "evren-llm" else context.platform_url
                )
            )
            scope = CapabilityScopeV2(
                schema_version=2,
                store_id=stamp.store_id,
                identity_epoch=stamp.identity_epoch,
                clock_generation=stamp.generation,
                service_id=service,
                service_origin=target.service_origin if target else None,
                api_base_path=target.api_base_path if target else None,
                account_id=context.account_id,
                project_id=context.project_id,
                credential_id=identity.credential_id if identity and not local else None,
                credential_revision=identity.credential_revision
                if identity and not local
                else None,
                authorization_scope=None,
                model=ModelBinding(
                    source=spec.model.source,
                    id=spec.model.id,
                    revision=spec.model.revision,
                    content_digest=None,
                )
                if spec.model
                else None,
                tool=ToolBinding(
                    id=selection.tool, version=None, executable_digest=None, environment_digest=None
                )
                if selection.tool
                else None,
                execution=ExecutionBinding(
                    backend=selection.execution,
                    runtime_id=None,
                    runtime_revision=None,
                    environment_digest=None,
                ),
            )
            key = CapabilityKey(capability_id=old.capability_id, task=spec.task, scope=scope)
            if refresh and not stamp.anomaly:
                cache.refresh(key, stamp, LocalPolicyProducer(old.support, old.reason_code))
            records.append(
                current_policy_result(
                    cache.query(key, stamp), frozenset({LocalPolicyProducer.SOURCE})
                )
            )
        return Result[CachedCapabilityView](data=CachedCapabilityView(records=tuple(records)))
