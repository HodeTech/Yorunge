"""Subprocess audit guard: a forbidden side effect makes the real command fail."""

import json
import os
import sys

META = os.environ.get("YORUNGE_TEST_METADATA") == "1"
CREDENTIAL = os.environ.get("YORUNGE_TEST_CREDENTIAL") == "1"
FORBIDDEN = ("torch", "transformers", "trl", "keyring", "forgelm", "axolotl")

original_getitem = type(os.environ).__getitem__
SECRET_NAMES = frozenset(
    ("EVREN_PLATFORM_API_KEY", "EVREN_LLM_API_KEY")
    + tuple(json.loads(os.environ.get("YORUNGE_TEST_SECRET_NAMES", "[]")))
)


def guarded_getitem(self, key):
    name = key.decode("ascii", errors="ignore") if isinstance(key, bytes) else key
    if name in SECRET_NAMES and (META or not CREDENTIAL):
        raise RuntimeError("forbidden implicit credential access")
    return original_getitem(self, key)


type(os.environ).__getitem__ = guarded_getitem


def audit(event, args):
    if event.startswith("socket.") or event in ("sqlite3.connect", "subprocess.Popen"):
        raise RuntimeError("forbidden offline side effect")
    if event == "import":
        root = args[0].split(".")[0]
        if root in FORBIDDEN or (META and root in ("pydantic", "yaml", "yorunge.api")):
            raise RuntimeError("forbidden eager import")
    if META and event == "open" and isinstance(args[0], (str, bytes)):
        if str(args[0]).endswith((".toml", ".yaml", ".sqlite", ".db")):
            raise RuntimeError("metadata command read configuration or state")


sys.addaudithook(audit)
