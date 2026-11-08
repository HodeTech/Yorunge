"""The download measurement fixtures: bytes, oracle, server semantics, cut and resume, counters."""

import hashlib
import json
import os
import runpy
import socket
import ssl
import stat
import subprocess
import sys
import tracemalloc
from email.message import Message

import pytest

from tests.fixtures import download_native_server as served
from tests.fixtures.download_native_client import flow, instruments, prepare
from tests.fixtures.download_native_control import ROOT, environment, server
from tests.fixtures.download_native_data import (
    API_BASE,
    BLOCK_BYTES,
    FILENAME,
    FIXTURES,
    JSON_TARGET,
    KEY,
    KEY_ENV,
    LABELS,
    MIB,
    ORIGIN,
    PLATFORM_HOST,
    RESUME_CUT_AT,
    SIGNED_PATH,
    SIGNED_PREFIX,
    SIGNED_TARGET,
    VERSION,
    WARM_CUT_AT,
    WARM_LABELS,
    WARM_OF,
    canonical,
    expected_sha256,
    fixture,
    paths,
    write_config,
)
from tests.fixtures.http_server import certificate, loopback_sockets
from tests.fixtures.model_network import loopback_models
from yorunge.adapters import artifact_publisher, download_sink, local_files
from yorunge.domain.errors import YorungeError

CONNECT, CONNECT_EX, GETADDRINFO = (
    socket.socket.connect,
    socket.socket.connect_ex,
    socket.getaddrinfo,
)


@pytest.fixture(autouse=True)
def loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("download-native-tls"), names=(PLATFORM_HOST,))


@pytest.fixture(scope="module")
def evidence():
    return runpy.run_path(str(ROOT / "scripts/download_evidence.py"))


def naive(start, stop):
    """The bytes of the object by its position formula, in memory: only for small ranges."""
    return bytes((position + 37 * (position >> 16)) % 256 for position in range(start, stop))


# --- the fixture data ---------------------------------------------------------------------------


def test_the_labels_sizes_and_cuts_are_the_documented_fixture(evidence):
    assert LABELS == ("16", "256", "1024", "resume")
    assert WARM_LABELS == ("warm", "warm-resume")
    assert {label: FIXTURES[label].size for label in FIXTURES} == {
        "warm": MIB,
        "warm-resume": MIB,
        "16": 16 * MIB,
        "256": 256 * MIB,
        "1024": 1024 * MIB,
        "resume": 256 * MIB,
    }
    assert FIXTURES["resume"].cut_at == RESUME_CUT_AT
    # More than three 8 MiB checkpoints precede the cut, fewer than four, and the end is ragged.
    assert 3 * 8 * MIB < RESUME_CUT_AT < 4 * 8 * MIB and RESUME_CUT_AT % 4096 != 0
    assert 0 < WARM_CUT_AT < MIB
    assert [label for label in FIXTURES if FIXTURES[label].cut_at is not None] == [
        "warm-resume",
        "resume",
    ]
    assert WARM_OF == {"16": "warm", "256": "warm", "1024": "warm", "resume": "warm-resume"}
    for label, item in FIXTURES.items():
        assert fixture(label) is item
        assert item.etag == f'"native-download-{label}"' and item.etag.isascii()
    with pytest.raises(ValueError):
        fixture("2048")
    # The independent copy in the verifier says the same, label for label.
    assert evidence["LABELS"] == LABELS and evidence["WARM"] == WARM_OF
    assert evidence["OBJECTS"] == {label: (i.size, i.cut_at) for label, i in FIXTURES.items()}


def test_the_addresses_follow_the_models_consumer_rules():
    assert SIGNED_PREFIX == f"{API_BASE}/files/evren-models/" and API_BASE == "/api/v1"
    assert SIGNED_TARGET.startswith(SIGNED_PATH + "?") and SIGNED_PATH.startswith(SIGNED_PREFIX)
    assert JSON_TARGET == f"{API_BASE}/models/versions/{VERSION}/download?format=onnx"
    assert KEY not in SIGNED_TARGET and KEY not in ORIGIN
    assert ORIGIN == f"https://{PLATFORM_HOST}" and PLATFORM_HOST in ("api.ssyz.org.tr",)


@pytest.mark.parametrize(
    "size", [1, 255, 256, 65_535, 65_536, 65_537, 131_072, 200_001, 3 * 65_536 + 7, 300_000]
)
def test_the_oracle_equals_the_naive_in_memory_digest(evidence, size):
    expected = hashlib.sha256(naive(0, size)).hexdigest()
    assert expected_sha256(size) == expected
    assert evidence["object_sha256"](size) == expected


@pytest.mark.parametrize("size", [0, -1, True, 1.0, "1", 1_073_741_825])
def test_the_oracle_refuses_a_size_outside_one_byte_to_one_gib(evidence, size):
    with pytest.raises(ValueError):
        expected_sha256(size)
    with pytest.raises(ValueError):
        evidence["object_sha256"](size)


def test_three_derivations_agree_across_the_rotation_wrap(evidence):
    """The pattern repeats after 256 blocks (16 MiB): every block and the wrap are covered."""
    size = 257 * BLOCK_BYTES + 5
    streamed = hashlib.sha256()
    for block in served.body_blocks(0, size):
        streamed.update(block)
    assert streamed.hexdigest() == expected_sha256(size) == evidence["object_sha256"](size)
    edge = b"".join(served.body_blocks(255 * BLOCK_BYTES - 3, 257 * BLOCK_BYTES + 3))
    assert edge == naive(255 * BLOCK_BYTES - 3, 257 * BLOCK_BYTES + 3)
    # A shift by one checkpoint interval is no alias: a wrong resume offset changes the digest.
    assert naive(0, 4096) != naive(8 * MIB, 8 * MIB + 4096)
    shifted = b"".join(served.body_blocks(8 * MIB, 8 * MIB + 4096))
    assert b"".join(served.body_blocks(0, 4096)) != shifted == naive(8 * MIB, 8 * MIB + 4096)


@pytest.mark.parametrize(
    ("start", "stop"),
    [
        (0, 0),
        (0, 1),
        (65_535, 65_537),
        (131_072 + 5, 131_072 + 70_000),
        (1_000_003, 1_200_003),
        (524_289, 524_289 + 65_536),
    ],
)
def test_the_server_blocks_are_the_formula_for_any_range(start, stop):
    blocks = list(served.body_blocks(start, stop))
    assert b"".join(blocks) == naive(start, stop)
    assert all(0 < len(block) <= served.SERVER_BLOCK for block in blocks)


def test_neither_the_server_stream_nor_the_oracle_holds_a_response_sized_object():
    size = 24 * MIB
    tracemalloc.start()
    try:
        digest, largest = hashlib.sha256(), 0
        for block in served.body_blocks(0, size):
            digest.update(block)
            largest = max(largest, len(block))
        _, stream_peak = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        oracle = expected_sha256(size)
        _, oracle_peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert largest == served.SERVER_BLOCK == 65_536
    assert digest.hexdigest() == oracle
    assert stream_peak < MIB // 2 and oracle_peak < MIB // 2


def test_write_config_names_the_key_variable_and_never_overwrites(tmp_path):
    path = tmp_path / "config.toml"
    write_config(path)
    text = path.read_text()
    assert f'platform_key_env = "{KEY_ENV}"' in text and KEY not in text
    with pytest.raises(FileExistsError):
        write_config(path)
    layout = paths(tmp_path)
    assert layout.target == tmp_path / "out" / "weights.onnx" and layout.state == tmp_path / "state"


def test_canonical_json_is_sorted_compact_and_rejects_nan():
    assert canonical({"b": 1, "a": [1.5, None, True]}) == b'{"a":[1.5,null,true],"b":1}'
    with pytest.raises(ValueError):
        canonical({"a": float("nan")})


# --- the server over real TLS, judged by a hand-written client ---------------------------------


class Raw:
    """A hand-written HTTP/1.1 client over TLS: nothing of the product, no library parsing."""

    def __init__(self, certificates, port):
        context = ssl.create_default_context(cafile=str(certificates[0]))
        connection = socket.create_connection(("127.0.0.1", port), timeout=30)
        self.tls = context.wrap_socket(connection, server_hostname=PLATFORM_HOST)
        self.buffer = b""

    def close(self):
        self.tls.close()

    def send(self, target, headers=(), method="GET"):
        lines = [f"{method} {target} HTTP/1.1", f"Host: {PLATFORM_HOST}"]
        lines += [f"{name}: {value}" for name, value in headers]
        self.tls.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))

    def head(self):
        while b"\r\n\r\n" not in self.buffer:
            chunk = self.tls.recv(65_536)
            if not chunk:
                raise EOFError("connection closed before a response head")
            self.buffer += chunk
        raw, _, self.buffer = self.buffer.partition(b"\r\n\r\n")
        lines = raw.decode("latin-1").split("\r\n")
        fields = dict(line.split(": ", 1) for line in lines[1:])
        return int(lines[0].split()[1]), {name.lower(): value for name, value in fields.items()}

    def body(self, length, keep=False):
        """Read up to ``length`` bytes: (count, digest, bytes if ``keep``); EOF ends it early."""
        digest, count, parts = hashlib.sha256(), 0, []
        while count < length:
            if self.buffer:
                chunk, self.buffer = self.buffer[: length - count], self.buffer[length - count :]
            else:
                try:
                    chunk = self.tls.recv(min(65_536, length - count))
                except (ssl.SSLError, ConnectionError):
                    chunk = b""
                if not chunk:
                    break
            digest.update(chunk)
            count += len(chunk)
            if keep:
                parts.append(chunk)
        return count, digest.hexdigest(), b"".join(parts)

    def get(self, target, headers=()):
        self.send(target, headers)
        status, fields = self.head()
        length = int(fields.get("content-length", "0"))
        return status, fields, self.body(length, keep=True)[2]


def summary(directory):
    """The server's stdout after it has stopped: one closed canonical JSON object."""
    content = (directory / "stdout.json").read_bytes()
    value = json.loads(content)
    assert content == canonical(value) + b"\n"
    assert (directory / "stderr.txt").read_bytes() == b""
    return value


def test_the_json_call_needs_the_exact_key_and_answers_the_signed_address(tmp_path, certificates):
    with server(tmp_path / "server", certificates, "warm") as ready:
        assert ready["pid"] != os.getpid()
        client = Raw(certificates, ready["port"])
        assert client.get(JSON_TARGET)[0] == 401
        assert client.get(JSON_TARGET, [("X-API-Key", KEY + "x")])[0] == 401
        status, fields, body = client.get(JSON_TARGET, [("X-API-Key", KEY)])
        assert status == 200 and fields["content-type"] == "application/json"
        assert body == canonical({"download_url": ORIGIN + SIGNED_TARGET, "filename": FILENAME})
        assert client.get(JSON_TARGET.replace("onnx", "pt"), [("X-API-Key", KEY)])[0] == 404
        client.close()
    found = summary(tmp_path / "server")
    assert found["requests"] == {"json": 3, "signed": 0, "unexpected": 1}
    assert (found["json_key_failures"], found["errors"], found["connection_count"]) == (2, 0, 1)
    assert found["json_header_names"] == ["host", "x-api-key"]


@pytest.mark.parametrize(
    "header",
    [
        ("X-API-Key", KEY),
        ("x-api-key", "anything"),
        ("Authorization", "Bearer synthetic"),
        ("Cookie", "session=synthetic"),
        ("Proxy-Authorization", "Basic synthetic"),
    ],
)
def test_a_signed_get_that_carries_a_credential_is_refused_and_counted(
    tmp_path, certificates, header
):
    with server(tmp_path / "server", certificates, "warm") as ready:
        client = Raw(certificates, ready["port"])
        status, _, _ = client.get(SIGNED_TARGET, [header])
        assert status == 403
        assert client.get(SIGNED_TARGET)[0] == 200  # the next clean request is served as usual
        client.close()
    found = summary(tmp_path / "server")
    assert found["credential_violations"] == 1 and found["header_violations"] == 0
    assert [row["status"] for row in found["signed"]] == [403, 200]
    assert found["signed"][0]["bytes_sent"] == 0 and found["signed"][0]["completed"] is False
    assert found["errors"] == 0


@pytest.mark.parametrize(
    "headers",
    [
        [("X-Unlisted", "1")],
        [("Range", "bytes=0-10")],
        [("Range", "bytes=-5")],
        [("Range", "bytes=1-")] * 2,
        [("Range", "bytes=1-"), ("If-Range", '"a"'), ("If-Range", '"a"')],
        [("Range", "bytes=01-")],
    ],
)
def test_a_signed_get_outside_the_closed_header_set_is_refused_and_counted(
    tmp_path, certificates, headers
):
    with server(tmp_path / "server", certificates, "warm") as ready:
        client = Raw(certificates, ready["port"])
        assert client.get(SIGNED_TARGET, headers)[0] == 400
        client.close()
    found = summary(tmp_path / "server")
    assert found["header_violations"] == 1 and found["credential_violations"] == 0
    assert found["bytes_sent"] == 0


def test_whole_objects_and_ranges_are_exact_and_the_connection_stays_alive(tmp_path, certificates):
    etag = FIXTURES["warm"].etag
    start = 700_000
    with server(tmp_path / "server", certificates, "warm") as ready:
        client = Raw(certificates, ready["port"])
        status, fields, body = client.get(SIGNED_TARGET, [("Accept-Encoding", "identity")])
        assert status == 200 and int(fields["content-length"]) == MIB
        assert (fields["etag"], fields["accept-ranges"]) == (etag, "bytes")
        assert "content-range" not in fields and "content-encoding" not in fields
        assert hashlib.sha256(body).hexdigest() == expected_sha256(MIB)
        assert body == naive(0, MIB)
        for headers in (
            [("Range", f"bytes={start}-"), ("If-Range", etag)],
            [("Range", f"bytes={start}-")],
        ):
            status, fields, body = client.get(SIGNED_TARGET, headers)
            assert status == 206 and fields["etag"] == etag
            assert fields["content-range"] == f"bytes {start}-{MIB - 1}/{MIB}"
            assert int(fields["content-length"]) == MIB - start == len(body)
            assert body == naive(start, MIB)
        # A stale validator turns the range into the whole object, as a real store does.
        status, fields, body = client.get(
            SIGNED_TARGET, [("Range", f"bytes={start}-"), ("If-Range", '"stale"')]
        )
        assert status == 200 and len(body) == MIB and "content-range" not in fields
        # If-Range alone is no range request.
        status, fields, body = client.get(SIGNED_TARGET, [("If-Range", etag)])
        assert status == 200 and len(body) == MIB
        for start_at in (MIB, MIB + 5, 10**18):
            status, fields, body = client.get(SIGNED_TARGET, [("Range", f"bytes={start_at}-")])
            assert status == 416 and fields["content-range"] == f"bytes */{MIB}" and body == b""
        status, fields, body = client.get(SIGNED_TARGET, [("Range", "bytes=0-")])
        assert status == 206 and fields["content-range"] == f"bytes 0-{MIB - 1}/{MIB}"
        client.close()
    found = summary(tmp_path / "server")
    assert found["connection_count"] == 1 and found["errors"] == 0
    assert found["requests"] == {"json": 0, "signed": 9, "unexpected": 0}
    assert found["max_block_bytes"] == 65_536 and found["peak_active_requests"] == 1
    assert found["signed_header_names"] == ["accept-encoding", "host", "if-range", "range"]
    assert [row["status"] for row in found["signed"]] == [
        200,
        206,
        206,
        200,
        200,
        416,
        416,
        416,
        206,
    ]
    assert found["bytes_sent"] == sum(row["bytes_sent"] for row in found["signed"])
    assert all(row["cut"] is False for row in found["signed"])


def test_the_first_signed_get_is_cut_and_every_later_one_is_served_normally(tmp_path, certificates):
    item = fixture("warm-resume")
    with server(tmp_path / "server", certificates, "warm-resume") as ready:
        first = Raw(certificates, ready["port"])
        first.send(SIGNED_TARGET, [("Accept-Encoding", "identity")])
        status, fields = first.head()
        # The status line and headers are the honest ones, with the whole Content-Length ...
        assert status == 200 and int(fields["content-length"]) == item.size
        assert fields["etag"] == item.etag
        # ... and the body ends after cut_at bytes, with the connection (no more bytes follow).
        count, digest, kept = first.body(item.size, keep=True)
        assert count == item.cut_at == WARM_CUT_AT and kept == naive(0, item.cut_at)
        assert first.body(1)[0] == 0
        first.close()
        second = Raw(certificates, ready["port"])
        status, fields, rest = second.get(
            SIGNED_TARGET, [("Range", f"bytes={item.cut_at}-"), ("If-Range", item.etag)]
        )
        assert status == 206 and len(rest) == item.size - item.cut_at
        assert hashlib.sha256(kept + rest).hexdigest() == expected_sha256(item.size)
        status, _, again = second.get(SIGNED_TARGET)  # a third GET is a whole object again
        assert status == 200 and len(again) == item.size
        second.close()
    found = summary(tmp_path / "server")
    cut, resumed, whole = found["signed"]
    assert (cut["cut"], cut["completed"], cut["bytes_sent"]) == (True, False, item.cut_at)
    assert (resumed["status"], resumed["bytes_sent"], resumed["completed"]) == (
        206,
        item.size - item.cut_at,
        True,
    )
    assert (whole["cut"], whole["completed"]) == (False, True)
    assert found["connection_count"] == 2 and found["errors"] == 0
    assert found["bytes_sent"] == item.cut_at + (item.size - item.cut_at) + item.size


def test_other_methods_paths_and_signatures_are_refused_and_counted_unexpected(
    tmp_path, certificates
):
    other_query = SIGNED_TARGET[:-1] + ("6" if SIGNED_TARGET[-1] == "5" else "5")
    with server(tmp_path / "server", certificates, "warm") as ready:
        client = Raw(certificates, ready["port"])
        client.send(SIGNED_TARGET, method="HEAD")
        assert client.head()[0] == 405
        client.send(SIGNED_TARGET, method="POST")
        status, fields = client.head()
        assert status == 405
        client.body(int(fields["content-length"]))
        assert client.get(SIGNED_PATH)[0] == 404  # the signature is part of the address
        assert client.get(other_query)[0] == 404
        assert client.get("/api/v1/other")[0] == 404
        client.close()
    found = summary(tmp_path / "server")
    assert found["requests"] == {"json": 0, "signed": 0, "unexpected": 5}
    assert found["bytes_sent"] == 0 and found["errors"] == 0


def test_the_closed_account_has_the_fields_the_verifier_requires(tmp_path, certificates, evidence):
    with server(tmp_path / "server", certificates, "warm-resume") as ready:
        client = Raw(certificates, ready["port"])
        client.get(JSON_TARGET, [("X-API-Key", KEY)])
        client.close()
    found = summary(tmp_path / "server")
    assert set(found) == set(evidence["SERVER_FIELDS"].split())
    assert found["label"] == "warm-resume" and found["pid"] != os.getpid()
    assert evidence["server"](found, "warm-resume")["requests"]["json"] == 1


def test_a_signed_row_has_exactly_the_verifier_fields(tmp_path, certificates, evidence):
    with server(tmp_path / "server", certificates, "warm") as ready:
        client = Raw(certificates, ready["port"])
        client.get(SIGNED_TARGET)
        client.close()
    row = summary(tmp_path / "server")["signed"][0]
    assert set(row) == set(evidence["SIGNED_FIELDS"].split())


def test_a_request_flood_is_cut_off_and_counted_as_an_error(tmp_path, certificates):
    with server(tmp_path / "server", certificates, "warm") as ready:
        client = Raw(certificates, ready["port"])
        refused = 0
        for _ in range(served.REQUEST_CAP + 2):
            try:
                refused += client.get("/other")[0] == 404
            except (EOFError, ConnectionError, ssl.SSLError):
                break
        client.close()
    found = summary(tmp_path / "server")
    assert refused == served.REQUEST_CAP and found["errors"] >= 1
    assert sum(found["requests"].values()) == served.REQUEST_CAP


# --- the provider without sockets: protocol logic, block sizes, and python -O ---------------------


class Wire:
    def __init__(self):
        self.writes = []
        self.flushed = 0

    def write(self, data):
        self.writes.append(len(data))

    def flush(self):
        self.flushed += 1


class Handler:
    """The slice of BaseHTTPRequestHandler the provider uses, kept in memory."""

    def __init__(self, path, headers=(), command="GET"):
        self.command, self.path, self.wfile = command, path, Wire()
        self.headers = Message()
        for name, value in headers:
            self.headers[name] = value
        self.close_connection = False
        self.status, self.fields = None, []

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.fields.append((name, value))

    def end_headers(self):
        pass


def test_the_provider_never_writes_a_block_larger_than_64_kib_and_cuts_only_the_first():
    provider = served.Provider("resume")
    first = Handler(SIGNED_TARGET)
    provider.respond(first)
    assert first.status == 200 and first.close_connection is True
    assert sum(first.wfile.writes) == RESUME_CUT_AT and max(first.wfile.writes) == 65_536
    assert ("Content-Length", str(256 * MIB)) in first.fields
    second = Handler(
        SIGNED_TARGET, [("Range", f"bytes={RESUME_CUT_AT}-"), ("If-Range", FIXTURES["resume"].etag)]
    )
    provider.respond(second)
    assert second.status == 206 and second.close_connection is False
    assert sum(second.wfile.writes) == 256 * MIB - RESUME_CUT_AT
    assert max(second.wfile.writes) == 65_536
    found = provider.summary()
    assert found["bytes_sent"] == 256 * MIB and found["max_block_bytes"] == 65_536
    assert (found["errors"], found["active_requests"]) == (0, 0)


def test_a_write_that_breaks_is_an_error_and_never_a_complete_response():
    provider = served.Provider("warm")
    handler = Handler(SIGNED_TARGET)

    def broken(data):
        raise BrokenPipeError

    handler.wfile.write = broken
    provider.respond(handler)
    found = provider.summary()
    assert found["errors"] == 1 and found["signed"][0]["completed"] is False
    assert handler.close_connection is True and found["active_requests"] == 0


INVALID_PRECONDITION_CODE = """
import sys
from email.message import Message
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
from tests.fixtures.download_native_data import KEY, JSON_TARGET
from tests.fixtures.download_native_server import Provider
provider = Provider('warm')
def unexpected(*args):
    raise RuntimeError('an invalid request reached a route')
provider.json_call = provider.signed_get = unexpected
headers = Message(); headers['X-API-Key'] = KEY; headers['Content-Length'] = '0'
handler = SimpleNamespace(command='GET', path=JSON_TARGET, headers=headers, close_connection=False)
invalid = sys.argv[2]
if invalid == 'method': handler.command = 'DELETE'
elif invalid == 'encoding': headers['Transfer-Encoding'] = 'chunked'
elif invalid == 'length': headers.replace_header('Content-Length', '5')
elif invalid == 'path': handler.path = '/elsewhere'
else: raise RuntimeError('unknown negative fixture')
refused = []
provider.reply = lambda handler, status, body, extra=(): refused.append(status)
provider.respond(handler)
status = {'method': 405, 'encoding': 400, 'length': 400, 'path': 404}[invalid]
if (refused, provider.errors, provider.active) != ([status], 0, 0):
    raise RuntimeError('invalid request was not refused and cleaned up: %r' % (refused,))
if provider.requests['unexpected'] != 1:
    raise RuntimeError('invalid request was not counted')
print('refused')
"""


@pytest.mark.parametrize("optimized", [False, True])
@pytest.mark.parametrize("invalid", ["method", "encoding", "length", "path"])
def test_provider_preconditions_remain_active_with_python_optimization(optimized, invalid):
    flags = ["-I", "-O"] if optimized else ["-I"]
    result = subprocess.run(
        [sys.executable, *flags, "-c", INVALID_PRECONDITION_CODE, str(ROOT), invalid],
        capture_output=True,
        timeout=20,
    )
    assert (result.returncode, result.stdout, result.stderr) == (0, b"refused\n", b"")


# --- the control module -------------------------------------------------------------------------


def test_the_server_environment_drops_python_variables_and_the_virtualenv(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/elsewhere")
    monkeypatch.setenv("VIRTUAL_ENV", "/elsewhere")
    monkeypatch.setenv("KEEP_ME", "1")
    result = environment()
    assert "PYTHONPATH" not in result and "VIRTUAL_ENV" not in result and result["KEEP_ME"] == "1"


def test_a_server_that_cannot_start_is_reported_and_leaves_its_output(tmp_path):
    broken = (tmp_path / "ca.pem", tmp_path / "key.pem")
    with (
        pytest.raises(ValueError, match="did not become ready"),
        server(tmp_path / "server", broken, "warm"),
    ):
        pytest.fail("a server without certificates cannot be ready")
    assert b"No such file" in (tmp_path / "server/stderr.txt").read_bytes()


# --- the instruments ----------------------------------------------------------------------------


def test_instruments_tell_the_stage_from_other_files_and_restore_everything(tmp_path):
    real = (os.write, os.fsync, local_files.full_sync)
    stage = os.open(tmp_path / ".yorunge-download-0123.part", os.O_CREAT | os.O_RDWR, 0o600)
    other = os.open(tmp_path / ".yorunge-download-0123.json.tmp", os.O_CREAT | os.O_RDWR, 0o600)
    directory = os.open(tmp_path, os.O_RDONLY)
    try:
        with instruments(tmp_path) as totals:
            assert totals["instrumented"] is True
            assert os.write(stage, b"abcd") == 4 and os.write(stage, memoryview(b"ef")) == 2
            assert os.write(other, b"zz") == 2
            os.fsync(stage)
            os.fsync(other)
            os.fsync(directory)
            download_sink.full_sync(stage)  # its own fsync is counted once, as a full-sync
            artifact_publisher.full_sync(stage)
            local_files.full_sync(stage)
            assert os.fstat(stage).st_size == 6
        assert (os.write, os.fsync, local_files.full_sync) == real
        assert download_sink.full_sync is artifact_publisher.full_sync is local_files.full_sync
    finally:
        for descriptor in (stage, other, directory):
            os.close(descriptor)
    assert (totals["write_calls"], totals["write_bytes"], totals["max_write_bytes"]) == (2, 6, 4)
    assert (totals["stage_fsync_calls"], totals["other_fsync_calls"]) == (1, 2)
    assert totals["full_sync_calls"] == 3
    assert all(totals[key] > 0 for key in ("write_seconds", "full_sync_seconds"))
    assert totals["max_write_seconds"] <= totals["write_seconds"]
    assert stat.S_ISREG(os.stat(tmp_path / ".yorunge-download-0123.part").st_mode)


def test_instruments_are_restored_when_the_window_fails(tmp_path):
    real = (os.write, os.fsync, local_files.full_sync)
    with pytest.raises(RuntimeError, match="boom"), instruments(tmp_path):
        raise RuntimeError("boom")
    assert (os.write, os.fsync, local_files.full_sync) == real


def test_instruments_refuse_a_sink_that_does_not_use_the_common_full_sync(tmp_path, monkeypatch):
    monkeypatch.setattr(download_sink, "full_sync", lambda descriptor: None)
    with pytest.raises(ValueError, match="does not use"), instruments(tmp_path):
        pytest.fail("the instruments must not start")


# --- the real client flow against the real separate-process server ------------------------------


@pytest.mark.parametrize("label", ["warm", "warm-resume"])
def test_the_public_flow_against_the_separate_process_server_is_measured_and_judged(
    tmp_path, certificates, monkeypatch, evidence, label
):
    monkeypatch.setenv(KEY_ENV, KEY)
    item = fixture(label)
    digest = expected_sha256(item.size)
    work = tmp_path / "work"
    prepare(work)
    layout = paths(work)
    with server(tmp_path / "server", certificates, label) as ready:
        assert ready["pid"] != os.getpid()
        with loopback_models(certificates[0], ready["port"]), instruments(layout.out) as window:
            first_error, result = flow(work, item, digest)
    data = result.data
    resumed = item.cut_at is not None
    assert first_error == ("download_incomplete" if resumed else None)
    assert (data.bytes, data.sha256) == (item.size, digest)
    assert (data.verification_level, data.expectation_source) == ("sha256_matched", "user_supplied")
    assert data.resumed is resumed and data.resumed_from_bytes == (item.cut_at or 0)
    # The target is the only file left in the directory, and holds the oracle's bytes.
    assert sorted(entry.name for entry in os.scandir(layout.out)) == ["weights.onnx"]
    assert hashlib.sha256(layout.target.read_bytes()).hexdigest() == digest
    found = summary(tmp_path / "server")
    assert found["bytes_sent"] == window["write_bytes"] == item.size
    assert found["requests"] == {"json": 1 + resumed, "signed": 1 + resumed, "unexpected": 0}
    verdict = evidence["exchange"](evidence["server"](found, label), label, data.resumed_from_bytes)
    assert verdict and all(verdict.values()), verdict
    evidence["window"](window)
    assert window["max_write_bytes"] <= 65_536 and window["full_sync_calls"] in (1, 2)
    assert window["stage_fsync_calls"] == (2 if resumed else 1)  # clean stop + completion
    outcome = {
        "bytes": data.bytes,
        "sha256": data.sha256,
        "verification_level": data.verification_level,
        "expectation_source": data.expectation_source,
        "resumed": data.resumed,
        "resumed_from_bytes": data.resumed_from_bytes,
        "first_error": first_error,
    }
    assert all(evidence["settled"](label, outcome).values())
    assert evidence["checkpoints"](label, window, data.resumed_from_bytes)


def test_the_worker_rejects_an_editable_install_before_any_network_or_file(tmp_path):
    provenance = tmp_path / "source.json"
    provenance.write_text(json.dumps({"source_sha256": {}, "locked_runtime": {}}))
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "tests/fixtures/download_native_client.py"),
            "--ca",
            str(tmp_path / "absent.pem"),
            "--port",
            "1",
            "--warm-port",
            "2",
            "--prefix",
            sys.prefix,
            "--provenance",
            str(provenance),
            "--work",
            str(tmp_path / "absent"),
            "--warm",
            str(tmp_path / "also-absent"),
            "--label",
            "16",
        ],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode != 0
    assert not result.stdout
    assert b"product import escaped the selected installed environment" in result.stderr
    assert not (tmp_path / "absent").exists() and not (tmp_path / "also-absent").exists()


def test_the_worker_needs_an_isolated_interpreter(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tests/fixtures/download_native_client.py"),
            "--ca",
            "x",
            "--port",
            "1",
            "--warm-port",
            "2",
            "--prefix",
            "x",
            "--provenance",
            "x",
            "--work",
            "x",
            "--warm",
            "y",
            "--label",
            "16",
        ],
        capture_output=True,
        timeout=20,
        env={"PATH": os.environ.get("PATH", "")},
        cwd=tmp_path,
    )
    assert result.returncode != 0 and not result.stdout
    assert b"requires isolated Python" in result.stderr


def test_a_cut_flow_with_a_wrong_expectation_leaves_nothing_but_the_error(
    tmp_path, certificates, monkeypatch
):
    """The oracle digest is a real expectation: a server of other bytes cannot satisfy it."""
    monkeypatch.setenv(KEY_ENV, KEY)
    item = fixture("warm")
    work = tmp_path / "work"
    prepare(work)
    with server(tmp_path / "server", certificates, "warm") as ready:
        with loopback_models(certificates[0], ready["port"]):
            with pytest.raises(YorungeError) as error:
                flow(work, item, "0" * 64)
    assert error.value.code == "download_integrity_mismatch"
    assert list(os.scandir(paths(work).out)) == []
    assert summary(tmp_path / "server")["bytes_sent"] == item.size
