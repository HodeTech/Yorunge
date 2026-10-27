"""Exercise the actual CI metadata guard, including fork and malformed events."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-pr-policy.py"


@pytest.mark.parametrize(
    "base,head,head_repository,accepted",
    [
        ("development", "feat/example", "HodeTech/Yorunge", True),
        ("development", "fix/example", "contributor/Yorunge", True),
        ("development", "Master", "HodeTech/Yorunge", True),
        ("Master", "development", "HodeTech/Yorunge", True),
        ("Master", "feat/example", "HodeTech/Yorunge", False),
        ("Master", "development", "contributor/Yorunge", False),
        ("Master", "Development", "HodeTech/Yorunge", False),
        ("other", "feat/example", "HodeTech/Yorunge", False),
    ],
)
def test_pr_routes(tmp_path, base, head, head_repository, accepted):
    event = {
        "pull_request": {
            "base": {"ref": base, "repo": {"full_name": "HodeTech/Yorunge"}},
            "head": {"ref": head, "repo": {"full_name": head_repository}},
        }
    }
    result = invoke(tmp_path, json.dumps(event))
    assert (result.returncode == 0) is accepted


def invoke(tmp_path, content, event_name="pull_request_target"):
    event_file = tmp_path / "event.json"
    event_file.write_text(content)
    environment = dict(os.environ)
    environment.update(
        GITHUB_EVENT_NAME=event_name,
        GITHUB_EVENT_PATH=str(event_file),
        GITHUB_REPOSITORY="HodeTech/Yorunge",
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT)], env=environment, capture_output=True, text=True, timeout=5
    )


@pytest.mark.parametrize("content", ["{broken", "{}", "[]", '{"pull_request": null}'])
def test_missing_metadata_fails_closed(tmp_path, content):
    result = invoke(tmp_path, content)
    assert result.returncode == 1
    assert "Traceback" not in result.stdout + result.stderr


def test_untrusted_event_context_is_rejected(tmp_path):
    result = invoke(tmp_path, "{}", event_name="pull_request")
    assert result.returncode == 1
