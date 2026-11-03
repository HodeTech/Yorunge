"""Budgeted single-attempt effects; only committed repository arms can dispatch."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, NoReturn

from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.application import platform_upload_codec as codec
from yorunge.application import upload_descriptors as descriptors
from yorunge.application import upload_metadata_codec as metadata
from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.application.response_json import check_response_secrets
from yorunge.application.upload_arms import UploadArm
from yorunge.application.upload_budget import UploadBudget, UploadReservation
from yorunge.application.upload_inputs import revalidate_input
from yorunge.domain.capabilities import timestamp
from yorunge.domain.create_receipt import CreateReceiptV2
from yorunge.domain.credentials import (
    BoundCredential,
    CredentialIdentity,
    EnvReference,
    ResolvedCredential,
    SecretValue,
    ServiceTarget,
    normalize_target,
)
from yorunge.domain.dataset_manifest import DatasetFile, DatasetManifest
from yorunge.domain.dataset_transfer import StageIntent, StageReceipt, VerifiedFile, scope_target
from yorunge.domain.dataset_upload import UploadScope, manifest_reference
from yorunge.domain.dataset_upload_v2 import DatasetUploadPlanV2
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_requests import upload_request_digest

if TYPE_CHECKING:
    from yorunge.adapters.platform_upload_put import PreparedPutCall

ControlKind = Literal["create", "project_link", "presign", "confirm"]


class _Private:
    def __repr__(self) -> str:
        return f"<{type(self).__name__} private>"

    def __copy__(self) -> NoReturn:
        raise TypeError("upload call cannot be copied")

    def __deepcopy__(self, memo: object) -> NoReturn:
        raise TypeError("upload call cannot be copied")

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("upload call cannot be serialized")


def _operation(value: str) -> str:
    valid = False
    try:
        canonical_uuid(value)
        valid = True
    except (ValueError, TypeError, AttributeError):
        pass
    if not valid:
        raise YorungeError("invalid_request")
    return value


@dataclass(frozen=True, slots=True, repr=False)
class ControlOutcome(_Private):
    receipt: CreateReceiptV2 | StageReceipt
    upload: descriptors.PresignedUpload | None = None


class PreparedUploadCall(_Private):
    """One pre-intent reservation, consumed or explicitly released by its owner."""

    def __init__(
        self,
        port: ObservedUploadPort,
        operation_id: str,
        kind: ControlKind,
        request: HttpRequest,
        reservation: UploadReservation,
        dataset_id: str | None,
        context: descriptors.FileContext | None,
        confirmed_count: int | None,
    ) -> None:
        self._port, self._operation, self._kind = port, operation_id, kind
        self._request, self._reservation = request, reservation
        self._dataset, self._context, self._count = dataset_id, context, confirmed_count
        self._closed = self._used = False
        self._pid, self._thread = os.getpid(), threading.current_thread()
        self._digest = upload_request_digest(
            port._plan.digest,
            kind,
            None if context is None else context.file_index,
            None if context is None else context.file,
            dataset_id,
            context.local_binding if context is not None and kind == "confirm" else None,
        )

    def close(self) -> None:
        self._owner()
        if not self._closed:
            if not self._reservation._closed:
                self._reservation.finish()
            self._closed = True

    def _owner(self) -> None:
        if os.getpid() != self._pid or threading.current_thread() is not self._thread:
            raise YorungeError("invalid_request")

    def _arm(self, arm: UploadArm) -> StageIntent:
        if type(arm) is not UploadArm or self._closed or self._used:
            raise YorungeError("invalid_request")
        intent = arm.intent
        if (
            intent.operation_id != self._operation
            or intent.kind != self._kind
            or intent.file_index != (None if self._context is None else self._context.file_index)
            or intent.request_digest != self._digest
        ):
            raise YorungeError("invalid_request")
        return intent

    async def execute(self, client: UploadHttpxTransport, arm: UploadArm) -> ControlOutcome:
        self._owner()
        try:
            self._port._client(client)
            if self._context is not None:
                self._port._file(self._context)
            self._arm(arm)
            intent, permit, deadline = arm.claim()
            self._used = True
            async with client.open_budgeted(
                self._request, self._reservation, deadline=deadline, permit=permit
            ) as response:
                raw = b"".join([part async for part in response.chunks()])
            return self._outcome(intent, raw)
        finally:
            self.close()

    def _outcome(self, intent: StageIntent, raw: bytes) -> ControlOutcome:
        port, secret = self._port, self._port._credential.secret
        if self._context is not None:
            port._file(self._context)
        at = port._now()
        if self._kind == "create":
            created = codec.created(raw, port._scope, port._plan.parameters, secret)
            return ControlOutcome(
                CreateReceiptV2(
                    schema_version=2,
                    intent_id=intent.intent_id,
                    recorded_at=at,
                    result="accepted",
                    dataset_id=created.id,
                    object_key=None,
                    sent_bytes=None,
                    sent_sha256=None,
                    created_dataset=created,
                )
            )
        upload = None
        if self._kind == "project_link":
            codec.link_ack(raw, secret)
        elif self._kind == "presign":
            assert self._context is not None
            upload = descriptors.presigned(raw, self._context, secret)
        else:
            assert self._count is not None
            metadata.confirm_ack(raw, self._count, secret)
        return ControlOutcome(
            StageReceipt(
                schema_version=1,
                intent_id=intent.intent_id,
                recorded_at=at,
                result="accepted",
                dataset_id=self._dataset,
                object_key=None if self._context is None else self._context.local_binding,
                sent_bytes=None,
                sent_sha256=None,
            ),
            upload,
        )


class ObservedUploadPort(_Private):
    def __init__(
        self,
        plan: DatasetUploadPlanV2,
        manifest: DatasetManifest,
        scope: UploadScope,
        bound: BoundCredential,
        credential: HttpCredential,
        budget: UploadBudget,
        *,
        utc_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._plan = revalidate_input(DatasetUploadPlanV2, plan)
        self._manifest = revalidate_input(DatasetManifest, manifest)
        self._scope = revalidate_input(UploadScope, scope)
        self._bound(bound, credential)
        valid = True
        try:
            for value in (self._plan, self._manifest, self._scope):
                check_response_secrets(value, (credential.secret,))
        except YorungeError:
            valid = False
        if not valid:
            raise YorungeError("invalid_request")
        if type(budget) is not UploadBudget:
            raise YorungeError("invalid_request")
        _ = budget.end
        if (
            budget._limits != self._plan.request_limits
            or manifest_reference(self._manifest) != self._plan.manifest
            or scope_target(self._scope) != scope_target(self._plan.scope)
        ):
            raise YorungeError("invalid_request")
        if self._plan.storage.mode != "proxy":
            raise YorungeError("unsupported_combination")
        self._credential, self._budget = credential, budget
        self._clock = utc_clock or (lambda: datetime.now(UTC))
        self._files: tuple[descriptors.FileContext, ...] = ()

    def _bound(self, bound: BoundCredential, credential: HttpCredential) -> None:
        if (
            type(bound) is not BoundCredential
            or type(bound.credential) is not ResolvedCredential
            or type(bound.credential.secret) is not SecretValue
            or type(credential) is not HttpCredential
        ):
            raise YorungeError("invalid_request")
        identity = revalidate_input(CredentialIdentity, bound.identity)
        context = revalidate_input(Context, bound.context)
        reference = revalidate_input(EnvReference, bound.credential.reference)
        target = revalidate_input(ServiceTarget, bound.credential.target)
        scope = self._scope
        if (
            credential.secret is not bound.credential.secret
            or credential.target != target
            or credential.service_id != "evren-platform"
            or credential.header_name.lower() != "x-api-key"
            or credential.prefix != ""
            or reference.service_id != "evren-platform"
            or normalize_target(context.platform_url) != target
            or context.profile != scope.profile
            or (target.service_origin, target.api_base_path)
            != (scope.service_origin, scope.api_base_path)
            or (identity.credential_id, identity.credential_revision, identity.identity_epoch)
            != (scope.credential_id, scope.credential_revision, scope.identity_epoch)
        ):
            raise YorungeError("invalid_request")
        if (target.service_origin, target.api_base_path) != ("https://api.ssyz.org.tr", "/api/v1"):
            raise YorungeError("unsupported_combination")

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

    def _write(self) -> None:
        _ = self._budget.end
        if (
            self._scope != self._plan.scope
            or self._budget._readonly
            or self._plan.status == "draft"
        ):
            raise YorungeError("upload_plan_not_valid")

    def files(self, operation_id: str, dataset_id: str) -> tuple[descriptors.FileContext, ...]:
        self._write()
        key = (_operation(operation_id), codec.segment(dataset_id, self._credential.secret))
        if self._files and (self._files[0].operation_id, self._files[0].dataset_id) != key:
            raise YorungeError("invalid_request")
        if not self._files:
            self._files = descriptors.contexts(
                self._plan, self._manifest, *key, self._credential.secret
            )
        return self._files

    def _file(self, context: descriptors.FileContext) -> None:
        if type(context) is not descriptors.FileContext:
            raise YorungeError("invalid_request")
        owned = self._files
        if (
            type(context.file_index) is not int
            or not 0 <= context.file_index < len(owned)
            or owned[context.file_index] is not context
            or revalidate_input(ServiceTarget, context.target) != self._credential.target
            or revalidate_input(DatasetFile, context.file)
            != self._manifest.files[context.file_index]
        ):
            raise YorungeError("invalid_request")

    def _prepare(
        self,
        operation_id: str,
        kind: ControlKind,
        endpoint: str,
        body: bytes,
        *,
        dataset_id: str | None = None,
        context: descriptors.FileContext | None = None,
        confirmed_count: int | None = None,
    ) -> PreparedUploadCall:
        self._write()
        operation_id = _operation(operation_id)
        request = HttpRequest(
            self._credential.target,
            "POST",
            endpoint,
            content=body,
            headers=(("Content-Type", "application/json"),),
            credential=self._credential,
            service_id="evren-platform",
            upload_endpoint=kind,
        )
        reserved = self._budget.reserve(
            kind, request_bytes=len(body), response_bytes=request.max_bytes
        )
        return PreparedUploadCall(
            self, operation_id, kind, request, reserved, dataset_id, context, confirmed_count
        )

    def prepare_create(self, operation_id: str) -> PreparedUploadCall:
        return self._prepare(
            operation_id,
            "create",
            "datasets",
            codec.create_content(self._scope, self._plan.parameters, self._credential.secret),
        )

    def prepare_link(self, operation_id: str, dataset_id: str) -> PreparedUploadCall:
        secret = self._credential.secret
        path = codec.segment(self._scope.project_id, secret)
        return self._prepare(
            operation_id,
            "project_link",
            f"projects/{path}/datasets",
            codec.link_content(dataset_id, secret),
            dataset_id=dataset_id,
        )

    def prepare_presign(self, context: descriptors.FileContext) -> PreparedUploadCall:
        self._file(context)
        path = codec.segment(context.dataset_id, self._credential.secret)
        return self._prepare(
            context.operation_id,
            "presign",
            f"datasets/{path}/upload/presign",
            descriptors.presign_content(context, self._credential.secret),
            dataset_id=context.dataset_id,
            context=context,
        )

    def prepare_confirm(
        self, upload: descriptors.PresignedUpload, *, confirmed_count: int
    ) -> PreparedUploadCall:
        if type(upload) is not descriptors.PresignedUpload:
            raise YorungeError("invalid_request")
        context = upload.context
        self._file(context)
        if type(confirmed_count) is not int or not 1 <= confirmed_count <= context.file_count:
            raise YorungeError("invalid_request")
        path = codec.segment(context.dataset_id, self._credential.secret)
        return self._prepare(
            context.operation_id,
            "confirm",
            f"datasets/{path}/upload/confirm",
            descriptors.confirm_content(upload, context, self._credential.secret),
            dataset_id=context.dataset_id,
            context=context,
            confirmed_count=confirmed_count,
        )

    def prepare_put(self, upload: descriptors.PresignedUpload) -> PreparedPutCall:
        from yorunge.adapters.platform_upload_put import PreparedPutCall

        return PreparedPutCall(self, upload)

    async def items(
        self, client: UploadHttpxTransport, dataset_id: str, *, deadline: float
    ) -> tuple[VerifiedFile, ...]:
        from yorunge.adapters.platform_upload_items import read_items

        return await read_items(self, client, dataset_id, deadline=deadline)
