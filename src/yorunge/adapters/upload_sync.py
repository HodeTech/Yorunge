"""Lightweight sync entry gate, independent of HTTP/session imports."""

import asyncio

from yorunge.domain.errors import YorungeError


def require_upload_sync_context() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    raise YorungeError("invalid_request")
