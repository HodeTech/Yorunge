import concurrent.futures
import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from yorunge import api
from yorunge.adapters.identity import StateCredentialRegistry
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.adapters.state import DB_NAME, open_store
from yorunge.application.credentials import bind_credential, resolve_credential
from yorunge.domain.credentials import CredentialBinding, SecretValue, observation_tag
from yorunge.domain.errors import YorungeError


def observe(config, root, **kwargs):
    return api.observe_credential("evren-platform", config=config, state_dir=root, **kwargs).data


def test_product_hmac_uses_independent_exact_byte_vectors():
    probe = Path(__file__).parents[2] / "docs/research/p01-2-review-probe.json"
    vectors = json.loads(probe.read_text())["binding_v1_byte_vectors"]
    binding = CredentialBinding(**vectors["binding"])
    key = bytes.fromhex(vectors["synthetic_key_hex"])
    assert binding.encoded() == vectors["binding_json"].encode()
    assert len(binding.encoded()) == vectors["binding_byte_length"]
    for vector in vectors["credential_vectors"]:
        assert (
            hmac.digest(key, bytes.fromhex(vector["message_hex"]), "sha256").hex()
            == vector["tag_hex"]
        )
        assert (
            observation_tag(binding, key, SecretValue(vector["synthetic_secret"])).hex()
            == vector["tag_hex"]
        )
    for field in CredentialBinding.model_fields:
        incomplete = binding.model_dump()
        del incomplete[field]
        with pytest.raises(ValidationError):
            CredentialBinding(**incomplete)
    with pytest.raises(ValidationError):
        CredentialBinding(**binding.model_dump(), profile="work")


def test_reopen_rotation_and_public_private_boundaries(config, tmp_path, monkeypatch, capsys):
    root = tmp_path / "state"
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "synthetic-value-A")
    first = observe(config, root)
    assert observe(config, root).identity == first.identity
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "synthetic-value-B")
    second = observe(config, root)
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "synthetic-value-A")
    third = observe(config, root)
    assert [v.identity.credential_revision for v in (first, second, third)] == [1, 2, 3]
    assert len({v.identity.credential_id for v in (first, second, third)}) == 1
    assert first.remote_verified is False
    with sqlite3.connect(root / DB_NAME) as connection:
        rows = connection.execute("SELECT * FROM credential_bindings").fetchall()
    assert len(rows) == 1
    raw = (root / DB_NAME).read_bytes()
    public = first.model_dump_json() + repr(first) + capsys.readouterr().out
    for value in ("synthetic-value-A", "synthetic-value-B"):
        assert value.encode() not in raw
        assert hashlib.sha256(value.encode()).digest() not in raw
        assert value not in public
    assert rows[0][-2].hex() not in public
    assert "reference_name" not in public


def test_same_observation_does_not_change_database_or_clock(config, tmp_path, monkeypatch):
    root = tmp_path / "state"
    first = observe(config, root)
    before = (root / DB_NAME).read_bytes()

    def denied():
        raise AssertionError("unchanged observation must not update timestamp")

    monkeypatch.setattr("yorunge.adapters.identity.utc_now", denied)
    assert observe(config, root).identity == first.identity
    assert (root / DB_NAME).read_bytes() == before


def test_snapshot_bound_once_to_context_and_identity(config, tmp_path, monkeypatch):
    from yorunge.domain.models import Profile

    context = api.show_context(config=config).data
    profile = Profile(platform_key_env="EVREN_PLATFORM_API_KEY")
    reads = []
    original = EnvSecretReader.read

    def read(self, reference):
        reads.append(reference.name)
        result = original(self, reference)
        os.environ[reference.name] = "changed-after-resolve"
        return result

    monkeypatch.setattr(EnvSecretReader, "read", read)
    resolved = resolve_credential(profile, "evren-platform", EnvSecretReader())
    with open_store(tmp_path / "state") as store:
        bound = bind_credential(context, resolved, StateCredentialRegistry(store))
        assert bound.credential is resolved
        assert bound.context is context
        assert bound.identity.credential_revision == 1
        assert bound.credential.secret.reveal() != "changed-after-resolve"
        with pytest.raises(YorungeError) as failure:
            bind_credential(
                context.model_copy(update={"platform_url": "https://other.test"}),
                resolved,
                StateCredentialRegistry(store),
            )
        assert failure.value.code == "state_changed"
    assert reads == ["EVREN_PLATFORM_API_KEY"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("platform_url", "https://different.test/api"),
        ("platform_url", "https://platform.evren.ai/v%31"),
        ("platform_key_env", "OTHER_TOKEN"),
    ],
)
def test_binding_dimensions_isolate(config, tmp_path, monkeypatch, field, value):
    root = tmp_path / "state"
    first = observe(config, root)
    monkeypatch.setenv("OTHER_TOKEN", os.environ["EVREN_PLATFORM_API_KEY"])
    text = config.read_text()
    if field == "platform_key_env":
        text = text.replace(
            'platform_key_env = "EVREN_PLATFORM_API_KEY"', 'platform_key_env = "OTHER_TOKEN"'
        )
    else:
        text = text.replace("[profiles.work]", '[profiles.work]\nplatform_url="' + value + '"')
    config.write_text(text)
    assert observe(config, root).identity.credential_id != first.identity.credential_id


def test_profile_account_project_do_not_replace_binding(config, tmp_path):
    root = tmp_path / "state"
    first = observe(config, root)
    config.write_text(
        config.read_text().replace(
            "[profiles.other]",
            """[profiles.other]
platform_key_env="EVREN_PLATFORM_API_KEY"
account_id="another-account"
""",
        )
    )
    other = observe(config, root, profile="other", project="explicit")
    assert other.identity == first.identity
    assert other.account_id == "another-account"
    assert other.project_id == "explicit"
    llm = api.observe_credential("evren-llm", config=config, state_dir=root).data
    assert llm.identity.credential_id != first.identity.credential_id


def test_max_revision_same_value_allowed_change_rolls_back(config, tmp_path, monkeypatch):
    root = tmp_path / "state"
    first = observe(config, root)
    with sqlite3.connect(root / DB_NAME) as connection:
        connection.execute("UPDATE credential_bindings SET revision=?", (2**63 - 1,))
    assert observe(config, root).identity.credential_revision == 2**63 - 1
    before = (root / DB_NAME).read_bytes()
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "different-value")
    with pytest.raises(YorungeError) as failure:
        observe(config, root)
    assert failure.value.code == "credential_revision_exhausted"
    assert (root / DB_NAME).read_bytes() == before
    assert first.identity.credential_revision == 1


def test_concurrent_same_value_increments_once_and_different_values_serialize(config, tmp_path):
    from yorunge.domain.models import Profile

    root = tmp_path / "state"
    observe(config, root)
    profile = Profile(platform_key_env="EVREN_PLATFORM_API_KEY")

    class Reader:
        def __init__(self, value):
            self.value = value

        def read(self, reference):
            return SecretValue(self.value)

    def run(value):
        resolved = resolve_credential(profile, "evren-platform", Reader(value))
        with open_store(root) as store:
            return value, StateCredentialRegistry(store).observe(resolved)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        same = list(pool.map(run, ["synthetic-B"] * 8))
        mixed = list(pool.map(run, ["synthetic-A", "synthetic-B"] * 4))
    assert {identity.credential_revision for _, identity in same} == {2}
    revisions = {}
    for value, identity in mixed:
        revisions.setdefault(identity.credential_revision, set()).add(value)
    assert all(len(values) == 1 for values in revisions.values())
    assert min(revisions) >= 2


def test_console_persistence_and_error_parity(config, tmp_path, cli, monkeypatch):
    root = tmp_path / "state"
    first = observe(config, root)
    command = (
        "context",
        "identity",
        "--service",
        "evren-platform",
        "--config",
        str(config),
        "--state-dir",
        str(root),
        "--output",
        "json",
    )
    result = cli(*command, credential=True, state=True)
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["data"] == first.model_dump(mode="json")
    monkeypatch.delenv("EVREN_PLATFORM_API_KEY")
    with pytest.raises(YorungeError) as failure:
        observe(config, root)
    result = cli(*command, credential=True, state=True)
    assert result.returncode == 3
    assert result.stdout == ""
    assert json.loads(result.stderr) == failure.value.envelope()


def test_separate_process_observations_share_one_revision(config, tmp_path, cli, monkeypatch):
    root = tmp_path / "state"
    first = observe(config, root)
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", "process-rotated-value")
    command = (
        "context",
        "identity",
        "--service",
        "evren-platform",
        "--config",
        str(config),
        "--state-dir",
        str(root),
        "--output",
        "json",
    )

    def run(_):
        result = cli(*command, credential=True, state=True)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)["data"]["identity"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        identities = list(pool.map(run, range(6)))
    assert {identity["credential_revision"] for identity in identities} == {2}
    assert {identity["credential_id"] for identity in identities} == {first.identity.credential_id}


@pytest.mark.parametrize("value", [None, "", "x" * 16385])
def test_invalid_secret_does_not_create_store(config, tmp_path, monkeypatch, value):
    root = tmp_path / "state"
    if value is None:
        monkeypatch.delenv("EVREN_PLATFORM_API_KEY")
    else:
        monkeypatch.setenv("EVREN_PLATFORM_API_KEY", value)
    with pytest.raises(YorungeError):
        observe(config, root)
    assert not root.exists()


@pytest.mark.parametrize("keep_db", [True, False])
def test_missing_lock_with_partial_payload_never_recreates_lock(tmp_path, keep_db):
    root = tmp_path / "state"
    api.initialize_state(state_dir=root)
    (root / "store.lock").unlink()
    if not keep_db:
        (root / DB_NAME).unlink()
    with pytest.raises(YorungeError) as failure:
        api.initialize_state(state_dir=root)
    assert failure.value.code == "state_repair_required"
    assert not (root / "store.lock").exists()


def test_inaccessible_state_ancestor_returns_safe_error_before_secret_read(
    config, tmp_path, monkeypatch, cli
):
    parent = tmp_path / "blocked"
    parent.mkdir()
    child = parent / "child"
    child.mkdir()

    def denied(self, reference):
        raise AssertionError("must validate path before reading a secret")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    parent.chmod(0)
    try:
        with pytest.raises(YorungeError) as failure:
            observe(config, child / "state")
        assert failure.value.code == "state_write_failed"
        result = cli(
            "context",
            "identity",
            "--service",
            "evren-platform",
            "--config",
            str(config),
            "--state-dir",
            str(child / "state"),
            "--output",
            "json",
            credential=True,
            state=True,
        )
        assert result.returncode == 2
        assert result.stdout == ""
        assert json.loads(result.stderr) == failure.value.envelope()
    finally:
        parent.chmod(0o700)


def test_unsupported_platform_rejected_before_secret_read(config, tmp_path, monkeypatch):
    def denied(self, reference):
        raise AssertionError("must validate runtime before reading a secret")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    monkeypatch.setattr("yorunge.adapters.state.sys.platform", "unsupported")
    with pytest.raises(YorungeError) as failure:
        observe(config, tmp_path / "state")
    assert failure.value.code == "state_unsupported"
