from typing import Literal

from yorunge.domain.errors import ErrorCode
from yorunge.domain.models import Identifier, Model


class ProfileSummary(Model):
    name: Identifier
    active: bool
    account_id: Identifier | None
    project_id: Identifier | None


class ProfilesView(Model):
    config_exists: bool
    active_profile: Identifier
    profiles: tuple[ProfileSummary, ...]


class ConfigUpdate(Model):
    config_path: str
    backup_path: str | None
    active_profile: Identifier
    selected_profile: Identifier
    project_id: Identifier | None


class Diagnostic(Model):
    name: Literal[
        "configuration",
        "profile",
        "platform_reference",
        "llm_reference",
        "state",
        "key",
        "key_check",
        "remote_access",
    ]
    status: Literal["ok", "missing", "invalid", "busy", "not_checked"]
    code: ErrorCode | None = None


class DoctorReport(Model):
    checks: tuple[Diagnostic, ...]
    issue_count: int
    remote_verified: Literal[False] = False
    credential_values_read: Literal[False] = False
