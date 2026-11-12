"""Public choices are exact, bounded and rejected before config/state side effects."""

import asyncio
from functools import partial
from pathlib import Path
from uuid import uuid4

import pytest

from tests.contracts.test_platform_upload_codec import PARAMETERS, SCOPE
from yorunge import api
from yorunge.adapters.upload_api import credit_micros
from yorunge.domain.errors import YorungeError


@pytest.mark.parametrize(
    "text,micros",
    [("0", 0), ("0.000001", 1), ("200", 200_000_000), ("9223372036854.775807", 2**63 - 1)],
)
def test_exact_credit_conversion_without_float(text, micros):
    assert credit_micros(text, False) == ("bounded_required", micros)
    assert credit_micros(None, True) == ("unpriced_accepted", None)


@pytest.mark.parametrize(
    "value,unpriced",
    [
        (None, False),
        ("200", True),
        ("200", 1),
        (True, False),
        (200, False),
        (200.0, False),
        ("", False),
        ("00", False),
        (" 1", False),
        ("+1", False),
        ("-0", False),
        ("1e2", False),
        ("NaN", False),
        ("۱", False),
        ("0.0000001", False),
        ("9223372036854.775808", False),
        ("1" * 33, False),
    ],
)
def test_invalid_or_unbounded_credit_choice_has_closed_error(value, unpriced):
    invoke = partial(credit_micros, value, unpriced)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "invalid_request"
    assert raised.value.__cause__ is raised.value.__context__ is None


@pytest.mark.parametrize(
    "change",
    [
        {"manifest": "not-path"},
        {"owner": None},
        {"project": 7},
        {"project": "bad"},
        {"parameters": PARAMETERS.model_copy(update={"name": True})},
        {"profile": True},
        {"profile": ""},
        {"config": "not-path"},
        {"state_dir": "not-path"},
        {"unpriced": True, "admission_policy": "verified_only"},
        {"unpriced": False},
        {"admission_policy": None},
    ],
)
def test_invalid_public_prepare_request_precedes_missing_config_and_state(tmp_path, change):
    root = tmp_path / "state"
    options = dict(
        manifest=tmp_path / "manifest",
        owner=SCOPE.owner,
        parameters=PARAMETERS,
        project=SCOPE.project_id,
        config=tmp_path / "missing.toml",
        state_dir=root,
        admission_policy="explicit_attempt",
        unpriced=True,
    )
    invoke = partial(api.prepare_dataset_upload, tmp_path / "root", **(options | change))
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "invalid_request"
    assert not root.exists()
    assert raised.value.__cause__ is raised.value.__context__ is None


def test_public_network_entrypoints_reject_active_loop_before_state(tmp_path):
    root, identity = tmp_path / "absent", str(uuid4())
    calls = (
        partial(
            api.prepare_dataset_upload,
            Path("root"),
            manifest=Path("manifest"),
            owner=SCOPE.owner,
            parameters=PARAMETERS,
            project=SCOPE.project_id,
            state_dir=root,
        ),
        partial(api.approve_dataset_upload, identity, "a" * 64, state_dir=root),
        partial(api.start_dataset_upload, identity, state_dir=root),
        partial(api.reconcile_dataset_upload, identity, state_dir=root),
    )

    async def run():
        for invoke in calls:
            with pytest.raises(YorungeError) as raised:
                invoke()
            assert raised.value.code == "invalid_request"

    asyncio.run(run())
    assert not root.exists()


@pytest.mark.parametrize(
    "origin,code",
    [
        ("https://storage.example", "unsupported_combination"),
        ("https://storage.example/path", "invalid_request"),
        (True, "invalid_request"),
    ],
)
def test_provider_direct_mode_is_not_silently_selected_or_contacted(tmp_path, origin, code):
    state = tmp_path / "state"
    invoke = partial(
        api.prepare_dataset_upload,
        tmp_path / "root",
        manifest=tmp_path / "manifest",
        owner=SCOPE.owner,
        parameters=PARAMETERS,
        project=SCOPE.project_id,
        storage_origin=origin,
        config=tmp_path / "missing",
        state_dir=state,
        admission_policy="explicit_attempt",
        unpriced=True,
    )
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == code
    assert not state.exists()
    assert raised.value.__cause__ is raised.value.__context__ is None


@pytest.mark.parametrize(
    "operation,change",
    [
        ("approve", {"confirmed_digest": None}),
        ("approve", {"accept_unpriced_cost": 1}),
        ("approve", {"accept_unverified_authority": "yes"}),
        ("approve", {"accept_unconfirmed_effects": 1}),
        ("reconcile", {"accept_unverified_read": 1}),
        ("start", {"profile": False}),
        ("resume", {"prepare": 1}),
        ("resume", {"accept_unverified_read": None}),
        ("resume", {"accept_unconfirmed_effects": "yes"}),
        # a choice of the plan, asked for without a plan: judged with the types, not after the store
        ("resume", {"accept_unconfirmed_effects": True}),
    ],
)
def test_invalid_public_controls_precede_store(tmp_path, operation, change):
    identity, root = str(uuid4()), tmp_path / "absent"
    if operation == "approve":
        options = dict(plan_id=identity, confirmed_digest="a" * 64, state_dir=root) | change
        invoke = partial(api.approve_dataset_upload, **options)
    elif operation == "reconcile":
        invoke = partial(api.reconcile_dataset_upload, identity, state_dir=root, **change)
    elif operation == "resume":
        invoke = partial(api.resume_dataset_upload, identity, state_dir=root, **change)
    else:
        invoke = partial(api.start_dataset_upload, identity, state_dir=root, **change)
    with pytest.raises(YorungeError) as raised:
        invoke()
    assert raised.value.code == "invalid_request"
    assert not root.exists()
    assert raised.value.__cause__ is raised.value.__context__ is None
