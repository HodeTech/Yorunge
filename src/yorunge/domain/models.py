from __future__ import annotations

import hashlib
import json
from typing import Annotated, Generic, Literal, TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
]
EnvName = Annotated[str, Field(max_length=128, pattern=r"^[A-Z_][A-Z0-9_]*$")]
Task = Literal[
    "llm.data.ingest",
    "llm.data.audit",
    "llm.data.generate",
    "llm.fit.check",
    "llm.train",
    "llm.evaluate",
    "llm.merge",
    "llm.export",
    "dataset.upload",
    "vision.train.managed",
    "llm.chat",
]
Execution = Literal["local", "evren-managed", "evren-workspace"]
Support = Literal["supported", "unsupported", "unknown", "requires_access"]
SelectionSource = Literal["request", "recipe", "profile", "product_default", "native"]
LLM_TASKS: frozenset[str] = frozenset(
    {
        "llm.data.ingest",
        "llm.data.audit",
        "llm.data.generate",
        "llm.fit.check",
        "llm.train",
        "llm.evaluate",
        "llm.merge",
        "llm.export",
    }
)
TOOL_IDS: frozenset[str] = frozenset({"forgelm", "axolotl", "llamafactory", "unsloth"})


class Model(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, hide_input_in_errors=True, allow_inf_nan=False
    )

    @field_validator("schema_version", mode="before", check_fields=False)
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer version required")
        return value

    @field_validator(
        "remote_verified", "executable", "inputs_verified", mode="before", check_fields=False
    )
    @classmethod
    def boolean_flag(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("boolean flag required")
        return value


class ExecutionSpec(Model):
    backend: Execution


class ToolSpec(Model):
    id: Identifier


class ModelSpec(Model):
    source: Literal["huggingface"]
    id: Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[\w.-]+/[\w.-]+$")]
    revision: Identifier


class DataSpec(Model):
    manifest: Annotated[str, Field(min_length=1, max_length=1024)]

    @field_validator("manifest")
    @classmethod
    def local_reference(cls, value: str) -> str:
        if ":" in value or "\x00" in value or "\n" in value or "\r" in value:
            raise ValueError("local path required")
        return value


class TrainingSpec(Model):
    method: Literal["sft"]
    epochs: Annotated[int, Field(ge=1, le=1000)]


class Recipe(Model):
    schema_version: Literal[1]
    task: Task
    profile: Identifier | None = None
    project: Identifier | None = None
    tool: ToolSpec | None = None
    execution: ExecutionSpec | None = None
    model: ModelSpec | None = None
    data: DataSpec | None = None
    training: TrainingSpec | None = None
    provider_options: dict[str, object] = Field(default_factory=dict)

    @field_validator("provider_options")
    @classmethod
    def no_unvalidated_options(cls, value: dict[str, object]) -> dict[str, object]:
        if value:
            raise ValueError("provider options require an implemented adapter")
        return value

    @model_validator(mode="after")
    def task_parameters(self) -> Recipe:
        if self.training is not None and self.task != "llm.train":
            raise ValueError("training parameters require llm.train")
        if self.task not in LLM_TASKS and (self.model is not None or self.data is not None):
            raise ValueError("native task parameters are not implemented")
        return self


class ToolDefaults(Model):
    defaults: dict[Task, Identifier] = Field(default_factory=dict)

    @field_validator("defaults")
    @classmethod
    def relevant_tasks(cls, value: dict[Task, str]) -> dict[Task, str]:
        if not set(value).issubset(LLM_TASKS):
            raise ValueError("native tasks do not select external tools")
        return value


class Profile(Model):
    platform_url: str = "https://api.ssyz.org.tr/api/v1"
    llm_url: str = "https://evren-llmapi.ssyz.org.tr/v1"
    platform_key_env: EnvName | None = None
    llm_key_env: EnvName | None = None
    account_id: Identifier | None = None
    project_id: Identifier | None = None
    tools: ToolDefaults = Field(default_factory=ToolDefaults)

    @field_validator("platform_url", "llm_url")
    @classmethod
    def service_url(cls, value: str) -> str:
        if len(value) > 2048 or any(ord(char) < 33 for char in value) or "\\" in value:
            raise ValueError("invalid service URL")
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.port not in (None, 443)
            or "%" in parts.netloc
            or parts.path.endswith("//")
            or any(segment in (".", "..") for segment in parts.path.split("/"))
        ):
            raise ValueError("HTTPS service root without credentials required")
        return value.rstrip("/")

    @model_validator(mode="after")
    def separate_services(self) -> Profile:
        if (
            urlsplit(self.platform_url).hostname == "evren-llmapi.ssyz.org.tr"
            or urlsplit(self.llm_url).hostname == "api.ssyz.org.tr"
            or self.platform_url == self.llm_url
        ):
            raise ValueError("service identities must remain separate")
        return self


class Configuration(Model):
    schema_version: Literal[1]
    active_profile: Identifier
    profiles: dict[Identifier, Profile]

    @model_validator(mode="after")
    def active_exists(self) -> Configuration:
        if self.active_profile not in self.profiles:
            raise ValueError("active profile missing")
        return self


class Context(Model):
    profile: Identifier
    project_id: Identifier | None
    account_id: Identifier | None
    platform_url: str
    llm_url: str
    remote_verified: Literal[False] = False

    @model_validator(mode="after")
    def service_roots(self) -> Context:
        Profile(platform_url=self.platform_url, llm_url=self.llm_url)
        return self


class Selection(Model):
    task: Task
    tool: Identifier | None
    tool_source: SelectionSource
    execution: Execution
    execution_source: SelectionSource
    tool_version: None = None


class Scope(Model):
    service_id: Literal["local", "evren-platform", "evren-llm"]
    service_origin: str | None
    api_base_path: str | None
    account_id: Identifier | None
    project_id: Identifier | None
    credential_id: None = None
    credential_revision: None = None
    authorization_scope: None = None
    tool: Identifier | None
    tool_version: None = None
    execution: Execution


class Capability(Model):
    schema_version: Literal[1] = 1
    capability_id: str
    task: str
    scope: Scope
    support: Support
    reason_code: str
    message: str
    evidence: Literal["local_policy", "not_verified"]
    checked_at: None = None
    expires_at: None = None


class CapabilityView(Model):
    context: Context
    selection: Selection
    records: tuple[Capability, ...]


class Plan(Model):
    schema_version: Literal[1] = 1
    mode: Literal["offline"] = "offline"
    state: Literal["draft"] = "draft"
    executable: Literal[False] = False
    context: Context
    selection: Selection
    recipe: Recipe
    capabilities: tuple[Capability, ...]
    blockers: tuple[str, ...]
    inputs_verified: Literal[False] = False
    digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def consistent_task(self) -> Plan:
        if self.selection.task != self.recipe.task:
            raise ValueError("plan task mismatch")
        return self

    def computed_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"digest"})
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


T = TypeVar("T")


class Result(Model, Generic[T]):
    schema_version: Literal[1] = 1
    operation_id: None = None
    status: Literal["completed"] = "completed"
    data: T
    warnings: tuple[str, ...] = ()
