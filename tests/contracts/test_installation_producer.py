"""The distribution verifier writes the closed v4 record and its two workspaces, or nothing."""

import json
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = runpy.run_path(str(ROOT / "scripts/verify-distributions.py"))
CHECKS = runpy.run_path(str(ROOT / "scripts/research_evidence.py"))
SMOKES = CHECKS["INSTALL_CHECKS_V4"][1:]
NEW = ("upload_smoke", "resume_smoke", "versions_smoke", "download_smoke")


def produce(monkeypatch, tmp_path, changes=None, *options):
    """Run the real ``main`` with ``verify_package`` replaced by a double that records its calls."""
    dist = tmp_path / "dist"
    dist.mkdir(exist_ok=True)
    for name in ("yorunge-0.1.0.dev0-py3-none-any.whl", "yorunge-0.1.0.dev0.tar.gz"):
        (dist / name).write_bytes(b"unused")
    calls = []

    def verify_package(package, uv, root, environment, upload_workspace, download_workspace):
        calls.append((package.name, upload_workspace, download_workspace, root))
        return {
            "archive": package.name,
            "sha256": "b" * 64,
            "members": 30,
            "origin_verified": True,
            **dict.fromkeys(SMOKES, "passed"),
            **(changes or {}),
        }

    monkeypatch.setitem(PRODUCER["main"].__globals__, "verify_package", verify_package)
    output = tmp_path / "installation.json"
    arguments = ["--uv", "uv", "--dist", str(dist), "--evidence-output", str(output), *options]
    monkeypatch.setattr(sys, "argv", ["verify-distributions.py", *arguments])
    return PRODUCER["main"], output, calls


def workspaces(tmp_path):
    return str(tmp_path / "upload"), str(tmp_path / "download")


def options(tmp_path):
    upload, download = workspaces(tmp_path)
    return ("--upload-workspace", upload, "--download-workspace", download)


def test_the_record_is_the_closed_v4_one_and_both_artifacts_get_their_own_workspaces(
    monkeypatch, tmp_path
):
    main, output, calls = produce(monkeypatch, tmp_path, None, *options(tmp_path))
    assert main() == 0
    report = json.loads(output.read_bytes())
    assert (report["schema_version"], report["report_kind"], report["passed"]) == (
        4,
        "installation_v4",
        True,
    )
    assert CHECKS["summarize"](report)["kind"] == "installation_v4"
    assert [set(row) for row in report["results"]] == [
        {"archive", "sha256", "members", *CHECKS["INSTALL_CHECKS_V4"]}
    ] * 2
    upload, download = (Path(name) for name in workspaces(tmp_path))
    assert [(name, up, down) for name, up, down, _ in calls] == [
        ("yorunge-0.1.0.dev0-py3-none-any.whl", upload, download),
        ("yorunge-0.1.0.dev0.tar.gz", upload, download),
    ]
    assert {root for *_, root in calls} == {ROOT}
    for directory in (upload, download):
        assert directory.is_dir() and directory.stat().st_mode & 0o777 == 0o700
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert report["source_commit"] == head


@pytest.mark.parametrize("name", NEW)
@pytest.mark.parametrize("status", ["failed", "not_run_unsupported_platform"])
def test_a_smoke_that_did_not_pass_makes_a_valid_record_that_fails(
    monkeypatch, tmp_path, name, status
):
    main, output, _ = produce(monkeypatch, tmp_path, {name: status}, *options(tmp_path))
    assert main() == 1
    report = json.loads(output.read_bytes())
    assert report["passed"] is False
    summary = CHECKS["summarize"](report)
    assert summary["passed"] is False and summary["checks"][name] == {status: 2}


def test_the_default_workspaces_are_the_ci_paths(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main, _, calls = produce(monkeypatch, tmp_path)
    assert main() == 0
    assert {(up, down) for _, up, down, _ in calls} == {
        (
            tmp_path / ".local/distribution-upload-check",
            tmp_path / ".local/distribution-download-check",
        )
    }
    assert (tmp_path / ".local/distribution-download-check").is_dir()


@pytest.mark.parametrize(
    "damage", ["exists", "link", "linked_parent", "same", "inside_upload", "around_upload"]
)
def test_unusable_workspaces_stop_everything_before_a_directory_is_made(
    monkeypatch, tmp_path, damage
):
    upload, download = (tmp_path / "upload", tmp_path / "download")
    if damage == "exists":
        download.mkdir()
    elif damage == "link":
        (tmp_path / "elsewhere").mkdir()
        download.symlink_to(tmp_path / "elsewhere")
    elif damage == "linked_parent":
        (tmp_path / "elsewhere").mkdir()
        (tmp_path / "linked").symlink_to(tmp_path / "elsewhere")
        download = tmp_path / "linked" / "download"
    elif damage == "same":
        download = upload
    elif damage == "inside_upload":
        download = upload / "download"
    else:
        upload, download = tmp_path / "all" / "upload", tmp_path / "all"
    main, _, calls = produce(
        monkeypatch,
        tmp_path,
        None,
        "--upload-workspace",
        str(upload),
        "--download-workspace",
        str(download),
    )
    before = sorted(tmp_path.rglob("*"))
    with pytest.raises(ValueError):
        main()
    assert not calls and sorted(tmp_path.rglob("*")) == before


def test_an_existing_record_is_never_replaced(monkeypatch, tmp_path):
    (tmp_path / "installation.json").write_bytes(b"earlier record")
    main, output, calls = produce(monkeypatch, tmp_path, None, *options(tmp_path))
    with pytest.raises(ValueError):
        main()
    assert output.read_bytes() == b"earlier record" and not calls
    assert not Path(workspaces(tmp_path)[0]).exists()


# --- verify_package: where the three new smokes run and what each result is called ---------


def verify_package_with_doubles(monkeypatch, tmp_path, name, platform="linux", results=None):
    """The real ``verify_package`` with the installer, the old smokes and the new ones doubled."""
    namespace = PRODUCER["verify_package"].__globals__
    calls, results = [], results or {}

    def run(command, *, cwd, environment, expected_code=0):
        if "prepare" in command:
            return json.dumps({"data": {"executable": False, "selection": {"tool": "forgelm"}}})
        if "import yorunge; print(yorunge.__file__)" in command:
            return str(cwd / "env/lib/yorunge/__init__.py")
        return ""

    def double(label, default="passed"):
        def smoke(*arguments):
            calls.append((label, arguments))
            return results.get(label, default)

        return smoke

    loaders = {
        "upload_installation.py": {"verify": double("upload")},
        "surface_installation.py": {
            "verify_resume": double("resume"),
            "verify_versions": double("versions"),
        },
        "download_installation.py": {"verify": double("download")},
    }
    monkeypatch.setitem(namespace, "run", run)
    monkeypatch.setitem(namespace, "inspect_archive", lambda package: ["member"])
    monkeypatch.setitem(namespace, "verify_installed_ndjson", double("ndjson"))
    monkeypatch.setitem(
        namespace,
        "verify_installed_transport",
        double("transport", {"http_smoke": "passed", "stream_smoke": "passed"}),
    )
    for old in ("datasets", "cache", "execution", "jobs"):
        monkeypatch.setitem(namespace, f"verify_installed_{old}", double(old))
    monkeypatch.setattr(runpy, "run_path", lambda path: loaders[Path(path).name])
    monkeypatch.setitem(namespace, "sys", SimpleNamespace(platform=platform, executable="python"))
    package = tmp_path / name
    package.write_bytes(b"synthetic archive")
    upload, download = tmp_path / "upload", tmp_path / "download"
    result = PRODUCER["verify_package"](package, "uv", ROOT, {"A": "b"}, upload, download)
    return result, calls, upload, download


@pytest.mark.parametrize(
    "name,kind", [("yorunge-1-py3-none-any.whl", "wheel"), ("yorunge-1.tar.gz", "sdist")]
)
def test_verify_package_runs_the_new_smokes_after_upload_in_their_own_workspaces(
    monkeypatch, tmp_path, capsys, name, kind
):
    result, calls, upload, download = verify_package_with_doubles(monkeypatch, tmp_path, name)
    steps = [call for call in calls if call[0] in {"upload", "resume", "versions", "download"}]
    assert [label for label, _ in steps] == ["upload", "resume", "versions", "download"]
    smokes = dict(steps)
    environment = {"A": "b"}
    # upload and download: (python, venv, root, scratch, workspace/kind, environment, kind)
    for label, workspace in (("upload", upload), ("download", download)):
        python, venv, root, scratch, where, issued, issued_kind = smokes[label]
        assert (python.name, venv.name, root, where, issued, issued_kind) == (
            "python",
            "env",
            ROOT,
            workspace / kind,
            environment,
            kind,
        )
        assert python.parent.parent == venv and scratch == venv.parent
    # resume and versions: (console, python, scratch, environment), the same installation
    for label in ("resume", "versions"):
        console, python, scratch, issued = smokes[label]
        assert (console.name, python.name, issued) == ("yorunge", "python", environment)
        assert console.parent == python.parent and scratch == python.parent.parent.parent
    assert {key: result[key] for key in CHECKS["INSTALL_CHECKS_V4"][1:]} == dict.fromkeys(
        CHECKS["INSTALL_CHECKS_V4"][1:], "passed"
    )
    assert json.loads(capsys.readouterr().out) == result


def test_each_new_result_is_the_result_of_its_own_smoke(monkeypatch, tmp_path):
    answers = {"upload": "u", "resume": "r", "versions": "v", "download": "d"}
    result, _, _, _ = verify_package_with_doubles(
        monkeypatch, tmp_path, "yorunge-1.tar.gz", results=answers
    )
    assert {key: result[key] for key in NEW} == {
        "upload_smoke": "u",
        "resume_smoke": "r",
        "versions_smoke": "v",
        "download_smoke": "d",
    }


def test_without_state_support_the_new_smokes_are_not_run_and_say_so(monkeypatch, tmp_path):
    result, calls, _, _ = verify_package_with_doubles(
        monkeypatch, tmp_path, "yorunge-1-py3-none-any.whl", platform="win32"
    )
    assert not [call for call in calls if call[0] in {"resume", "versions", "download", "upload"}]
    for key in NEW:
        assert result[key] == "not_run_unsupported_platform"
