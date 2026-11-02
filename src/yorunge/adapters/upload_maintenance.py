"""Transfer-aware reset consent and recovery without consuming effect slots."""

import hashlib
import sqlite3
from datetime import datetime

from yorunge.adapters.capability_cache import Stamp
from yorunge.adapters.local_files import Deadline
from yorunge.adapters.upload_store import read_record, read_view, write_record
from yorunge.domain.capabilities import canonical, timestamp
from yorunge.domain.dataset_transfer import TERMINAL, TransferControl


def upload_snapshot(connection: sqlite3.Connection, deadline: Deadline) -> dict[str, int | str]:
    digest = hashlib.sha256()
    counts = {
        "upload_plan_count": 0,
        "transfer_operation_count": 0,
        "nonterminal_transfer_count": 0,
        "unknown_transfer_count": 0,
    }
    if connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE name='upload_plans' AND type='table'"
    ).fetchone():
        for row in connection.execute("SELECT plan_id FROM upload_plans ORDER BY plan_id"):
            deadline.remaining()
            view = read_view(connection, row[0])
            record = view.operation
            current = record.model_dump(mode="json") if record else None
            body = {
                "plan": view.plan.model_dump(mode="json"),
                "approval": view.approval.model_dump(mode="json") if view.approval else None,
                "operation": current,
                "journal_digest": hashlib.sha256(
                    canonical(
                        {
                            "intents": [v.model_dump(mode="json") for v in view.intents],
                            "receipts": [v.model_dump(mode="json") for v in view.receipts],
                            "controls": [v.model_dump(mode="json") for v in view.controls],
                            "verification": view.verification.model_dump(mode="json")
                            if view.verification
                            else None,
                        }
                    )
                ).hexdigest(),
            }
            if record and record.lease and current is not None:
                # Renewals alone do not invalidate an otherwise reviewed reset.
                current["lease"].pop("expires_at")
                current["lease"].pop("renewed_at")
            digest.update(canonical(body) + b"\n")
            counts["upload_plan_count"] += 1
            if record:
                counts["transfer_operation_count"] += 1
                counts["nonterminal_transfer_count"] += record.status not in TERMINAL
                counts["unknown_transfer_count"] += record.status == "unknown"
    return {**counts, "transfer_fingerprint": digest.hexdigest()}


def invalidate_uploads(
    connection: sqlite3.Connection, store_id: str, epoch: str, now: datetime, deadline: Deadline
) -> None:
    if not connection.in_transaction:
        raise ValueError("reset transaction required")
    stamp = Stamp(store_id, epoch, 1, now, False)
    for row in connection.execute(
        "SELECT operation_id FROM upload_operations ORDER BY operation_id"
    ).fetchall():
        deadline.remaining()
        record = read_record(connection, row[0])
        if record.status in TERMINAL:
            continue
        armed = record.workflow_latched
        changed = record.model_copy(
            update={
                "updated_at": timestamp(now),
                "revision": record.revision + 1,
                "status": "unknown" if armed else "cancelled",
                "lease": None,
                "reason": "identity_reset",
                "observed_identity_epoch": epoch,
                "observed_clock_generation": 1,
                "clock_anomaly": record.clock_anomaly or timestamp(now) < record.updated_at,
            }
        )
        write_record(connection, changed, record.revision)
        control = TransferControl(
            schema_version=1,
            kind="recovery" if armed else "terminal",
            operation_id=record.operation_id,
            revision=changed.revision,
            observed_at=changed.updated_at,
            identity_epoch=epoch,
            clock_generation=stamp.generation,
            reason="identity_reset",
            verification_digest=None,
        )
        connection.execute(
            "INSERT INTO upload_controls VALUES(?,?,?) ON "
            "CONFLICT(operation_id,kind) DO UPDATE SET payload=excluded.payload",
            (record.operation_id, control.kind, control.encoded().decode("ascii")),
        )
