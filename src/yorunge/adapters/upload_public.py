"""Local public history/intent reads; no config, secret, filesystem source or HTTP."""

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from yorunge.adapters.execution_store import decode_cursor, encode_cursor
from yorunge.adapters.operation_store import read_snapshot
from yorunge.adapters.state import Store, open_existing_store
from yorunge.adapters.upload_projection import review, summary
from yorunge.adapters.upload_repository import StateUploads
from yorunge.adapters.upload_store import read_any_view
from yorunge.adapters.upload_sync import require_upload_sync_context
from yorunge.domain.capabilities import canonical
from yorunge.domain.errors import OperationError, YorungeError
from yorunge.domain.models import Model, Result
from yorunge.domain.state import canonical_uuid
from yorunge.domain.upload_public import (
    DatasetUploadsPage,
    DatasetUploadSummary,
    UploadIntentReview,
)

MAX_PAGE_RESULT_BYTES = 1024 * 1024
T = TypeVar("T", bound=Model)


def validate_local(state_dir: Path | None, *identities: str | None) -> None:
    require_upload_sync_context()
    valid = state_dir is None or isinstance(state_dir, Path)
    for identity in identities:
        if identity is not None:
            try:
                canonical_uuid(identity)
            except (ValueError, TypeError, AttributeError):
                valid = False
    if not valid:
        raise YorungeError("invalid_request")


def _safe_local(
    state_dir: Path | None,
    operation_id: str | None,
    action: Callable[[Store], T],
) -> T:
    failure = None
    try:
        with open_existing_store(state_dir) as store:
            return action(store)
    except YorungeError as error:
        failure = OperationError(
            error.code,
            error.operation_id if isinstance(error, OperationError) else operation_id,
            reason_code=error.reason_code if isinstance(error, OperationError) else None,
        )
    except KeyboardInterrupt:
        failure = OperationError("request_cancelled", operation_id)
    failure.__cause__ = failure.__context__ = None
    raise failure


def show_upload(
    state_dir: Path | None, *, plan_id: str | None = None, operation_id: str | None = None
) -> Result[DatasetUploadSummary]:
    validate_local(state_dir, plan_id, operation_id)
    if (plan_id is None) == (operation_id is None):
        raise YorungeError("invalid_request")

    def read(store: Store) -> DatasetUploadSummary:
        repository = StateUploads(store)
        with repository.phase(operation_id):
            return summary(repository.show(plan_id=plan_id, operation_id=operation_id))

    return Result[DatasetUploadSummary](data=_safe_local(state_dir, operation_id, read))


def review_upload(plan_id: str, state_dir: Path | None) -> Result[UploadIntentReview]:
    validate_local(state_dir, plan_id)
    if plan_id is None:
        raise YorungeError("invalid_request")

    def read(store: Store) -> UploadIntentReview:
        repository = StateUploads(store)
        with repository.phase():
            return review(repository.show(plan_id=plan_id))

    return Result[UploadIntentReview](data=_safe_local(state_dir, None, read))


def revoke_upload(plan_id: str, state_dir: Path | None) -> Result[DatasetUploadSummary]:
    validate_local(state_dir, plan_id)
    if plan_id is None:
        raise YorungeError("invalid_request")

    def revoke(store: Store) -> DatasetUploadSummary:
        repository = StateUploads(store)
        with repository.phase():
            plan = repository.show(plan_id=plan_id).plan
            return summary(repository.revoke(plan_id, plan.digest))

    return Result[DatasetUploadSummary](data=_safe_local(state_dir, None, revoke))


def _page(
    store: Store, plan_id: str | None, limit: int, after: tuple[str, str]
) -> DatasetUploadsPage:
    repository = StateUploads(store)
    with repository.phase(), read_snapshot(store.connection):
        rows = store.connection.execute(
            "SELECT prepared_at,plan_id FROM upload_plans WHERE "
            "(prepared_at,plan_id)>(?,?) AND (? IS NULL OR plan_id=?) "
            "ORDER BY prepared_at,plan_id LIMIT ?",
            (*after, plan_id, plan_id, limit + 1),
        ).fetchall()
        included: list[DatasetUploadSummary] = []
        cursor = None
        for index, row in enumerate(rows[:limit]):
            item = summary(read_any_view(store.connection, row[1]))
            pending_cursor = encode_cursor(*row) if index + 1 < len(rows) else None
            candidate = DatasetUploadsPage(
                schema_version=1, uploads=(*included, item), next_cursor=pending_cursor
            )
            encoded = canonical(Result[DatasetUploadsPage](data=candidate).model_dump(mode="json"))
            if len(encoded) > MAX_PAGE_RESULT_BYTES:
                if not included:
                    raise YorungeError("state_invalid")
                break
            included.append(item)
            cursor = pending_cursor
        return DatasetUploadsPage(schema_version=1, uploads=tuple(included), next_cursor=cursor)


def _cursor(value: str | None) -> tuple[str, str]:
    if value is None:
        return "", ""
    decoded = None
    try:
        decoded = decode_cursor(value)
    except YorungeError:
        pass
    if decoded is None:
        # The shared decoder suppresses its traceback, but its Unicode/base64
        # exception chain may retain input. Do not export that private chain.
        raise YorungeError("invalid_request")
    return decoded


def list_uploads(
    state_dir: Path | None,
    *,
    plan_id: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> Result[DatasetUploadsPage]:
    validate_local(state_dir, plan_id)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise YorungeError("invalid_request")
    after = _cursor(cursor)
    return Result[DatasetUploadsPage](
        data=_safe_local(state_dir, None, lambda store: _page(store, plan_id, limit, after))
    )
