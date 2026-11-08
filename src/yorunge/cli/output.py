"""UTF-8 output and the CLI's single-owner result/event renderer.

Metadata uses only the standard-library writer. Event models and the bounded
codec are loaded only by explicit NDJSON rendering.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, BinaryIO, TextIO, TypeVar

if TYPE_CHECKING:
    from pydantic import BaseModel

    from yorunge.domain.errors import ErrorCode, YorungeError
    from yorunge.domain.models import Result
    from yorunge.domain.streams import StreamEvent

T = TypeVar("T", bound="BaseModel")


def write_utf8(message: str | bytes, stream: TextIO) -> None:
    """Write and flush a complete message, independent of stdio's encoding.

    StringIO and other text-only in-process sinks retain their normal interface.
    A short/zero write is never mistaken for successful delivery.
    """
    if stream is None:
        raise OSError("output stream is unavailable")
    binary = getattr(stream, "buffer", None)
    if binary is not None:
        _write_binary(message, binary)
    else:
        _write_text(message, stream)


def _write_binary(message: str | bytes, stream: BinaryIO) -> None:
    pending = memoryview(message.encode("utf-8", "strict") if isinstance(message, str) else message)
    while pending:
        written = stream.write(pending)
        if type(written) is not int or written <= 0 or written > len(pending):
            raise OSError("incomplete output write")
        pending = pending[written:]
    stream.flush()


def _write_text(message: str | bytes, stream: TextIO) -> None:
    text = message.decode("utf-8", "strict") if isinstance(message, bytes) else message
    while text:
        written = stream.write(text)
        if type(written) is not int or written <= 0 or written > len(text):
            raise OSError("incomplete output write")
        text = text[written:]
    stream.flush()


def _silence_failed_descriptor(stream: TextIO) -> None:
    """Prevent interpreter shutdown from retrying a confirmed failed stdio sink."""
    if not any(stream is item for item in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)):
        return
    try:
        descriptor = stream.fileno()
        replacement = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(replacement, descriptor)
        finally:
            os.close(replacement)
    except (OSError, ValueError, AttributeError):
        pass


class OutputRenderer:
    """Render one invocation without retries or mutation of its business result.

    Trusted compositions supply their already bound stream/operation identities,
    call event() for each typed event and finish() after source completion.
    The normal CLI calls result() once. error() is the CLI boundary and returns
    the controlled exit code; it never propagates a secondary output failure.
    """

    def __init__(
        self,
        output: str = "text",
        *,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
        stream_id: str | None = None,
        operation_id: str | None = None,
        upload_guidance: bool = False,
        error_hints: Mapping[str, str | Callable[[YorungeError], str | None]] | None = None,
        requested_operation_id: str | None = None,
    ) -> None:
        self.output = output
        self._upload_guidance = upload_guidance
        # The operation the person asked about, so that an error naming another one (the successor
        # of a source, the running one that blocks it) is not mistaken for it (text output only).
        self._requested = requested_operation_id
        # What a person is told on top of the fixed message, for the codes this command can meet
        # in its own way (text output only; the machine envelope never changes).
        self._error_hints = error_hints or {}
        self.stdout = sys.stdout if stdout is None else stdout
        self.stderr = sys.stderr if stderr is None else stderr
        if stream_id is not None or operation_id is not None:
            from yorunge.domain.errors import YorungeError
            from yorunge.domain.state import canonical_uuid

            valid = False
            try:
                for identity in (stream_id, operation_id):
                    if identity is not None:
                        canonical_uuid(identity)
                valid = True
            except Exception:
                pass
            if not valid:
                raise YorungeError("invalid_request")
        self._stream_id, self.operation_id = stream_id, operation_id
        self._sequence = 1
        self._published = False
        self._terminal = False
        self._output_failed = False
        self._reported = False
        self._exit_code = 0

    @property
    def stream_id(self) -> str:
        if self._stream_id is None:
            from uuid import uuid4

            self._stream_id = str(uuid4())
        return self._stream_id

    def _failure(self, code: ErrorCode) -> YorungeError:
        from yorunge.domain.errors import OperationError, YorungeError

        return (
            OperationError(code, self.operation_id)
            if self.operation_id is not None
            else YorungeError(code)
        )

    def output_failure(self, error: OSError | UnicodeError | ValueError) -> YorungeError:
        """Map a failed stdout write, including argparse metadata output."""
        self._output_failed = True
        if isinstance(error, OSError):
            _silence_failed_descriptor(self.stdout)
        return self._failure(
            "output_closed" if isinstance(error, BrokenPipeError) else "output_write_failed"
        )

    def _write_stdout(self, message: str | bytes) -> None:
        if self._output_failed:
            raise self._failure("output_write_failed")
        failure: YorungeError | None = None
        try:
            write_utf8(message, self.stdout)
        except (OSError, ValueError) as error:
            failure = self.output_failure(error)
        except KeyboardInterrupt:
            # An interrupted write may already have delivered a partial record.
            # It cannot be followed by an error record on the same stdout line.
            self._output_failed = True
            _silence_failed_descriptor(self.stdout)
            raise
        if failure is not None:
            raise failure
        self._published = True

    def result(self, result: Result[T], *, text: str | None = None) -> None:
        if self.output == "ndjson":
            from yorunge.domain.streams import result_event

            event = None
            try:
                event = result_event(
                    result,
                    stream_id=self.stream_id,
                    sequence=self._sequence,
                    operation_id=self.operation_id,
                )
            except Exception:
                pass
            if event is None:
                raise self._failure("output_write_failed")
            self.event(event)
            self.finish()
        else:
            message = None
            try:
                message = result.model_dump_json() if self.output == "json" else text or ""
            except Exception:
                pass
            if message is None:
                raise self._failure("output_write_failed")
            self._write_stdout(message + "\n")

    def event(self, event: StreamEvent[T]) -> None:
        from yorunge.application.stream_results import encode_event
        from yorunge.domain.streams import EventMeta

        valid = False
        try:
            meta = EventMeta.model_validate(
                {
                    name: getattr(event, name)
                    for name in ("schema_version", "stream_id", "sequence", "event", "operation_id")
                },
                strict=True,
            )
            valid = (
                self.output == "ndjson"
                and not self._terminal
                and not self._output_failed
                and meta.stream_id == self.stream_id
                and meta.operation_id == self.operation_id
                and meta.sequence == self._sequence
            )
        except Exception:
            pass
        if not valid:
            raise self._failure("invalid_response")
        encoded = encode_event(event)
        self._write_stdout(encoded)
        self._sequence += 1
        self._terminal = meta.event != "progress"
        if meta.event == "error":
            from yorunge.domain.errors import YorungeError
            from yorunge.domain.streams import ErrorEvent

            assert isinstance(event, ErrorEvent)
            self._exit_code = YorungeError(event.payload.code).exit_code

    def finish(self) -> int:
        if self.output == "ndjson" and not self._terminal:
            raise self._failure("stream_interrupted")
        return self._exit_code

    def _bound_error(self, error: YorungeError) -> YorungeError:
        from yorunge.domain.errors import OperationError

        if self.operation_id is None:
            return error
        if isinstance(error, OperationError):
            if error.operation_id not in (None, self.operation_id):
                return self._failure("invalid_response")
            return OperationError(
                error.code,
                self.operation_id,
                reason_code=error.reason_code,
                capacity_kind=error.capacity_kind,
                blockers=error.blockers,
            )
        return self._failure(error.code)

    @staticmethod
    def _blockers_text(blockers: tuple[str, ...], operation_id: str) -> str:
        """Why a continuation was refused: a sentence of reason and one of next step for each."""
        from yorunge.cli.upload import BLOCKER_TEXT

        lines: list[str] = []
        for name in blockers:
            reason, step = BLOCKER_TEXT[name]
            lines.extend((f"- {name}: {reason}", f"  Sonraki adım: {step}"))
        lines.append(
            f"Rapor: yorunge datasets upload resume --operation-id {operation_id} "
            "--accept-unverified-read"
        )
        return "\n" + "\n".join(lines)

    def _stderr_error(self, error: YorungeError) -> None:
        message = (
            json.dumps(error.envelope(), ensure_ascii=False)
            if self.output in ("json", "ndjson")
            else error.message
        )
        if self.output == "text":
            from yorunge.domain.errors import OperationError

            hint = self._error_hints.get(error.code)
            if callable(hint):
                hint = hint(error)
            if hint:
                message += "\n" + hint
            if isinstance(error, OperationError) and error.operation_id is not None:
                message += f"\nİş: {error.operation_id}"
                if (
                    error.code == "operation_conflict"
                    and self._requested is not None
                    and error.operation_id.lower() != self._requested.lower()
                ):
                    message += (
                        f"\nİstediğiniz iş {self._requested} değil; yukarıdaki iş ona bağlı "
                        "(devamı ya da onu engelleyen iş). Önce onun durumuna bakın."
                    )
                if error.blockers:
                    message += self._blockers_text(error.blockers, error.operation_id)
                elif self._upload_guidance:
                    message += (
                        "\nİncele: yorunge datasets upload show --operation-id "
                        f"{error.operation_id}\nAynı --state-dir seçimini koruyun; "
                        "yeni plan/ad/store ile tekrar göndermeyin."
                    )
        try:
            write_utf8(message + "\n", self.stderr)
        except (OSError, ValueError):
            _silence_failed_descriptor(self.stderr)

    def error(self, error: YorungeError) -> int:
        from yorunge.domain.errors import OperationError

        try:
            return self._report_error(error)
        except KeyboardInterrupt:
            # A second SIGINT during best-effort reporting must not hide an
            # already known operation failure or uncertain write. The cached
            # exit also preserves a rejected/mismatched operation identity.
            self._reported = True
            known = (
                error.exit_code == 5
                or isinstance(error, OperationError)
                or self.operation_id is not None
            )
            self._exit_code = (self._exit_code or error.exit_code) if known else 6
            return self._exit_code

    def _publish_error(self, error: YorungeError) -> YorungeError | None:
        from yorunge.domain.streams import ErrorEvent, error_payload

        failure: YorungeError | None = None
        try:
            self.event(
                ErrorEvent(
                    schema_version=1,
                    stream_id=self.stream_id,
                    sequence=self._sequence,
                    event="error",
                    operation_id=self.operation_id,
                    payload=error_payload(error, operation_id=self.operation_id),
                )
            )
        except Exception as secondary:
            from yorunge.domain.errors import YorungeError

            failure = (
                secondary
                if isinstance(secondary, YorungeError)
                else self._failure("output_write_failed")
            )
        return failure

    def _report_error(self, error: YorungeError) -> int:
        error = self._bound_error(error)
        if self._reported:
            return self._exit_code
        self._reported = True
        self._exit_code = error.exit_code
        if self.output == "ndjson" and self._published and not self._output_failed:
            if not self._terminal:
                failure = self._publish_error(error)
                if failure is not None:
                    if error.exit_code != 5:
                        error = failure
                    self._stderr_error(error)
        else:
            self._stderr_error(error)
        self._exit_code = error.exit_code
        return self._exit_code
