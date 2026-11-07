"""Actual mandatory reads for the observed profile; never produces a grant or price."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from yorunge.adapters.platform_upload_items import read_inventory
from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.adapters.upload_input_files import UploadInputObservation
from yorunge.application import platform_upload_codec as codec
from yorunge.application.http_transport import HttpCredential, HttpRequest, HttpStatusFailure
from yorunge.application.platform_upload_literals import (
    OWNED_MAX_PAGES,
    OWNED_PAGE_SIZE,
    UploadEndpoint,
)
from yorunge.application.response_json import check_response_secrets
from yorunge.application.upload_budget import UploadBudget
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.capabilities import instant, timestamp
from yorunge.domain.dataset_upload import (
    UploadParameters,
    UploadPermission,
    UploadScope,
    manifest_reference,
)
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import ErrorCode, YorungeError
from yorunge.domain.platform_upload import LocatedDataset, ProviderDataset
from yorunge.domain.upload_checks import (
    UNAVAILABLE_CODES,
    AuthorizationCheck,
    AuthorizationOutcome,
    ConsumerProfile,
    UploadCurrentCheck,
    UploadObservation,
    mandatory_http_failure,
    require_fresh,
)
from yorunge.domain.upload_resume import RemoteInventory

_PROFILE: ConsumerProfile = "evren-platform-observed-upload-v2"
_ACTIONS = {
    "create_private_dataset",
    "link_project",
    "upload_created_dataset",
    "read_created_dataset",
}


@dataclass(frozen=True, slots=True)
class BaselineCheck:
    """What a create-free reading observed of the baseline dataset of a lineage.

    ``authorization`` is the check for uploading to it; ``dataset_observed`` is whether the project
    lists it and its detail is the baseline's. A well-formed answer that does not say so is not an
    error: the caller reports the dataset as unobserved and nothing is planned on it.
    """

    authorization: AuthorizationCheck
    dataset_observed: bool


def _failure(error: YorungeError) -> tuple[AuthorizationOutcome, ErrorCode]:
    if error.code == "remote_access_denied":
        return "denied", error.code
    if error.code == "invalid_response":
        return "invalid", error.code
    if error.code in UNAVAILABLE_CODES:
        return "unavailable", error.code
    raise error


class ObservedUploadReader:
    def __init__(
        self,
        scope: UploadScope,
        credential: HttpCredential,
        budget: UploadBudget,
        *,
        utc_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.scope = revalidate_input(UploadScope, scope)
        if type(credential) is not HttpCredential or type(budget) is not UploadBudget:
            raise YorungeError("invalid_request")
        target = credential.target
        if (
            credential.service_id != "evren-platform"
            or credential.header_name.lower() != "x-api-key"
            or credential.prefix != ""
        ):
            raise YorungeError("invalid_credential")
        if (target.service_origin, target.api_base_path) != (
            self.scope.service_origin,
            self.scope.api_base_path,
        ):
            raise YorungeError("invalid_service_target")
        if (target.service_origin, target.api_base_path) != ("https://api.ssyz.org.tr", "/api/v1"):
            raise YorungeError("unsupported_combination")
        valid = True
        try:
            check_response_secrets(self.scope, (credential.secret,))
        except YorungeError:
            valid = False
        if not valid:
            raise YorungeError("invalid_request")
        self._credential, self._budget = credential, budget
        self._clock = utc_clock or (lambda: datetime.now(UTC))

    def _now(self) -> str:
        now = self._clock()
        if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
            raise YorungeError("invalid_request")
        return timestamp(now)

    def _client(self, client: UploadHttpxTransport) -> None:
        if (
            type(client) is not UploadHttpxTransport
            or client._budget is not self._budget
            or client._credential is not self._credential
        ):
            raise YorungeError("invalid_request")

    async def _get(
        self,
        client: UploadHttpxTransport,
        kind: UploadEndpoint,
        endpoint: str,
        end: float,
        query: tuple[tuple[str, str], ...] = (),
    ) -> bytes:
        request = HttpRequest(
            self._credential.target,
            "GET",
            endpoint,
            query=query,
            credential=self._credential,
            service_id="evren-platform",
            read_only=True,
            upload_endpoint=kind,
        )
        reserved = self._budget.reserve("read", response_bytes=request.max_bytes)
        try:
            async with client.open_budgeted(request, reserved, deadline=end) as response:
                return b"".join([part async for part in response.chunks()])
        finally:
            if not reserved._closed:
                reserved.finish()

    async def _context(self, client: UploadHttpxTransport, end: float) -> None:
        secret = self._credential.secret
        me = codec.identity(await self._get(client, "me", "auth/me", end), secret)
        project_id = codec.segment(self.scope.project_id, secret)
        project = codec.project(
            await self._get(client, "project", f"projects/{project_id}", end), self.scope, secret
        )
        codec.context(me, project, self.scope)

    async def _located(
        self,
        client: UploadHttpxTransport,
        expected: ProviderDataset,
        parameters: UploadParameters,
        end: float,
    ) -> bool:
        """Whether the owned list shows the dataset and its detail is the expected one.

        ``False`` is the one well-formed answer that it is not: it is not listed, it is listed
        under another owner or name, its detail is another one, or its detail is gone (404/410).
        Anything malformed, any other status and any transport failure still raises.
        """
        secret = self._credential.secret
        seen: set[str] = set()
        located: LocatedDataset | None = None
        try:
            for page in range(1, OWNED_MAX_PAGES + 1):
                raw = await self._get(
                    client,
                    "owned",
                    "datasets",
                    end,
                    (("page", str(page)), ("page_size", str(OWNED_PAGE_SIZE)), ("scope", "owned")),
                )
                owned = codec.owned_page(raw, expected.id, self.scope, parameters, secret)
                if seen.intersection(owned.ids):
                    raise YorungeError("invalid_response")
                seen.update(owned.ids)
                if owned.selected is not None:
                    located = owned.selected
                    break
                if len(owned.ids) < OWNED_PAGE_SIZE:
                    break
            if located is None:
                return False
            try:
                detail = await self._get(client, "detail", codec.detail_path(located, secret), end)
            except HttpStatusFailure as error:
                if error.status_code in (404, 410):
                    return False
                raise
            codec.detail(detail, expected, self.scope, parameters, secret)
        except codec.DatasetMismatch:
            return False
        return True

    async def _dataset(
        self,
        client: UploadHttpxTransport,
        expected: ProviderDataset,
        parameters: UploadParameters,
        end: float,
    ) -> None:
        if not await self._located(client, expected, parameters, end):
            raise YorungeError("invalid_response")

    def _check(
        self,
        action: UploadPermission,
        dataset_id: str | None,
        at: str,
        outcome: AuthorizationOutcome,
        code: ErrorCode | None,
    ) -> AuthorizationCheck:
        return AuthorizationCheck(
            consumer_profile=_PROFILE,
            policy_version=2,
            action=action,
            scope=self.scope,
            dataset_id=dataset_id,
            producer_id="evren-platform-upload-http",
            producer_version="2",
            checked_at=at,
            outcome=outcome,
            grant=None,
            error_code=code,
        )

    async def _mandatory(
        self,
        client: UploadHttpxTransport,
        action: UploadPermission,
        expected: ProviderDataset | None,
        parameters: UploadParameters | None,
        end: float,
        at: str,
    ) -> UploadObservation | None:
        dataset_id = None if expected is None else expected.id
        await self._context(client, end)
        if expected is not None:
            assert parameters is not None
            await self._dataset(client, expected, parameters, end)
        if action in {"upload_created_dataset", "read_created_dataset"}:
            assert dataset_id is not None
            project_id = codec.segment(self.scope.project_id, self._credential.secret)
            member = await self._get(client, "membership", f"projects/{project_id}/datasets", end)
            if not codec.membership(member, dataset_id, self._credential.secret):
                raise YorungeError("invalid_response")
        if action == "upload_created_dataset":
            assert dataset_id is not None
            path = codec.segment(dataset_id, self._credential.secret)
            codec.role(
                await self._get(client, "role", f"datasets/{path}/my-role", end),
                self._credential.secret,
            )
            return UploadObservation(
                consumer_profile=_PROFILE,
                policy_version=2,
                scope=self.scope,
                dataset_id=dataset_id,
                checked_at=at,
                has_upload=True,
            )
        return None

    async def _observe(
        self,
        client: UploadHttpxTransport,
        action: UploadPermission,
        expected: ProviderDataset | None,
        parameters: UploadParameters | None,
    ) -> tuple[AuthorizationCheck, UploadObservation | None]:
        self._client(client)
        if type(action) is not str or action not in _ACTIONS:
            raise YorungeError("invalid_request")
        if (action == "create_private_dataset") != (expected is None):
            raise YorungeError("invalid_request")
        if expected is not None:
            expected = revalidate_input(ProviderDataset, expected)
            if parameters is None:
                raise YorungeError("invalid_request")
            parameters = revalidate_input(UploadParameters, parameters)
            valid = True
            try:
                codec._owner(expected, self.scope, parameters)
            except YorungeError:
                valid = False
            if not valid:
                raise YorungeError("invalid_request")
        at, end = self._now(), min(self._budget.end, time.monotonic() + 30.0)
        dataset_id = None if expected is None else expected.id
        outcome: AuthorizationOutcome = "not_exposed"
        code: ErrorCode | None = None
        observation: UploadObservation | None = None
        try:
            observation = await self._mandatory(client, action, expected, parameters, end, at)
        except HttpStatusFailure as error:
            outcome, code = mandatory_http_failure(error.status_code)
            at = self._now()  # Timestamp the negative actually observed now.
        except YorungeError as error:
            outcome, code = _failure(error)
            at = self._now()
        require_fresh(at, self._now())
        return self._check(action, dataset_id, at, outcome, code), observation

    async def preparation(self, client: UploadHttpxTransport) -> AuthorizationCheck:
        check, _ = await self._observe(client, "create_private_dataset", None, None)
        return check

    async def current(
        self,
        client: UploadHttpxTransport,
        plan: DatasetUploadPlanV2,
        inputs: UploadInputObservation,
        *,
        action: UploadPermission,
        expected_dataset: ProviderDataset | None = None,
    ) -> UploadCurrentCheck:
        plan = revalidate_input(DatasetUploadPlanV2, plan)
        if type(inputs) is not UploadInputObservation or action == "read_created_dataset":
            raise YorungeError("invalid_request")
        if (
            plan.scope != self.scope
            or plan.grant is not None
            or plan.cost_bound is not None
            or plan.status == "draft"
            or not instant(plan.prepared_at) <= instant(self._now()) < instant(plan.expires_at)
        ):
            raise YorungeError("upload_plan_not_valid")
        if inputs.root != plan.root or manifest_reference(inputs.manifest) != plan.manifest:
            raise YorungeError("input_changed")
        inputs.recheck()
        check, observation = await self._observe(client, action, expected_dataset, plan.parameters)
        inputs.recheck()
        require_fresh(check.checked_at, self._now())
        return UploadCurrentCheck(
            saved_plan_id=plan.plan_id,
            saved_plan_digest=plan.digest,
            saved_binding_digest=plan.binding_digest(),
            work_digest=plan.cost_work().digest(),
            scope=self.scope,
            checked_at=check.checked_at,
            baseline_grant=None,
            baseline_cost_bound=None,
            supplemental_grant=None,
            supplemental_cost_bound=None,
            authorization=check,
            inputs_verified=True,
            upload_observation=observation,
        )

    async def _baseline_dataset(
        self,
        client: UploadHttpxTransport,
        expected: ProviderDataset,
        parameters: UploadParameters,
        end: float,
    ) -> bool:
        """Whether the project holds the dataset the baseline names, as it describes it."""
        if not await self._located(client, expected, parameters, end):
            return False
        secret = self._credential.secret
        project_id = codec.segment(self.scope.project_id, secret)
        member = await self._get(client, "membership", f"projects/{project_id}/datasets", end)
        return codec.membership(member, expected.id, secret)

    async def baseline(
        self,
        client: UploadHttpxTransport,
        expected: ProviderDataset,
        parameters: UploadParameters,
    ) -> BaselineCheck:
        """Context, the baseline's detail and project membership, then the caller's role.

        Reads only and plans nothing: it is the observation a resume report and a continuation plan
        stand on, without a plan to check it against. Access and transport failures are recorded
        in the check as everywhere; an absent or different dataset is ``dataset_observed=False``.
        """
        self._client(client)
        expected = revalidate_input(ProviderDataset, expected)
        parameters = revalidate_input(UploadParameters, parameters)
        valid = True
        try:
            codec._owner(expected, self.scope, parameters)
        except YorungeError:
            valid = False
        if not valid:
            raise YorungeError("invalid_request")
        at, end = self._now(), min(self._budget.end, time.monotonic() + 30.0)
        outcome: AuthorizationOutcome = "not_exposed"
        code: ErrorCode | None = None
        observed = False
        try:
            await self._context(client, end)
            observed = await self._baseline_dataset(client, expected, parameters, end)
            if observed:
                path = codec.segment(expected.id, self._credential.secret)
                codec.role(
                    await self._get(client, "role", f"datasets/{path}/my-role", end),
                    self._credential.secret,
                )
        except HttpStatusFailure as error:
            outcome, code = mandatory_http_failure(error.status_code)
            at = self._now()
        except YorungeError as error:
            outcome, code = _failure(error)
            at = self._now()
        require_fresh(at, self._now())
        return BaselineCheck(
            self._check("upload_created_dataset", expected.id, at, outcome, code), observed
        )

    async def inventory(
        self, client: UploadHttpxTransport, dataset_id: str, *, deadline: float
    ) -> RemoteInventory:
        """The dataset's item listing as observed (see ``read_inventory``)."""
        return await read_inventory(self, client, dataset_id, deadline=deadline)

    async def read_authorization(
        self,
        client: UploadHttpxTransport,
        expected_dataset: ProviderDataset,
        parameters: UploadParameters,
    ) -> AuthorizationCheck:
        check, _ = await self._observe(client, "read_created_dataset", expected_dataset, parameters)
        return check

    def __repr__(self) -> str:
        return "<observed upload reader private>"
