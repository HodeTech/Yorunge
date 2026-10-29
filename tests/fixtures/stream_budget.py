"""Bounded synthetic TLS server and installed-only raw stream RSS worker.

This fixture is not a product endpoint or an EVREN acceptance probe. The server
and client always run in separate processes; the client never imports tests.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import re
import signal
import sqlite3
import ssl
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from typing import Any

CHUNK_BYTES = 32_768
MAX_BYTES = 1_073_741_824
RSS_LIMIT_BYTES = 67_108_864
WARMUP_BYTES = CHUNK_BYTES


def publish_ready(path: Path, payload: dict[str, int]) -> None:
    """Expose only complete readiness JSON without replacing another writer."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".ready-", suffix=".pending"
    ) as target:
        json.dump(payload, target)
        target.flush()
        os.fsync(target.fileno())
        os.link(target.name, path)


def rss_bytes(native: int | float, system: str) -> int:
    """Native RSS is bytes on macOS and KiB on Linux; no child-process sum is used."""
    if system not in {"Darwin", "Linux"}:
        raise ValueError("RSS measurement requires Linux or macOS")
    if (
        type(native) not in (int, float)
        or not math.isfinite(native)
        or native < 0
        or native != int(native)
    ):
        raise ValueError("invalid RSS measurement")
    return int(native) * (1024 if system == "Linux" else 1)


def self_peak_rss() -> tuple[int | float, int]:
    if platform.system() == "Linux":
        native = linux_rss_snapshot()[1]
    else:
        import resource

        native = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return native, rss_bytes(native, platform.system())


def parse_linux_rss(value: str) -> tuple[int, int]:
    """Read a coherent current/peak pair from one Linux status snapshot, in KiB."""
    if not isinstance(value, str):
        raise ValueError("process status must be text")
    values = []
    for name in ("VmRSS", "VmHWM"):
        fields = [line for line in value.splitlines() if line.startswith(name + ":")]
        if len(fields) != 1:
            raise ValueError("process status must contain exactly one field per RSS counter")
        match = re.fullmatch(name + r":[ \t]+(\d+)[ \t]+kB", fields[0], flags=re.ASCII)
        if match is None or int(match[1]) <= 0:
            raise ValueError("invalid process status RSS counter")
        values.append(int(match[1]))
    if values[0] > values[1]:
        raise ValueError("process status RSS counters are inconsistent")
    return values[0], values[1]


def linux_rss_snapshot() -> tuple[int, int]:
    with Path("/proc/self/status").open(encoding="ascii") as source:
        value = source.read(65_536)
    if len(value) == 65_536:
        raise ValueError("process status exceeded the bounded probe input")
    return parse_linux_rss(value)


def linux_current_rss() -> int:
    return linux_rss_snapshot()[0]


class MachTimeValue(ctypes.Structure):
    _layout_ = "ms"
    _pack_ = 4
    _fields_ = [("seconds", ctypes.c_int32), ("microseconds", ctypes.c_int32)]


class MachTaskBasicInfo(ctypes.Structure):
    # Apple's exported task_info.h uses pragma pack(4), flavor 20, count 12.
    _layout_ = "ms"
    _pack_ = 4
    _fields_ = [
        ("virtual_size", ctypes.c_uint64),
        ("resident_size", ctypes.c_uint64),
        ("resident_size_max", ctypes.c_uint64),
        ("user_time", MachTimeValue),
        ("system_time", MachTimeValue),
        ("policy", ctypes.c_int32),
        ("suspend_count", ctypes.c_int32),
    ]


class DarwinRssProbe:
    def __init__(self) -> None:
        if ctypes.sizeof(MachTaskBasicInfo) != 48 or ctypes.sizeof(ctypes.c_uint32) != 4:
            raise ValueError("unsupported MACH_TASK_BASIC_INFO ABI")
        self.library = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        self.task = ctypes.c_uint32.in_dll(self.library, "mach_task_self_").value
        if not self.task:
            raise ValueError("invalid current Mach task port")
        self.task_info = self.library.task_info
        self.task_info.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.POINTER(MachTaskBasicInfo),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self.task_info.restype = ctypes.c_int32

    def __call__(self) -> int:
        info = MachTaskBasicInfo()
        count = ctypes.c_uint32(12)
        result = self.task_info(self.task, 20, ctypes.byref(info), ctypes.byref(count))
        if result != 0 or count.value != 12:
            raise ValueError("MACH_TASK_BASIC_INFO failed or returned an unexpected count")
        if info.resident_size <= 0:
            raise ValueError("invalid MACH_TASK_BASIC_INFO resident_size")
        return int(info.resident_size)


def prepare_current_rss() -> tuple[str, Callable[[], int]]:
    system = platform.system()
    if system == "Linux":
        method, probe = "linux.proc_self_status.VmRSS", linux_current_rss
    elif system == "Darwin":
        method, probe = "darwin.MACH_TASK_BASIC_INFO.resident_size", DarwinRssProbe()
    else:
        raise ValueError("RSS measurement requires Linux or macOS")
    # Initialize native calls and their Python machinery before TLS/baseline.
    rss_bytes(probe(), system)
    self_peak_rss()
    return method, probe


def rss_bounds(baseline: int, pretransfer_peak: int, peak: int) -> tuple[int, int]:
    """Bound measured-window extra RSS without subtracting a historical peak."""
    if any(type(value) is not int or value <= 0 for value in (baseline, pretransfer_peak, peak)):
        raise ValueError("invalid process RSS byte measurements")
    if not baseline <= pretransfer_peak <= peak:
        raise ValueError("process RSS baseline and high-water counters are inconsistent")
    upper = peak - baseline
    return (upper if peak > pretransfer_peak else 0), upper


def installed_provenance(
    expected: dict[str, str], prefix: Path, locked: dict[str, str]
) -> dict[str, Any]:
    """Prove the complete installed package's Python bytes, not only its Git label."""
    import yorunge

    prefix = prefix.resolve()
    package = Path(yorunge.__file__).resolve().parent
    if Path(sys.prefix).resolve() != prefix or not package.is_relative_to(prefix):
        raise ValueError("product import escaped the selected installed environment")
    expected_package = {
        name.removeprefix("src/yorunge/"): digest
        for name, digest in expected.items()
        if name.startswith("src/yorunge/")
    }
    actual = {
        str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(package.rglob("*.py"))
    }
    if not expected_package or actual != expected_package:
        raise ValueError("installed package bytes do not match the measured source")
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "yorunge" or name.startswith("yorunge."):
            origin = getattr(module, "__file__", None)
            if origin is None or not Path(origin).resolve().is_relative_to(prefix):
                raise ValueError("product module escaped the selected installation: " + name)
            origins[name] = str(Path(origin).resolve())
    distribution = importlib.metadata.distribution("yorunge")
    metadata = Path(str(distribution.locate_file(""))).resolve()
    if not metadata.is_relative_to(prefix):
        raise ValueError("distribution metadata escaped the selected installation")
    packages = {}
    for dist in importlib.metadata.distributions():
        raw_name = dist.metadata["Name"]
        if not isinstance(raw_name, str) or not raw_name:
            raise ValueError("installed distribution has no package name")
        name = re.sub(r"[-_.]+", "-", raw_name.lower())
        if name in packages:
            raise ValueError("duplicate normalized installed distribution")
        packages[name] = dist.version
    if not locked or packages != locked:
        raise ValueError("installed runtime packages do not match the frozen runtime closure")
    if importlib.util.find_spec("pytest") is not None:
        raise ValueError("raw stream measurement must not import test tooling")
    return {
        "prefix": str(prefix),
        "pid": os.getpid(),
        "modules": origins,
        "installed_source_sha256": actual,
        "installed_source_matches": True,
        "metadata": str(metadata),
        "packages": packages,
        "python": sys.version,
        "python_executable": sys.executable,
        "isolated": bool(sys.flags.isolated),
        "sqlite": sqlite3.sqlite_version,
        "os": platform.platform(),
        "machine": platform.machine(),
    }


async def consume(port: int, ca: Path, size: int, total_seconds: float) -> dict[str, Any]:
    """Only the TLS address is mapped: the installed product consumes actual bytes."""
    import httpx

    from yorunge.adapters.http_transport import HttpxTransport
    from yorunge.application.http_transport import HttpRequest
    from yorunge.domain.credentials import normalize_target

    class LoopbackTransport(httpx.AsyncBaseTransport):
        def __init__(self) -> None:
            self.inner = httpx.AsyncHTTPTransport(
                verify=ssl.create_default_context(cafile=str(ca)),
                retries=0,
                trust_env=False,
                limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
            )

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.host != "localhost" or request.url.port not in (None, 443):
                raise ValueError("fixture permits only canonical localhost HTTPS")
            mapped = httpx.Request(
                request.method,
                request.url.copy_with(port=port),
                headers=request.headers,
                stream=request.stream,
                extensions=request.extensions,
            )
            return await self.inner.handle_async_request(mapped)

        async def aclose(self) -> None:
            await self.inner.aclose()

    async def receive(transport: HttpxTransport, amount: int) -> tuple[int, str, int, int]:
        digest = hashlib.sha256()
        received, largest, chunks = 0, 0, 0
        request = HttpRequest(
            normalize_target("https://localhost/v1"),
            "GET",
            f"raw/{amount}",
            service_id="evren-platform",
            max_bytes=amount,
        )
        async with transport.open(request, deadline=time.monotonic() + total_seconds) as response:
            async for chunk in response.chunks():
                if not 0 < len(chunk) <= CHUNK_BYTES:
                    raise ValueError("raw stream emitted an unbounded or empty chunk")
                digest.update(chunk)
                received += len(chunk)
                largest = max(largest, len(chunk))
                chunks += 1
        return received, digest.hexdigest(), largest, chunks

    baseline_method, current_rss = prepare_current_rss()
    async with HttpxTransport(transport=LoopbackTransport()) as transport:
        warmed = await receive(transport, WARMUP_BYTES)
        if warmed[:2] != (
            WARMUP_BYTES,
            "e11360251d1173650cdcd20f111d8f1ca2e412f572e8b36a4dc067121c1799b8",
        ):
            raise ValueError("TLS warmup bytes did not match the independent fixed oracle")
        if platform.system() == "Linux":
            baseline_native, pretransfer_peak_native = linux_rss_snapshot()
            pretransfer_peak = rss_bytes(pretransfer_peak_native, "Linux")
        else:
            baseline_native = current_rss()
            pretransfer_peak_native, pretransfer_peak = self_peak_rss()
        baseline = rss_bytes(baseline_native, platform.system())
        started = time.perf_counter()
        received, digest, largest, chunks = await receive(transport, size)
        elapsed = time.perf_counter() - started
        peak_native, peak = self_peak_rss()
        lower, upper = rss_bounds(baseline, pretransfer_peak, peak)
    return {
        "size_bytes": size,
        "stream_count": 1,
        "received_bytes": received,
        "received_sha256": digest,
        "baseline_rss_native": baseline_native,
        "baseline_rss_method": baseline_method,
        "pretransfer_peak_rss_native": pretransfer_peak_native,
        "pretransfer_peak_rss_bytes": pretransfer_peak,
        "peak_rss_native": peak_native,
        "rss_native_unit": "bytes" if platform.system() == "Darwin" else "KiB",
        "baseline_rss_bytes": baseline,
        "peak_rss_bytes": peak,
        "extra_rss_lower_bound_bytes": lower,
        "extra_rss_upper_bound_bytes": upper,
        "elapsed_seconds": elapsed,
        "max_chunk_bytes": largest,
        "chunk_count": chunks,
        "warmup_requests": 1,
        "measurement_requests": 1,
    }


def client(args: argparse.Namespace) -> int:
    if not sys.flags.isolated:
        raise ValueError("raw stream worker requires isolated Python")
    if type(args.size) is not int or not 1 <= args.size <= MAX_BYTES:
        raise ValueError("raw stream fixture size must be between 1 byte and 1 GiB")
    expected = json.loads(args.manifest.read_text(encoding="utf-8"))
    # Import the exercised runtime before checking every imported origin.
    from yorunge.adapters import http_transport  # noqa: F401
    from yorunge.application import http_transport as http_port  # noqa: F401

    before = installed_provenance(
        expected["source_sha256"], args.prefix, expected["locked_runtime"]
    )
    measured = asyncio.run(consume(args.port, args.ca, args.size, args.total_seconds))
    after = installed_provenance(expected["source_sha256"], args.prefix, expected["locked_runtime"])

    def identity(value: dict[str, Any]) -> dict[str, Any]:
        return {name: item for name, item in value.items() if name not in {"pid", "modules"}}

    if identity(before) != identity(after):
        raise ValueError("installed runtime changed during measurement")
    measured["runtime"] = after
    print(json.dumps(measured, allow_nan=False))
    return 0


def serve(args: argparse.Namespace) -> int:
    # Exactly one reusable block exists regardless of requested response size.
    block = bytes(range(256)) * (CHUNK_BYTES // 256)
    lock = threading.Lock()
    records: list[dict[str, Any]] = []
    connections: set[tuple[str, int]] = set()
    active, peak_active = 0, 0

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *values: object) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal active, peak_active
            prefix = "/v1/raw/"
            raw = self.path.removeprefix(prefix)
            if not self.path.startswith(prefix) or not raw.isascii() or not raw.isdigit():
                self.send_error(404)
                return
            size = int(raw)
            if not 1 <= size <= MAX_BYTES:
                self.send_error(400)
                return
            with lock:
                if len(records) >= 16:
                    self.send_error(429)
                    return
                record = {"size_bytes": size, "sent_bytes": 0, "completed": False}
                records.append(record)
                connections.add(self.client_address)
                active += 1
                peak_active = max(peak_active, active)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(size))
                self.end_headers()
                sent = 0
                while sent < size:
                    chunk = block if size - sent >= len(block) else block[: size - sent]
                    self.wfile.write(chunk)
                    sent += len(chunk)
                    record["sent_bytes"] = sent
                self.wfile.flush()
                record["completed"] = True
            except (BrokenPipeError, ConnectionError, ssl.SSLError):
                self.close_connection = True
            finally:
                with lock:
                    active -= 1

    class LoopbackServer(ThreadingHTTPServer):
        def server_bind(self) -> None:
            # HTTPServer otherwise performs an unnecessary reverse DNS lookup
            # before readiness. This fixture has a fixed localhost identity.
            TCPServer.server_bind(self)
            self.server_name = "localhost"
            self.server_port = int(self.server_address[1])

    server = LoopbackServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(args.ca), str(args.key))
    server.socket = context.wrap_socket(server.socket, server_side=True)

    def shutdown(signum: int, frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        publish_ready(args.ready, {"port": server.server_address[1], "pid": os.getpid()})
        server.serve_forever(poll_interval=0.05)
    finally:
        server.server_close()
    print(
        json.dumps(
            {
                "requests": records,
                "request_count": len(records),
                "connection_count": len(connections),
                "peak_active_requests": peak_active,
                "pid": os.getpid(),
            }
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    server = sub.add_parser("server")
    server.add_argument("--ca", type=Path, required=True)
    server.add_argument("--key", type=Path, required=True)
    server.add_argument("--ready", type=Path, required=True)
    worker = sub.add_parser("client")
    worker.add_argument("--ca", type=Path, required=True)
    worker.add_argument("--port", type=int, required=True)
    worker.add_argument("--size", type=int, required=True)
    worker.add_argument("--manifest", type=Path, required=True)
    worker.add_argument("--prefix", type=Path, required=True)
    worker.add_argument("--total-seconds", type=float, default=120.0)
    args = parser.parse_args()
    return serve(args) if args.mode == "server" else client(args)


if __name__ == "__main__":
    raise SystemExit(main())
