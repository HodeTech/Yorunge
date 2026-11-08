"""Installed download smoke failures retain metadata/measurement bytes outside temporary venvs."""

import base64
import copy
import json
import runpy
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.contracts.test_download_evidence import proof, row
from tests.contracts.test_download_evidence import server as server_account
from tests.contracts.test_surface_installation import clean_environment, installed_console

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.usefixtures("evidence_publication_context")
FAILURES = [
    "source_unreadable",
    "metadata_exit",
    "metadata_utf8",
    "metadata_stderr",
    "surface",
    "measure",
    "judged",
    "source_changed",
]
STAGES = {
    "source_unreadable": "source",
    "metadata_exit": "metadata",
    "metadata_utf8": "metadata",
    "metadata_stderr": "metadata",
    "surface": "surface",
    "measure": "measurement",
    "judged": "judgement",
    "source_changed": "judgement",
}


def retained(rejected):
    return {item["name"]: base64.b64decode(item["content_base64"]) for item in rejected["files"]}


CI = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "HodeTech/Yorunge", "GITHUB_RUN_ID": "123"}


@pytest.mark.parametrize("ci", [False, True])
@pytest.mark.parametrize("failure", [None, *FAILURES])
def test_installed_smoke_surface_source_and_metadata_failures_cannot_be_hidden(
    tmp_path, monkeypatch, failure, ci
):
    helper = runpy.run_path(str(ROOT / "scripts/download_installation.py"))
    namespace = helper["verify"].__globals__
    root = tmp_path.resolve()
    (root / "docs/research").mkdir(parents=True)
    (root / "dist").mkdir()
    synthetic = proof()
    before = synthetic["source_before"]
    calls = []

    def source(root):
        calls.append("source")
        if failure == "source_unreadable":
            raise ValueError("synthetic source map failure")
        value = copy.deepcopy(before)
        if failure == "source_changed" and len(calls) > 1:
            value["source_sha256"]["src/yorunge/__init__.py"] = "9" * 64
        return value

    def run(command, **kwargs):
        if command[0] == "git":
            return SimpleNamespace(stdout="a" * 40)
        assert command[1:3] == ["-I", "-c"]
        kwargs["stdout"].write(
            b"\xffbroken"
            if failure == "metadata_utf8"
            else json.dumps(synthetic["wheel_metadata_sha256"]).encode()
        )
        if failure == "metadata_exit":
            kwargs["stderr"].write(b"metadata failed")
            raise subprocess.CalledProcessError(1, command)
        if failure == "metadata_stderr":
            kwargs["stderr"].write(b"a warning the probe printed while exiting 0")
        return SimpleNamespace(returncode=0)

    def surface(*arguments):
        calls.append(("surface", arguments))
        run_directory = arguments[3]
        (run_directory / "measured-server").mkdir(parents=True)
        (run_directory / "client-stdout.json").write_bytes(b'{"console":"output"}\n')
        (run_directory / "client-stderr.txt").write_bytes(b"")
        (run_directory / "measured-server/stdout.json").write_bytes(b'{"server":"account"}\n')
        if failure == "surface":
            raise ValueError("synthetic surface failure")

    def measured(*arguments):
        calls.append(("measure_one", arguments))
        if failure == "measure":
            raise ValueError("synthetic worker failure")
        return row("16", 1, 0)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setitem(namespace["EVIDENCE"], "source", source)
    monkeypatch.setitem(
        namespace["STREAM"], "locked_runtime", lambda root: synthetic["locked_runtime"]
    )
    monkeypatch.setitem(
        namespace["HTTP"], "certificate", lambda *args, **kwargs: (root / "ca", root / "key")
    )
    monkeypatch.setitem(namespace, "surface", surface)
    monkeypatch.setitem(namespace["DRIVER"], "measure_one", measured)
    if failure == "judged":
        monkeypatch.setitem(namespace["EVIDENCE"], "evaluate_run", lambda *args: False)
        monkeypatch.setitem(
            namespace["EVIDENCE"],
            "judge_run",
            lambda *args: {"rss_upper": False, "result_sha256": False, "window_seconds": True},
        )
    python, prefix = root / "env/bin/python", root / "env"
    scratch, workspace = root / "scratch", root / "workspace"
    arguments = (python, prefix, root, scratch, workspace, dict(CI) if ci else {}, "wheel")
    rejection = root / "dist/installation-download-wheel-rejected.json"
    if failure is None:
        assert helper["verify"](*arguments) == "passed"
        assert not rejection.exists()
        # The CLI download runs first, into the next free sample slot, then the harness sample.
        steps = [call for call in calls if isinstance(call, tuple)]
        assert [name for name, _ in steps] == ["surface", "measure_one"]
        assert steps[0][1][:4] == (python, prefix / "bin/yorunge", scratch, workspace / "16-2")
        assert steps[1][1][:2] == (python, workspace) and steps[1][1][4:] == ("16", 1)
        assert calls.count("source") == 2  # before and after, around both steps
        manifest = json.loads((workspace / "source-manifest.json").read_bytes())
        assert manifest == {
            "source_sha256": before["source_sha256"],
            "locked_runtime": synthetic["locked_runtime"],
            "metadata_sha256": synthetic["wheel_metadata_sha256"],
        }
        for name in ("source-before.json", "source-after.json", "stdout.json"):
            assert (workspace / name).is_file()
        assert not (workspace / "controller-error.json").exists()
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)) as caught:
            helper["verify"](*arguments)
        if failure == "judged":
            assert "failed rules rss_upper, result_sha256; source map changed False" in str(
                caught.value
            )
        if failure == "source_changed":
            assert "failed rules none; source map changed True" in str(caught.value)
        rejected = helper["CHECKS"]["decode"](rejection.read_bytes())
        assert helper["DIAGNOSTIC"]["summarize"](rejected)["accepted"] is False
        assert rejected["rejection_reason"] == "interrupted_measurement"
        assert rejected["source_commit"] == "a" * 40
        assert rejected["run_url"] == (
            "https://github.com/HodeTech/Yorunge/actions/runs/123" if ci else None
        )
        files = retained(rejected)
        assert json.loads(files["controller-error.json"]) == {
            "outcome": "incomplete_installation_download",
            "stage": STAGES[failure],
        }
        if failure not in {"source_unreadable"}:
            assert {"source-before.json", "metadata-stdout.json", "metadata-stderr.txt"} <= set(
                files
            )
        if failure in {"surface", "measure", "judged", "source_changed"}:
            assert {"16-2/client-stdout.json", "16-2/measured-server/stdout.json"} <= set(files)
            assert files["16-2/client-stdout.json"] == b'{"console":"output"}\n'
        if failure == "metadata_utf8":
            assert (workspace / "metadata-stdout.json").read_bytes() == b"\xffbroken"
            assert not any((root / "docs/research").iterdir())
        else:
            assert helper["CHECKS"]["verify"](root) == 1
    if failure not in {"source_unreadable"}:
        assert (workspace / "metadata-stdout.json").is_file()


def test_an_unknown_artifact_kind_is_refused_before_anything_is_made(tmp_path):
    helper = runpy.run_path(str(ROOT / "scripts/download_installation.py"))
    arguments = (tmp_path, tmp_path, tmp_path, tmp_path, tmp_path / "workspace", {}, "zip")
    with pytest.raises(ValueError, match="unknown installation download artifact"):
        helper["verify"](*arguments)
    assert not (tmp_path / "workspace").exists()


def test_ci_installation_diagnostics_require_real_run_identity_before_start(tmp_path):
    helper = runpy.run_path(str(ROOT / "scripts/download_installation.py"))
    assert helper["run_url"]({}) is None
    assert (
        helper["run_url"](
            {
                "GITHUB_ACTIONS": "true",
                "GITHUB_REPOSITORY": "HodeTech/Yorunge",
                "GITHUB_RUN_ID": "123",
            }
        )
        == "https://github.com/HodeTech/Yorunge/actions/runs/123"
    )
    environment = {"GITHUB_ACTIONS": "true"}
    arguments = (
        tmp_path / "python",
        tmp_path,
        tmp_path,
        tmp_path,
        tmp_path / "workspace",
        environment,
        "wheel",
    )
    with pytest.raises(ValueError):
        helper["verify"](*arguments)
    assert not (tmp_path / "workspace").exists()


# --- the surface: what a person and the object server see ----------------------------------

SERVER = runpy.run_path(str(ROOT / "tests/fixtures/download_native_server.py"))
SIZE = 16 * 1_048_576


@pytest.fixture(scope="module")
def helper():
    return runpy.run_path(str(ROOT / "scripts/download_installation.py"))


@pytest.fixture(scope="module")
def payload(tmp_path_factory, helper):
    """The 16 MiB fixture object, written once from the server's own generator."""
    path = tmp_path_factory.mktemp("payload") / "object.bin"
    with path.open("wb") as target:
        for block in SERVER["body_blocks"](0, SIZE):
            target.write(block)
    assert helper["file_digest"](path) == (SIZE, helper["DATA"]["expected_sha256"](SIZE))
    return path


@pytest.fixture
def staged(tmp_path, helper, payload):
    """A finished, correct download: the files, the console's output and the server's account."""
    data = helper["DATA"]
    work, run = tmp_path / "cli-download", tmp_path / "16-2"
    layout = data["paths"](work)
    layout.out.mkdir(parents=True)
    shutil.copyfile(payload, layout.target)
    occupied = work / "occupied" / "taken.onnx"
    occupied.parent.mkdir()
    occupied.write_bytes(b"mine")
    (run / "measured-server").mkdir(parents=True)
    oracle = data["expected_sha256"](SIZE)

    def account(changes=None):
        value = {**server_account("16", 4242), **(changes or {})}
        (run / "measured-server/stdout.json").write_bytes(data["canonical"](value) + b"\n")

    account()
    (run / "measured-server/stderr.txt").write_bytes(b"")
    stdout = data["canonical"](helper["summary"](layout.target, SIZE, oracle)) + b"\n"
    fetched = subprocess.CompletedProcess(["synthetic"], 0, stdout, b"")
    return SimpleNamespace(
        layout=layout,
        occupied=occupied,
        run=run,
        oracle=oracle,
        fetched=fetched,
        account=account,
        settle=lambda result=None: helper["settle"](
            result or fetched, layout, occupied, run, SIZE, oracle
        ),
    )


def test_the_options_the_installed_download_help_is_held_to(helper):
    assert helper["HELP"] == (
        "--version-id",
        "--format",
        "--weights-out",
        "--sha256",
        "--timeout",
        "--no-resume",
    )


def test_a_correct_download_settles(staged):
    staged.settle()


def test_the_summary_is_the_cli_result_the_installed_package_prints(helper, tmp_path):
    value = helper["summary"](tmp_path / "w.onnx", SIZE, "f" * 64)
    assert value["data"]["verification_level"] == "sha256_matched"
    assert value["data"]["expectation_source"] == "user_supplied"
    assert (value["status"], value["operation_id"], value["warnings"]) == ("completed", None, [])
    assert value["data"]["bytes"] == SIZE and value["data"]["resumed"] is False


@pytest.mark.parametrize(
    "path,value",
    [
        (("data", "bytes"), SIZE - 1),
        (("data", "bytes"), float(SIZE)),
        (("data", "sha256"), "0" * 64),
        (("data", "verification_level"), "transfer_complete"),
        (("data", "expectation_source"), "provider"),
        (("data", "resumed"), True),
        (("data", "resumed_from_bytes"), 1),
        (("data", "kind"), "download_partial"),
        (("data", "output_path"), "/elsewhere/weights.onnx"),
        (("data", "source", "format"), "pt"),
        (("data", "source", "fold"), 0),
        (("data", "source", "version_id"), "00000000-0000-4000-8000-000000000000"),
        (("status",), "failed"),
        (("operation_id",), "00000000-0000-4000-8000-000000000001"),
        (("warnings",), ["unexpected"]),
        (("schema_version",), 2),
        (("extra",), 1),
    ],
)
def test_a_result_that_differs_from_the_closed_summary_is_refused(helper, staged, path, value):
    document = helper["CHECKS"]["decode"](staged.fetched.stdout)
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    changed = subprocess.CompletedProcess(
        ["synthetic"], 0, helper["DATA"]["canonical"](document) + b"\n", b""
    )
    with pytest.raises(ValueError, match="differs from the closed summary"):
        staged.settle(changed)


@pytest.mark.parametrize(
    "stdout,stderr,code",
    [(b"", b"", 0), (b"not json", b"", 0), (b"[]\n", b"", 0), (b"{}\n", b"", 0)],
)
def test_a_result_that_is_not_the_closed_summary_at_all_is_refused(staged, stdout, stderr, code):
    with pytest.raises(ValueError):
        staged.settle(subprocess.CompletedProcess(["synthetic"], code, stdout, stderr))


@pytest.mark.parametrize("code,stderr", [(1, b""), (7, b""), (0, b"warning\n"), (-9, b"")])
def test_a_download_that_failed_or_spoke_on_stderr_is_refused(staged, code, stderr):
    ok = staged.fetched
    with pytest.raises(ValueError, match="installed download failed"):
        staged.settle(subprocess.CompletedProcess(ok.args, code, ok.stdout, stderr))


@pytest.mark.parametrize("damage", ["short", "long", "flipped", "empty", "missing"])
def test_bytes_that_differ_from_the_independent_oracle_are_refused(staged, damage):
    target = staged.layout.target
    content = target.read_bytes()
    if damage == "missing":
        target.unlink()
    else:
        target.write_bytes(
            {
                "short": content[:-1],
                "long": content + b"\x00",
                "flipped": content[:100] + bytes([content[100] ^ 1]) + content[101:],
                "empty": b"",
            }[damage]
        )
    with pytest.raises((ValueError, OSError)):
        staged.settle()


@pytest.mark.parametrize(
    "damage", ["stage", "sidecar", "taken_rewritten", "taken_removed", "parent"]
)
def test_files_that_should_not_exist_or_change_are_refused(staged, damage):
    if damage == "stage":
        (staged.layout.out / "weights.onnx.part").write_bytes(b"x")
    elif damage == "sidecar":
        (staged.layout.out / ".weights.onnx.json").write_bytes(b"{}")
    elif damage == "taken_rewritten":
        staged.occupied.write_bytes(b"theirs")
    elif damage == "taken_removed":
        staged.occupied.unlink()
    else:
        (staged.layout.out.parent / "missing").mkdir()
    with pytest.raises((ValueError, OSError)):
        staged.settle()


@pytest.mark.parametrize(
    "changes",
    [
        {"requests": {"json": 2, "signed": 1, "unexpected": 0}},
        {"requests": {"json": 1, "signed": 1, "unexpected": 1}},
        {"requests": {"json": 0, "signed": 1, "unexpected": 0}},
        {"credential_violations": 1},
        {"header_violations": 1},
        {"json_key_failures": 1},
        {"errors": 1},
        {"connection_count": 2},
        {"active_requests": 1},
        {"peak_active_requests": 3},
        {"max_block_bytes": 65_537},
        {"signed_header_names": ["accept-encoding", "host", "range"]},
        {"json_header_names": ["accept-encoding", "host"]},
        {"json_header_names": ["accept-encoding", "authorization", "host", "x-api-key"]},
        {"label": "256", "size": 256 * 1_048_576},
        {"extra_field": 1},
    ],
)
def test_a_server_account_that_shows_a_gate_or_a_stray_request_is_refused(staged, changes):
    staged.account(changes)
    with pytest.raises(ValueError):
        staged.settle()


def test_a_server_that_spoke_on_stderr_is_refused(staged):
    (staged.run / "measured-server/stderr.txt").write_bytes(b"Traceback (most recent call last)")
    with pytest.raises(ValueError, match="server wrote unexpected stderr"):
        staged.settle()


def test_a_missing_or_foreign_server_account_is_refused(staged):
    (staged.run / "measured-server/stdout.json").write_bytes(b'{"requests":{}}\n')
    with pytest.raises(ValueError):
        staged.settle()
    (staged.run / "measured-server/stdout.json").unlink()
    with pytest.raises((ValueError, OSError)):
        staged.settle()


# --- the real surface, against the development interpreter ---------------------------------


@pytest.fixture
def development(tmp_path, helper):
    """The development interpreter and its console, a scratch directory and a loopback CA."""
    console, python, scratch, environment = installed_console(tmp_path, clean_environment(tmp_path))
    certificates = helper["HTTP"]["certificate"](
        tmp_path / "cert", names=(helper["DATA"]["PLATFORM_HOST"],)
    )
    return console, python, scratch, certificates, environment, tmp_path / "16-2"


def test_the_real_surface_helps_refuses_downloads_and_leaves_its_evidence(development, helper):
    console, python, scratch, certificates, environment, run = development
    helper["surface"](python, console, scratch, run, certificates, environment)
    assert sorted(path.name for path in run.iterdir()) == [
        "client-stderr.txt",
        "client-stdout.json",
        "measured-server",
    ]
    assert (run / "client-stderr.txt").read_bytes() == b""
    document = helper["CHECKS"]["decode"]((run / "client-stdout.json").read_bytes())
    assert document["data"]["bytes"] == SIZE and document["data"]["resumed"] is False
    account = helper["DRIVER"]["decode_output"](run / "measured-server/stdout.json")
    assert account["requests"] == {"json": 1, "signed": 1, "unexpected": 0}
    assert (scratch / "cli-download/out").is_dir()
    assert not (scratch / "cli-download/missing").exists()


def test_a_gate_that_really_downloads_is_caught_by_the_server_account(
    development, helper, monkeypatch
):
    """Defect injection: the 'existing file' gate is pointed at a free path, so it succeeds."""
    console, python, scratch, certificates, environment, run = development
    namespace = helper["surface"].__globals__
    real = namespace["SURFACE"]["execute"]

    def redirect(command, cwd, issued):
        command = [
            str(Path(word).with_name("free.onnx")) if word.endswith("taken.onnx") else word
            for word in command
        ]
        return real(command, cwd, issued)

    monkeypatch.setitem(namespace["SURFACE"], "execute", redirect)
    monkeypatch.setitem(namespace["SURFACE"], "check_error", lambda *arguments: {})
    with pytest.raises(ValueError, match="server account differs: .*requests"):
        helper["surface"](python, console, scratch, run, certificates, environment)
    assert (scratch / "cli-download/occupied/free.onnx").stat().st_size == SIZE
    assert (run / "client-stdout.json").is_file()  # the evidence is kept before it is judged


def test_a_console_without_the_download_options_fails_the_help_check(development, helper):
    console, python, scratch, certificates, environment, run = development
    console.write_text("#!/bin/sh\necho 'usage: yorunge models download --version-id'\n")
    with pytest.raises(ValueError, match="models download help failed.*--format"):
        helper["surface"](python, console, scratch, run, certificates, environment)
    assert not run.exists()  # nothing was started before the help was judged


def test_the_two_independent_byte_derivations_must_agree(helper, staged, monkeypatch):
    """A fixture oracle that matched the file but not the verifier's own derivation is refused."""
    namespace = helper["settle"].__globals__
    monkeypatch.setitem(namespace["EVIDENCE"], "object_sha256", lambda size: "0" * 64)
    with pytest.raises(ValueError, match="independent oracle"):
        staged.settle()
