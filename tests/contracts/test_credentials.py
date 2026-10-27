import dataclasses
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from yorunge import api
from yorunge.adapters.secrets import EnvSecretReader
from yorunge.application.credentials import resolve_credential
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Profile

PLATFORM = "synthetic-platform-NEVER-PRINT"
LLM = "synthetic-llm-NEVER-PRINT"


def configured():
    return Profile(platform_key_env="EVREN_PLATFORM_API_KEY", llm_key_env="EVREN_LLM_API_KEY")


@pytest.mark.parametrize(
    "service,name,expected",
    [
        ("evren-platform", "EVREN_PLATFORM_API_KEY", PLATFORM),
        ("evren-llm", "EVREN_LLM_API_KEY", LLM),
    ],
)
def test_selected_env_is_read_once_and_snapshot_does_not_change(
    monkeypatch, service, name, expected
):
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", PLATFORM)
    monkeypatch.setenv("EVREN_LLM_API_KEY", LLM)
    original = type(os.environ).__getitem__
    reads = []

    def tracked(self, key):
        if key in ("EVREN_PLATFORM_API_KEY", "EVREN_LLM_API_KEY"):
            reads.append(key)
        return original(self, key)

    monkeypatch.setattr(type(os.environ), "__getitem__", tracked)
    value = resolve_credential(configured(), service, EnvSecretReader())
    assert reads == [name]
    # Fixture bookkeeping reads the previous env value; measure only product accesses.
    with monkeypatch.context() as instrumentation:
        instrumentation.setattr(type(os.environ), "__getitem__", original)
        monkeypatch.setenv(name, "changed-after-resolution")
    assert value.secret.reveal() == expected
    assert reads == [name]
    assert value.reference.service_id == service
    assert expected not in repr(value)
    assert expected not in str(value)
    for convert in (json.dumps, pickle.dumps, dataclasses.asdict, vars):
        with pytest.raises(TypeError) as failure:
            convert(value)
        assert expected not in str(failure.value)
    with pytest.raises(TypeError) as failure:
        json.dumps(value.secret, default=lambda item: item.__getstate__())
    assert expected not in str(failure.value)


@pytest.mark.parametrize(
    "value,code",
    [
        (None, "credential_unavailable"),
        ("", "credential_unavailable"),
        ("x" * 16_385, "invalid_credential"),
        ("ğ" * 8193, "invalid_credential"),
        ("synthetic-surrogate-\udcff", "invalid_credential"),
    ],
)
def test_missing_invalid_value_never_uses_other_service(config, monkeypatch, value, code):
    monkeypatch.setenv("EVREN_LLM_API_KEY", LLM)
    if value is None:
        monkeypatch.delenv("EVREN_PLATFORM_API_KEY")
    else:
        monkeypatch.setenv("EVREN_PLATFORM_API_KEY", value)
    with pytest.raises(YorungeError) as failure:
        api.check_credential("evren-platform", config=config)
    assert failure.value.code == code
    assert failure.value.exit_code == 3
    assert LLM not in json.dumps(failure.value.envelope())
    assert failure.value.__context__ is None


@pytest.mark.parametrize("value", [" ", "\tvalue\n", "ğ" * 8192, "x" * 16_384])
def test_exact_utf8_value_is_not_trimmed_or_normalized(value):
    assert SecretValue(value).reveal() == value


def test_credential_api_console_success_and_error_agree(config, cli, monkeypatch):
    monkeypatch.setenv("EVREN_PLATFORM_API_KEY", PLATFORM)
    result = api.check_credential("evren-platform", config=config, project="chosen")
    console = cli(
        "context",
        "credential",
        "--service",
        "evren-platform",
        "--config",
        str(config),
        "--project",
        "chosen",
        "--output",
        "json",
        credential=True,
    )
    assert console.returncode == 0
    assert console.stderr == ""
    assert json.loads(console.stdout) == result.model_dump(mode="json")
    assert result.data.project_id == "chosen"
    assert result.data.remote_verified is False
    assert PLATFORM not in console.stdout
    monkeypatch.delenv("EVREN_PLATFORM_API_KEY")
    with pytest.raises(YorungeError) as failure:
        api.check_credential("evren-platform", config=config)
    console = cli(
        "context",
        "credential",
        "--service",
        "evren-platform",
        "--config",
        str(config),
        "--output",
        "json",
        credential=True,
    )
    assert console.returncode == 3
    assert console.stdout == ""
    assert json.loads(console.stderr) == failure.value.envelope()
    assert console.stderr.count("\n") == 1


def test_wrong_service_and_invalid_target_fail_before_secret_read(config, monkeypatch):
    def denied(self, reference):
        raise AssertionError("unexpected credential read")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    with pytest.raises(YorungeError) as failure:
        api.check_credential("invalid-service", config=config)
    assert failure.value.code == "invalid_request"
    invalid = Profile(platform_url="https://api.example.test/v1?", platform_key_env="SOME_KEY")
    reader = EnvSecretReader()
    with pytest.raises(YorungeError) as failure:
        resolve_credential(invalid, "evren-platform", reader)
    assert failure.value.code == "invalid_service_target"


def test_local_api_does_not_resolve_any_secret(config, monkeypatch):
    def denied(self, reference):
        raise AssertionError("unexpected credential read")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    api.show_context(config=config)
    api.inspect_capabilities(config=config, task="llm.train")
    plan = api.prepare_plan(config=config, task="llm.train").data
    assert plan.context.remote_verified is False
    assert plan.executable is False


@pytest.mark.parametrize(
    "url,origin,path",
    [
        ("https://API.EXAMPLE.TEST:443/api/v1/", "https://api.example.test", "/api/v1"),
        ("https://api.example.test", "https://api.example.test", "/"),
        ("https://api.example.test/", "https://api.example.test", "/"),
        ("https://[2001:0DB8:0000::1]:443/v1", "https://[2001:db8::1]", "/v1"),
        ("https://192.0.2.1/v1", "https://192.0.2.1", "/v1"),
        ("https://api.example.test/v%31", "https://api.example.test", "/v%31"),
        ("https://api.example.test/örnek", "https://api.example.test", "/%C3%B6rnek"),
        ("https://api.example.test/%c3%b6rnek", "https://api.example.test", "/%C3%B6rnek"),
        ("https://api.example.test/a//b", "https://api.example.test", "/a//b"),
    ],
)
def test_target_contract_and_idempotence(url, origin, path):
    result = normalize_target(url)
    assert result.service_origin == origin
    assert result.api_base_path == path
    assert normalize_target(origin + path) == result


@pytest.mark.parametrize(
    "suffix",
    [
        "/v1//",
        "/a/../b",
        "/a/./b",
        "/a%2fb",
        "/%252E",
        "/%ZZ",
        "/%",
        "/%FF",
        "/%2E",
        "/%5c",
        "/%00",
        "/%C2%80",
        "/%20",
        "/v1?",
        "/v1#",
        "/a\\b",
        "/a b",
    ],
)
def test_ambiguous_target_paths_are_rejected(suffix):
    with pytest.raises(YorungeError) as failure:
        normalize_target("https://api.example.test" + suffix)
    assert failure.value.code == "invalid_service_target"


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.test:8443/v1",
        "https://api.example.test./v1",
        "http://api.example.test",
        "https://user@api.example.test",
        "https://@api.example.test",
        "https://örnek.test/v1",
        "https://192.000.2.1",
        "https://[fe80::1%25en0]/v1",
        "https://-bad.test/v1",
        "https://[::1]unexpected/v1",
        "https://[::1]:/v1",
        "https://api.example.test:/v1",
        "https://[v1.a]/v1",
        "https://K.test/v1",
    ],
)
def test_invalid_target_authorities(url):
    with pytest.raises(YorungeError):
        normalize_target(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://örnek.test/v1",
        "https://api.example.test/v1?",
        "https://api.example.test/v1#",
        "https://[2001:0DB8::1]:443/v1",
    ],
)
def test_new_target_policy_does_not_rewrite_legacy_offline_plans(tmp_path, url):
    config = tmp_path / "legacy.toml"
    config.write_text(
        'schema_version=1\nactive_profile="old"\n[profiles.old]\nplatform_url='
        + json.dumps(url)
        + "\n",
        encoding="utf-8",
    )
    plan = api.prepare_plan(config=config, task="vision.train.managed").data
    saved = tmp_path / "old-plan.json"
    before = plan.model_dump_json().encode()
    saved.write_bytes(before)
    assert api.load_plan(saved).data == plan
    assert saved.read_bytes() == before
    assert plan.context.platform_url == Profile(platform_url=url).platform_url


@pytest.mark.parametrize(
    "expression",
    [
        'os.environ["CUSTOM_API_TOKEN"]',
        'os.environb[b"CUSTOM_API_TOKEN"]',
    ],
)
def test_subprocess_guard_covers_configured_custom_names_and_bytes(monkeypatch, expression):
    environment = dict(os.environ)
    environment["CUSTOM_API_TOKEN"] = PLATFORM
    environment["YORUNGE_TEST_SECRET_NAMES"] = '["CUSTOM_API_TOKEN"]'
    environment["YORUNGE_TEST_CREDENTIAL"] = "0"
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "fixtures" / "guards")
    result = subprocess.run(
        [sys.executable, "-c", "import os; print(" + expression + ")"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "forbidden implicit credential access" in result.stderr
    assert PLATFORM not in result.stdout
    assert PLATFORM not in result.stderr


@pytest.mark.parametrize("url", ["https://[v1.a]/v1", "https://K.test/v1"])
def test_non_contract_authority_fails_before_secret_read(url, monkeypatch):
    def denied(self, reference):
        raise AssertionError("unexpected credential read")

    monkeypatch.setattr(EnvSecretReader, "read", denied)
    profile = Profile(platform_url=url, platform_key_env="CUSTOM_API_TOKEN")
    reader = EnvSecretReader()
    with pytest.raises(YorungeError) as failure:
        resolve_credential(profile, "evren-platform", reader)
    assert failure.value.code == "invalid_service_target"
