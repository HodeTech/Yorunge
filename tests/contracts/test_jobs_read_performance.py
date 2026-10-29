"""Local reads stay independent of execution composition and keep text validation."""

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge.domain.execution import InputBinding
from yorunge.domain.models import has_control_characters


def test_control_detection_preserves_ascii_c1_and_unicode_boundaries():
    characters = [chr(code) for code in range(256)] + [
        "\u0301",
        "\u200b",
        "\u200d",
        "\u2028",
        "\u202e",
        "\ufeff",
        "\ud800",
        "🌍",
    ]
    for character in characters:
        expected = ord(character) < 32 or 127 <= ord(character) <= 159
        for value in (character, "a" * 1024 + character, character + "🌍"):
            assert has_control_characters(value) is expected
    assert has_control_characters("") is False


def test_control_detection_cannot_be_overridden_by_string_subclasses():
    class Text(str):
        def isascii(self):
            return True

        def isprintable(self):
            return True

    assert has_control_characters(Text("prefix\x7fsuffix")) is True
    assert has_control_characters(Text("prefix\x85suffix")) is True
    assert has_control_characters(Text("printable")) is False


@pytest.mark.parametrize("character", ["\x00", "\t", "\x1f", "\x7f", "\x80", "\x9f"])
def test_saved_input_binding_rejects_control_characters(character):
    with pytest.raises(ValidationError):
        InputBinding(role="data.manifest", path=f"data{character}.jsonl", size=0, digest="a" * 64)


@pytest.mark.parametrize("action", ["list", "show"])
def test_jobs_read_does_not_import_execution_or_cache_composition(admitted_operation, action):
    state, _, record, _, _ = admitted_operation
    script = """
import importlib.abc
import sys
from pathlib import Path

blocked = (
    'yorunge.adapters.capability_cache', 'yorunge.adapters.identity',
    'yorunge.adapters.input_files', 'yorunge.adapters.secrets',
    'yorunge.application.execution', 'yorunge.application.capabilities',
    'yorunge.application.planning', 'httpx', 'yaml',
)
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + '.') for name in blocked):
            raise AssertionError('local read imported ' + fullname)
sys.meta_path.insert(0, Guard())
from yorunge import api
state, action, identifier = sys.argv[1:]
result = (api.list_jobs(state_dir=Path(state)) if action == 'list'
          else api.show_job(identifier, state_dir=Path(state)))
data = result.data
actual = data.jobs[0].operation_id if action == 'list' else data.operation.operation_id
assert actual == identifier
assert result.warnings == ('local_history_only',)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(state), action, record.summary.operation_id],
        cwd=Path(state).parent,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
