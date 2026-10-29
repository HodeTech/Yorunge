"""Immutable decode reuse never caches live relationships or accepts changed rows."""

import json
from functools import partial
from uuid import uuid4

import pytest

from tests.integration.test_operation_store import raw_record, terminal_fixture
from yorunge.adapters.operation_store import read_job
from yorunge.adapters.state import open_store, validate_contents
from yorunge.adapters.validation_memo import validation_session
from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import YorungeError


@pytest.mark.parametrize("entry", ["warm", "full"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("ownership_clock_generation", 2),
        ("ownership_identity_epoch", "different"),
        ("expires_at", "same_time"),
    ],
)
def test_persisted_owner_scope_and_interval_match_its_last_business_observation(
    admitted_operation, entry, field, value
):
    root, _, record, _, _ = admitted_operation
    value = (
        str(uuid4())
        if value == "different"
        else record.summary.updated_at
        if value == "same_time"
        else value
    )
    changed = record.model_copy(update={"lease": record.lease.model_copy(update={field: value})})
    with open_store(root) as store:
        raw_record(store.connection, changed)
        if entry == "warm":
            invoke = partial(read_job, store.connection, record.summary.operation_id)
        else:
            invoke = partial(validate_contents, store.connection)
        with pytest.raises(YorungeError) as error:
            invoke()
        assert error.value.code == "state_invalid"


@pytest.mark.parametrize("entry", ["warm", "full"])
def test_delivery_policy_cannot_be_changed_in_stored_admission(admitted_operation, entry):
    root, _, record, _, event = admitted_operation
    changed = record.model_copy(
        update={
            "admission": record.admission.model_copy(update={"delivery_required": True}),
            "summary": record.summary.model_copy(update={"delivery_status": "pending"}),
        }
    )
    with open_store(root) as store:
        raw_record(store.connection, changed)
        store.connection.execute(
            "UPDATE operation_events SET payload=?",
            (
                canonical(
                    event.model_copy(update={"delivery_status": "pending"}).model_dump(mode="json")
                ).decode(),
            ),
        )
        if entry == "warm":
            invoke = partial(read_job, store.connection, record.summary.operation_id)
        else:
            invoke = partial(validate_contents, store.connection)
        with pytest.raises(YorungeError) as error:
            invoke()
        assert error.value.code == "state_invalid"


@pytest.mark.parametrize(
    "tamper", ["event", "event_index", "attempt_index", "outcome", "plan", "record_counter"]
)
def test_warmed_validation_session_rechecks_changed_row_bytes_and_live_relationships(
    admitted_operation, tamper
):
    root, _, record, attempt, event = admitted_operation
    with open_store(root) as store, validation_session():
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        record, _, _ = terminal_fixture(connection, record, attempt, event)
        connection.execute("COMMIT")
        validate_contents(connection)
        assert read_job(connection, record.summary.operation_id).operation.status == "succeeded"
        if tamper == "event":
            payload = connection.execute(
                "SELECT payload FROM operation_events WHERE sequence=2"
            ).fetchone()[0]
            raw = json.loads(payload)
            raw["status"] = raw["execution_status"] = "running"
            connection.execute(
                "UPDATE operation_events SET payload=? WHERE sequence=2", (canonical(raw).decode(),)
            )
        elif tamper == "event_index":
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute(
                "UPDATE operation_events SET attempt_id=? WHERE sequence=2", (str(uuid4()),)
            )
        elif tamper == "attempt_index":
            connection.execute("UPDATE operation_attempts SET status='unknown'")
        elif tamper == "outcome":
            payload = connection.execute("SELECT payload FROM operation_outcomes").fetchone()[0]
            raw = json.loads(payload)
            raw["provider_exit_code"] = 7
            connection.execute(
                "UPDATE operation_outcomes SET payload=?", (canonical(raw).decode(),)
            )
        elif tamper == "plan":
            payload = connection.execute("SELECT payload FROM execution_plans").fetchone()[0]
            connection.execute(
                "UPDATE execution_plans SET payload=?", ('{"schema_version":2,' + payload[1:],)
            )
        else:
            raw_record(
                connection,
                record.model_copy(
                    update={"summary": record.summary.model_copy(update={"revision": 2})}
                ),
            )
        with pytest.raises(YorungeError) as error:
            read_job(connection, record.summary.operation_id)
        assert error.value.code == "state_invalid"
        with pytest.raises(YorungeError) as error:
            validate_contents(connection)
        assert error.value.code == "state_invalid"
