"""Lazy bounded PUT from an approved file; raw descriptor stays volatile."""

from __future__ import annotations

import os
import sys
import threading

from yorunge.adapters.platform_upload_port import ControlOutcome, ObservedUploadPort, _Private
from yorunge.adapters.storage_source import DescriptorByteSource
from yorunge.adapters.upload_http import UploadHttpxTransport
from yorunge.application import upload_descriptors as descriptors
from yorunge.application import upload_metadata_codec as metadata
from yorunge.application.storage import StorageRequest
from yorunge.application.upload_arms import UploadArm
from yorunge.domain.dataset_transfer import StageReceipt
from yorunge.domain.errors import YorungeError
from yorunge.domain.upload_requests import upload_request_digest


class PreparedPutCall(_Private):
    def __init__(self, port: ObservedUploadPort, upload: descriptors.PresignedUpload) -> None:
        port._write()
        if type(upload) is not descriptors.PresignedUpload:
            raise YorungeError("invalid_request")
        context = upload.context
        port._file(context)
        # Recheck nested target models as well as the frozen outer descriptor.
        descriptors.PresignedUpload(
            context, upload.provider_key, upload.target, upload.content_type
        )
        self._port, self._context = port, context
        self._source = DescriptorByteSource(
            port._plan.root, context.file, deadline=port._budget.end
        )
        self._request = StorageRequest(
            upload.target,
            self._source,
            port._credential.secret,
            upload.content_type,
            credential=port._credential,
        )
        self._digest = upload_request_digest(
            port._plan.digest,
            "put",
            context.file_index,
            context.file,
            context.dataset_id,
            context.local_binding,
        )
        self._reservation = port._budget.reserve(
            "put", upload_bytes=self._request.size, response_bytes=self._request.max_bytes
        )
        self._pid, self._thread = os.getpid(), threading.current_thread()
        self._closed = self._used = False

    def _owner(self) -> None:
        if os.getpid() != self._pid or threading.current_thread() is not self._thread:
            raise YorungeError("invalid_request")

    async def aclose(self) -> None:
        self._owner()
        if self._closed:
            return
        self._closed = True
        pending, failed = sys.exc_info()[0] is not None, False
        try:
            await self._source.aclose()
        except (OSError, YorungeError):
            failed = True
        finally:
            try:
                if not self._reservation._closed:
                    self._reservation.finish()
            except YorungeError:
                failed = True
        if failed and not pending:
            raise YorungeError("transport_failed")

    async def execute(self, client: UploadHttpxTransport, arm: UploadArm) -> ControlOutcome:
        self._owner()
        try:
            self._port._client(client)
            self._port._file(self._context)
            if type(arm) is not UploadArm or self._closed or self._used:
                raise YorungeError("invalid_request")
            intent = arm.intent
            context = self._context
            if (
                intent.operation_id != context.operation_id
                or intent.kind != "put"
                or intent.file_index != context.file_index
                or intent.request_digest != self._digest
            ):
                raise YorungeError("invalid_request")
            intent, permit, deadline = arm.claim()
            self._used = True
            self._source.restrict_deadline(deadline)
            async with client.open_storage_budgeted(
                self._request, self._reservation, deadline=deadline, permit=permit
            ) as response:
                raw = b"".join([part async for part in response.chunks()])
                sent = response.sent_bytes, response.sent_sha256
            self._port._file(context)
            if (
                sent != (context.file.size, context.file.sha256)
                or not self._source.complete
                or (self._source.sent_bytes, self._source.sent_sha256) != sent
            ):
                raise YorungeError("input_changed")
            metadata.put_ack(raw, self._port._credential.secret)
            return ControlOutcome(
                StageReceipt(
                    schema_version=1,
                    intent_id=intent.intent_id,
                    recorded_at=self._port._now(),
                    result="accepted",
                    dataset_id=context.dataset_id,
                    object_key=context.local_binding,
                    sent_bytes=sent[0],
                    sent_sha256=sent[1],
                )
            )
        finally:
            await self.aclose()
