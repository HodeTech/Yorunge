"""Fresh synthetic history at the declared operation quotas; no product backend."""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from tests.fixtures.seed_migration_state import seed as seed_history
from yorunge.adapters.execution_store import read_approval, read_plan
from yorunge.adapters.operation_store import OPERATION_COLUMNS, operation_row, plan_authorities
from yorunge.adapters.state import open_store
from yorunge.domain.capabilities import canonical, instant, timestamp
from yorunge.domain.operations import (
    AttemptView,
    JobSummary,
    OperationAdmission,
    OperationEvent,
    OperationLease,
    OperationOutcome,
    OperationRecord,
)


def seed(root: Path, *, layout="terminal", maximum=True):
    if (
        root.exists()
        or root.is_symlink()
        or layout not in {"normal", "terminal", "mixed", "leases"}
    ):
        raise ValueError("new disposable root and known fixture layout required")
    seed_history(root, version=4, maximum=maximum)
    counts = {"operations": 0, "attempts": 0, "events": 0, "outcomes": 0}
    with open_store(root, timeout=120) as store:
        connection = store.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            ids = connection.execute(
                "SELECT plan_id FROM execution_plans ORDER BY plan_id"
            ).fetchall()
            for index, (plan_id,) in enumerate(ids):
                plan = read_plan(connection, plan_id)
                approval = read_approval(connection, plan).model_copy(
                    update={"status": "approved", "revoked_at": None}
                )
                identifier = str(uuid4())
                number = 1 if layout == "normal" else 16
                event_count = (
                    3
                    if layout == "normal"
                    else 256
                    if layout == "terminal" or (layout == "mixed" and index % 2)
                    else 255
                )
                terminal = event_count == 256
                status = "succeeded" if terminal else "running"
                delivery = "complete" if terminal else "pending"
                now = approval.approved_at
                attempt_ids = [str(uuid4()) for _ in range(number)]
                admission = OperationAdmission(
                    operation_id=identifier,
                    plan_id=plan_id,
                    plan_digest=plan.digest,
                    store_id=plan.store_id,
                    admission_identity_epoch=plan.identity_epoch,
                    admission_clock_generation=plan.clock_generation,
                    approval=approval,
                    authorities=plan_authorities(plan),
                    correlation=str(uuid4()),
                    delivery_required=True,
                )
                summary = JobSummary(
                    operation_id=identifier,
                    plan_id=plan_id,
                    plan_digest=plan.digest,
                    task=plan.selection.task,
                    tool=plan.selection.tool,
                    execution=plan.selection.execution,
                    created_at=now,
                    updated_at=now,
                    status=status,
                    execution_status=status,
                    delivery_status=delivery,
                    attempt_count=number,
                    revision=number + event_count - 1,
                    clock_anomaly=False,
                )
                lease = (
                    None
                    if terminal
                    else OperationLease(
                        owner_id=str(uuid4()),
                        fence=number,
                        ownership_identity_epoch=plan.identity_epoch,
                        ownership_clock_generation=plan.clock_generation,
                        expires_at=timestamp(instant(now) + timedelta(seconds=30)),
                    )
                )
                record = OperationRecord(
                    admission=admission,
                    summary=summary,
                    lease=lease,
                    fence=number,
                    dispatch_attempt_id=attempt_ids[-1],
                    event_count=event_count,
                    recovery_reason=None,
                    observed_identity_epoch=plan.identity_epoch,
                    observed_clock_generation=plan.clock_generation,
                )
                connection.execute(
                    f"INSERT INTO operations({OPERATION_COLUMNS}) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    operation_row(record),
                )
                for candidate, attempt_id in enumerate(attempt_ids, 1):
                    current = candidate == number
                    attempt = AttemptView(
                        attempt_id=attempt_id,
                        number=candidate,
                        created_at=now,
                        updated_at=now,
                        status=status if current else "abandoned",
                        provider_run_id=f"fixture-{index}" if current else None,
                        provider_status="complete"
                        if terminal and current
                        else "running"
                        if current
                        else None,
                        provider_exit_code=0 if terminal and current else None,
                        reason_code=None if current else "owner_changed",
                    )
                    connection.execute(
                        "INSERT INTO operation_attempts VALUES(?,?,?,?,?)",
                        (
                            attempt_id,
                            identifier,
                            candidate,
                            attempt.status,
                            canonical(attempt.model_dump(mode="json")).decode("ascii"),
                        ),
                    )
                for sequence in range(1, event_count + 1):
                    event_status = (
                        "admitted"
                        if sequence == 1
                        else "submitted"
                        if sequence == 2
                        else status
                        if sequence == event_count
                        else "running"
                    )
                    event = OperationEvent(
                        sequence=sequence,
                        revision=1 if sequence == 1 else number + sequence - 1,
                        fence=1 if sequence == 1 else number,
                        attempt_id=attempt_ids[0] if sequence == 1 else attempt_ids[-1],
                        observed_at=now,
                        identity_epoch=plan.identity_epoch,
                        clock_generation=plan.clock_generation,
                        status=event_status,
                        execution_status="not_started" if sequence == 1 else event_status,
                        delivery_status=delivery
                        if terminal and sequence == event_count
                        else "pending",
                        reason_code=None,
                    )
                    connection.execute(
                        "INSERT INTO operation_events VALUES(?,?,?,?)",
                        (
                            identifier,
                            sequence,
                            event.attempt_id,
                            canonical(event.model_dump(mode="json")).decode("ascii"),
                        ),
                    )
                if terminal:
                    outcome = OperationOutcome(
                        recorded_at=now,
                        execution_status="succeeded",
                        delivery_status="complete",
                        provider_exit_code=0,
                        reason_code=None,
                    )
                    connection.execute(
                        "INSERT INTO operation_outcomes VALUES(?,?)",
                        (identifier, canonical(outcome.model_dump(mode="json")).decode("ascii")),
                    )
                counts["operations"] += 1
                counts["attempts"] += number
                counts["events"] += event_count
                counts["outcomes"] += terminal
            connection.execute("COMMIT")
        finally:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
        store.verify()
    return counts
