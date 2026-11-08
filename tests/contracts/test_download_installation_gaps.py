"""What round one found nobody pinning in scripts/download_installation.py: every closed gate."""

import json
import subprocess

import pytest

from tests.contracts.test_download_installation import development as development
from tests.contracts.test_download_installation import helper as helper

pytestmark = pytest.mark.usefixtures("evidence_publication_context")

GATES = [
    ("download without a key", "credential_unavailable/3"),
    ("download onto a file", "download_output_exists/2"),
    ("download beside a missing parent", "download_target_invalid/2"),
    ("download of a malformed version", "invalid_request/2"),
    ("download with a malformed digest", "invalid_request/2"),
]


@pytest.mark.parametrize(
    ("index", "expected"), [(i, g[1]) for i, g in enumerate(GATES)], ids=[g[0] for g in GATES]
)
@pytest.mark.parametrize("damage", ["exit", "code"])
def test_gap_every_closed_download_gate_is_asserted_by_code_and_exit(
    development, helper, monkeypatch, index, expected, damage
):
    console, python, scratch, certificates, environment, run = development
    namespace = helper["surface"].__globals__
    real = namespace["SURFACE"]["execute"]
    seen = []

    def wrong(command, cwd, issued):
        result = real(command, cwd, issued)
        if "--weights-out" in command:
            seen.append(command)
            if len(seen) - 1 == index:
                if damage == "exit":
                    return subprocess.CompletedProcess(
                        result.args, result.returncode + 1, result.stdout, result.stderr
                    )
                envelope = json.loads(result.stderr)
                envelope["code"] = "invalid_response"
                return subprocess.CompletedProcess(
                    result.args, result.returncode, result.stdout, json.dumps(envelope)
                )
        return result

    monkeypatch.setitem(namespace["SURFACE"], "execute", wrong)
    with pytest.raises(ValueError, match="did not end closed as " + expected):
        helper["surface"](python, console, scratch, run, certificates, environment)
    assert len(seen) == index + 1  # the first damaged gate stops the smoke


def test_gap_sdist_is_a_known_artifact_kind(helper, tmp_path):
    # the kind check passes for both kinds: it is the next statement (git) that fails here
    for kind in ("wheel", "sdist"):
        with pytest.raises(Exception) as caught:
            helper["verify"](
                tmp_path / "py",
                tmp_path,
                tmp_path / "no-such-root",
                tmp_path,
                tmp_path / "w",
                {},
                kind,
            )
        assert "unknown installation download artifact" not in str(caught.value)


def test_the_stderr_of_the_cli_download_is_kept_as_it_was_even_when_it_fails_the_smoke(
    development, helper, monkeypatch
):
    from types import SimpleNamespace

    console, python, scratch, certificates, environment, run = development
    namespace = helper["surface"].__globals__
    real_run = namespace["subprocess"].run

    def noisy(command, **keywords):
        result = real_run(command, **keywords)
        if "--sha256" in command:  # the real download, with something said on stderr afterwards
            return subprocess.CompletedProcess(
                result.args, result.returncode, result.stdout, b"warning: noise"
            )
        return result

    shim = SimpleNamespace(
        **{name: getattr(subprocess, name) for name in dir(subprocess) if not name.startswith("_")}
    )
    shim.run = noisy
    monkeypatch.setitem(namespace, "subprocess", shim)
    with pytest.raises(ValueError, match="installed download failed"):
        helper["surface"](python, console, scratch, run, certificates, environment)
    assert (run / "client-stderr.txt").read_bytes() == b"warning: noise"
    assert json.loads((run / "client-stdout.json").read_bytes())  # the console's output is kept


def test_a_failed_cli_download_keeps_its_stderr_and_no_empty_stdout_original(
    development, helper, monkeypatch
):
    """A failed ``models download`` prints nothing on stdout: an empty ``client-stdout.json``
    would be refused by the privacy scan and hide the real cause, so that file is not kept."""
    from types import SimpleNamespace

    console, python, scratch, certificates, environment, run = development
    namespace = helper["surface"].__globals__
    real_run = namespace["subprocess"].run
    envelope = b'{"schema_version":1,"code":"download_write_failed"}'

    def failing(command, **keywords):
        result = real_run(command, **keywords)
        if "--sha256" in command:
            return subprocess.CompletedProcess(result.args, 2, b"", envelope)
        return result

    shim = SimpleNamespace(
        **{name: getattr(subprocess, name) for name in dir(subprocess) if not name.startswith("_")}
    )
    shim.run = failing
    monkeypatch.setitem(namespace, "subprocess", shim)
    with pytest.raises(ValueError, match="installed download failed: exit 2"):
        helper["surface"](python, console, scratch, run, certificates, environment)
    assert (run / "client-stderr.txt").read_bytes() == envelope
    assert not (run / "client-stdout.json").exists()
