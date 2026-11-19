"""The catalog reads on loopback TLS (P02-4d, ADR-0035): what goes on the wire and what comes back.

The provider is a synthetic TLS server; the product's own session and transport run against it.
Every assertion looks at the recorded requests: the key only where the schema says it goes, the
exact query, the number of GETs per command, no redirect followed, and no state written.
"""

import argparse
import json
import shlex
import socket
from pathlib import Path

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
    assert error is not None
    assert error.code == "invalid_response"
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
    assert error is not None
    assert error.code == "invalid_response"


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
    assert error is not None
    assert error.code == "model_ambiguous"


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
    assert error is not None
    assert error.code == "invalid_response"


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
    assert error is not None
    assert error.code == "model_not_visible"


def test_a_dot_segment_is_refused_before_any_request(certificates, keys, monkeypatch):
    rig, _, error = run(
        certificates,
        monkeypatch,
        {},
        lambda: client.show_platform_model(loader, "..", SLUG, versions=False),
    )
    assert error is not None
    assert error.code == "invalid_request"
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
            headers=(("X-Has-Next", "0"), ("X-Total-Count", "1")),
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
    assert error is not None
    assert error.code == "model_not_visible"


def test_a_llm_task_mismatch_is_refused(certificates, keys, monkeypatch):
    routes = {f"{LLM_BASE}/models/llm-a": body(llm_model(task="chat"))}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_llm_model(loader, "llm-a", task="embedding"),
    )
    assert error is not None
    assert error.code == "model_task_mismatch"


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
    assert error is not None
    assert error.code == code
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
    assert error is not None
    assert error.code == "invalid_response"


def test_a_key_echoed_by_the_provider_is_refused_and_never_shown(certificates, keys, monkeypatch):
    echoed = {"items": [model_json(description=PLATFORM_KEY)], "total": 1}
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": body(echoed)}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 20),
    )
    assert error is not None
    assert error.code == "invalid_response"
    assert PLATFORM_KEY not in str(error)
    assert PLATFORM_KEY not in error.message


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
    assert error is not None
    assert error.code == "invalid_request"


# --- review round 1: bounds, statuses, identities and arguments before any request --------------


@pytest.mark.parametrize(
    "page", [pytest.param(2**53 + 1, id="above-range"), pytest.param(10**5000, id="huge")]
)
def test_an_absurd_page_number_is_refused_before_any_request(certificates, keys, monkeypatch, page):
    rig, _, error = run(
        certificates,
        monkeypatch,
        {},
        lambda: client.list_platform_models(loader, page, 20),
    )
    assert error is not None
    assert error.code == "invalid_request"
    assert rig.server.requests == []


def test_a_refused_list_request_is_an_invalid_request_on_every_catalog_endpoint(
    certificates, keys, monkeypatch
):
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=100": Reply(status=422, body=b"{}")}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 100),
    )
    assert error is not None
    assert error.code == "invalid_request"


def test_platform_detail_404_is_not_visible_and_422_is_a_refused_request(
    certificates, keys, monkeypatch
):
    routes = {f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": Reply(status=404, body=b"{}")}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=False),
    )
    assert error is not None
    assert error.code == "model_not_visible"
    routes = {f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": Reply(status=422, body=b"{}")}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=False),
    )
    assert error is not None
    assert error.code == "invalid_request"


def test_a_versions_404_is_not_visible_after_a_visible_detail(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": Reply(status=404, body=b"{}"),
    }
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=True),
    )
    assert error is not None
    assert error.code == "model_not_visible"


def test_a_detail_redirect_is_not_followed(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": Reply(
            status=302, headers=(("Location", "https://evil.example/x"),)
        )
    }
    rig, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=False),
    )
    assert error is not None
    assert error.code == "remote_failed"
    assert len(rig.server.requests) == 1


def test_resolving_a_tag_refuses_a_detail_of_another_model_after_one_get(
    certificates, keys, monkeypatch
):
    routes = {f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(owner_username="other"))}
    rig, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.resolve_platform_version(loader, OWNER, SLUG, "1.0"),
    )
    assert error is not None
    assert error.code == "invalid_response"
    assert len(rig.server.requests) == 1


def test_a_provider_identifier_outside_the_alphabet_is_a_bad_answer_not_a_bad_argument(
    certificates, keys, monkeypatch
):
    routes = {f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(id="bad:id"))}
    rig, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=True),
    )
    assert error is not None
    assert error.code == "invalid_response"
    assert len(rig.server.requests) == 1


@pytest.mark.parametrize("task", ["", 123, "emb​edding", "x" * 65])
def test_a_bad_task_argument_is_refused_before_any_request(certificates, keys, monkeypatch, task):
    rig, _, error = run(
        certificates,
        monkeypatch,
        {},
        lambda: client.show_llm_model(loader, "llm-a", task=task),
    )
    assert error is not None
    assert error.code == "invalid_request"
    assert rig.server.requests == []


@pytest.mark.parametrize("flag", ["no", 1, None])
def test_a_versions_flag_that_is_not_a_boolean_is_refused_before_any_request(
    certificates, keys, monkeypatch, flag
):
    rig, _, error = run(
        certificates,
        monkeypatch,
        {},
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=flag),
    )
    assert error is not None
    assert error.code == "invalid_request"
    assert rig.server.requests == []


def test_each_request_carries_only_its_own_service_key(certificates, keys, monkeypatch):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json()),
        f"{LLM_BASE}/models/llm-a": body(llm_model()),
    }
    rig, _, _ = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=False),
    )
    assert rig.server.requests[0].header("Authorization") is None
    assert rig.server.requests[0].header("X-API-Key") == PLATFORM_KEY
    rig, _, _ = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_llm_model(loader, "llm-a", task=None),
    )
    assert rig.server.requests[0].header("X-API-Key") is None
    assert rig.server.requests[0].header("Authorization") == f"Bearer {LLM_KEY}"


def test_the_window_starts_at_the_first_request_and_ends_after_the_last_body(
    certificates, keys, monkeypatch
):
    from datetime import UTC, datetime, timedelta

    class Ticks:
        """A clock that moves one second for every reading, so the window's ends are countable."""

        readings = 0

        def now(self):
            Ticks.readings += 1
            return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=Ticks.readings)

    monkeypatch.setattr(client, "SystemClock", Ticks)
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    _, observed, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=True),
    )
    assert error is None
    # The first reading opens the window (the first request); the last body closes it (the third
    # reading: the first body, then the second). A window ending at the first body would read two.
    assert observed.observed_from == "2026-01-01T00:00:01.000000Z"
    assert observed.observed_until == "2026-01-01T00:00:03.000000Z"


def test_a_model_id_longer_than_the_address_alphabet_cannot_be_listed_by_versions(
    certificates, keys, monkeypatch
):
    long_id = "m" * 129
    routes = {f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(id=long_id))}
    rig, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.show_platform_model(loader, OWNER, SLUG, versions=True),
    )
    assert error is not None
    assert error.code == "invalid_response"
    assert len(rig.server.requests) == 1


def test_a_list_endpoint_404_is_a_remote_failure_not_a_visibility_answer(
    certificates, keys, monkeypatch
):
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": Reply(status=404, body=b"{}")}
    _, _, error = run(
        certificates,
        monkeypatch,
        routes,
        lambda: client.list_platform_models(loader, 1, 20),
    )
    assert error is not None
    assert error.code == "remote_failed"


def test_api_lists_versions_datasets_and_llm_models(certificates, keys, monkeypatch, config_file):
    from yorunge import api

    routes = {
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
        f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned": Reply(
            body=json.dumps([]).encode("utf-8"), headers=(("X-Has-Next", "0"),)
        ),
        f"{LLM_BASE}/models": body({"object": "list", "data": [llm_model()]}),
    }
    with Rig(certificates, routes, monkeypatch):
        versions = api.list_platform_versions(MODEL_ID, config=config_file).data.data
        datasets = api.list_platform_datasets(config=config_file).data.data
        models = api.list_llm_models(config=config_file).data.data
    assert versions.completeness == "unknown"
    assert datasets.completeness == "complete"
    assert datasets.returned == 0
    assert models.models[0].model_id == "llm-a"


# --- the command line over the same fixture (P02-4e) ------------------------------------------


def cli(capsys, argv):
    from yorunge.cli import main as cli_main

    code = cli_main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def test_the_list_prints_a_plain_page_and_hides_control_characters(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body(
            {"items": [model_json(name="Model\x1b[2JA")], "total": 1}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, err = cli(
            capsys,
            ["models", "list", "--service", "evren-platform", "--config", str(config_file)],
        )
    assert code == 0
    assert f"{OWNER}/{SLUG}" in out
    assert "Platform modelleri" in out
    assert "\x1b" not in out
    assert "\x1b" not in err
    assert "Gözlem:" in out


def test_the_json_list_is_the_result_envelope_with_its_window(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body({"items": [model_json()], "total": 1})
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-platform",
                "--config",
                str(config_file),
                "--output",
                "json",
            ],
        )
    assert code == 0
    envelope = json.loads(out)
    assert envelope["data"]["data"]["models"][0]["slug"] == SLUG
    assert envelope["data"]["observed_from"] <= envelope["data"]["observed_until"]
    assert "weights_url" not in out


def test_the_ndjson_list_is_one_result_event_per_command(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body({"items": [model_json()], "total": 1})
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-platform",
                "--config",
                str(config_file),
                "--output",
                "ndjson",
            ],
        )
    assert code == 0
    events = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert any(event.get("event") == "result" for event in events)


def test_show_with_versions_prints_the_versions_and_no_location(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "show",
                "--service",
                "evren-platform",
                "--model",
                f"{OWNER}/{SLUG}",
                "--versions",
                "--config",
                str(config_file),
            ],
        )
    assert code == 0
    assert "Sürümler" in out
    assert "version-1" in out
    assert "--version-id" in out
    assert "signed" not in out
    assert "weights_url" not in out


def test_an_llm_list_filters_by_task_on_the_client_only(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{LLM_BASE}/models": body(
            {
                "object": "list",
                "data": [
                    llm_model(id="emb-a", task="embedding"),
                    llm_model(id="chat-b", task="chat"),
                ],
            }
        )
    }
    with Rig(certificates, routes, monkeypatch) as rig:
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-llm",
                "--task",
                "embedding",
                "--config",
                str(config_file),
            ],
        )
    assert code == 0
    assert "emb-a" in out
    assert "chat-b" not in out
    assert "görev süzmesi: embedding" in out
    assert [record.path for record in rig.server.requests] == [f"{LLM_BASE}/models"]


@pytest.mark.parametrize(
    "argv,code",
    [
        (["models", "list", "--service", "evren-llm", "--page", "1"], 2),
        (["models", "list", "--service", "evren-platform", "--task", "chat"], 2),
        (["models", "show", "--service", "evren-platform", "--model-id", "x"], 2),
        (["models", "show", "--service", "evren-llm", "--model-id", "x", "--versions"], 2),
        (["models", "show", "--service", "evren-llm", "--model", "a/b"], 2),
        (["models", "show", "--service", "evren-platform", "--model", "no-slash"], 2),
        (["models", "show", "--service", "evren-platform", "--model", "a/b", "--model-id", "x"], 2),
        (["models", "show", "--service", "evren-platform", "--model", "a/b", "--task", "chat"], 2),
        (["models", "list", "--service", "evren-llm", "--page-size", "5"], 2),
        (["datasets", "list", "--state-dir", "/tmp/state"], 2),
    ],
)
def test_a_refused_combination_exits_two_without_a_request(
    certificates, keys, monkeypatch, config_file, capsys, argv, code
):
    with Rig(certificates, {}, monkeypatch) as rig:
        got, out, err = cli(capsys, [*argv, "--config", str(config_file), "--output", "json"])
    assert got == code
    assert "invalid_request" in out + err
    assert rig.server.requests == []


def test_a_model_not_visible_says_it_is_not_a_proof_of_absence(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {f"{LLM_BASE}/models/llm-a": Reply(status=404, body=b"{}")}
    with Rig(certificates, routes, monkeypatch):
        code, out, err = cli(
            capsys,
            [
                "models",
                "show",
                "--service",
                "evren-llm",
                "--model-id",
                "llm-a",
                "--config",
                str(config_file),
            ],
        )
    assert code == 1
    assert "kesin bir yokluk kanıtı değildir" in out + err


def test_the_dataset_page_says_its_scope_is_not_confirmed(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned": Reply(
            body=b"[]", headers=(("X-Has-Next", "0"),)
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(capsys, ["datasets", "list", "--config", str(config_file)])
    assert code == 0
    assert "Veri setleri" in out
    assert "kapsam: teyit edilmedi" in out


# --- review round 1 of the command line (P02-4e) ----------------------------------------------


@pytest.mark.parametrize("task", ["", "x" * 65, "emb\x1bedding", " chat", "chat ", "   "])
def test_a_bad_llm_task_is_refused_before_the_list_is_requested(
    certificates, keys, monkeypatch, config_file, capsys, task
):
    with Rig(certificates, {}, monkeypatch) as rig:
        code, out, err = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-llm",
                "--task",
                task,
                "--config",
                str(config_file),
                "--output",
                "json",
            ],
        )
    assert code == 2
    assert "invalid_request" in out + err
    assert rig.server.requests == []


def test_a_task_filter_with_no_match_says_so_and_not_that_nothing_is_visible(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{LLM_BASE}/models": body(
            {"object": "list", "data": [llm_model(id="emb-a", task="embedding")]}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-llm",
                "--task",
                "rerank",
                "--config",
                str(config_file),
            ],
        )
    assert code == 0
    assert "görev rerank ile eşleşen model yok" in out
    assert "(görünen model yok)" not in out


def test_a_long_description_is_shown_in_full_up_to_the_display_limit(
    certificates, keys, monkeypatch, config_file, capsys
):
    description = "d" * 300
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(
            model_json(versions_count=0, description=description)
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "show",
                "--service",
                "evren-platform",
                "--model",
                f"{OWNER}/{SLUG}",
                "--config",
                str(config_file),
            ],
        )
    assert code == 0
    assert f"açıklama: {description}" in out


def test_a_long_identifier_is_shown_whole_not_cut_with_an_ellipsis(
    certificates, keys, monkeypatch, config_file, capsys
):
    long_id = "L" * 200
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body(
            {"items": [model_json(id=long_id)], "total": 1}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            ["models", "list", "--service", "evren-platform", "--config", str(config_file)],
        )
    assert code == 0
    assert f"kimlik {long_id}" in out
    assert "…" not in out


def test_an_owner_less_model_in_a_list_gets_the_identifier_route_once(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body(
            {"items": [model_json(owner_username=None)], "total": 1}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            ["models", "list", "--service", "evren-platform", "--config", str(config_file)],
        )
    assert code == 0
    assert "(sahip adı yok)" in out
    assert out.count("--model-id KIMLIK --versions") == 1


def test_a_partial_platform_page_names_the_next_page_command(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body(
            {"items": [model_json()] * 20, "total": 45}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            ["models", "list", "--service", "evren-platform", "--config", str(config_file)],
        )
    assert code == 0
    assert (
        "Sonraki sayfa: yorunge models list --service evren-platform --page 2 --page-size 20" in out
    )


def test_a_partial_dataset_page_names_the_next_page_command(
    certificates, keys, monkeypatch, config_file, capsys
):
    row = {
        "id": "dataset-1",
        "name": "Dataset A",
        "slug": "dataset-a",
        "modality": "VISION",
        "item_count": 3,
        "visibility": "PRIVATE",
        "updated_at": STAMP,
        "owner_username": OWNER,
    }
    routes = {
        f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned": Reply(
            body=json.dumps([row] * 20).encode("utf-8"), headers=(("X-Has-Next", "1"),)
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(capsys, ["datasets", "list", "--config", str(config_file)])
    assert code == 0
    assert "Sonraki sayfa: yorunge datasets list --page 2 --page-size 20" in out


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--page-size", "0"),
        ("--page", "١"),
        ("--page", "9" * 40),
        ("--page-size", "101"),
        ("--page", "-1"),
        ("--page", "1e3"),
    ],
)
def test_a_bad_page_number_is_refused_before_any_request(
    certificates, keys, monkeypatch, config_file, capsys, flag, value
):
    with Rig(certificates, {}, monkeypatch) as rig:
        code, out, err = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-platform",
                flag,
                value,
                "--config",
                str(config_file),
                "--output",
                "json",
            ],
        )
    assert code == 2
    assert rig.server.requests == []


def test_a_model_not_visible_error_names_a_command_that_runs(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {f"{LLM_BASE}/models/llm-a": Reply(status=404, body=b"{}")}
    with Rig(certificates, routes, monkeypatch):
        code, out, err = cli(
            capsys,
            [
                "models",
                "show",
                "--service",
                "evren-llm",
                "--model-id",
                "llm-a",
                "--config",
                str(config_file),
            ],
        )
    assert code == 1
    assert "yorunge models list --service evren-platform" in out + err


def test_ndjson_stdout_is_only_event_lines(certificates, keys, monkeypatch, config_file, capsys):
    routes = {f"{PLATFORM_BASE}/models?page=1&page_size=20": body({"items": [], "total": 0})}
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-platform",
                "--config",
                str(config_file),
                "--output",
                "ndjson",
            ],
        )
    assert code == 0
    lines = [line for line in out.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    assert events
    assert all(isinstance(event, dict) for event in events)


# --- review round 2 of the command line (P02-4e) ------------------------------------------------


def dataset_row(**overrides):
    row = {
        "id": "dataset-1",
        "name": "Dataset A",
        "slug": "dataset-a",
        "modality": "VISION",
        "item_count": 3,
        "visibility": "PRIVATE",
        "updated_at": STAMP,
        "owner_username": OWNER,
    }
    row.update(overrides)
    return row


def test_a_task_filter_is_recorded_in_the_json_reading(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{LLM_BASE}/models": body(
            {"object": "list", "data": [llm_model(id="emb-a", task="embedding")]}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-llm",
                "--task",
                "embedding",
                "--config",
                str(config_file),
                "--output",
                "json",
            ],
        )
    assert code == 0
    assert json.loads(out)["data"]["data"]["task_filter"] == "embedding"


def test_a_task_filter_on_an_empty_provider_list_records_no_filter(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {f"{LLM_BASE}/models": body({"object": "list", "data": []})}
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-llm",
                "--task",
                "embedding",
                "--config",
                str(config_file),
                "--output",
                "json",
            ],
        )
    assert code == 0
    assert json.loads(out)["data"]["data"]["task_filter"] is None
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-llm",
                "--task",
                "embedding",
                "--config",
                str(config_file),
            ],
        )
    assert code == 0
    assert "görev süzmesi" not in out
    assert "(görünen model yok)" in out


def test_the_task_filter_keeps_the_provider_warnings_and_the_window() -> None:
    from yorunge.cli.catalog import _filter_by_task
    from yorunge.domain.catalog import CatalogReading, LlmListing, LlmModel
    from yorunge.domain.models import Result

    listing = LlmListing(
        models=(
            LlmModel(model_id="emb-a", task="embedding", created=1),
            LlmModel(model_id="chat-b", task="chat", created=1),
        )
    )
    reading = CatalogReading[LlmListing](observed_from=STAMP, observed_until=STAMP, data=listing)
    result = Result[CatalogReading[LlmListing]](data=reading, warnings=("kısmi uyarı",))
    filtered = _filter_by_task(result, "embedding")
    assert [model.model_id for model in filtered.data.data.models] == ["emb-a"]
    assert filtered.data.data.task_filter == "embedding"
    assert filtered.data.observed_from == STAMP
    assert filtered.data.observed_until == STAMP
    assert filtered.warnings == ("kısmi uyarı",)


@pytest.mark.parametrize(
    "flag,value",
    [("--page-size", "0"), ("--page", "0"), ("--page-size", "101"), ("--page", "9" * 40)],
)
def test_a_page_outside_the_catalog_range_says_invalid_request_before_any_request(
    certificates, keys, monkeypatch, config_file, capsys, flag, value
):
    with Rig(certificates, {}, monkeypatch) as rig:
        code, out, err = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-platform",
                flag,
                value,
                "--config",
                str(config_file),
                "--output",
                "json",
            ],
        )
    assert code == 2
    assert "invalid_request" in out + err
    assert rig.server.requests == []


def test_suggested_commands_repeat_the_config_and_profile_the_person_gave(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models?page=1&page_size=20": body(
            {"items": [model_json(owner_username=None)] + [model_json()] * 19, "total": 45}
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "list",
                "--service",
                "evren-platform",
                "--config",
                str(config_file),
                "--profile",
                "test",
            ],
        )
    assert code == 0
    lines = out.splitlines()
    owner_less = next(line for line in lines if "--model-id KIMLIK" in line)
    next_page = next(line for line in lines if line.startswith("Sonraki sayfa"))
    assert owner_less.endswith("--profile test")
    assert next_page.endswith("--profile test")

    routes = {
        f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned": Reply(
            body=json.dumps([dataset_row()] * 20).encode("utf-8"), headers=(("X-Has-Next", "1"),)
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            ["datasets", "list", "--config", str(config_file), "--profile", "test"],
        )
    assert code == 0
    next_page = next(line for line in out.splitlines() if line.startswith("Sonraki sayfa"))
    assert next_page.endswith("--profile test")


def test_the_download_hint_repeats_the_profile_the_person_gave(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {
        f"{PLATFORM_BASE}/models/{OWNER}/{SLUG}": body(model_json(versions_count=1)),
        f"{PLATFORM_BASE}/models/{MODEL_ID}/versions": body([version_json(1)]),
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(
            capsys,
            [
                "models",
                "show",
                "--service",
                "evren-platform",
                "--model",
                f"{OWNER}/{SLUG}",
                "--versions",
                "--config",
                str(config_file),
                "--profile",
                "test",
            ],
        )
    assert code == 0
    hint = next(line for line in out.splitlines() if "İndirme" in line)
    assert hint.endswith("--profile test")


def test_a_model_not_visible_error_repeats_the_config_and_profile(
    certificates, keys, monkeypatch, config_file, capsys
):
    routes = {f"{LLM_BASE}/models/llm-a": Reply(status=404, body=b"{}")}
    with Rig(certificates, routes, monkeypatch):
        code, out, err = cli(
            capsys,
            [
                "models",
                "show",
                "--service",
                "evren-llm",
                "--model-id",
                "llm-a",
                "--config",
                str(config_file),
                "--profile",
                "test",
            ],
        )
    assert code == 1
    assert f"--config {shlex.quote(str(config_file))} --profile test" in out + err


def test_the_catalog_hints_quote_the_config_path_and_leave_no_placeholder() -> None:
    from yorunge.cli.models import error_hints

    config = Path("my dir/config.toml")
    hints = error_hints(argparse.Namespace(config=config, profile="pilot"))
    expected = f"--config {shlex.quote(str(config))} --profile pilot"
    for code in (
        "model_not_visible",
        "model_ambiguous",
        "model_task_mismatch",
        "model_not_addressable",
    ):
        assert expected in hints[code]
        assert "{options}" not in hints[code]
    bare = error_hints(argparse.Namespace())
    assert "--config" not in bare["model_not_visible"]
    assert "{options}" not in bare["model_not_visible"]


def test_a_long_dataset_identifier_is_shown_whole_in_the_text_view(
    certificates, keys, monkeypatch, config_file, capsys
):
    long_id = "D" * 200
    routes = {
        f"{PLATFORM_BASE}/datasets?page=1&page_size=20&scope=owned": Reply(
            body=json.dumps([dataset_row(id=long_id)]).encode("utf-8"),
            headers=(("X-Has-Next", "0"),),
        )
    }
    with Rig(certificates, routes, monkeypatch):
        code, out, _ = cli(capsys, ["datasets", "list", "--config", str(config_file)])
    assert code == 0
    assert f"kimlik {long_id}" in out
    assert "…" not in out
