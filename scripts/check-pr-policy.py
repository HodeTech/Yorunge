"""Validate PR routing from event metadata, without loading code from the PR head."""

from __future__ import annotations

import json
import os
from pathlib import Path


def nested_string(document: object, *keys: str) -> str:
    current: object = document
    for key in keys:
        if not isinstance(current, dict):
            raise ValueError("Missing pull request metadata.")
        current = current.get(key)
    if not isinstance(current, str) or not current:
        raise ValueError("Missing pull request metadata.")
    return current


def validate_policy(event: object, repository: str) -> None:
    base = nested_string(event, "pull_request", "base", "ref")
    base_repository = nested_string(event, "pull_request", "base", "repo", "full_name")
    if not repository or base_repository.casefold() != repository.casefold():
        raise ValueError("Unexpected base repository.")
    if base not in ("development", "Master"):
        raise ValueError("Pull requests must target development or Master.")
    if base == "Master":
        head = nested_string(event, "pull_request", "head", "ref")
        head_repository = nested_string(event, "pull_request", "head", "repo", "full_name")
        if head != "development" or head_repository.casefold() != repository.casefold():
            raise ValueError(
                "Master pull requests must originate from this repository's development."
            )


def main() -> int:
    try:
        if os.environ.get("GITHUB_EVENT_NAME") != "pull_request_target":
            raise ValueError("Only trusted pull_request_target events are accepted.")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        validate_policy(event, os.environ["GITHUB_REPOSITORY"])
    except (OSError, ValueError, KeyError):
        # Do not echo untrusted event values or parser exceptions.
        print("Pull request branch policy failed; check the base and source repository/branch.")
        return 1
    print("Pull request branch policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
