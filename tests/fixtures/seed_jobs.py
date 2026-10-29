"""New disposable jobs fixtures, never an existing user store or product command."""

from pathlib import Path

from tests.fixtures.seed_operation_state import seed as seed_operations
from yorunge.adapters.state import open_store, validate_contents
from yorunge.domain.capabilities import canonical


def seed(root: Path, *, dense: bool) -> str:
    if root.exists() or root.is_symlink() or type(dense) is not bool:
        raise ValueError("new disposable root and bool layout required")
    seed_operations(root, layout="terminal" if dense else "normal", maximum=dense)
    with open_store(root, timeout=120) as store:
        connection = store.connection
        identifier, plan_id = connection.execute(
            "SELECT operation_id,plan_id FROM operations ORDER BY operation_id LIMIT 1"
        ).fetchone()
        connection.execute("BEGIN IMMEDIATE")
        if not dense:
            # This fixture was just created above. Shape a one-job store outside
            # timing; no retention/forget or repair behavior is added to product.
            for table in ("operation_events", "operation_outcomes", "operation_attempts"):
                connection.execute(f"DELETE FROM {table} WHERE operation_id<>?", (identifier,))
            connection.execute("DELETE FROM operations WHERE operation_id<>?", (identifier,))
            connection.execute("DELETE FROM execution_approvals WHERE plan_id<>?", (plan_id,))
            connection.execute("DELETE FROM execution_plans WHERE plan_id<>?", (plan_id,))
            connection.execute(
                "DELETE FROM capability_cache WHERE cache_key<>"
                "(SELECT min(cache_key) FROM capability_cache)"
            )
        else:
            # Only the current submitted candidate can legally carry provider
            # metadata. Older abandoned candidates and closed outcome have no
            # arbitrary padding field; report their actual bounded byte volume.
            rows = connection.execute(
                "SELECT attempt_id,payload FROM operation_attempts WHERE status='succeeded'"
            ).fetchall()
            import json

            for attempt_id, payload in rows:
                raw = json.loads(payload)
                raw["provider_run_id"] = "fixture-" + str(attempt_id) + "x" * 212
                raw["provider_status"] = "fixture-" + "x" * 120
                connection.execute(
                    "UPDATE operation_attempts SET payload=? WHERE attempt_id=?",
                    (canonical(raw).decode(), attempt_id),
                )
        connection.execute("COMMIT")
        if not dense:
            connection.execute("VACUUM")
        validate_contents(connection)
    return identifier
