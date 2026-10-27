"""Execution preparation/validation orchestrated through bounded input and state ports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from pydantic import ValidationError

from yorunge.application.capabilities import LocalPolicyProducer, combine, policy_keys
from yorunge.domain.capabilities import canonical, instant, timestamp
from yorunge.domain.credentials import BoundCredential
from yorunge.domain.errors import YorungeError
from yorunge.domain.execution import (
    Effect,
    ExecutionAssessment,
    ExecutionBody,
    ExecutionMoment,
    ExecutionPlan,
    ExecutionPlanView,
    ExecutionValidity,
    InputBinding,
    InputRoot,
)
from yorunge.domain.models import Context, Recipe, Selection


class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


class ExecutionBudget:
    def __init__(self, clock: Clock, started: float) -> None:
        self.clock, self.end = clock, started + 30.0

    def check(self) -> None:
        if self.clock.monotonic() >= self.end:
            raise YorungeError("execution_timeout")

    def remaining(self) -> float:
        self.check()
        return self.end - self.clock.monotonic()


class InputReader(Protocol):
    def bind(
        self,
        root: Path | InputRoot | None,
        references: tuple[tuple[str, str], ...],
        budget: ExecutionBudget,
    ) -> tuple[InputRoot | None, tuple[InputBinding, ...]]: ...


class ExecutionRepository(Protocol):
    def moment(self) -> ExecutionMoment: ...
    def finish(self, expected: ExecutionMoment) -> ExecutionMoment: ...
    def read(self, plan_id: str) -> ExecutionPlan: ...
    def save(self, plan: ExecutionPlan, expected: ExecutionMoment) -> None: ...


@dataclass(frozen=True)
class ExecutionRequest:
    context: Context
    selection: Selection
    recipe: Recipe
    input_root: InputRoot | None
    inputs: tuple[InputBinding, ...]
    credentials: tuple[BoundCredential, ...] = field(repr=False)


class ExecutionValidator(Protocol):
    def observe(
        self, request: ExecutionRequest, moment: ExecutionMoment
    ) -> ExecutionAssessment: ...


class LocalExecutionValidator:
    """Current product policy: no execution adapter or complete input-closure claim."""

    def observe(self, request: ExecutionRequest, moment: ExecutionMoment) -> ExecutionAssessment:
        identity = request.credentials[0].identity if request.credentials else None
        records = tuple(
            combine(
                key,
                None,
                LocalPolicyProducer(old.support, old.reason_code).observe(key, moment.now),
                moment.now,
                replace_own=True,
            )
            for key, old in policy_keys(
                request.context,
                request.selection,
                request.recipe,
                store_id=moment.store_id,
                identity_epoch=moment.identity_epoch,
                clock_generation=moment.generation,
                identity=identity,
            )
        )
        return ExecutionAssessment(
            capabilities=records,
            inputs_verified=False,
            blockers=tuple(
                dict.fromkeys(
                    [r.reason_code for r in records if r.support != "supported"]
                    + ["input_closure_unverified", "execution_adapter_unavailable"]
                )
            ),
            effects=(
                Effect(kind="local_read", service_id="local", description_code="input_binding"),
            ),
            parameter_mapping=(),
            parameter_losses=("adapter_mapping_unavailable",),
            cost=None,
        )


def report(
    plan: ExecutionPlan,
    moment: ExecutionMoment,
    reasons: list[str],
    until: datetime,
) -> ExecutionValidity:
    if (plan.store_id, plan.identity_epoch) != (moment.store_id, moment.identity_epoch):
        reasons.append("identity_epoch_changed")
    if plan.clock_generation != moment.generation or moment.anomaly:
        reasons.append("clock_generation_changed")
    if not instant(plan.prepared_at) <= moment.now < min(instant(plan.expires_at), until):
        reasons.append("plan_expired")
    if plan.status != "prepared":
        reasons.extend(("plan_blocked", *plan.assessment.blockers))
    return ExecutionValidity(
        plan_id=plan.plan_id,
        digest=plan.digest,
        valid=not reasons,
        checked_at=timestamp(moment.now),
        valid_until=timestamp(min(instant(plan.expires_at), until)) if not reasons else None,
        reasons=tuple(dict.fromkeys(reasons)),
    )


class ExecutionUseCases:
    def __init__(
        self,
        repository: ExecutionRepository,
        reader: InputReader,
        validator: ExecutionValidator,
        budget: ExecutionBudget,
    ) -> None:
        self.repository, self.reader, self.validator, self.budget = (
            repository,
            reader,
            validator,
            budget,
        )

    def _assessment(
        self, request: ExecutionRequest, expected: ExecutionMoment
    ) -> ExecutionAssessment:
        self.budget.check()
        current = self.repository.finish(expected)
        try:
            result = self.validator.observe(request, current)
        finally:
            # Even rejected observations must durably fence a clock regression.
            self.repository.finish(expected)
        self.budget.check()
        try:
            result = ExecutionAssessment.model_validate_json(
                canonical(result.model_dump(mode="json"))
            )
        except (ValueError, ValidationError, TypeError):
            raise YorungeError("plan_not_valid") from None
        final = self.repository.finish(expected)
        for record in result.capabilities:
            scope = record.key.scope
            if not instant(record.checked_at) <= final.now < instant(record.expires_at) or (
                scope.store_id,
                scope.identity_epoch,
                scope.clock_generation,
                record.key.task,
            ) != (final.store_id, final.identity_epoch, final.generation, request.selection.task):
                raise YorungeError("plan_not_valid")
            if scope.credential_id is not None and not any(
                (
                    c.identity.credential_id,
                    c.identity.credential_revision,
                    c.credential.reference.service_id,
                    c.credential.target.service_origin,
                    c.credential.target.api_base_path,
                )
                == (
                    scope.credential_id,
                    scope.credential_revision,
                    scope.service_id,
                    scope.service_origin,
                    scope.api_base_path,
                )
                for c in request.credentials
            ):
                raise YorungeError("plan_not_valid")
        if result.cost is not None and not (
            instant(result.cost.checked_at) <= final.now < instant(result.cost.expires_at)
        ):
            raise YorungeError("plan_not_valid")
        return result

    def prepare(
        self,
        context: Context,
        selection: Selection,
        recipe: Recipe,
        input_root: Path | None,
        credentials: tuple[BoundCredential, ...],
    ) -> ExecutionPlanView:
        expected = self.repository.moment()
        references = (("data.manifest", recipe.data.manifest),) if recipe.data else ()
        root, inputs = self.reader.bind(input_root, references, self.budget)
        request = ExecutionRequest(context, selection, recipe, root, inputs, credentials)
        assessment = self._assessment(request, expected)
        current = self.repository.finish(expected)
        expires = min(current.now + timedelta(seconds=300), assessment.expiry())
        if current.anomaly or current.generation != expected.generation or expires <= current.now:
            raise YorungeError("plan_not_valid")
        try:
            body = ExecutionBody(
                plan_id=str(uuid4()),
                store_id=current.store_id,
                identity_epoch=current.identity_epoch,
                clock_generation=current.generation,
                context=context,
                selection=selection,
                recipe=recipe,
                input_root=root,
                inputs=inputs,
                assessment=assessment,
                prepared_at=timestamp(current.now),
                expires_at=timestamp(expires),
                status="prepared" if assessment.ready() else "draft",
            ).model_dump(mode="json")
            body["digest"] = hashlib.sha256(canonical(body)).hexdigest()
            plan = ExecutionPlan.model_validate_json(canonical(body))
        except (ValueError, TypeError):
            raise YorungeError("plan_not_valid") from None
        self.budget.check()
        self.repository.save(plan, expected)
        final = self.repository.finish(expected)
        self.budget.check()
        return ExecutionPlanView(plan=plan, validity=report(plan, final, [], expires))

    def validate(
        self, plan: ExecutionPlan, context: Context, credentials: tuple[BoundCredential, ...]
    ) -> ExecutionValidity:
        expected = self.repository.moment()
        reasons = [] if context == plan.context else ["context_changed"]
        until = instant(plan.expires_at)
        try:
            root, inputs = self.reader.bind(
                plan.input_root, tuple((i.role, i.path) for i in plan.inputs), self.budget
            )
            if (root, inputs) != (plan.input_root, plan.inputs):
                reasons.append("inputs_changed")
            request = ExecutionRequest(
                context, plan.selection, plan.recipe, root, inputs, credentials
            )
            assessment = self._assessment(request, expected)
            until = min(until, assessment.expiry())
            if not assessment.ready():
                reasons.append("current_validation_blocked")
            if assessment.semantic() != plan.assessment.semantic():
                reasons.append("execution_bindings_changed")
        except YorungeError as error:
            if error.code in ("input_changed", "input_invalid"):
                reasons.append("inputs_changed")
            elif error.code == "plan_not_valid":
                reasons.append("current_validation_blocked")
            else:
                raise
        self.budget.check()
        final = self.repository.finish(expected)
        return report(plan, final, reasons, until)
