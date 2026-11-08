"""Read-only reads of dataset versions on one owned shared HTTP session (ADR-0033).

``versions`` reads one page (one GET); ``version`` reads one version and its split counts (two GETs,
not an atomic snapshot: if the provider moved between them the two answers disagree and the answer
is ``invalid_response``). Nothing here writes, approves or records an operation. The 404 of the
version's detail route is the one status with a meaning of its own (the caller says which: the tag
was never there, or a bound version is gone); the 404 of the split route is a read that failed.
"""

from __future__ import annotations

from types import TracebackType
from typing import Final, Literal, Self

from yorunge.adapters.http_session import HttpSession
from yorunge.application.context_discovery import DiscoveryClock, remaining
from yorunge.application.dataset_version_codec import (
    observation,
    version_detail,
    version_page,
    version_splits,
)
from yorunge.application.http_transport import (
    HttpCredential,
    HttpRequest,
    HttpStatusFailure,
    HttpTransport,
)
from yorunge.application.response_json import JSON_LIMIT
from yorunge.domain.capabilities import timestamp
from yorunge.domain.credentials import ResolvedCredential
from yorunge.domain.dataset_upload import provider_uuid
from yorunge.domain.dataset_version import (
    MAX_PAGE,
    MIN_PAGE,
    DatasetVersionList,
    DatasetVersionObservation,
    validate_version_tag,
)
from yorunge.domain.errors import YorungeError

Absent = Literal["dataset_version_not_found", "dataset_version_missing"]
ABSENT_CODES: Final = ("dataset_version_not_found", "dataset_version_missing")
VERSION_SECONDS: Final = (
    30.0  # the budget a caller gives one read: ``monotonic() + VERSION_SECONDS``
)


class VersionReader:
    def __init__(
        self,
        credential: ResolvedCredential,
        clock: DiscoveryClock,
        *,
        session: HttpSession | None = None,
    ) -> None:
        if credential.reference.service_id != "evren-platform":
            raise YorungeError("invalid_service_target")
        self.credential, self.clock = credential, clock
        self.session = session if session is not None else HttpSession()

    def __enter__(self) -> Self:
        self.session.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.__exit__(exc_type, exc, traceback)

    def versions(self, dataset_id: str, page: int, *, deadline: float) -> DatasetVersionList:
        """One page of the dataset's versions: one GET, the page that was asked for."""
        self._arguments(dataset_id, page)
        self.session.preflight()
        data = self._get(f"datasets/{dataset_id}/versions", deadline, query=(("page", str(page)),))
        assert data is not None
        remaining(deadline, self.clock)
        return version_page(
            data,
            dataset_id=dataset_id,
            page=page,
            secret=self.credential.secret,
            observed_at=timestamp(self.clock.now()),
        )

    def version(
        self,
        dataset_id: str,
        version_tag: str,
        *,
        deadline: float,
        absent: Absent,
    ) -> DatasetVersionObservation:
        """One version: its detail, then its split counts (two GETs), observed once they agree.

        ``absent`` is the code a 404 of the detail route means to the caller, and it has no default:
        a version that was never there (``dataset_version_not_found``, exit 2) and a bound version
        that is gone (``dataset_version_missing``, exit 7) are different answers.
        """
        if absent not in ABSENT_CODES:
            raise YorungeError("invalid_request")
        self._arguments(dataset_id, MIN_PAGE)
        try:
            validate_version_tag(version_tag)
        except ValueError:
            raise YorungeError("invalid_request") from None
        self.session.preflight()
        secret = self.credential.secret
        base = f"datasets/{dataset_id}/versions/{version_tag}"
        found = self._get(base, deadline, absent=absent)
        assert found is not None
        detail = version_detail(
            found, dataset_id=dataset_id, version_tag=version_tag, secret=secret
        )
        splits = self._get(f"{base}/splits", deadline)
        assert splits is not None
        remaining(deadline, self.clock)
        observed_at = timestamp(self.clock.now())
        return observation(detail, version_splits(splits, secret=secret), observed_at=observed_at)

    @staticmethod
    def _arguments(dataset_id: object, page: object) -> None:
        if type(dataset_id) is not str or type(page) is not int:
            raise YorungeError("invalid_request")
        try:
            provider_uuid(dataset_id)
        except ValueError:
            raise YorungeError("invalid_request") from None
        if not MIN_PAGE <= page <= MAX_PAGE:
            raise YorungeError("invalid_request")

    def _get(
        self,
        path: str,
        deadline: float,
        *,
        query: tuple[tuple[str, str], ...] = (),
        absent: Absent | None = None,
    ) -> bytes | None:
        remaining(deadline, self.clock)
        return self.session.call(
            lambda transport: self._read(transport, path, query, deadline, absent)
        )

    async def _read(
        self,
        transport: HttpTransport,
        path: str,
        query: tuple[tuple[str, str], ...],
        deadline: float,
        absent: Absent | None,
    ) -> bytes:
        credential = self.credential
        request = HttpRequest(
            credential.target,
            "GET",
            path,
            query=query,
            service_id="evren-platform",
            credential=HttpCredential(
                "X-API-Key",
                credential.secret,
                target=credential.target,
                service_id="evren-platform",
            ),
            read_only=True,
            max_bytes=JSON_LIMIT,
        )
        data = bytearray()
        try:
            async with transport.open(request, deadline=deadline) as response:
                async for part in response.chunks():
                    if len(data) + len(part) > JSON_LIMIT:
                        raise YorungeError("invalid_response")
                    data.extend(part)
        except HttpStatusFailure as error:
            if error.status_code == 404 and absent is not None:
                raise YorungeError(absent) from None
            raise
        return bytes(data)
