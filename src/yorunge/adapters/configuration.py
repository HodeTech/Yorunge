"""Bounded TOML updates: no-clobber initialization and optimistic atomic replacement."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tomllib
from asyncio import CancelledError
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from yorunge.adapters.files import CONFIG_LIMIT, bounded_tree, validate
from yorunge.adapters.local_files import (
    Deadline,
    durable_private_chain,
    file_lock,
    private_directory,
    require_local_files,
    safe_ancestors,
    sync_directory,
    sync_private,
    write_new,
)
from yorunge.domain.configuration import ConfigUpdate
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Configuration, Profile, has_control_characters


@dataclass(frozen=True)
class ConfigSnapshot:
    raw: bytes
    identity: tuple[int, int, int, int, str]
    value: Configuration


def config_path(path: Path | None) -> Path:
    if path is not None and not isinstance(path, Path):
        raise YorungeError("invalid_request")
    require_local_files("config_unsupported")
    try:
        chosen = (
            path if path is not None else Path.home() / ".config/yorunge/config.toml"
        ).absolute()
        if has_control_characters(str(chosen)):
            raise YorungeError("invalid_request")
        os.fsencode(chosen)
        safe_ancestors(chosen)
        return Path(os.path.normpath(chosen))
    except YorungeError as error:
        if error.code == "state_invalid":
            raise YorungeError("invalid_config") from None
        raise
    except UnicodeError:
        raise YorungeError("invalid_request") from None
    except OSError:
        raise YorungeError("config_write_failed") from None


@contextmanager
def config_lock(path: Path) -> Iterator[None]:
    try:
        with file_lock(
            path.with_name("." + path.name + ".lock"), Deadline(), exclusive=True, create=True
        ):
            yield
    except YorungeError as error:
        if error.code == "state_busy":
            raise YorungeError("config_busy") from None
        if error.code == "state_invalid":
            raise YorungeError("invalid_config") from None
        raise


def parse(content: bytes) -> Configuration:
    try:
        value = tomllib.loads(content.decode("utf-8"))
        bounded_tree(value)
    except (ValueError, RecursionError):
        raise YorungeError("invalid_config") from None
    return validate(Configuration, value, "invalid_config")


def read_snapshot(path: Path) -> ConfigSnapshot:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or info.st_mode & 0o022
    ):
        raise YorungeError("invalid_config")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as reader:
        actual = os.fstat(reader.fileno())
        if (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size) != (
            actual.st_dev,
            actual.st_ino,
            actual.st_mtime_ns,
            actual.st_size,
        ):
            raise YorungeError("config_conflict")
        content = reader.read(CONFIG_LIMIT + 1)
        after = os.fstat(reader.fileno())
        if (actual.st_mtime_ns, actual.st_size) != (after.st_mtime_ns, after.st_size):
            raise YorungeError("config_conflict")
    if len(content) > CONFIG_LIMIT:
        raise YorungeError("invalid_config")
    identity = (
        info.st_dev,
        info.st_ino,
        info.st_mtime_ns,
        info.st_size,
        hashlib.sha256(content).hexdigest(),
    )
    return ConfigSnapshot(content, identity, parse(content))


def encoded(configuration: Configuration) -> bytes:
    def quoted(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    lines = ["schema_version = 1", "active_profile = " + quoted(configuration.active_profile)]
    for name, profile in configuration.profiles.items():
        lines.append("\n[profiles." + quoted(name) + "]")
        for field, value in profile.model_dump(exclude={"tools"}, exclude_none=True).items():
            lines.append(field + " = " + quoted(value))
        if profile.tools.defaults:
            lines.append("[profiles." + quoted(name) + ".tools.defaults]")
            lines.extend(
                quoted(task) + " = " + quoted(tool) for task, tool in profile.tools.defaults.items()
            )
    try:
        content = ("\n".join(lines) + "\n").encode("utf-8")
    except UnicodeError:
        raise YorungeError("invalid_config") from None
    if len(content) > CONFIG_LIMIT or parse(content) != configuration:
        raise YorungeError("invalid_config")
    return content


def stage(path: Path, content: bytes) -> Path:
    temporary = path.with_name("." + path.name + "." + str(uuid4()) + ".tmp")
    write_new(temporary, content)
    return temporary


def publish(path: Path, temporary: Path, *, initial: bool) -> None:
    try:
        if initial:
            os.link(temporary, path, follow_symlinks=False)
            temporary.unlink()
        else:
            os.replace(temporary, path)
        sync_directory(path.parent)
        sync_private(path)
    except FileExistsError:
        error = YorungeError("config_exists")
    except (OSError, YorungeError, KeyboardInterrupt, CancelledError):
        # Publication may already have changed the target. Cancellation cannot
        # prove rollback and must not invite a second publication attempt.
        error = YorungeError("config_write_uncertain")
    else:
        return
    # Do not retain filesystem or cancellation payloads in the public chain.
    raise error from None


def initialize(path: Path | None, name: str, project: str | None) -> ConfigUpdate:
    chosen = config_path(path)
    configuration = Configuration(
        schema_version=1,
        active_profile=name,
        profiles={
            name: Profile(
                platform_key_env="EVREN_PLATFORM_API_KEY",
                llm_key_env="EVREN_LLM_API_KEY",
                project_id=project,
            )
        },
    )
    content = encoded(configuration)
    try:
        # Reject an existing target before creating any auxiliary directory/lock.
        if chosen.exists() or chosen.is_symlink():
            raise YorungeError("config_exists")
        if not chosen.parent.exists():
            private_directory(chosen.parent)
        durable_private_chain(chosen.parent)
        with config_lock(chosen):
            publish(chosen, stage(chosen, content), initial=True)
        return ConfigUpdate(
            config_path=str(chosen),
            backup_path=None,
            active_profile=name,
            selected_profile=name,
            project_id=project,
        )
    except YorungeError as error:
        if error.code == "state_invalid":
            raise YorungeError("invalid_config") from None
        raise
    except OSError:
        raise YorungeError("config_write_failed") from None


def update(
    path: Path | None,
    selected: str | None,
    change: Callable[[Configuration, str], Configuration],
) -> ConfigUpdate:
    chosen = config_path(path)
    try:
        original = read_snapshot(chosen)
        name = selected or original.value.active_profile
        if name not in original.value.profiles:
            raise YorungeError("profile_not_found")
        revised = change(original.value, name)
        content = encoded(revised)
        with config_lock(chosen):
            if read_snapshot(chosen).identity != original.identity:
                raise YorungeError("config_conflict")
            backups = chosen.with_name("." + chosen.name + ".backups")
            private_directory(backups)
            durable_private_chain(backups)
            saved = backups / (str(uuid4()) + ".toml")
            write_new(saved, original.raw)
            temporary = stage(chosen, content)
            if read_snapshot(chosen).identity != original.identity:
                raise YorungeError("config_conflict")
            publish(chosen, temporary, initial=False)
        return ConfigUpdate(
            config_path=str(chosen),
            backup_path=str(saved),
            active_profile=revised.active_profile,
            selected_profile=name,
            project_id=revised.profiles[name].project_id,
        )
    except YorungeError as error:
        if error.code == "state_invalid":
            raise YorungeError("invalid_config") from None
        raise
    except FileNotFoundError:
        raise YorungeError("file_unreadable") from None
    except OSError:
        raise YorungeError("config_write_failed") from None
