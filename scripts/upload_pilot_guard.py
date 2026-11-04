"""Additional one-process pilot ceilings; delegate every production ownership and byte gate."""

from __future__ import annotations

import runpy
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

from yorunge.adapters.platform_upload_port import PreparedUploadCall
from yorunge.adapters.platform_upload_put import PreparedPutCall
from yorunge.application import upload_metadata_codec as metadata
from yorunge.application.http_transport import HttpStatusFailure
from yorunge.application.upload_budget import UploadBudget, UploadReservation
from yorunge.domain.errors import YorungeError

LIMITS = {
    "read": 40,
    "read_attempts": 80,
    "create": 1,
    "project_link": 1,
    "presign": 3,
    "put": 3,
    "confirm": 3,
    "effect_attempts": 11,
    "request_bytes": 65_536,
    "response_bytes": 16_777_216,
    "upload_bytes": 1_048_576,
    "seconds": 180,
}
TRACE = runpy.run_path(str(Path(__file__).with_name("upload_control_trace.py")))


class PilotGuard:
    """Conservative cross-invocation claims; never returns a permit or changes a target."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.end = self.started + LIMITS["seconds"]
        self.counts = dict.fromkeys(LIMITS, 0)
        self.budgets: set[UploadBudget] = set()
        self.pending: dict[UploadReservation, int] = {}
        self.response_claims = 0
        self.controls: list[dict[str, Any]] = []
        self.active_controls: dict[Any, dict[str, Any]] = {}
        self.put_context: ContextVar[Any] = ContextVar("pilot_put_trace", default=None)

    def current(self) -> None:
        if time.monotonic() >= self.end:
            raise YorungeError("execution_timeout")

    def claim(self, name: str, size: int = 1) -> None:
        self.current()
        if type(size) is not int or size < 0 or self.counts[name] + size > LIMITS[name]:
            raise YorungeError("upload_limit_exceeded")
        self.counts[name] += size

    def require(self, reservation: UploadReservation) -> None:
        if reservation not in self.pending or reservation._budget not in self.budgets:
            raise YorungeError("invalid_request")

    def reserve(self, delegate: Any, budget: UploadBudget, kind: str, **sizes: int) -> Any:
        if budget not in self.budgets:
            raise YorungeError("invalid_request")
        response = sizes.get("response_bytes", 1_048_576)
        self.claim(kind)
        self.claim("request_bytes", sizes.get("request_bytes", 0))
        self.claim("upload_bytes", sizes.get("upload_bytes", 0))
        if (
            self.counts["response_bytes"] + self.response_claims + response
            > LIMITS["response_bytes"]
        ):
            raise YorungeError("upload_limit_exceeded")
        reserved = delegate(budget, kind, **sizes)
        self.pending[reserved] = response
        self.response_claims += response
        return reserved

    def snapshot(self) -> dict[str, Any]:
        actual = [asdict(budget.snapshot()) for budget in self.budgets]
        return {
            "claims": dict(self.counts),
            "actual": {name: sum(row[name] for row in actual) for name in actual[0]}
            if actual
            else {},
            "response_pending": self.response_claims,
            "open_reservations": len(self.pending),
            "elapsed_seconds": time.monotonic() - self.started,
            "control_responses": list(self.controls),
        }

    def _control_trace_methods(self, execute: Any, outcome: Any) -> tuple[Any, Any]:
        async def executed(call: Any, client: Any, arm: Any) -> Any:
            row = {"kind": call._kind, "http_status": None, "typed_accepted": False}
            self.controls.append(row)
            self.active_controls[call] = row
            try:
                result = await execute(call, client, arm)
                row["typed_accepted"] = True
                return result
            except HttpStatusFailure as error:
                row["http_status"] = error.status_code
                raise
            except YorungeError as error:
                row["error_code"] = error.code
                raise
            finally:
                self.active_controls.pop(call, None)

        def observed(call: Any, intent: Any, raw: bytes) -> Any:
            expected = {"dataset_id": call._dataset, "project_id": call._port._scope.project_id}
            expected.update(
                created=1,
                actual_count=None if call._count is None else call._count + 1,
                batch_duplicates=0,
            )
            row = self.active_controls[call]
            row["transport_2xx_accepted"] = True
            row["body_bytes"] = len(raw)
            row["shape"] = TRACE["body_shape"](raw, expected)
            return outcome(call, intent, raw)

        return executed, observed

    def _put_trace_methods(self, put_execute: Any, put_ack: Any) -> tuple[Any, Any]:
        async def put_executed(call: Any, client: Any, arm: Any) -> Any:
            row: dict[str, Any] = {
                "kind": "put",
                "file_index": call._context.file_index,
                "http_status": None,
                "typed_accepted": False,
            }
            self.controls.append(row)
            file = call._context.file
            expected = {
                "dataset_id": call._context.dataset_id,
                "file_size": file.size,
                "size": file.size,
                "bytes_written": file.size,
                "sha256_hash": file.sha256,
            }
            token = self.put_context.set((row, expected))
            try:
                result = await put_execute(call, client, arm)
                row["typed_accepted"] = True
                return result
            except HttpStatusFailure as error:
                row["http_status"] = error.status_code
                raise
            except YorungeError as error:
                row["error_code"] = error.code
                raise
            finally:
                self.put_context.reset(token)

        def put_observed(raw: bytes, secret: Any, **kwargs: Any) -> None:
            current = self.put_context.get()
            if current is not None:
                row, expected = current
                row.update(
                    transport_2xx_accepted=True,
                    body_bytes=len(raw),
                    shape=TRACE["body_shape"](raw, expected),
                )
            put_ack(raw, secret, **kwargs)

        return put_executed, put_observed

    @contextmanager
    def install(self) -> Iterator[None]:
        initialize, reserve = UploadBudget.__init__, UploadBudget.reserve
        attempt, response = UploadReservation.attempt, UploadReservation.response
        upload, finish = UploadReservation.upload, UploadReservation.finish
        execute, outcome = PreparedUploadCall.execute, PreparedUploadCall._outcome
        put_execute, put_ack = PreparedPutCall.execute, metadata.put_ack

        executed, observed = self._control_trace_methods(execute, outcome)
        put_executed, put_observed = self._put_trace_methods(put_execute, put_ack)

        def initialized(budget: UploadBudget, limits: Any, *, end: float, read_only: bool) -> None:
            self.current()
            initialize(budget, limits, end=min(end, self.end), read_only=read_only)
            self.budgets.add(budget)

        def reserved(budget: UploadBudget, kind: str, **sizes: int) -> Any:
            return self.reserve(reserve, budget, kind, **sizes)

        def attempted(reservation: UploadReservation) -> None:
            self.require(reservation)
            self.claim("read_attempts" if reservation._kind == "read" else "effect_attempts")
            attempt(reservation)

        def responded(reservation: UploadReservation, size: int) -> None:
            self.require(reservation)
            response(reservation, size)
            self.pending[reservation] -= size
            self.response_claims -= size
            self.counts["response_bytes"] += size

        def uploaded(reservation: UploadReservation, size: int) -> None:
            self.require(reservation)
            upload(reservation, size)

        def finished(reservation: UploadReservation) -> None:
            self.require(reservation)
            finish(reservation)
            self.response_claims -= self.pending.pop(reservation)

        patches = (
            (UploadBudget, "__init__", initialized),
            (UploadBudget, "reserve", reserved),
            (UploadReservation, "attempt", attempted),
            (UploadReservation, "response", responded),
            (UploadReservation, "upload", uploaded),
            (UploadReservation, "finish", finished),
            (PreparedUploadCall, "execute", executed),
            (PreparedUploadCall, "_outcome", observed),
            (PreparedPutCall, "execute", put_executed),
            (metadata, "put_ack", put_observed),
        )
        with ExitStack() as stack:
            for kind, name, method in patches:
                stack.enter_context(patch.object(kind, name, method))
            yield
