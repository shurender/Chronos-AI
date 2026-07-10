"""
Structured logging setup for the backend.

Replaces ad-hoc `print()` calls with standard `logging`, and stamps every log
record with a request_id (set per-request by RequestIdMiddleware, "-" outside
a request context, e.g. at import time or in scripts/tests).
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_LOG_FORMAT = "%(asctime)s %(levelname)s [request_id=%(request_id)s] %(name)s: %(message)s"


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once. Safe to call more than once (idempotent)."""
    root = logging.getLogger()
    if any(isinstance(f, _RequestIdFilter) for h in root.handlers for f in h.filters):
        return  # already configured

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.addFilter(_RequestIdFilter())

    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class RequestIdMiddleware:
    """Minimal ASGI middleware: assigns a request_id (from X-Request-ID header if
    present, else a fresh uuid4) to request_id_var for the duration of the request,
    so every log line emitted while handling it carries the same id."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id")
        run_id = incoming.decode("utf-8") if incoming else str(uuid.uuid4())

        token = request_id_var.set(run_id)
        try:
            await self.app(scope, receive, send)
        finally:
            request_id_var.reset(token)
