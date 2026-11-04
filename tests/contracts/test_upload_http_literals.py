"""Registered service URI provenance never weakens the generic HTTP constructor."""

import pytest

from yorunge.application.http_transport import HttpCredential, HttpRequest
from yorunge.domain.credentials import SecretValue, normalize_target
from yorunge.domain.errors import YorungeError

API = normalize_target("https://api.ssyz.org.tr/api/v1")
ID = "01a19492-2404-7701-afee-d45c26561062"
ROUTES = [
    ("me", "GET", "auth/me", ()),
    ("project", "GET", f"projects/{ID}", ()),
    ("create", "POST", "datasets", ()),
    ("project_link", "POST", f"projects/{ID}/datasets", ()),
    ("membership", "GET", f"projects/{ID}/datasets", ()),
    ("owned", "GET", "datasets", (("page", "1"), ("page_size", "20"), ("scope", "owned"))),
    ("detail", "GET", "datasets/sample-user/my-role", ()),
    ("role", "GET", f"datasets/{ID}/my-role", ()),
    ("presign", "POST", f"datasets/{ID}/upload/presign", ()),
    ("confirm", "POST", f"datasets/{ID}/upload/confirm", ()),
    ("items", "GET", f"datasets/{ID}/items", (("limit", "128"), ("cursor", "opaque-token"))),
]


def request(
    kind="me", method="GET", endpoint="auth/me", query=(), *, secret="synthetic-key", **changes
):
    captured = SecretValue(secret)
    args = dict(
        target=API,
        method=method,
        endpoint=endpoint,
        query=query,
        upload_endpoint=kind,
        credential=HttpCredential("X-API-Key", captured, target=API, service_id="evren-platform"),
        service_id="evren-platform",
        read_only=method == "GET",
    )
    args.update(changes)
    return HttpRequest(**args)


@pytest.mark.parametrize("kind,method,endpoint,query", ROUTES)
@pytest.mark.parametrize(
    "secret", ["a", "datasets", "projects", "my-role", "cursor", "owned", "1", "128"]
)
def test_fixed_protocol_is_exempt_only_for_exact_registered_shape(
    kind, method, endpoint, query, secret
):
    # The detail's slug is dynamic even when it spells a known protocol suffix.
    if kind == "detail" and secret == "my-role":
        with pytest.raises(YorungeError) as error:
            request(kind, method, endpoint, query, secret=secret)
        assert error.value.code == "invalid_request"
    else:
        result = request(kind, method, endpoint, query, secret=secret)
        assert result.upload_endpoint == kind
        assert result.wire_headers()[-1] == ("X-API-Key", secret)


@pytest.mark.parametrize(
    "kind,method,endpoint,query",
    [
        r
        for r in ROUTES
        if r[0] in {"project", "project_link", "membership", "role", "presign", "confirm", "items"}
    ],
)
def test_uuid_resource_is_checked_before_fixed_prefix_could_hide_it(kind, method, endpoint, query):
    with pytest.raises(YorungeError) as error:
        request(kind, method, endpoint, query, secret=ID)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("kind,method,endpoint,query", ROUTES)
def test_registered_kind_does_not_bypass_other_method_or_extra_query(kind, method, endpoint, query):
    other = "POST" if method == "GET" else "GET"
    with pytest.raises(YorungeError) as error:
        request(kind, other, endpoint, query)
    assert error.value.code == "invalid_service_target"
    extra = (*query, ("extra", "value"))
    with pytest.raises(YorungeError) as error:
        request(kind, method, endpoint, extra)
    assert error.value.code == "invalid_service_target"


@pytest.mark.parametrize("kind", ["unknown", "ME", "", True, 3])
def test_kind_is_closed_and_not_a_public_permission_flag(kind):
    with pytest.raises(YorungeError) as error:
        request(kind)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("target", ["https://api.example/api/v1", "https://api.ssyz.org.tr/v2"])
def test_registered_protocol_cannot_be_applied_to_another_origin_or_api_root(target):
    other = normalize_target(target)
    with pytest.raises(YorungeError) as error:
        request(target=other)
    assert error.value.code == "invalid_service_target"


def test_registered_profile_requires_bound_x_api_key_and_platform_service():
    with pytest.raises(YorungeError) as error:
        request(credential=None)
    assert error.value.code == "invalid_credential"
    bearer = HttpCredential(
        "Authorization", SecretValue("a"), prefix="Bearer ", target=API, service_id="evren-platform"
    )
    with pytest.raises(YorungeError) as error:
        request(credential=bearer)
    assert error.value.code == "invalid_credential"
    with pytest.raises(YorungeError) as error:
        request(service_id="evren-llm")
    assert error.value.code == "invalid_service_target"


def test_default_generic_http_policy_stays_strict_and_marker_is_not_sent():
    args = ROUTES[2]
    value = request(*args, secret="datasets")
    assert value.url == "https://api.ssyz.org.tr/api/v1/datasets"
    assert "upload_endpoint" not in dict(value.wire_headers())
    with pytest.raises(YorungeError) as error:
        request(*args, secret="datasets", upload_endpoint=None)
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize("page", ["0", "01", "129", "1.0", "1e2", "١", ""])
def test_owned_pagination_is_canonical_bounded_protocol_not_free_query(page):
    query = (("page", page), ("page_size", "20"), ("scope", "owned"))
    with pytest.raises(YorungeError) as error:
        request("owned", "GET", "datasets", query)
    assert error.value.code == "invalid_service_target"


@pytest.mark.parametrize("page", ["1", "128"])
def test_owned_page_boundaries_and_order_independence(page):
    query = (("scope", "owned"), ("page_size", "20"), ("page", page))
    assert request("owned", "GET", "datasets", query, secret=page)


@pytest.mark.parametrize("size", ["5", "128", "020", "21"])
def test_owned_page_size_is_the_observed_fixed_value_with_no_automatic_fallback(size):
    query = (("page", "1"), ("page_size", size), ("scope", "owned"))
    with pytest.raises(YorungeError) as error:
        request("owned", "GET", "datasets", query)
    assert error.value.code == "invalid_service_target"


@pytest.mark.parametrize("cursor", ["", "x" * 1025, "a\n", "\u202e", "ü" * 513])
def test_cursor_rejects_control_and_utf8_byte_overflow(cursor):
    query = (("limit", "128"), ("cursor", cursor))
    with pytest.raises(YorungeError) as error:
        request("items", "GET", f"datasets/{ID}/items", query)
    assert error.value.exit_code == 2


def test_cursor_is_opaque_but_selected_credential_is_dynamic():
    query = (("limit", "128"), ("cursor", "a%2F+b="))
    result = request("items", "GET", f"datasets/{ID}/items", query)
    assert result.url.endswith("limit=128&cursor=a%252F%2Bb%3D")
    query = (("limit", "128"), ("cursor", "cursor"))
    with pytest.raises(YorungeError) as error:
        request("items", "GET", f"datasets/{ID}/items", query, secret="cursor")
    assert error.value.code == "invalid_request"


@pytest.mark.parametrize(
    "endpoint",
    [
        f"datasets/{ID}/other",
        f"datasets/{ID}/upload/confirm/extra",
        f"datasets/{ID}/%75pload/confirm",
    ],
)
def test_kind_never_grants_an_unregistered_route(endpoint):
    with pytest.raises(YorungeError) as error:
        request("confirm", "POST", endpoint)
    assert error.value.code == "invalid_service_target"
