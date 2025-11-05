"""Utility helpers for enriching audit events with HTTP context."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request


def build_request_metadata(request: Request) -> Dict[str, Any]:
    """Return a serialisable snapshot of relevant HTTP request metadata."""

    client = request.client.host if request.client else None
    return {
        "method": request.method,
        "path": request.url.path,
        "client": client,
        "user_agent": request.headers.get("user-agent"),
        "host": request.headers.get("host"),
    }


def get_request_identifier(request: Request) -> Optional[str]:
    """Extract a correlation identifier from common header names."""

    for header in ("x-request-id", "x-correlation-id", "x-trace-id"):
        value = request.headers.get(header)
        if value:
            return value
    return None
