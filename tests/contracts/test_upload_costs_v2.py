"""Independent literal work/cost vectors and unsafe quote reuse regressions."""

import hashlib
import json
from pathlib import Path

import pytest

from yorunge.domain.dataset_upload import DatasetUploadPlan
from yorunge.domain.upload_costs import UploadCostBoundV2, UploadCostWork, complete_cost

FIXTURES = Path(__file__).parents[1] / "fixtures"
WORK = FIXTURES / "dataset-upload-cost-work-v2.json"
COST = FIXTURES / "dataset-upload-cost-bound-v2.json"
DIGEST = "6d44a978afb1076869c38239a94015462ee0ac888523541eb723574f5bb088a4"


def encode(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def work():
    return UploadCostWork.model_validate_json(WORK.read_bytes())


def cost(**updates):
    return UploadCostBoundV2.model_validate_json(
        encode({**json.loads(COST.read_bytes()), **updates})
    )


def test_independent_literal_wire_and_domain_separation():
    w, c = work(), cost()
    assert w.encoded() == WORK.read_bytes()
    assert c.encoded() == COST.read_bytes()
    assert w.digest() == DIGEST == c.work_digest
    assert w.digest() != hashlib.sha256(w.encoded()).hexdigest()
    assert complete_cost(w, c)
    assert not complete_cost(w, None)
    for value in (w, c):
        with pytest.raises(ValueError):
            value.scope = None


@pytest.mark.parametrize(
    "path,value",
    [
        (("manifest", "digest"), "1" * 64),
        (("manifest", "content_sha256"), "2" * 64),
        (("root", "anchor"), "/datasets/other"),
        (("root", "inode"), 3),
        (("parameters", "name"), "other"),
        (("parameters", "tags"), ["other"]),
        (("storage",), {"mode": "direct", "origin": "https://storage.invalid"}),
        (("scope", "service_origin"), "https://other.invalid"),
        (("scope", "api_base_path"), "/api/v2"),
        (("scope", "credential_revision"), 2),
        (("scope", "clock_generation"), 2),
        (("scope", "owner", "kind"), "organization"),
        (("scope", "project_id"), "00000000-0000-4000-8000-000000000009"),
        (("execution_window", "not_after"), "2026-11-02T11:14:59.000000Z"),
    ],
)
def test_different_work_never_reuses_same_scope_quote(path, value):
    data = json.loads(WORK.read_bytes())
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    changed = UploadCostWork.model_validate_json(encode(data))
    assert changed.digest() != DIGEST
    quote = cost()
    with pytest.raises(ValueError, match="scope or work mismatch"):
        complete_cost(changed, quote)


@pytest.mark.parametrize("count,total", [(4, 8), (3, 9), (128, 1024**3)])
def test_count_and_byte_change_require_new_bound_even_with_correct_limits(count, total):
    data = json.loads(WORK.read_bytes())
    data["manifest"].update(file_count=count, total_bytes=total)
    data["request_limits"].update(
        max_presign=count, max_put=count, max_confirm=count, max_upload_bytes=total
    )
    changed = UploadCostWork.model_validate_json(encode(data))
    assert len(changed.encoded()) < 16 * 1024
    quote = cost()
    with pytest.raises(ValueError, match="work mismatch"):
        complete_cost(changed, quote)


@pytest.mark.parametrize(
    "updates",
    [
        {"charge_categories": ["transfer"]},
        {"post_period_storage": "unknown"},
        {"charge_period_start": "2026-11-02T11:00:00.000001Z"},
        {"charge_period_end": "2026-11-02T11:14:59.999999Z"},
        {
            "charge_categories": ["transfer"],
            "post_period_storage": "unknown",
            "maximum_micros": 1,
        },
    ],
)
def test_legitimate_partial_evidence_is_not_whole_work_budget_coverage(updates):
    w, quote = work(), cost(**updates)
    assert not complete_cost(w, quote)
    assert quote.maximum_micros <= 200_000_000


def test_quote_freshness_is_distinct_from_charge_period():
    w = work()
    # Coverage alone is not a freshness/arm permission: the plan gate checks timestamps.
    expired = cost(
        checked_at="2026-11-01T00:00:00.000000Z",
        expires_at="2026-11-01T00:00:01.000000Z",
    )
    assert complete_cost(w, expired)
    refreshed = cost(checked_at="2026-11-02T11:00:00.000000Z")
    assert refreshed.semantic_key() == cost().semantic_key()
    changed = cost(charge_period_end="2026-11-02T11:16:00.000000Z")
    assert changed.semantic_key() != cost().semantic_key()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 1),
        ("maximum_micros", True),
        ("maximum_micros", 1.0),
        ("maximum_micros", -1),
        ("maximum_micros", 2**63),
        ("charge_categories", []),
        ("charge_categories", ["transfer", "create"]),
        ("charge_categories", ["transfer", "transfer"]),
        ("charge_categories", ["other"]),
        ("charge_categories", "transfer"),
        ("charge_period_start", "2026-11-02T11:15:00.000000Z"),
        ("charge_period_end", "2026-11-02T10:59:59.000000Z"),
        ("charge_period_end", "2026-11-02T11:15:00Z"),
        ("expires_at", "2026-11-02T10:59:59.000000Z"),
        ("work_digest", "G" * 64),
        ("post_period_storage", "assume_free"),
        ("source_id", "bad\nsource"),
        ("extra", None),
    ],
)
def test_invalid_cost_is_rejected_instead_of_becoming_unknown(field, value):
    data = json.loads(COST.read_bytes())
    data[field] = value
    raw = encode(data)
    with pytest.raises(ValueError):
        UploadCostBoundV2.model_validate_json(raw)


@pytest.mark.parametrize("field", list(json.loads(WORK.read_bytes())["request_limits"]))
@pytest.mark.parametrize("value", [True, 1.0, -1, 2**63])
def test_strict_request_limits(field, value):
    data = json.loads(WORK.read_bytes())
    data["request_limits"][field] = value
    raw = encode(data)
    with pytest.raises(ValueError):
        UploadCostWork.model_validate_json(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_create", 2),
        ("max_presign", 4),
        ("max_put", 4),
        ("max_confirm", 4),
        ("max_read_requests", 513),
        ("max_read_attempts", 1025),
        ("max_control_request_bytes", 4194305),
        ("max_control_response_bytes", 16777217),
        ("max_upload_bytes", 9),
    ],
)
def test_valid_integer_limits_cannot_widen_or_disagree_with_work(field, value):
    data = json.loads(WORK.read_bytes())
    data["request_limits"][field] = value
    raw = encode(data)
    with pytest.raises(ValueError):
        UploadCostWork.model_validate_json(raw)


@pytest.mark.parametrize("end", ["2026-11-02T11:00:00.000000Z", "2026-11-02T11:15:00.000001Z"])
def test_execution_window_is_positive_and_bounded(end):
    data = json.loads(WORK.read_bytes())
    data["execution_window"]["not_after"] = end
    raw = encode(data)
    with pytest.raises(ValueError):
        UploadCostWork.model_validate_json(raw)


@pytest.mark.parametrize("model", [UploadCostWork, UploadCostBoundV2])
@pytest.mark.parametrize(
    "raw",
    [
        b"{}",
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":1,"x":2}',
        b'{"x":"\xff"}',
        b'{"x":"\\ud800"}',
        b"\xef\xbb\xbf{}",
        b"{} trailing",
        b" " * (16 * 1024 + 1),
    ],
)
def test_strict_bounded_wire(model, raw):
    with pytest.raises(ValueError):
        model.model_validate_json(raw)


@pytest.mark.parametrize(
    "model,path,key",
    [
        (UploadCostWork, WORK, "root"),
        (UploadCostBoundV2, COST, "maximum_micros"),
    ],
)
def test_wire_guards_reject_otherwise_valid_duplicate_and_oversized_json(model, path, key):
    raw = path.read_bytes()
    data = json.loads(raw)
    assert model.model_validate_json(raw).encoded() == raw
    duplicate = raw[:-1] + b"," + encode(key) + b":" + encode(data[key]) + b"}"
    # Both values are valid and equal: a last-key-wins parser would accept this.
    assert json.loads(duplicate) == data
    with pytest.raises(ValueError, match="duplicate"):
        model.model_validate_json(duplicate)
    padded = b" " * (16 * 1024) + raw
    assert json.loads(padded) == data
    with pytest.raises(ValueError, match="bounded upload wire"):
        model.model_validate_json(padded)


def test_v1_literal_history_remains_byte_identical():
    raw = (FIXTURES / "dataset-upload-plan-v1.json").read_bytes()
    assert DatasetUploadPlan.model_validate_json(raw).encoded() == raw
    with pytest.raises(ValueError):
        UploadCostBoundV2.model_validate_json(raw)
