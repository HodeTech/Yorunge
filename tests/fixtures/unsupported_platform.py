"""Simulate platform/import absence in a fresh process, without pretending to run Windows."""

import builtins
import json
import sys
from pathlib import Path

from yorunge import api
from yorunge.cli import main
from yorunge.domain.errors import YorungeError

scenario, surface, action, config_arg, state_arg = sys.argv[1:]
config, state_dir = Path(config_arg), Path(state_arg)
if scenario != "native-missing-fcntl":
    sys.platform = "win32"
original_import = builtins.__import__


def importing(name, *args, **kwargs):
    if name == "fcntl" and scenario != "unsupported-with-fcntl":
        raise ModuleNotFoundError("synthetic missing fcntl")
    return original_import(name, *args, **kwargs)


builtins.__import__ = importing
confirmation = "0" * 64
calls = {
    "cache": lambda: api.query_capabilities(task="llm.train", state_dir=state_dir),
    "refresh": lambda: api.query_capabilities(task="llm.train", refresh=True, state_dir=state_dir),
    "state-init": lambda: api.initialize_state(state_dir=state_dir),
    "reset-preview": lambda: api.preview_identity_reset(state_dir=state_dir),
    "reset": lambda: api.reset_identity(confirmation, state_dir=state_dir),
    "restore-preview": lambda: api.preview_state_restore(state_dir / "backup", state_dir=state_dir),
    "restore": lambda: api.restore_state(state_dir / "backup", confirmation, state_dir=state_dir),
    "recover-preview": lambda: api.preview_state_recovery(state_dir=state_dir),
    "recover": lambda: api.recover_state(confirmation, state_dir=state_dir),
    "identity": lambda: api.observe_credential(
        "evren-platform",
        config=config,
        state_dir=state_dir,
    ),
    "config-init": lambda: api.initialize_config(config=config.with_name("new.toml")),
    "activate": lambda: api.activate_profile("other", config=config),
    "set-project": lambda: api.set_project("selected", config=config),
    "clear-project": lambda: api.clear_project(config=config),
    "doctor": lambda: api.diagnose_local(config=config, state_dir=state_dir),
}
commands = {
    "cache": ["capabilities", "--task", "llm.train", "--cached"],
    "refresh": ["capabilities", "--task", "llm.train", "--refresh"],
    "state-init": ["state", "init"],
    "reset-preview": ["state", "reset"],
    "reset": ["state", "reset", "--confirm", confirmation],
    "restore-preview": ["state", "restore", "--backup", str(state_dir / "backup")],
    "restore": [
        "state",
        "restore",
        "--backup",
        str(state_dir / "backup"),
        "--confirm",
        confirmation,
    ],
    "recover-preview": ["state", "recover"],
    "recover": ["state", "recover", "--confirm", confirmation],
    "identity": ["context", "identity", "--service", "evren-platform", "--config", str(config)],
    "config-init": ["init", "--config", str(config.with_name("new.toml"))],
    "activate": ["context", "use-profile", "other", "--config", str(config)],
    "set-project": ["context", "set-project", "selected", "--config", str(config)],
    "clear-project": ["context", "clear-project", "--config", str(config)],
    "doctor": ["doctor", "--config", str(config)],
}
if surface == "cli":
    command = commands[action] + ["--output", "json"]
    if action not in ("config-init", "activate", "set-project", "clear-project"):
        command += ["--state-dir", str(state_dir)]
    raise SystemExit(main(command))
try:
    calls[action]()
except YorungeError as error:
    print(json.dumps(error.envelope(), ensure_ascii=False), file=sys.stderr)
    raise SystemExit(error.exit_code) from None
raise AssertionError("unsupported local operation unexpectedly succeeded")
