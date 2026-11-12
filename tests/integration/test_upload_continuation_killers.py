"""Gates, mappings and validators of the resume surface that no step test pinned (P02-3i R1-B).

The approval gate refuses locally before the provider is asked, the review of a continuation judges
its limits against its summary and its manifest, a start that finds an unfinished operation names
it with the code its latch says, and the reconcile of a continuation needs the explicit read choice.
"""

from types import SimpleNamespace

import pytest

from tests.integration.test_upload_continuation_public import (
    certificates as certificates,
)
from tests.integration.test_upload_continuation_public import (
    cli_show,
    code_of,
    interrupted_world,
)
from tests.integration.test_upload_continuation_public import loopback_only as loopback_only
from tests.integration.test_upload_continuation_public import prepared_input as prepared_input
from tests.integration.test_upload_continuation_public import public_inputs as public_inputs
from yorunge import api
from yorunge.domain.errors import OperationError, YorungeError


def test_a_second_approval_is_refused_before_the_provider_is_asked(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        requests = len(rig.server.requests)
        assert code_of(rig.approve) == "operation_conflict"
        assert len(rig.server.requests) == requests
        # the acknowledgements are judged before the existing approval (the original's order)
        assert (
            code_of(lambda: rig.approve(accept_unverified_authority=False)) == "approval_required"
        )
        assert len(rig.server.requests) == requests


def test_a_wrong_or_malformed_digest_is_refused_before_the_provider_is_asked(
    public_inputs, certificates, monkeypatch
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        requests = len(rig.server.requests)
        options = dict(
            accept_unverified_authority=True,
            accept_unpriced_cost=True,
            config=rig.config,
            state_dir=rig.state,
        )
        wrong = "0" * 64
        assert (
            code_of(lambda: api.approve_dataset_upload(rig.plan_id, wrong, **options))
            == "upload_plan_not_valid"
        )
        assert len(rig.server.requests) == requests
        for malformed in (rig.digest.upper(), rig.digest[:-1], rig.digest + "0"):
            assert (
                code_of(
                    lambda malformed=malformed: api.approve_dataset_upload(
                        rig.plan_id, malformed, **options
                    )
                )
                == "invalid_request"
            )
        assert len(rig.server.requests) == requests
        assert rig.show().approval_status is None


def test_a_succeeded_continuation_does_not_claim_a_verified_authority(
    public_inputs, certificates, monkeypatch, capsys
):
    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        started = rig.start().data
        assert started.operation_status == "succeeded"
        assert started.authority_verified is False
        code, out, _ = cli_show(capsys, rig.state, started.operation_id)
        assert "Yazma yetkisi doğrulanmış sayılmaz." in out
        assert "tarihsel olarak doğrulandı" not in out
        assert "Veri setinin bütün dosyalarının metadata eşliği doğrulandı" in out


def test_the_resume_api_refuses_an_active_loop_before_the_state_is_touched(tmp_path):
    import asyncio
    from uuid import uuid4

    from yorunge.domain.errors import YorungeError

    root, identity = tmp_path / "absent", str(uuid4())

    async def run():
        for call in (
            lambda: api.resume_dataset_upload(
                identity, accept_unverified_read=True, state_dir=root
            ),
            lambda: api.resume_dataset_upload(
                identity, prepare=True, accept_unverified_read=True, state_dir=root
            ),
        ):
            with pytest.raises(YorungeError) as raised:
                call()
            assert raised.value.code == "invalid_request"

    asyncio.run(run())
    assert not root.exists()


def test_a_hint_that_cannot_be_made_says_nothing_not_that_resume_is_fine(
    public_inputs, certificates, monkeypatch, capsys
):
    from yorunge.adapters import upload_public
    from yorunge.domain.errors import YorungeError

    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:

        def broken(source):
            raise YorungeError("state_invalid")

        monkeypatch.setattr(upload_public, "source_journal", broken)
        code, out, err = cli_show(capsys, rig.state, rig.source)
        assert code == 0
        assert "Durum: belirsiz" in out
        assert "Devam için" not in out
        assert "Devam şu an mümkün değil" not in out


def test_the_journal_is_in_the_closed_order_with_the_successor_named(monkeypatch):
    from yorunge.adapters import upload_chain
    from yorunge.domain.upload_resume import BLOCKERS

    calls = {}
    source = SimpleNamespace(
        chain=SimpleNamespace(journals=("j",), descendants=("d",), source="s"),
        manifest="m",
    )
    monkeypatch.setattr(upload_chain, "merge_chain", lambda journals, manifest: "chain")

    def verdict(descendants):
        calls["descendants"] = descendants
        return SimpleNamespace(related_operation_id="successor")

    monkeypatch.setattr(upload_chain, "descendant_verdict", verdict)
    monkeypatch.setattr(
        upload_chain, "source_blockers", lambda facts, v: ("source_terminal", "source_active")
    )
    monkeypatch.setattr(
        upload_chain, "chain_blockers", lambda chain: ("known_negative", "reconcile_available")
    )
    chain, blockers, related = upload_chain.source_journal(source)
    assert chain == "chain"
    assert related == "successor"
    assert calls["descendants"] == ("d",)
    assert blockers == tuple(name for name in BLOCKERS if name in blockers)
    assert set(blockers) == {
        "source_terminal",
        "source_active",
        "known_negative",
        "reconcile_available",
    }
    monkeypatch.setattr(
        upload_chain,
        "merge_chain",
        lambda journals, manifest: (_ for _ in ()).throw(ValueError("x")),
    )
    with pytest.raises(YorungeError) as raised:
        upload_chain.source_journal(source)
    assert raised.value.code == "state_invalid"


def test_a_plan_outside_its_window_is_refused_before_the_provider_is_asked(
    public_inputs, certificates, monkeypatch
):
    import time
    from datetime import UTC, datetime, timedelta

    from yorunge.adapters.upload_continuation_approval import approve_continuation_plan
    from yorunge.domain.errors import YorungeError

    class Shifted:
        def __init__(self, delta):
            self.delta = delta

        def now(self):
            return datetime.now(UTC) + self.delta

        def monotonic(self):
            return time.monotonic()

    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        requests = len(rig.server.requests)
        for delta in (timedelta(minutes=16), timedelta(hours=-1)):
            shifted = Shifted(delta)
            with pytest.raises(YorungeError) as raised:
                approve_continuation_plan(
                    rig.plan_id,
                    rig.digest,
                    lambda plan: api._upload_context(rig.config, None, plan),
                    rig.state,
                    authority=True,
                    unpriced=True,
                    unconfirmed=False,
                    clock=shifted,
                )
            assert raised.value.code == "upload_plan_not_valid", delta
        assert len(rig.server.requests) == requests
        assert rig.show().approval_status is None


def _review_payload(review):
    import json

    return json.loads(review.encoded())


def test_the_review_of_a_continuation_judges_its_limits_against_its_summary_and_manifest(
    public_inputs, certificates, monkeypatch
):
    import json

    from yorunge.domain.upload_public import UploadIntentReview

    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        review = api.review_dataset_upload(rig.plan_id, state_dir=rig.state).data
        original = api.review_dataset_upload(
            api.show_dataset_upload(operation_id=rig.source, state_dir=rig.state).data.plan_id,
            state_dir=rig.state,
        ).data
    good = _review_payload(review)
    total = good["manifest"]["total_bytes"]
    assert UploadIntentReview.model_validate_json(json.dumps(good)) == review

    def changed(base, limits=None, summary=None, whole=None):
        value = json.loads(json.dumps(base))
        value["request_limits"] = {**value["request_limits"], **(limits or {})}
        value["summary"] = {**value["summary"], **(summary or {})}
        value.update(whole or {})
        return value

    def refused(payload):
        dumps_value = json.dumps(payload)
        with pytest.raises(ValueError):  # a ValidationError, never another exception
            UploadIntentReview.model_validate_json(dumps_value)

    # M in the limits is not the M of the summary
    refused(changed(good, {"max_presign": 2, "max_put": 2, "max_confirm": 2}))  # F01
    # M plus what is on the provider is not the manifest
    refused(changed(good, summary={"remote_present_files": 0}))  # F02
    # the byte ceiling may not exceed the manifest's total ...
    refused(changed(good, {"max_upload_bytes": total + 1}))
    # ... but may equal it when the files left out are empty (M < N, bytes == total)
    UploadIntentReview.model_validate_json(
        json.dumps(changed(good, {"max_upload_bytes": total}))
    )  # F03
    # sending every file means sending every byte
    all_files = changed(
        good,
        {"max_presign": 3, "max_put": 3, "max_confirm": 3, "max_upload_bytes": total - 1},
        {"continuation_files": 3, "remote_present_files": 0},
    )
    refused(all_files)  # F04
    UploadIntentReview.model_validate_json(
        json.dumps(
            changed(
                good,
                {"max_presign": 3, "max_put": 3, "max_confirm": 3, "max_upload_bytes": total},
                {"continuation_files": 3, "remote_present_files": 0},
            )
        )
    )
    # a continuation has limits, an original upload does not carry a continuation's
    refused({**good, "request_limits": None})  # F05
    ref = _review_payload(original)
    all_limits = {
        **good["request_limits"],
        "max_presign": 3,
        "max_put": 3,
        "max_confirm": 3,
        "max_upload_bytes": total,
    }
    refused(
        {**ref, "request_limits": all_limits}
    )  # F06: M = N limits would pass the original's rules
    refused({**good, "request_limits": ref["request_limits"]})  # F07


def test_a_check_only_continuation_shows_no_counter_even_with_an_observer(
    public_inputs, certificates, monkeypatch
):
    """M=0 sends no byte: an observer (a terminal) must see nothing and nothing may fail."""
    from tests.fixtures.upload_provider import UploadProvider  # noqa: F401
    from tests.integration.test_upload_resume_observation import lose_confirm_of
    from yorunge.application.upload_progress import UploadProgress, observe_upload

    with interrupted_world(public_inputs, certificates, monkeypatch, prepare=False) as rig:
        lose_confirm_of(rig.provider, "ölçüm.bin", remembered=True)
        rig.provider.route_table[
            "/api/v1/datasets/00000000-0000-4000-8000-000000000909/upload/confirm"
        ] = rig.provider.confirm
        options = dict(accept_unverified_read=True, config=rig.config, state_dir=rig.state)
        first = api.resume_dataset_upload(rig.source, prepare=True, **options).data
        flags = dict(
            accept_unverified_authority=True,
            accept_unpriced_cost=True,
            config=rig.config,
            state_dir=rig.state,
        )
        api.approve_dataset_upload(first.plan_id, first.plan_digest, **flags)
        with pytest.raises(OperationError) as stopped:
            api.start_dataset_upload(first.plan_id, config=rig.config, state_dir=rig.state)
        interrupted = stopped.value.operation_id
        second = api.resume_dataset_upload(interrupted, prepare=True, **options).data
        assert second.observation.send_files == 0
        api.approve_dataset_upload(second.plan_id, second.plan_digest, **flags)
        seen: list[UploadProgress] = []
        with observe_upload(seen.append):
            done = api.start_dataset_upload(second.plan_id, config=rig.config, state_dir=rig.state)
        assert done.data.operation_status == "succeeded"
        assert done.data.continuation_files == 0
        assert seen == []


@pytest.mark.parametrize(
    "status,latched,code",
    [
        ("admitted", False, "operation_conflict"),  # another process admitted it, nothing sent yet
        ("running", True, "operation_uncertain"),
        ("unknown", True, "operation_uncertain"),
        ("failed", True, "operation_conflict"),
        ("cancelled", False, "operation_conflict"),
    ],
)
def test_a_start_that_finds_an_unfinished_operation_names_it_with_the_right_code(
    monkeypatch, status, latched, code
):
    """The loser of a start race: the winner's record is no success; its latch names the code."""
    from uuid import uuid4

    from yorunge.adapters import upload_api
    from yorunge.domain.dataset_continuation import DatasetContinuationPlanV3

    operation = str(uuid4())
    record = SimpleNamespace(status=status, workflow_latched=latched, operation_id=operation)
    monkeypatch.setattr(
        upload_api, "_plan_of", lambda *a, **k: object.__new__(DatasetContinuationPlanV3)
    )
    monkeypatch.setattr(
        upload_api,
        "run_upload_continuation",
        lambda *a, **k: SimpleNamespace(record=record, existing=True),
    )
    with pytest.raises(OperationError) as raised:
        upload_api.start_upload(str(uuid4()), lambda plan: None, None)
    assert (raised.value.code, raised.value.operation_id) == (code, operation)


def test_the_show_hint_gives_the_reason_then_the_next_step_of_each_blocker(
    public_inputs, certificates, monkeypatch, capsys
):
    from yorunge.cli.upload import BLOCKER_TEXT

    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()
        rig.start()
        code, out, _ = cli_show(capsys, rig.state, rig.source)
        reason, step = BLOCKER_TEXT["source_superseded"]
        assert f"- source_superseded: {reason}\n  Sonraki adım: {step}" in out


def test_reconcile_of_a_continuation_needs_the_explicit_read_choice(
    public_inputs, certificates, monkeypatch
):
    from yorunge.adapters.upload_continuation import ContinuationStages

    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        rig.approve()

        async def fails(self):
            raise OperationError("operation_uncertain", self.record.operation_id)

        real = ContinuationStages.verify
        monkeypatch.setattr(ContinuationStages, "verify", fails)
        with pytest.raises(OperationError) as stopped:
            rig.start()
        monkeypatch.setattr(ContinuationStages, "verify", real)
        operation = stopped.value.operation_id
        requests = len(rig.server.requests)
        with pytest.raises(OperationError) as refused:
            api.reconcile_dataset_upload(
                operation, accept_unverified_read=False, config=rig.config, state_dir=rig.state
            )
        assert refused.value.code == "approval_required"
        assert refused.value.operation_id == operation
        assert len(rig.server.requests) == requests
        # and an error of the reconcile names the operation that was asked about (B09)
        with pytest.raises(OperationError) as missing:
            api.reconcile_dataset_upload(
                "00000000-0000-4000-8000-0000000000aa",
                accept_unverified_read=True,
                config=rig.config,
                state_dir=rig.state,
            )
        assert missing.value.operation_id == "00000000-0000-4000-8000-0000000000aa"


def test_resume_of_a_v1_source_is_state_invalid_not_a_report(tmp_path):
    from tests.fixtures.upload_history import install_legacy_running
    from yorunge.adapters.state import open_existing_store
    from yorunge.domain.errors import YorungeError

    state = tmp_path / "state"
    api.initialize_state(state_dir=state)
    with open_existing_store(state) as store:
        install_legacy_running(store, history=True)
        operation, plan = store.connection.execute(
            "SELECT operation_id, plan_id FROM upload_operations"
        ).fetchone()
        scope = store.connection.execute(
            "SELECT payload FROM upload_plans WHERE plan_id=?", (plan,)
        ).fetchone()[0]
    import json

    scope = json.loads(scope)["scope"]
    config = tmp_path / "c.toml"
    config.write_text(
        f'schema_version = 1\nactive_profile = "{scope["profile"]}"\n'
        f'[profiles.{scope["profile"]}]\nplatform_key_env = "YB_KEY"\n'
        f'project_id = "{scope["project_id"]}"\n'
    )
    for prepare in (False, True):
        with pytest.raises(YorungeError) as raised:
            api.resume_dataset_upload(
                operation,
                prepare=prepare,
                accept_unverified_read=True,
                config=config,
                state_dir=state,
            )
        assert raised.value.code == "state_invalid"


def test_the_window_of_the_plan_is_closed_at_its_start_and_open_at_its_end(
    public_inputs, certificates, monkeypatch
):
    import time

    from yorunge.adapters.state import open_existing_store
    from yorunge.adapters.upload_continuation_approval import _approval_input
    from yorunge.adapters.upload_repository import StateUploads
    from yorunge.domain.capabilities import instant
    from yorunge.domain.errors import YorungeError

    class At:
        def __init__(self, moment):
            self.moment = moment

        def now(self):
            return self.moment

        def monotonic(self):
            return time.monotonic()

    with interrupted_world(public_inputs, certificates, monkeypatch) as rig:
        with open_existing_store(rig.state) as store:
            plan = StateUploads(store).show(plan_id=rig.plan_id).plan
        start, end = instant(plan.prepared_at), instant(plan.expires_at)
        flags = (True, True, False)
        _approval_input(rig.plan_id, rig.digest, flags, rig.state, At(start))
        at = At(end)
        with pytest.raises(YorungeError) as raised:
            _approval_input(rig.plan_id, rig.digest, flags, rig.state, at)
        assert raised.value.code == "upload_plan_not_valid"
