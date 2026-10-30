"""Reject false installed transport acceptance and exercise a runtime-only -I child."""

import importlib.metadata
import json
import os
import shutil
import socket
import subprocess
import venv
from pathlib import Path

import pytest

from tests.fixtures import installed_transport as acceptance
from tests.fixtures.http_server import loopback_sockets

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def runtime_tree(tmp_path_factory):
    """Synthetic installed layout; real wheel/sdist installs belong to the verifier.

    Copy the current product and frozen runtime dependencies, never development
    packages or editable-path hooks. No installer/network or stale dist is used.
    """
    prefix = tmp_path_factory.mktemp("installed-runtime") / "env"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(prefix)
    python = prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = Path(
        subprocess.check_output(
            [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
            text=True,
        ).strip()
    )
    for name in (
        "annotated-types",
        "anyio",
        "certifi",
        "h11",
        "httpcore",
        "httpx",
        "idna",
        "pydantic",
        "pydantic-core",
        "PyYAML",
        "typing-extensions",
        "typing-inspection",
    ):
        distribution = importlib.metadata.distribution(name)
        base = Path(distribution.locate_file("")).resolve()
        for member in distribution.files or ():
            source = Path(distribution.locate_file(member)).resolve()
            if source.is_file() and source.is_relative_to(base):
                target = site / source.relative_to(base)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    shutil.copytree(ROOT / "src/yorunge", site / "yorunge", ignore=shutil.ignore_patterns("*.pyc"))
    metadata = site / "yorunge-0.1.0.dev0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.4\nName: yorunge\nVersion: 0.1.0.dev0\nRequires-Dist: httpx\n",
        encoding="utf-8",
    )
    return prefix, python, site


def test_runtime_only_isolated_child_uses_actual_tls_and_all_new_product_paths(
    runtime_tree, tmp_path
):
    prefix, python, _ = runtime_tree
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        assert acceptance.verify(python, prefix, tmp_path) == {
            "http_smoke": "passed",
            "stream_smoke": "passed",
        }
    for case in acceptance.CASES:
        report = json.loads((tmp_path / (case + "-origins.json")).read_text())
        assert acceptance.REQUIRED_MODULES.issubset(report["modules"])
        assert all(Path(value).is_relative_to(prefix) for value in report["modules"].values())
        assert Path(report["metadata"]).is_relative_to(prefix)
        if case == "discovery":
            assert acceptance.DISCOVERY_MODULES.issubset(report["modules"])


@pytest.mark.parametrize("mutation", ["terms-type", "selected", "auth", "warning", "data-type"])
def test_installed_discovery_oracle_rejects_identity_claims_and_coercion(mutation):
    # Independent critical-field vector; actual full wire is exercised above
    # using the isolated installation and the real TLS endpoint.
    data = {
        "schema_version": 1,
        "service_id": "evren-llm",
        "profile": "installed",
        "terms": {"accepted": False, "current_version": 7, "is_material": True},
        "profile_preference": {
            "account_id": "platform-account",
            "project_id": "platform-project",
            "service_scope": "unknown",
        },
        "selected": {"account_id": None, "project_id": None},
        "provider": {
            "principal_id": None,
            "account_id": None,
            "organization_id": None,
            "project_id": None,
            "identity_status": "not_exposed",
        },
        "authorization_scope": None,
        "validation": "unverified",
        "consistency": "not_guaranteed",
        "observations": [{"authentication": "unknown"}],
        "reasons": [
            "authorization_not_verified",
            "identity_not_exposed",
            "profile_scope_unknown",
            "remote_snapshot_not_guaranteed",
            "terms_not_accepted",
        ],
    }
    envelope = {
        "schema_version": 1,
        "operation_id": None,
        "status": "completed",
        "data": data,
        "warnings": ["context_not_verified"],
    }
    acceptance.verify_output("discovery", 0, acceptance.wire(envelope), b"")
    if mutation == "terms-type":
        data["terms"]["accepted"] = 0
    elif mutation == "selected":
        data["selected"]["project_id"] = "platform-project"
    elif mutation == "auth":
        data["observations"][0]["authentication"] = "verified"
    elif mutation == "warning":
        envelope["warnings"] = []
    else:
        envelope["data"] = []
    encoded = acceptance.wire(envelope)
    with pytest.raises(ValueError):
        acceptance.verify_output("discovery", 0, encoded, b"")


@pytest.mark.parametrize("kind", ["prefix", "product", "metadata", "lazy-module", "runtime-only"])
def test_installed_origin_guard_rejects_foreign_and_late_sources(runtime_tree, tmp_path, kind):
    prefix, python, _ = runtime_tree
    # The guard runs in a real isolated interpreter. Source injection is solely
    # the negative test input; acceptance itself has no such fallback.
    injection = {
        "prefix": "expected = expected / 'wrong-prefix'",
        "product": "sys.path.insert(0, str(root / 'src'))",
        "metadata": (
            "foreign = Path(sys.argv[3]); "
            "info = foreign / 'yorunge-0.1.0.dev0.dist-info'; info.mkdir(); "
            "(info / 'METADATA').write_text('Metadata-Version: 2.4\\nName: yorunge\\n'"
            "'Version: 0.1.0.dev0\\nRequires-Dist: httpx\\n'); "
            "sys.path.insert(0, str(foreign))"
        ),
        "lazy-module": (
            "foreign = types.ModuleType('yorunge.foreign_lazy'); "
            "foreign.__file__ = str(root / 'src/yorunge/domain/models.py'); "
            "sys.modules[foreign.__name__] = foreign"
        ),
        "runtime-only": (
            "foreign = Path(sys.argv[3]); (foreign / 'pytest.py').write_text(''); "
            "sys.path.insert(0, str(foreign))"
        ),
    }[kind]
    script = (
        "import sys, types; from pathlib import Path; "
        "root=Path(sys.argv[1]); expected=Path(sys.argv[2]); "
        "sys.path.insert(0, str(root)); "
        + injection
        + "; from tests.fixtures.installed_transport import installed_origins; "
        "import yorunge.adapters.http_transport; import yorunge.application.stream_results; "
        "import yorunge.cli.output; installed_origins(expected)"
    )
    child = subprocess.run(
        [str(python), "-I", "-c", script, str(ROOT), str(prefix), str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert child.returncode != 0
    assert {
        "prefix": "interpreter prefix mismatch",
        "product": "product import outside installed environment",
        "metadata": "distribution metadata outside installed environment",
        "lazy-module": "product import outside installed environment: yorunge.foreign_lazy",
        "runtime-only": "runtime-only environment",
    }[kind] in child.stderr


def test_worker_rejects_nonisolated_interpreter_before_contacting_server(runtime_tree, tmp_path):
    prefix, python, _ = runtime_tree
    child = subprocess.run(
        [
            str(python),
            str(Path(acceptance.__file__)),
            "--case",
            "http",
            "--venv",
            str(prefix),
            "--ca",
            str(tmp_path / "absent.pem"),
            "--port",
            "1",
            "--origins",
            str(tmp_path / "origins.json"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert child.returncode != 0
    assert "installed smoke requires isolated Python" in child.stderr
    assert not (tmp_path / "origins.json").exists()


@pytest.mark.parametrize(
    "case,code,stdout,stderr",
    [
        ("http", 0, acceptance.wire({"text": acceptance.TEXT}), b""),
        ("http-invalid", 0, acceptance.wire(acceptance.result_payload()), b""),
        (
            "stream",
            0,
            acceptance.wire(acceptance.event(2, "result", acceptance.result_payload())),
            b"",
        ),
        (
            "stream-trailing",
            0,
            acceptance.wire(acceptance.progress())
            + acceptance.wire(acceptance.event(2, "result", acceptance.result_payload())),
            b"",
        ),
        (
            "stream-truncated",
            0,
            acceptance.wire(acceptance.progress())
            + acceptance.wire(acceptance.event(2, "result", acceptance.result_payload())),
            b"",
        ),
        (
            "stream",
            0,
            acceptance.wire(acceptance.progress())
            + acceptance.wire(acceptance.event(2, "result", acceptance.result_payload()))
            + b"\n",
            b"",
        ),
        (
            "stream",
            0,
            acceptance.wire(acceptance.progress())
            + acceptance.wire(acceptance.event(2, "result", acceptance.result_payload())),
            b"warning\n",
        ),
    ],
)
def test_acceptance_rejects_raw_untyped_incomplete_or_fake_completed_output(
    case, code, stdout, stderr
):
    with pytest.raises(ValueError):
        acceptance.verify_output(case, code, stdout, stderr)


def error_output(case):
    """Independent expected catalog values, never read from the product/helper."""
    bound = case != "http-invalid"
    code = "stream_interrupted" if case == "stream-truncated" else "invalid_response"
    envelope = {
        "schema_version": 1,
        "code": code,
        "message": (
            "Yanıt akışı doğrulanmış terminal sonuç olmadan kesildi."
            if code == "stream_interrupted"
            else "Yanıt beklenen biçim, içerik veya boyut koşullarını karşılamıyor."
        ),
        "operation_id": acceptance.OPERATION if bound else None,
        "retryable": False,
        "details": {"reason_code": code, "capacity_kind": None} if bound else {},
    }
    return acceptance.event(2, "error", envelope) if bound else envelope


@pytest.mark.parametrize("case", ["http-invalid", "stream-trailing", "stream-truncated"])
@pytest.mark.parametrize("message", [None, "wrong catalog message"])
def test_error_acceptance_rejects_null_or_wrong_message(case, message):
    output = error_output(case)
    payload = output if case == "http-invalid" else output["payload"]
    payload["message"] = message
    encoded = acceptance.wire(output)
    stdout = b"" if case == "http-invalid" else acceptance.wire(acceptance.progress()) + encoded
    stderr = encoded if case == "http-invalid" else b""
    with pytest.raises(ValueError):
        acceptance.verify_output(case, 1, stdout, stderr)


@pytest.mark.parametrize(
    "case,original,replacement",
    [
        (case, b'"event":"error"', b'"event":"result","event":"error"')
        for case in ("stream-trailing", "stream-truncated")
    ]
    + [
        (case, b'"code":', b'"code":"wrong-code","code":')
        for case in ("http-invalid", "stream-trailing", "stream-truncated")
    ]
    + [
        (case, b'"reason_code":', b'"reason_code":"wrong-code","reason_code":')
        for case in ("stream-trailing", "stream-truncated")
    ],
)
def test_error_acceptance_rejects_duplicate_keys_at_every_depth(case, original, replacement):
    encoded = acceptance.wire(error_output(case))
    assert encoded.count(original) == 1
    encoded = encoded.replace(original, replacement)
    stdout = b"" if case == "http-invalid" else acceptance.wire(acceptance.progress()) + encoded
    stderr = encoded if case == "http-invalid" else b""
    with pytest.raises(ValueError):
        acceptance.verify_output(case, 1, stdout, stderr)


def test_http_error_acceptance_allows_json_whitespace_with_correct_catalog_message():
    encoded = (json.dumps(error_output("http-invalid"), ensure_ascii=False) + "\n").encode("utf-8")
    acceptance.verify_output("http-invalid", 1, b"", encoded)


@pytest.mark.parametrize("case", ["http-invalid", "stream-trailing", "stream-truncated"])
def test_error_acceptance_rejects_json_encoding_autodetection(case):
    # UTF-16BE ends with the same LF byte and can pass json.loads(bytes)'s
    # implicit encoding detection. Product wire is strictly UTF-8.
    encoded = (json.dumps(error_output(case)) + "\n").encode("utf-16-be")
    stdout = b"" if case == "http-invalid" else acceptance.wire(acceptance.progress()) + encoded
    stderr = encoded if case == "http-invalid" else b""
    with pytest.raises(ValueError):
        acceptance.verify_output(case, 1, stdout, stderr)
