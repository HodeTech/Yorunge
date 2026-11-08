"""The signed GET's private typed boundary: the target, the closed request, the view of an answer.

ADR-0032 §2 (a partial change of ADR-0025). The target is an address the provider signed: its raw
bytes are kept exactly, it carries no credential and no expiry is demanded of it. The request adds
no header of its own beyond the two the resume protocol names; the transport adds ``Host`` and
``Accept-Encoding: identity``. What the engine sees of an answer is the typed
:class:`~yorunge.domain.download_response.DownloadResponse` and the action it calls for, never a
raw header.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import NoReturn, Protocol
from urllib.parse import urlsplit

from yorunge.application.http_transport import HttpTransport
from yorunge.application.response_json import literal_secret_match
from yorunge.application.storage import StorageTarget, _decoded, _path
from yorunge.domain.credentials import SecretValue
from yorunge.domain.download import MAX_DOWNLOAD_BYTES
from yorunge.domain.download_response import (
    Disposition,
    DownloadResponse,
    ResumeAsk,
    request_headers,
)
from yorunge.domain.errors import YorungeError


class DownloadTarget:
    """A signed address, never re-encoded, logged, serialized or sent with a credential."""

    __slots__ = ("_url", "origin", "prefix")
    _url: str
    origin: str
    prefix: str

    def __init__(self, url: str, *, origin: str, prefix: str) -> None:
        if type(url) is not str or type(origin) is not str or type(prefix) is not str:
            raise YorungeError("invalid_service_target")
        # HTTPS on 443 to the one known origin, no userinfo or fragment, no dot segment or double
        # encoding, at most 16 KiB, below the consumer's path prefix (an answer cannot widen it);
        # the query's raw bytes stay as they were signed.
        StorageTarget._validate_url(url, origin, prefix)
        object.__setattr__(self, "_url", url)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "prefix", prefix)

    @property
    def wire_url(self) -> str:
        return self._url

    def check_secret(self, secret: SecretValue) -> None:
        """No part of the address may be the selected key (it would travel in the clear)."""
        parsed = urlsplit(self._url)
        values = [self._url, parsed.hostname or "", *_path(parsed.path)]
        for pair in parsed.query.split("&"):
            values.extend(_decoded(part) for part in pair.split("=", 1))
        if any(literal_secret_match(value, secret.reveal()) for value in values):
            raise YorungeError("invalid_service_target")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("download targets are immutable")

    def __repr__(self) -> str:
        return "<DownloadTarget redacted>"

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        raise TypeError("download targets cannot be serialized")


@dataclass(frozen=True, slots=True, repr=False)
class DownloadRequest:
    """One GET of a signed address: whole, or the rest of a prefix already held.

    ``selected_secret`` is the key in use; it is only compared with, never sent. ``max_bytes`` is
    the most a body may deliver (the contract's limit unless a caller asks for less).
    """

    target: DownloadTarget = field(repr=False)
    selected_secret: SecretValue = field(repr=False)
    ask: ResumeAsk | None = None
    max_bytes: int = MAX_DOWNLOAD_BYTES

    def __post_init__(self) -> None:
        if (
            type(self.target) is not DownloadTarget
            or type(self.selected_secret) is not SecretValue
            or (self.ask is not None and type(self.ask) is not ResumeAsk)
            or type(self.max_bytes) is not int
            or not 1 <= self.max_bytes <= MAX_DOWNLOAD_BYTES
        ):
            raise YorungeError("invalid_request")
        self.target.check_secret(self.selected_secret)
        if any(
            literal_secret_match(value, self.selected_secret.reveal())
            for name, value in self.public_headers()
            if name != "Accept-Encoding"
        ):
            raise YorungeError("invalid_request")

    def public_headers(self) -> tuple[tuple[str, str], ...]:
        """The closed header set: ``Range`` and ``If-Range`` of a resume, and identity encoding."""
        return request_headers(self.ask) + (("Accept-Encoding", "identity"),)

    def wire_headers(self) -> tuple[tuple[str, str], ...]:
        """Exactly the public headers: a signed address needs no credential and gets none."""
        return self.public_headers()

    def __repr__(self) -> str:
        return "<DownloadRequest redacted>"


class DownloadView(Protocol):
    """An accepted answer: what it says, what it calls for, and its body as it arrives."""

    @property
    def response(self) -> DownloadResponse: ...

    @property
    def disposition(self) -> Disposition: ...

    @property
    def received(self) -> int: ...

    def chunks(self) -> AsyncIterator[bytes]:
        """The body, in chunks. A short, over-long or cut body raises its closed code at the end
        (or where it breaks); a 416 has no body to read."""
        ...


class DownloadTransport(HttpTransport, Protocol):
    def open_download(
        self, request: DownloadRequest, *, deadline: float
    ) -> AbstractAsyncContextManager[DownloadView]: ...
