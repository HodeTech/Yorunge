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
    venv.EnvBuilder(with_pip=False).create(prefix)
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
