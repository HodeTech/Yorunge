"""What round one found nobody pinning in scripts/surface_installation.py: every closed gate."""

import json
import subprocess

import pytest

from tests.contracts.test_surface_installation import HELPER, altered
from tests.contracts.test_surface_installation import installed as installed

# (smoke, nth guarded gate command) -> every closed gate the smokes assert
RESUME_GATES = 5
VERSIONS_GATES = 7  # check, list, show, bind, bind-onto-directory, malformed list, malformed bind


def guarded_commands(command):
    return len(command) > 3 and command[1:3] == ["-I", "-c"]


@pytest.mark.parametrize("damage", ["code", "exit"])
@pytest.mark.parametrize("nth", range(VERSIONS_GATES))
def test_gap_every_versions_gate_is_asserted_by_code_and_exit(installed, monkeypatch, damage, nth):
    seen = []

    def edit(command, result):
        if guarded_commands(command) and "versions" in command:
            seen.append(command)
            if len(seen) - 1 == nth:
                value = json.loads(result.stderr)
                if damage == "code":
                    value["code"] = "invalid_response"
                return subprocess.CompletedProcess(
                    result.args,
                    result.returncode + 1 if damage == "exit" else result.returncode,
                    "",
                    json.dumps(value),
                )
        return result

    altered(monkeypatch, edit)
    with pytest.raises(ValueError, match="did not end closed as"):
        HELPER["verify_versions"](*installed)
    assert len(seen) == nth + 1


@pytest.mark.parametrize("damage", ["code", "exit"])
@pytest.mark.parametrize("nth", range(RESUME_GATES))
def test_gap_every_resume_gate_is_asserted_by_code_and_exit(installed, monkeypatch, damage, nth):
    seen = []

    def edit(command, result):
        if guarded_commands(command) and "upload" in command:
            seen.append(command)
            if len(seen) - 1 == nth:
                value = json.loads(result.stderr)
                if damage == "code":
                    value["code"] = "invalid_response"
                return subprocess.CompletedProcess(
                    result.args,
                    result.returncode + 1 if damage == "exit" else result.returncode,
                    "",
                    json.dumps(value),
                )
        return result

    altered(monkeypatch, edit)
    with pytest.raises(ValueError, match="did not end closed as"):
        HELPER["verify_resume"](*installed)
    assert len(seen) == nth + 1
