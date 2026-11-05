"""Synthetic declared provenance for archive tests; never a producer attestation."""


def synthetic_context(root, *, ci=False):
    home = "/Users/synthetic-private-operator"
    if ci:
        home = "/Users/runner" if root.is_relative_to("/Users/runner") else "/home/runner"
    return {
        "schema_version": 1,
        "mode": "ci" if ci else "local",
        "system_home": home,
        "effective_home": home,
        "source_root": str(root),
        "workspaces": [str(root / "work")],
        "child_roots": [str(root / "work/env")],
        "controller": {
            "executable": "/opt/python/bin/python",
            "resolved_executable": "/opt/python/bin/python",
            "prefix": "/opt/python",
            "temp": "/private/tmp/neutral-producer",
        },
        "git_author_email": {"status": "present", "value": "synthetic-author@example.invalid"},
        "runner": {"home": home, "workspace": str(root), "temp": str(root / "tmp")} if ci else None,
    }
