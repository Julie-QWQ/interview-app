"""Application factories for the interview service."""

from __future__ import annotations

from typing import Any


def create_app(*args: Any, **kwargs: Any):
    from .fastapi_app import create_app as _create_app

    return _create_app(*args, **kwargs)

__all__ = ["create_app"]
