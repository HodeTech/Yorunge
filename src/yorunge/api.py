"""Local use cases; credential access requires an explicit service check."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Literal, overload

from pydantic import ConfigDict, ValidationError

from yorunge.adapters.files import load_config, load_recipe, load_saved_plan, validate
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
    Selection,
    ServiceId,
    Task,
)

if TYPE_CHECKING:
    from yorunge.adapters.execution_store import PlanRepository
    from yorunge.adapters.state import Store
    from yorunge.application.execution import ExecutionBudget, ExecutionUseCases, ExecutionValidator
    from yorunge.application.operation_observations import ReadContext, ReadPort
    from yorunge.application.operations import OperationCoordinator, StartPort
    from yorunge.domain.capabilities import CachedCapabilityView
    from yorunge.domain.configuration import ConfigUpdate, Diagnostic, DoctorReport, ProfilesView
    from yorunge.domain.credentials import BoundCredential, CredentialCheck, CredentialObservation
    from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3
    from yorunge.domain.dataset_manifest import DatasetInspection, DatasetVerification
    from yorunge.domain.dataset_upload import UploadOwner, UploadParameters
    from yorunge.domain.dataset_upload_v2 import AdmissionPolicy, DatasetUploadPlanV2
    from yorunge.domain.dataset_version import (
        DatasetVersionBound,
        DatasetVersionCheck,
        DatasetVersionList,
        DatasetVersionObservation,
    )
    from yorunge.domain.discovery import ContextDiscovery
    from yorunge.domain.download import DownloadSummary
    from yorunge.domain.execution import (
        ExecutionApprovalState,
        ExecutionPlan,
        ExecutionPlans,
        ExecutionPlanView,
        ExecutionValidity,
        ForgottenExecutionPlan,
    )
    from yorunge.domain.maintenance import Preview as MaintenancePreview
    from yorunge.domain.operations import JobsPage, JobView
    from yorunge.domain.platform_discovery import PlatformContextDiscovery
    from yorunge.domain.state import StateInfo
    from yorunge.domain.upload_public import (
        DatasetUploadsPage,
        DatasetUploadSummary,
        UploadIntentReview,
        UploadSummary,
    )
    from yorunge.domain.upload_resume_report import DatasetUploadResumeReport


class Request(Model):
    model_config = ConfigDict(defer_build=True)

    profile: Identifier | None = None
    project: Identifier | None = None
    task: Task | None = None
    tool: Identifier | None = None
    execution: Execution | None = None


class CredentialRequest(Request):
    model_config = ConfigDict(defer_build=True)

    service_id: ServiceId


def inspect_dataset(root: Path, *, manifest_out: Path) -> Result[DatasetInspection]:
    """Hash a local tree and publish a new external manifest; never overwrite."""
    import time

    started = time.monotonic()
    from yorunge.adapters.dataset_files import anchor_dataset_paths, open_dataset
    from yorunge.adapters.dataset_reports import DatasetManifestWriter, PublicationState
    from yorunge.application.datasets import DatasetBudget, inspect_dataset_tree

    budget = DatasetBudget(started=started)
    root, target = anchor_dataset_paths(root, manifest_out)
    state = PublicationState()
    try:
        with open_dataset(root, budget) as source:
            with source.location(target) as location:
                writer = DatasetManifestWriter(location, state, source.recheck)
                result = inspect_dataset_tree(source, writer, str(target), budget)
        budget.check()
        return result
    except BaseException as error:
        state.reraise(error)


def verify_dataset(root: Path, *, manifest: Path) -> Result[DatasetVerification]:
    """Validate a manifest, then freshly hash the entire local tree for equality."""
    import time

    started = time.monotonic()
    from yorunge.adapters.dataset_files import anchor_dataset_paths, open_dataset
    from yorunge.application.datasets import DatasetBudget, decode_manifest, verify_dataset_tree

    budget = DatasetBudget(started=started)
    root, artifact = anchor_dataset_paths(root, manifest)
    with open_dataset(root, budget) as source:
        expected = decode_manifest(source.read_manifest(artifact), budget)
        result = verify_dataset_tree(source, expected, budget)
    budget.check()
    return result


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
    from yorunge.domain.maintenance import Preview as MaintenancePreview

    return Result[MaintenancePreview](data=preview_reset(state_dir))


def reset_identity(confirmation: str, *, state_dir: Path | None = None) -> Result[StateInfo]:
    from yorunge.adapters.maintenance import reset
    from yorunge.domain.state import StateInfo

    return Result[StateInfo](data=reset(state_dir, confirmation))


def preview_state_restore(
    backup_dir: Path, *, state_dir: Path | None = None
) -> Result[MaintenancePreview]:
    from yorunge.adapters.maintenance import preview_restore
    from yorunge.domain.maintenance import Preview as MaintenancePreview

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
    from yorunge.domain.maintenance import Preview as MaintenancePreview

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


@overload
def discover_context(
    service_id: Literal["evren-llm"],
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ContextDiscovery]: ...


@overload
def discover_context(
    service_id: Literal["evren-platform"],
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[PlatformContextDiscovery]: ...


@overload
def discover_context(
    service_id: ServiceId,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ContextDiscovery] | Result[PlatformContextDiscovery]: ...


def discover_context(
    service_id: ServiceId,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ContextDiscovery] | Result[PlatformContextDiscovery]:
    """Explicit bounded remote observation; never initializes state or grants authority."""
    import time

    started = time.monotonic()
    request = validate(
        CredentialRequest,
        {"service_id": service_id, "profile": profile, "project": project},
        "invalid_request",
    )
    if any(path is not None and not isinstance(path, Path) for path in (config, state_dir)):
        raise YorungeError("invalid_request")
    if request.service_id == "evren-llm" and request.project is not None:
        raise YorungeError("invalid_request")
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.capability_cache import SystemClock
    from yorunge.adapters.context_state import StateDiscovery
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.application.context_discovery import ObservationClock

    clock = ObservationClock(SystemClock())
    state = StateDiscovery(
        state_dir,
        lambda: _context(config, request, None),
        EnvSecretReader(),
        clock,
        service_id=request.service_id,
    )
    if request.service_id == "evren-platform":
        from yorunge.adapters.platform_context import PlatformReader
        from yorunge.application.platform_discovery import discover_platform
        from yorunge.domain.platform_discovery import PlatformContextDiscovery

        return Result[PlatformContextDiscovery](
            data=discover_platform(state, PlatformReader(clock), clock, deadline=started + 30.0),
            warnings=("context_not_verified",),
        )
    from yorunge.adapters.llm_context import LlmTermsReader
    from yorunge.application.context_discovery import discover_context as discover
    from yorunge.domain.discovery import ContextDiscovery

    return Result[ContextDiscovery](
        data=discover(state, LlmTermsReader(clock), clock, deadline=started + 30.0),
        warnings=("context_not_verified",),
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
    from yorunge.application.planning import capability_records, resolve_selection

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
    from yorunge.application.planning import build_plan, resolve_selection

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
    from yorunge.application.planning import build_plan

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
    from yorunge.application.capabilities import (
        LocalPolicyProducer,
        current_policy_result,
        policy_keys,
    )
    from yorunge.application.credentials import bind_credential, resolve_credential
    from yorunge.application.planning import capability_records, resolve_selection
    from yorunge.domain.capabilities import CachedCapabilityView

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
        for key, old in policy_keys(
            context,
            selection,
            spec,
            store_id=stamp.store_id,
            identity_epoch=stamp.identity_epoch,
            clock_generation=stamp.generation,
            identity=identity,
        ):
            if refresh and not stamp.anomaly:
                cache.refresh(key, stamp, LocalPolicyProducer(old.support, old.reason_code))
            records.append(key)
        final = tuple(
            current_policy_result(record, frozenset({LocalPolicyProducer.SOURCE}))
            for record in cache.query_many(tuple(records), stamp)
        )
        return Result[CachedCapabilityView](data=CachedCapabilityView(records=final))


def _execution_validator() -> ExecutionValidator:
    from yorunge.application.execution import LocalExecutionValidator

    return LocalExecutionValidator()


def _execution_credentials(
    context: Context, selected: Profile, selection: Selection, store: Store
) -> tuple[BoundCredential, ...]:
    from yorunge.adapters.identity import StateCredentialRegistry
    from yorunge.adapters.secrets import EnvSecretReader
    from yorunge.application.credentials import bind_credential, resolve_credential
    from yorunge.application.planning import capability_records

    remote = next(
        (
            r.scope.service_id
            for r in capability_records(context, selection)
            if r.capability_id != "planning.offline" and r.scope.service_id != "local"
        ),
        None,
    )
    if remote not in ("evren-platform", "evren-llm"):
        return ()
    reference = selected.platform_key_env if remote == "evren-platform" else selected.llm_key_env
    if reference is None:
        return ()
    resolved = resolve_credential(selected, remote, EnvSecretReader())
    return (bind_credential(context, resolved, StateCredentialRegistry(store)),)


def _execution_repository(
    store: Store, credentials: tuple[BoundCredential, ...], budget: ExecutionBudget
) -> PlanRepository:
    from yorunge.adapters.capability_cache import StateCache
    from yorunge.adapters.execution_store import PlanRepository

    cache = StateCache(
        store,
        budget.clock,
        bindings=tuple(c.identity for c in credentials),
        budget_seconds=budget.remaining(),
    )
    cache.end = budget.end
    return PlanRepository(store, cache, budget)


def _execution_budget() -> ExecutionBudget:
    import time

    started = time.monotonic()
    from yorunge.adapters.input_files import require_input_files
    from yorunge.adapters.local_files import require_local_files

    require_input_files()
    require_local_files()
    from yorunge.adapters.capability_cache import SystemClock
    from yorunge.application.execution import ExecutionBudget

    return ExecutionBudget(SystemClock(), started)


def _operation_read_context(
    plan: ExecutionPlan, context: Context, credentials: tuple[BoundCredential, ...]
) -> ReadContext:
    from yorunge.adapters.operation_store import plan_authorities
    from yorunge.application.operation_observations import ReadContext

    authorities = []
    for authority in plan_authorities(plan):
        if (context.account_id, context.project_id) != (
            authority.account_id,
            authority.project_id,
        ):
            raise YorungeError("state_changed")
        if authority.service_id == "local":
            authorities.append(authority)
            continue
        bound = next(
            (
                item
                for item in credentials
                if (
                    item.credential.reference.service_id,
                    item.credential.target.service_origin,
                    item.credential.target.api_base_path,
                )
                == (authority.service_id, authority.service_origin, authority.api_base_path)
            ),
            None,
        )
        if bound is None:
            raise YorungeError("credential_unavailable")
        authorities.append(
            authority.model_copy(
                update={
                    "credential_id": bound.identity.credential_id,
                    "credential_revision": bound.identity.credential_revision,
                }
            )
        )
    return ReadContext(tuple(authorities), credentials)


@contextmanager
def _operation_session(
    plan_id: str,
    backend: StartPort,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
    observer: ReadPort | None = None,
) -> Iterator[OperationCoordinator]:
    """Trusted composition only; no public run, backend registration or caller evidence."""
    import os

    from yorunge.application.operations import OperationCoordinator, preflight_port

    preflight_port(backend)
    preflight_port(observer)
    budget = _execution_budget()
    from yorunge.adapters.input_files import DescriptorInputs
    from yorunge.adapters.operation_repository import StateOperations
    from yorunge.adapters.state import open_store
    from yorunge.application.execution import ExecutionUseCases

    request = validate(Request, {"profile": profile, "project": project}, "invalid_request")
    with open_store(state_dir, timeout=min(5.0, budget.remaining())) as store:
        from yorunge.adapters.execution_store import read_plan

        read_plan(store.connection, plan_id)
        store.deadline.end = budget.end
        repository = StateOperations(store, (), budget)
        snapshot: tuple[Context, tuple[BoundCredential, ...]] | None = None

        def captured(plan: ExecutionPlan) -> tuple[Context, tuple[BoundCredential, ...]]:
            nonlocal snapshot
            if plan.plan_id != plan_id:
                raise YorungeError("invalid_request")
            if snapshot is None:
                context, selected = _context(config, request, None)
                credentials = _execution_credentials(context, selected, plan.selection, store)
                snapshot = context, credentials
            context, credentials = snapshot
            repository.credentials = credentials
            coordinator.credentials = credentials
            return context, credentials

        def current(plan: ExecutionPlan) -> ExecutionValidity:
            context, credentials = captured(plan)
            plans = _execution_repository(store, credentials, budget)
            if plans.read(plan_id) != plan:
                raise YorungeError("state_changed")
            use_cases = ExecutionUseCases(plans, DescriptorInputs(), _execution_validator(), budget)
            return use_cases.validate(plan, context, credentials)

        def read_context(plan: ExecutionPlan) -> ReadContext:
            context, credentials = captured(plan)
            return _operation_read_context(plan, context, credentials)

        coordinator = OperationCoordinator(
            repository, current, backend, (), budget, os.getpid, observer, read_context
        )
        yield coordinator


def prepare_execution_plan(
    *,
    task: str | None = None,
    config: Path | None = None,
    recipe: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    tool: str | None = None,
    execution: str | None = None,
    input_root: Path | None = None,
    state_dir: Path | None = None,
) -> Result[ExecutionPlanView]:
    """Persist a separate execution snapshot; no run or caller-supplied evidence."""
    budget = _execution_budget()
    if (input_root is not None and not isinstance(input_root, Path)) or (
        state_dir is not None and not isinstance(state_dir, Path)
    ):
        raise YorungeError("invalid_request")
    from yorunge.adapters.input_files import DescriptorInputs, anchor_input_root

    if input_root is not None:
        input_root = anchor_input_root(input_root)
    from yorunge.adapters.state import open_store
    from yorunge.application.execution import ExecutionUseCases
    from yorunge.application.planning import resolve_selection
    from yorunge.domain.execution import ExecutionPlanView

    context, selected, request, spec = _resolve(
        config=config,
        recipe=recipe,
        profile=profile,
        project=project,
        task=task,
        tool=tool,
        execution=execution,
    )
    selection = resolve_selection(spec.task, selected, spec, request.tool, request.execution)
    with open_store(state_dir, timeout=budget.remaining()) as store:
        credentials = _execution_credentials(context, selected, selection, store)
        repository = _execution_repository(store, credentials, budget)
        use_cases = ExecutionUseCases(
            repository, DescriptorInputs(), _execution_validator(), budget
        )
        return Result[ExecutionPlanView](
            data=use_cases.prepare(context, selection, spec, input_root, credentials),
            warnings=("execution_does_not_dispatch",),
        )


def list_execution_plans(
    *, limit: int = 50, cursor: str | None = None, state_dir: Path | None = None
) -> Result[ExecutionPlans]:
    """Bounded historical summaries; does not read credentials or input contents."""
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.execution_store import list_plans
    from yorunge.adapters.state import open_store
    from yorunge.domain.execution import ExecutionPlans

    with open_store(state_dir) as store:
        return Result[ExecutionPlans](data=list_plans(store.connection, limit, cursor))


def list_jobs(
    *,
    status: str | None = None,
    plan_id: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    state_dir: Path | None = None,
) -> Result[JobsPage]:
    """Page through last local records without config, credentials or provider access."""
    from yorunge.domain.jobs import JobsCursor, JobsQuery

    query = validate(
        JobsQuery,
        {"status": status, "plan_id": plan_id, "limit": limit, "cursor": cursor},
        "invalid_request",
    )
    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    if query.cursor is not None:
        JobsCursor.decode(query.cursor)
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.jobs import list_jobs as read_jobs
    from yorunge.adapters.state import open_store
    from yorunge.domain.operations import JobsPage

    with open_store(state_dir) as store:
        return Result[JobsPage](
            data=read_jobs(store.connection, query), warnings=("local_history_only",)
        )


def show_job(operation_id: str, *, state_dir: Path | None = None) -> Result[JobView]:
    """Read one complete historical job in one snapshot; never reconciles it."""
    from yorunge.domain.state import canonical_uuid

    try:
        canonical_uuid(operation_id)
    except (ValueError, TypeError, AttributeError):
        raise YorungeError("invalid_request") from None
    if state_dir is not None and not isinstance(state_dir, Path):
        raise YorungeError("invalid_request")
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.operation_store import read_job
    from yorunge.adapters.state import open_store
    from yorunge.domain.operations import JobView

    with open_store(state_dir) as store:
        return Result[JobView](
            data=read_job(store.connection, operation_id), warnings=("local_history_only",)
        )


def show_execution_plan(
    plan_id: str, *, state_dir: Path | None = None
) -> Result[ExecutionPlanView]:
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.execution_store import read_approval, read_plan
    from yorunge.adapters.state import open_store
    from yorunge.application.execution import approval_state
    from yorunge.domain.execution import ExecutionPlanView

    with open_store(state_dir) as store:
        plan = read_plan(store.connection, plan_id)
        return Result[ExecutionPlanView](
            data=ExecutionPlanView(
                plan=plan,
                approval=approval_state(plan, read_approval(store.connection, plan), None),
            )
        )


@contextmanager
def _execution_validation(
    plan_id: str,
    config: Path | None,
    profile: str | None,
    project: str | None,
    state_dir: Path | None,
    budget: ExecutionBudget,
    *,
    confirmation: str | None = None,
    consent: bool = False,
) -> Iterator[tuple[ExecutionUseCases, ExecutionPlan, Context, tuple[BoundCredential, ...]]]:
    from yorunge.adapters.execution_store import read_plan
    from yorunge.adapters.input_files import DescriptorInputs
    from yorunge.adapters.state import open_store
    from yorunge.application.execution import ExecutionUseCases, require_confirmation

    request = validate(Request, {"profile": profile, "project": project}, "invalid_request")
    with open_store(state_dir, timeout=budget.remaining()) as store:
        plan = read_plan(store.connection, plan_id)
        if consent:
            require_confirmation(plan, confirmation)
        context, selected = _context(config, request, None)
        credentials = _execution_credentials(context, selected, plan.selection, store)
        repository = _execution_repository(store, credentials, budget)
        if repository.read(plan_id) != plan:
            raise YorungeError("state_changed")
        use_cases = ExecutionUseCases(
            repository, DescriptorInputs(), _execution_validator(), budget
        )
        yield use_cases, plan, context, credentials


def validate_execution_plan(
    plan_id: str,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ExecutionValidity]:
    budget = _execution_budget()
    from yorunge.domain.execution import ExecutionValidity

    with _execution_validation(plan_id, config, profile, project, state_dir, budget) as (
        use_cases,
        plan,
        context,
        credentials,
    ):
        return Result[ExecutionValidity](data=use_cases.validate(plan, context, credentials))


def approve_execution_plan(
    plan_id: str,
    confirmation: str | None = None,
    *,
    config: Path | None = None,
    profile: str | None = None,
    project: str | None = None,
    state_dir: Path | None = None,
) -> Result[ExecutionApprovalState]:
    budget = _execution_budget()
    from yorunge.domain.execution import ExecutionApprovalState

    with _execution_validation(
        plan_id,
        config,
        profile,
        project,
        state_dir,
        budget,
        confirmation=confirmation,
        consent=True,
    ) as (use_cases, plan, context, credentials):
        return Result[ExecutionApprovalState](
            data=use_cases.approve(plan, confirmation, context, credentials)
        )


def revoke_execution_approval(
    plan_id: str, *, state_dir: Path | None = None
) -> Result[ExecutionApprovalState]:
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.execution_store import revoke_approval
    from yorunge.adapters.state import open_store
    from yorunge.domain.execution import ExecutionApprovalState

    with open_store(state_dir) as store:
        return Result[ExecutionApprovalState](data=revoke_approval(store, plan_id))


def forget_execution_plan(
    plan_id: str, confirmation: str | None = None, *, state_dir: Path | None = None
) -> Result[ForgottenExecutionPlan]:
    from yorunge.adapters.local_files import require_local_files

    require_local_files()
    from yorunge.adapters.execution_store import forget_plan
    from yorunge.adapters.state import open_store
    from yorunge.domain.execution import ForgottenExecutionPlan

    with open_store(state_dir) as store:
        return Result[ForgottenExecutionPlan](
            data=forget_plan(store, plan_id, confirmation),
            warnings=("local_forget_does_not_cancel_remote_work",),
        )


def show_dataset_upload(
    *,
    plan_id: str | None = None,
    operation_id: str | None = None,
    state_dir: Path | None = None,
) -> Result[UploadSummary]:
    """Read one durable upload summary; no credentials or network are needed."""
    from yorunge.adapters.upload_public import show_upload

    return show_upload(state_dir, plan_id=plan_id, operation_id=operation_id)


def review_dataset_upload(
    plan_id: str,
    *,
    state_dir: Path | None = None,
) -> Result[UploadIntentReview]:
    """Review the selected plan intent before confirming its full digest."""
    from yorunge.adapters.upload_public import review_upload

    return review_upload(plan_id, state_dir)


def list_dataset_uploads(
    *,
    plan_id: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetUploadsPage]:
    """Read a bounded keyset page without resolving configuration or secrets."""
    from yorunge.adapters.upload_public import list_uploads

    return list_uploads(state_dir, plan_id=plan_id, limit=limit, cursor=cursor)


def revoke_dataset_upload(
    plan_id: str,
    *,
    state_dir: Path | None = None,
) -> Result[UploadSummary]:
    """Revoke the saved approval locally; an issued permit is not recalled."""
    from yorunge.adapters.upload_public import revoke_upload

    return revoke_upload(plan_id, state_dir)


def _upload_options(config: Path | None, profile: str | None) -> None:
    from yorunge.adapters.upload_preparation import require_upload_sync_context
    from yorunge.application.upload_inputs import revalidate_input

    require_upload_sync_context()
    if config is not None and not isinstance(config, Path):
        raise YorungeError("invalid_request")
    revalidate_input(Request, Request.model_construct(profile=profile))


def _upload_context(
    config: Path | None,
    profile: str | None,
    plan: DatasetUploadPlanV2 | DatasetContinuationPlanV3,
) -> tuple[Context, Profile]:
    return _context(
        config, Request(profile=profile or plan.scope.profile, project=plan.scope.project_id), None
    )


def prepare_dataset_upload(
    root: Path,
    *,
    manifest: Path,
    owner: UploadOwner,
    parameters: UploadParameters,
    project: str,
    budget_cr: str | None = None,
    unpriced: bool = False,
    admission_policy: AdmissionPolicy = "verified_only",
    storage_origin: str | None = None,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetUploadSummary]:
    """Freshly hash local files and save a scoped plan; never writes remotely."""
    from yorunge.adapters.upload_api import prepare_upload

    _upload_options(config, profile)
    return prepare_upload(
        root,
        manifest,
        owner,
        parameters,
        project,
        lambda: _context(config, Request(profile=profile, project=project), None),
        state_dir,
        budget_cr=budget_cr,
        unpriced=unpriced,
        admission_policy=admission_policy,
        storage_origin=storage_origin,
    )


def approve_dataset_upload(
    plan_id: str,
    confirmed_digest: str,
    *,
    accept_unverified_authority: bool = False,
    accept_unpriced_cost: bool = False,
    accept_unconfirmed_effects: bool = False,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[UploadSummary]:
    """Recheck current files/context before recording exact digest/risk consent.

    ``accept_unconfirmed_effects`` exists for a continuation plan whose files include some whose
    last confirm may or may not have landed; it is required exactly then and refused otherwise.
    """
    from yorunge.adapters.upload_api import approve_upload

    _upload_options(config, profile)
    return approve_upload(
        plan_id,
        confirmed_digest,
        lambda plan: _upload_context(config, profile, plan),
        state_dir,
        authority=accept_unverified_authority,
        unpriced=accept_unpriced_cost,
        unconfirmed=accept_unconfirmed_effects,
    )


def start_dataset_upload(
    plan_id: str,
    *,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[UploadSummary]:
    """Run a new original workflow once; existing operations are local lookups."""
    from yorunge.adapters.upload_api import start_upload

    _upload_options(config, profile)
    return start_upload(plan_id, lambda plan: _upload_context(config, profile, plan), state_dir)


def resume_dataset_upload(
    operation_id: str,
    *,
    prepare: bool = False,
    accept_unverified_read: bool = False,
    accept_unconfirmed_effects: bool = False,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetUploadResumeReport]:
    """What an interrupted upload still needs; with ``prepare``, the plan that continues it.

    The default is a read-only report: it answers with the same shape whether the source can be
    continued or not (what rules it out is in ``blockers``) and writes nothing. ``prepare`` makes
    the same observation and, only without blockers, saves the local plan; it is an error
    (``continuation_not_possible``, or ``operation_conflict`` naming the operation in the way)
    otherwise. ``accept_unverified_read`` is the human's choice to read the dataset on an explicit
    attempt; ``accept_unconfirmed_effects`` belongs to ``prepare`` and to files whose last confirm
    was sent without an answer.
    """
    from yorunge.adapters.upload_api import resume_upload

    _upload_options(config, profile)
    return resume_upload(
        operation_id,
        lambda plan: _upload_context(config, profile, plan),
        state_dir,
        prepare=prepare,
        accept_unverified_read=accept_unverified_read,
        accept_unconfirmed_effects=accept_unconfirmed_effects,
    )


def reconcile_dataset_upload(
    operation_id: str,
    *,
    accept_unverified_read: bool = False,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[UploadSummary]:
    """Inspect the same resource through a new bounded read; never resumes writes."""
    from yorunge.adapters.upload_api import recover_upload

    _upload_options(config, profile)
    return recover_upload(
        operation_id,
        lambda plan: _upload_context(config, profile, plan),
        state_dir,
        accepted=accept_unverified_read,
    )


def _platform_loader(
    config: Path | None, profile: str | None
) -> Callable[[], tuple[Context, Profile]]:
    request = validate(
        CredentialRequest,
        {"service_id": "evren-platform", "profile": profile, "project": None},
        "invalid_request",
    )
    if config is not None and not isinstance(config, Path):
        raise YorungeError("invalid_request")
    return lambda: _context(config, request, None)


def list_dataset_versions(
    dataset_id: str,
    *,
    page: int = 1,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetVersionList]:
    """One page (1-10 000) of a dataset's versions; read-only, one request."""
    from yorunge.adapters.dataset_version_api import list_dataset_versions as use

    return use(dataset_id, page, _platform_loader(config, profile), state_dir)


def show_dataset_version(
    dataset_id: str,
    version_tag: str,
    *,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetVersionObservation]:
    """One version from its detail and its split counts (two requests, which must agree)."""
    from yorunge.adapters.dataset_version_api import show_dataset_version as use

    return use(dataset_id, version_tag, _platform_loader(config, profile), state_dir)


def bind_dataset_version(
    dataset_id: str,
    version_tag: str,
    *,
    binding_out: Path,
    manifest: Path | None = None,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetVersionBound]:
    """Bind a frozen version into a new file; never overwrites, never writes remotely."""
    from yorunge.adapters.dataset_version_api import bind_dataset_version as use

    return use(
        dataset_id,
        version_tag,
        binding_out,
        manifest,
        _platform_loader(config, profile),
        state_dir,
    )


def check_dataset_version(
    binding: Path,
    *,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
) -> Result[DatasetVersionCheck]:
    """``unchanged`` if the provider still shows what the binding holds; else a closed error."""
    from yorunge.adapters.dataset_version_api import check_dataset_version as use

    return use(binding, _platform_loader(config, profile), state_dir)


def download_model_weights(
    version_id: str,
    *,
    artifact_format: str,
    weights_out: Path,
    fold: int | None = None,
    sha256: str | None = None,
    timeout: int | None = None,
    no_resume: bool = False,
    config: Path | None = None,
    profile: str | None = None,
    state_dir: Path | None = None,
    progress: Callable[[int, int | None], None] | None = None,
) -> Result[DownloadSummary]:
    """Download the weights of one exact model version into a new file; never overwrites.

    ``artifact_format`` is ``onnx``, ``pt`` or ``tflite`` (never guessed). ``sha256`` is the
    caller's own expected digest: only with it do the written bytes earn ``sha256_matched``;
    without it the result says no more than ``transfer_complete``. ``timeout`` is whole seconds
    (30-3600, default 900) for the download; a partial download of the same thing resumes unless
    ``no_resume``. ``progress(bytes_written, total_or_None)`` is called while the body is
    received, at most ten times a second, and must return quickly.
    """
    from yorunge.adapters.model_download import download_model_weights as use

    return use(
        version_id,
        artifact_format,
        weights_out,
        fold,
        sha256,
        timeout,
        no_resume,
        _platform_loader(config, profile),
        state_dir,
        progress,
    )
