"""FastAPI routes for runtime voice configuration."""

from __future__ import annotations

import logging
from copy import deepcopy

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.api.utils import _normalize_voice_config_payload
from config.settings import DEFAULT_VOICE_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def _get_settings(request: Request):
    return request.app.state.settings


@router.get("/voice/config")
def get_voice_config(request: Request):
    try:
        settings = _get_settings(request)
        return settings.voice_config
    except Exception as exc:
        logger.error("Failed to get voice config: %s", exc)
        return _error(str(exc))


@router.post("/voice/config")
def update_voice_config(request: Request, payload: dict = Body(default_factory=dict)):
    try:
        settings = _get_settings(request)
        config = _normalize_voice_config_payload(payload)
        settings.update_section("voice", config)
        request.app.state.settings = settings
        return {"message": "Voice config updated", "config": settings.voice_config}
    except ValueError as exc:
        logger.warning("Voice config validation failed: %s", exc)
        return _error(str(exc), status_code=400)
    except Exception as exc:
        logger.error("Failed to update voice config: %s", exc)
        return _error("Internal server error")


@router.post("/voice/config/reset")
def reset_voice_config(request: Request):
    try:
        settings = _get_settings(request)
        settings.update_section("voice", deepcopy(DEFAULT_VOICE_CONFIG))
        request.app.state.settings = settings
        return {"message": "Voice config reset", "config": settings.voice_config}
    except Exception as exc:
        logger.error("Failed to reset voice config: %s", exc)
        return _error(str(exc))
