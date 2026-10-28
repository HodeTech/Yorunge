"""Selective parser construction preserves help, precedence and repeated parsing."""

import argparse
from pathlib import Path

import pytest

from yorunge import cli


def test_cached_parser_does_not_build_unselected_families(monkeypatch):
    def unexpected(parser):
        pytest.fail("unselected execution family was constructed")

    monkeypatch.setattr(cli, "execution_options", unexpected)
    root = cli.parser()
    args = root.parse_args(["capabilities", "--task", "llm.train", "--cached", "--output", "json"])
    assert args.cached
    assert args.task == "llm.train"
    with pytest.raises(SystemExit) as result:
        root.parse_args(["capabilities", "--help"])
    assert result.value.code == 0


def test_metadata_and_root_help_leave_unused_option_builders_unloaded(monkeypatch, capsys):
    def unexpected(parser):
        pytest.fail("metadata loaded a command family")

    for name in ("_context_options", "_state_options", "_capability_options", "_plan_options"):
        monkeypatch.setattr(cli, name, unexpected)
    root = cli.parser()
    with pytest.raises(SystemExit) as result:
        root.parse_args(["--help"])
    assert result.value.code == 0
    output = capsys.readouterr().out
    for command in ("init", "doctor", "context", "state", "capabilities", "plan", "train"):
        assert command in output
    with pytest.raises(SystemExit) as result:
        root.parse_args(["--version"])
    assert result.value.code == 0
    assert capsys.readouterr().out.startswith("yorunge ")


@pytest.mark.parametrize(
    "argv",
    [
        ["--output", "json", "context", "show", "--profile", "work"],
        ["context", "--output", "json", "show", "--profile", "work"],
        ["context", "show", "--output", "json", "--profile", "work"],
    ],
)
def test_deferred_children_preserve_parent_options_and_parser_reuse(argv):
    root = cli.parser()
    for _ in range(2):
        args = root.parse_args(argv)
        assert args.output == "json"
        assert args.profile == "work"
        assert args.action == "show"
    namespace = argparse.Namespace(marker="retained")
    parsed, rest = root.parse_known_args(argv, namespace=namespace)
    assert parsed is namespace
    assert parsed.marker == "retained"
    assert rest == []


def test_nested_execution_preserves_leaf_validation_and_state_option_locations():
    root = cli.parser()
    args = root.parse_args(["plan", "execution", "list", "--limit", "7", "--state-dir", "fixture"])
    assert args.execution_action == "list"
    assert args.limit == 7
    assert args.state_dir == Path("fixture")
    for arguments in (
        ["plan", "execution", "show"],
        ["capabilities", "--cache"],
        ["state", "restore", "--backup", "fixture", "--conf"],
    ):
        with pytest.raises(cli.UsageError):
            root.parse_args(arguments)
    for arguments in (["state", "--state-dir", "a", "init"], ["state", "init", "--state-dir", "a"]):
        assert root.parse_args(arguments).state_dir == Path("a")
