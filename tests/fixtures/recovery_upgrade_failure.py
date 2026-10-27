"""Cut old restore or the following shadow migration in disposable private stores."""

import os
import signal
import sys
from pathlib import Path

from yorunge import api
from yorunge.adapters import maintenance as m
from yorunge.adapters import state_schema

mode, root_arg, boundary, version_arg = sys.argv[1:5]
root, version = Path(root_arg), int(version_arg)
if mode == "old":
    source = Path(sys.argv[5])
    state_schema.MIGRATIONS = state_schema.MIGRATIONS[:version]
    original_reset, original_sync = m.reset_connection, m.sync_private

    def reset(*args, **kwargs):
        result = original_reset(*args, **kwargs)
        if boundary == "stage":
            os._exit(73)
        return result

    def sync(path):
        original_sync(path)
        if boundary == "live" and path == root / m.DB_NAME:
            os._exit(73)

    m.reset_connection, m.sync_private = reset, sync
    preview = api.preview_state_restore(source, state_dir=root)
    api.restore_state(source, preview.data.digest, state_dir=root)
else:
    intent = m.read_intent(root)
    pair = root / (
        m.DB_NAME if sys.argv[5] == "live" else "restore-" + intent.stage_id + m.STAGE_SUFFIX
    )
    original_connect, original_apply = m.connect, m.apply_migration
    original_upgrade, original_sync, original_replace = m.upgrade, m.sync_private, os.replace
    migrated = False

    def cut():
        os.kill(os.getpid(), signal.SIGKILL)

    def connect(path, deadline):
        connection = original_connect(path, deadline)
        if path.name.startswith("upgrade-"):
            connection.execute("PRAGMA cache_size=1")
        return connection

    def apply(connection, step):
        original_apply(connection, step)
        if boundary == "migration-write":
            cut()

    def upgrade(*args):
        global migrated
        original_upgrade(*args)
        migrated = True
        if boundary == "migration-committed":
            cut()

    def sync(path):
        original_sync(path)
        if migrated and path.name.startswith("upgrade-") and boundary == "shadow-synced":
            cut()
        if migrated and path == pair and boundary == "pair-synced":
            cut()

    def replace(source, target):
        if Path(source).name.startswith("upgrade-") and boundary == "publish-before":
            cut()
        original_replace(source, target)
        if Path(source).name.startswith("upgrade-") and boundary == "publish-after":
            cut()

    m.connect, m.apply_migration, m.upgrade = connect, apply, upgrade
    m.sync_private, os.replace = sync, replace
    preview = api.preview_state_recovery(state_dir=root)
    api.recover_state(preview.data.digest, state_dir=root)
raise AssertionError("requested process cut was not reached")
