"""Installed-only TLS transport acceptance; never a selectable product backend."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import importlib.util
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

# The checkout supplies test helpers only. Never add src or package fallbacks:
# every product module must resolve from the explicitly selected installation.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.fixtures.http_server import (  # noqa: E402
    LoopbackTransport,
    Reply,
    TlsServer,
    certificate,
    loopback_sockets,
)

STREAM = "1923801e-38d9-4790-9001-7139be4d9d1d"
OPERATION = "74c1fc7b-65fb-42ef-8768-3d09a1b44aeb"
TEXT = "Kurulu Türkçe 🛰\nikinci satır"
CASES = ("http", "http-invalid", "stream", "stream-trailing", "stream-truncated")
REQUIRED_MODULES = {
    "yorunge",
    "yorunge.adapters.http_transport",
    "yorunge.application.http_transport",
    "yorunge.application.response_json",
    "yorunge.application.stream_results",
    "yorunge.cli.output",
    "yorunge.domain.credentials",
    "yorunge.domain.errors",
    "yorunge.domain.models",
    "yorunge.domain.streams",
}


def installed_origins(venv: Path) -> dict[str, object]:
    """Reject editable/source or foreign-prefix imports, including lazy modules."""
    expected = venv.resolve()
    if Path(sys.prefix).resolve() != expected:
        raise ValueError("installed interpreter prefix mismatch")
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "yorunge" or name.startswith("yorunge."):
            origin = getattr(module, "__file__", None)
            if origin is None or not Path(origin).resolve().is_relative_to(expected):
                raise ValueError("product import outside installed environment: " + name)
            origins[name] = str(Path(origin).resolve())
    if not REQUIRED_MODULES.issubset(origins):
        raise ValueError("installed transport modules were not exercised")
    distribution = importlib.metadata.distribution("yorunge")
    metadata = Path(distribution.locate_file("")).resolve()
    if not metadata.is_relative_to(expected):
        raise ValueError("distribution metadata outside installed environment")
    dependencies = distribution.requires or []
    if not any(value.lower().startswith("httpx") for value in dependencies):
        raise ValueError("installed distribution does not declare HTTPX")
    if importlib.util.find_spec("pytest") is not None:
        raise ValueError("installed smoke requires runtime-only environment")
    return {"modules": origins, "metadata": str(metadata), "version": distribution.version}


def result_payload() -> dict[str, object]:
    # An independent wire oracle, without importing product encoders/models.
    return {
        "schema_version": 1,
        "operation_id": None,
        "status": "completed",
        "data": {"text": TEXT},
        "warnings": [],
    }


def event(sequence: int, kind: str, payload: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "stream_id": STREAM,
        "sequence": sequence,
        "event": kind,
        "operation_id": OPERATION,
        "payload": payload,
    }


def progress() -> dict[str, object]:
    return event(1, "progress", {"stage": "receiving", "completed": 1, "total": 2})


def wire(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


async def consume(case: str, ca: Path, port: int, renderer: object) -> int:
    from yorunge.adapters.http_transport import HttpxTransport
    from yorunge.application.http_transport import RAW_LIMIT, HttpRequest
    from yorunge.application.response_json import decode_response
    from yorunge.application.stream_results import open_stream
    from yorunge.domain.credentials import normalize_target
    from yorunge.domain.models import Model, Result

    class Value(Model):
        text: str

    request = HttpRequest(
        normalize_target("https://localhost/v1"),
        "GET",
        case,
        service_id="evren-platform",
        max_bytes=RAW_LIMIT if case.startswith("stream") else 1024,
    )
    context = ssl.create_default_context(cafile=str(ca))
    async with HttpxTransport(transport=LoopbackTransport(port, context)) as transport:
        if case.startswith("http"):
            async with transport.open(request, deadline=time.monotonic() + 5) as response:
                data = bytearray()
                async for chunk in response.chunks():
                    data.extend(chunk)
                value = decode_response(bytes(data), Value)
            renderer.result(Result[Value](data=value))
            return 0
        async with open_stream(
            transport,
            request,
            Value,
            deadline=time.monotonic() + 5,
            stream_id=STREAM,
            operation_id=OPERATION,
        ) as stream:
            async for item in stream:
                renderer.event(item)
    return renderer.finish()


def worker(args: argparse.Namespace) -> int:
    if not sys.flags.isolated:
        raise ValueError("installed smoke requires isolated Python")
    # Import the full exercised surface before accepting the prefix. Recheck
    # after consumption to include modules imported lazily by HTTP/renderer.
    from yorunge.adapters import http_transport  # noqa: F401
    from yorunge.application import response_json, stream_results  # noqa: F401
    from yorunge.cli.output import OutputRenderer
    from yorunge.domain.errors import YorungeError

    installed_origins(args.venv)
    streaming = args.case.startswith("stream")
    renderer = OutputRenderer(
        "ndjson" if streaming else "json",
        stream_id=STREAM if streaming else None,
        operation_id=OPERATION if streaming else None,
    )
    try:
        with loopback_sockets(socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo):
            code = asyncio.run(consume(args.case, args.ca, args.port, renderer))
    except YorungeError as error:
        code = renderer.error(error)
    args.origins.write_text(json.dumps(installed_origins(args.venv)), encoding="utf-8")
    return code


def verify_output(case: str, code: int, stdout: bytes, stderr: bytes) -> None:
    """Prove typed failure and never publish a fake completed stream terminal."""
    if case == "http":
        if code != 0 or stderr or stdout != wire(result_payload()):
            raise ValueError("installed typed HTTP result failed")
        return
    if case == "http-invalid":
        if code != 1 or stdout or not stderr.endswith(b"\n") or stderr.count(b"\n") != 1:
            raise ValueError("installed malformed JSON output boundary failed")
        envelope = json.loads(stderr)
        if (
            set(envelope)
            != {"schema_version", "code", "message", "operation_id", "retryable", "details"}
            or type(envelope["schema_version"]) is not int
            or envelope["schema_version"] != 1
            or envelope["code"] != "invalid_response"
            or envelope["operation_id"] is not None
            or envelope["retryable"] is not False
            or envelope["details"] != {}
        ):
            raise ValueError("installed malformed JSON was not rejected")
        return
    if stderr or not stdout.endswith(b"\n") or stdout.count(b"\n") != 2:
        raise ValueError("installed stream output boundary failed")
    records = [json.loads(line) for line in stdout.splitlines()]
    if stdout.splitlines(keepends=True)[0] != wire(progress()):
        raise ValueError("installed stream progress changed")
    if case == "stream":
        if code != 0 or stdout != wire(progress()) + wire(event(2, "result", result_payload())):
            raise ValueError("installed stream result failed")
        return
    expected = "invalid_response" if case == "stream-trailing" else "stream_interrupted"
    terminal = records[1]
    payload = terminal.get("payload", {})
    if (
        code != 1
        or terminal != event(2, "error", payload)
        or type(terminal["schema_version"]) is not int
        or type(terminal["sequence"]) is not int
        or set(payload)
        != {"schema_version", "code", "message", "operation_id", "retryable", "details"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or payload["code"] != expected
        or payload["operation_id"] != OPERATION
        or payload["retryable"] is not False
        or payload["details"] != {"reason_code": expected, "capacity_kind": None}
        or b'"status":"completed"' in stdout
    ):
        raise ValueError("installed corrupt stream published a false result")


def verify(python: Path, venv: Path, scratch: Path) -> dict[str, str]:
    body = wire(progress()) + wire(event(2, "result", result_payload()))
    routes = {
        "/v1/http": Reply(body=wire({"text": TEXT}), chunk_size=3),
        "/v1/http-invalid": Reply(body=b'{"text":17}', chunk_size=2),
        "/v1/stream": Reply(body=body, chunk_size=7),
        "/v1/stream-trailing": Reply(body=body + b" ", chunk_size=7),
        # A complete terminal frame in an incomplete HTTP message is not success.
        "/v1/stream-truncated": Reply(body=body + b" ", truncate_at=len(body), chunk_size=7),
    }
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    with TlsServer(certificate(scratch / "installed-tls"), routes) as server:
        for case in CASES:
            origins = scratch / (case + "-origins.json")
            child = subprocess.run(
                [
                    str(python),
                    "-I",
                    str(Path(__file__).resolve()),
                    "--case",
                    case,
                    "--venv",
                    str(venv),
                    "--ca",
                    str(server.certificates[0]),
                    "--port",
                    str(server.port),
                    "--origins",
                    str(origins),
                ],
                cwd=scratch,
                env=environment,
                capture_output=True,
                timeout=15,
                check=False,
            )
            verify_output(case, child.returncode, child.stdout, child.stderr)
            report = json.loads(origins.read_text(encoding="utf-8"))
            modules = report["modules"]
            if (
                not REQUIRED_MODULES.issubset(modules)
                or any(not Path(path).is_relative_to(venv.resolve()) for path in modules.values())
                or not Path(report["metadata"]).is_relative_to(venv.resolve())
                or not report["version"]
            ):
                raise ValueError("installed transport origin report failed")
        if [record.path for record in server.requests] != ["/v1/" + case for case in CASES]:
            raise ValueError("installed transport repeated or missed a request")
        if any(record.header("Host") != "localhost" for record in server.requests):
            raise ValueError("installed TLS mapping changed canonical request authority")
    return {"http_smoke": "passed", "stream_smoke": "passed"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--venv", required=True, type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--ca", type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--origins", type=Path)
    args = parser.parse_args(argv)
    if args.case is not None:
        if any(value is None for value in (args.ca, args.port, args.origins)):
            parser.error("worker requires CA, port and origin report")
        return worker(args)
    if args.python is None or args.scratch is None:
        parser.error("verifier requires Python and scratch directory")
    print(json.dumps(verify(args.python, args.venv, args.scratch)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
