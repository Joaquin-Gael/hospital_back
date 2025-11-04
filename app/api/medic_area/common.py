"""Shared utilities and dependencies for the medical area routers."""
from fastapi import Depends
from fastapi.responses import ORJSONResponse
from rich.console import Console

from app.core.auth import JWTBearer, JWTWebSocket


__all__ = [
    "auth",
    "ws_auth",
    "console",
    "default_response_class",
    "auth_dependency",
]


auth = JWTBearer()
ws_auth = JWTWebSocket()
console = Console()

default_response_class = ORJSONResponse


def auth_dependency():
    """Return the shared authentication dependency."""
    return Depends(auth)
