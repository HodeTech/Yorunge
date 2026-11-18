"""The catalog reads on loopback TLS (P02-4d, ADR-0035): what goes on the wire and what comes back.

The provider is a synthetic TLS server; the product's own session and transport run against it.
Every assertion looks at the recorded requests: the key only where the schema says it goes, the
exact query, the number of GETs per command, no redirect followed, and no state written.
"""

import json
import socket

import pytest

from tests.fixtures.http_server import Reply, TlsServer, certificate, loopback_sockets
from yorunge.adapters import catalog_http as client
from yorunge.adapters.http_session import HttpSession
from yorunge.adapters.http_transport import HttpxTransport
from yorunge.domain.errors import YorungeError
from yorunge.domain.models import Context, Profile

CONNECT = socket.socket.connect
CONNECT_EX = socket.socket.connect_ex
GETADDRINFO = socket.getaddrinfo
HOSTS = ("localhost",)  # both services are the loopback fixture under distinct roots
PLATFORM_KEY_ENV = "CATALOG_TEST_PLATFORM_KEY"
LLM_KEY_ENV = "CATALOG_TEST_LLM_KEY"
PLATFORM_KEY = "sk-platform-synthetic-0001"
LLM_KEY = "sk-llm-synthetic-0002"
OWNER = "owner-1"
SLUG = "model-a"
MODEL_ID = "model-uuid-1"
STAMP = "2026-01-01T00:00:00Z"
PLATFORM_BASE = "/api/v1"
LLM_BASE = "/v1"


def model_json(**overrides):
    model = {
        "id": MODEL_ID,
        "owner_username": OWNER,
        "slug": SLUG,
        "name": "Model A",
        "description": "Synthetic",
        "license": "mit",
        "modality": "VISION",
        "stage": "EXPERIMENTAL",
        "visibility": "PRIVATE",
        "versions_count": 2,
        "architecture": "yolov8n",
        "created_at": STAMP,
        "updated_at": STAMP,
    }
    model.update(overrides)
    return model


def version_json(number):
    return {
        "id": f"version-{number}",
        "version_tag": f"1.{number}",
        "framework": "pytorch",
        "file_size_bytes": 10,
        "created_at": STAMP,
        "weights_url": "https://example.invalid/private/signed?sig=synthetic",
        "onnx_url": None,
        "tflite_url": None,
    }


def body(value) -> Reply:
    return Reply(body=json.dumps(value).encode("utf-8"))


@pytest.fixture(autouse=True)
def actual_loopback_only():
    with loopback_sockets(CONNECT, CONNECT_EX, GETADDRINFO):
        yield


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    return certificate(tmp_path_factory.mktemp("catalog-tls"), names=(*HOSTS, "localhost"))


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv(PLATFORM_KEY_ENV, PLATFORM_KEY)
    monkeypatch.setenv(LLM_KEY_ENV, LLM_KEY)


def loader():
    context = Context(
        profile="test",
        project_id=None,
        account_id=None,
        platform_url=f"https://localhost{PLATFORM_BASE}",
        llm_url=f"https://localhost{LLM_BASE}",
    )
    profile = Profile(
        platform_url=context.platform_url,
        llm_url=context.llm_url,
        platform_key_env=PLATFORM_KEY_ENV,
        llm_key_env=LLM_KEY_ENV,
    )
    return context, profile


class Rig:
    def __init__(self, certificates, routes, monkeypatch):
        self.server = TlsServer(certificates, routes)
        self.monkeypatch = monkeypatch
        self.certificates = certificates

    def __enter__(self):
        self.server.__enter__()
        server = self.server
        factory = lambda: HttpSession(  # noqa: E731
            transport_factory=lambda: HttpxTransport(
                transport=server.transport(hostname="localhost")
            )
        )
        self.monkeypatch.setattr(client, "HttpSession", factory)
        return self

    def __exit__(self, *exc):
        self.server.__exit__(*exc)

    def paths(self):
        return [record.path for record in self.server.requests]


def run(certificates, monkeypatch, routes, action):
    with Rig(certificates, routes, monkeypatch) as rig:
        try:
            value = action()
            return rig, value, None
        except YorungeError as error:
            return rig, None, error


# --- Platform models ----------------------------------------------------------------------------


def test_platform_page_sends_the_key_as_x_api_key_and_nothing_else(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body(
            {"items": [model_json()] * 20, "total": 45}
        )
    }
    rig, observed, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 20),
    )
    assert error is None
    assert observed.value.completeness == "partial"
    record = rig.server.requests[0]
    assert record.header("X-API-Key") == PLATFORM_KEY
    assert record.header("Authorization") is None
    assert rig.paths() == [f"{PLATFORM_BASE}/models?page=1&page_size=20"]
    assert observed.observed_from <= observed.observed_until


def test_a_silently_smaller_page_is_refused_and_one_request_only(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=100": body(
            {"items": [model_json()] * 20, "total": 45}
        )
    }
    rig, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 100),
    )
    assert error is not None and error.code == "invalid_response"
    assert len(rig.server.requests) == 1


def test_show_with_versions_makes_two_gets_and_the_second_uses_the_model_id(
    certificates, keys, monkeypatch
):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json()),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1), version_json(2)]),
    }
    rig, observed, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=True),
    )
    assert error is None
    model, listing = observed.value
    assert model.model_id == MODEL_ID
    assert listing.completeness == "complete"
    assert rig.paths() == [
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}",
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions",
    ]


def test_a_detail_of_another_model_is_refused(certificates, keys, monkeypatch):
    routes = {f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(slug="other"))}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=False),
    )
    assert error is not None and error.code == "invalid_response"


def test_one_tag_resolves_with_two_gets_and_nothing_is_guessed(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=2)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1), version_json(2)]),
    }
    rig, observed, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.resolve_platform_version(loader, OWNER, SLUG, "1.2"),
    )
    assert error is None
    _, version = observed.value
    assert version.version_id == "version-2"
    assert len(rig.server.requests) == 2


def test_an_ambiguous_tag_stops_before_any_choice(certificates, keys, monkeypatch):
    same = version_json(1) | {"version_tag": "1.0"}
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=2)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([same, same | {"id": "version-x"}]),
    }
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.resolve_platform_version(loader, OWNER, SLUG, "1.0"),
    )
    assert error is not None and error.code == "model_ambiguous"


def test_a_version_list_that_disagrees_with_the_detail_is_refused(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=3)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.resolve_platform_version(loader, OWNER, SLUG, "1.1"),
    )
    assert error is not None and error.code == "invalid_response"


def test_a_missing_tag_is_not_visible_and_not_absent(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.resolve_platform_version(loader, OWNER, SLUG, "9.9"),
    )
    assert error is not None and error.code == "model_not_visible"


def test_a_dot_segment_is_refused_before_any_request(certificates, keys, monkeypatch):
    rig, _, error = run(
        certificates,
        monkeypatch,
        {},
        lambda: client.show_platform_model(loader, "..", SLUG, versions=False),
    )
    assert error is not None and error.code == "invalid_request"
    assert rig.server.requests == []


def test_an_owner_less_model_lists_its_versions_with_unknown_completeness(
    certificates, keys, monkeypatch
):
    routes = {f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)])}
    rig, observed, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_versions(loader, MODEL_ID),
    )
    assert error is None
    assert observed.value.completeness == "unknown"
    assert rig.paths() == [f"{PLATFORM_BASE}/models/{MODEL_ID}/versions"]


def test_datasets_send_owned_scope_and_read_the_paging_headers(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned": Reply(
            body=json.dumps(
                [
                    {
                        "id": "dataset-1",
                        "name": "Dataset A",
                        "slug": "dataset-a",
                        "modality": "VISION",
                        "item_count": 3,
                        "visibility": "PRIVATE",
                        "updated_at": STAMP,
                        "owner_username": OWNER,
                    }
                ]
            ).encode("utf-8"),
            headers=(("X-Has-Next", "false"), ("X-Total-Count", "1")),
        )
    }
    rig, observed, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_datasets(loader, 1, 20),
    )
    assert error is None
    assert observed.value.completeness == "complete"
    assert observed.value.scope == "unknown"
    assert rig.paths() == [f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned"]


# --- LLM -----------------------------------------------------------------------------------------


def llm_model(**overrides):
    model = {"id": "llm-a", "object": "model", "created": 1700000000, "task": "embedding"}
    model.update(overrides)
    return model


def test_llm_list_sends_the_bearer_key_to_the_llm_target_only(certificates, keys, monkeypatch):
    routes = {f"{LLM_BASE}/models": body({"object": "list", "data": [llm_model()]})}
    rig, observed, error = run(
        certificates, monkeypatch, routes, lambda: client.list_llm_models(loader)
    )
    assert error is None
    assert observed.value.models[0].model_id == "llm-a"
    record = rig.server.requests[0]
    assert record.header("Authorization") == f"Bearer {LLM_KEY}"
    assert record.header("X-API-Key") is None


def test_a_llm_model_outside_the_key_is_not_visible(certificates, keys, monkeypatch):
    routes = {f"{LLM_BASE}/models/llm-a": Reply(status=404, body=b"{}")}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_llm_model(loader, "llm-a", task=None),
    )
    assert error is not None and error.code == "model_not_visible"


def test_a_llm_task_mismatch_is_refused(certificates, keys, monkeypatch):
    routes = {f"{LLM_BASE}/models/llm-a": body(llm_model(task="chat"))}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_llm_model(loader, "llm-a", task="embedding"),
    )
    assert error is not None and error.code == "model_task_mismatch"


# --- status, redirects, bounds and secrets -------------------------------------------------------


@pytest.mark.parametrize(
    "status,code,count",
    [
        (403, "remote_access_denied", 1),
        (429, "remote_rate_limited", 2),
        (500, "remote_failed", 1),
        (503, "remote_failed", 2),
        (302, "remote_failed", 1),
    ],
)
def test_status_codes_map_to_the_closed_codes_and_the_retry_policy(
    certificates, keys, monkeypatch, status, code, count
):
    headers = (("Location", "https://evil.example/x"),) if status == 302 else ()
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": Reply(status=status, headers=headers)}
    rig, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 20),
    )
    assert error is not None and error.code == code
    assert len(rig.server.requests) == count
    assert all(record.path.startswith(PLATFORM_BASE) for record in rig.server.requests)


def test_an_answer_over_the_shared_limit_is_refused(certificates, keys, monkeypatch):
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": Reply(body=b" " * (1024 * 1024 + 1))}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 20),
    )
    assert error is not None and error.code == "invalid_response"


def test_a_key_echoed_by_the_provider_is_refused_and_never_shown(certificates, keys, monkeypatch):
    echoed = {"items": [model_json(description=PLATFORM_KEY)], "total": 1}
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": body(echoed)}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 20),
    )
    assert error is not None and error.code == "invalid_response"
    assert PLATFORM_KEY not in str(error) and PLATFORM_KEY not in error.message


def test_a_catalog_command_writes_nothing_to_disk(certificates, keys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": body({"items": [], "total": 0})}
    run(certificates, monkeypatch, routes, lambda: client.list_platform_models(loader, 1, 20))
    assert list(tmp_path.iterdir()) == []


# --- the public API over the same fixture ------------------------------------------------------


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        f"""schema_version = 1
active_profile = "test"

[profiles.test]
platform_url = "https://localhost{PLATFORM_BASE}"
llm_url = "https://localhost{LLM_BASE}"
platform_key_env = "{PLATFORM_KEY_ENV}"
llm_key_env = "{LLM_KEY_ENV}"
"""
    )
    return path


def test_the_api_returns_the_page_inside_one_result_with_its_window(
    certificates, keys, monkeypatch, config_file
):
    from yorunge import api

    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body({"items": [model_json()], "total": 1})
    }
    with Rig(certificates, routes, monkeypatch) as rig:
        result = api.list_platform_models(config=config_file)
    reading = result.data
    assert reading.data.completeness == "complete"
    assert reading.data.models[0].model_id == MODEL_ID
    assert reading.observed_from <= reading.observed_until
    assert len(rig.server.requests) == 1


def test_the_api_shows_a_model_with_its_versions(certificates, keys, monkeypatch, config_file):
    from yorunge import api

    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    with Rig(certificates, routes, monkeypatch):
        result = api.show_platform_model(OWNER, SLUG, versions=True, config=config_file)
    detail = result.data.data
    assert detail.model.slug == SLUG
    assert detail.versions.completeness == "complete"


def test_the_api_resolves_one_tag_to_one_version(certificates, keys, monkeypatch, config_file):
    from yorunge import api

    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    with Rig(certificates, routes, monkeypatch):
        result = api.resolve_platform_version(OWNER, SLUG, "1.1", config=config_file)
    assert result.data.data.version.version_id == "version-1"


def test_the_api_refuses_a_missing_profile_before_any_request(
    certificates, keys, monkeypatch, config_file
):
    from yorunge import api

    with Rig(certificates, {}, monkeypatch) as rig:
        with pytest.raises(YorungeError) as info:
            api.list_platform_models(config=config_file, profile="nope")
    assert info.value.code == "profile_not_found"
    assert rig.server.requests == []


def test_the_api_refuses_a_missing_key_before_any_request(certificates, monkeypatch, config_file):
    from yorunge import api

    monkeypatch.delenv(PLATFORM_KEY_ENV, raising=False)
    with Rig(certificates, {}, monkeypatch) as rig:
        with pytest.raises(YorungeError) as info:
            api.list_platform_models(config=config_file)
    assert info.value.code == "credential_unavailable"
    assert rig.server.requests == []


def test_the_api_shows_the_llm_model_and_refuses_a_task_mismatch(
    certificates, keys, monkeypatch, config_file
):
    from yorunge import api

    routes = {f"{LLM_BASE}/models/llm-a": body(llm_model(task="chat"))}
    with Rig(certificates, routes, monkeypatch):
        assert api.show_llm_model("llm-a", config=config_file).data.data.task == "chat"
        with pytest.raises(YorungeError) as info:
            api.show_llm_model("llm-a", task="embedding", config=config_file)
    assert info.value.code == "model_task_mismatch"


def test_a_refused_model_request_is_an_invalid_request_not_a_remote_failure(
    certificates, keys, monkeypatch
):
    routes = {f"{LLM_BASE}/models/llm-a": Reply(status=422, body=b"{}")}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_llm_model(loader, "llm-a", task=None),
    )
    assert error is not None and error.code == "invalid_request"
