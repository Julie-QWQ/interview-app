"""FastAPI routes for digital human session bootstrap."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.utils import _resolve_interviewer_avatar_runtime_config
from app.db import database
from app.services.xunfei_digital_human_service import get_xunfei_digital_human_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/interviews/{interview_id}/avatar-session")
def create_avatar_session(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)

        digital_human_service = get_xunfei_digital_human_service()
        if not digital_human_service.health_check():
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "讯飞数字人服务未启用或配置不完整"},
            )

        avatar_runtime_config = _resolve_interviewer_avatar_runtime_config(interview_id)
        result = digital_human_service.initialize_session(
            avatar_id=avatar_runtime_config.get("avatar_id") or None,
            vcn=avatar_runtime_config.get("vcn") or None,
            interview_id=interview_id,
        )
        if result["success"]:
            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "session_id": result["session_id"],
                    "avatar_id": result["avatar_id"],
                    "config": result["config"],
                    "provider": "xunfei",
                },
            )
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": result.get("error", "Unknown error")},
        )
    except Exception as exc:
        logger.error("Failed to create avatar session: %s", exc)
        return _error("Internal server error")
