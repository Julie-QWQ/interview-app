"""FastAPI routes for tool orchestration endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.db import database
from app.services.smart_reply_service import get_smart_reply_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/tools/smart-reply")
def smart_reply_provider(payload: dict = Body(default_factory=dict)):
    try:
        response_payload = get_smart_reply_service().execute(payload)
        status_code = 200 if response_payload.get("status") == "success" else 400
        return JSONResponse(status_code=status_code, content=response_payload)
    except Exception as exc:
        logger.error("Smart reply provider failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "summary": "",
                "structured_payload": {},
                "cache_ttl_seconds": 0,
                "errors": [str(exc)],
            },
        )


@router.get("/interviews/{interview_id}/tool-contexts")
def get_tool_contexts(interview_id: int):
    try:
        contexts = database.list_interview_tool_contexts(interview_id)
        return {"tool_contexts": contexts}
    except Exception as exc:
        logger.error("Failed to get tool contexts for interview %s: %s", interview_id, exc)
        return _error(f"获取工具上下文失败: {str(exc)}")


@router.get("/interviews/{interview_id}/tool-invocations")
def get_tool_invocations(interview_id: int, limit: int = Query(default=50)):
    try:
        invocations = database.get_tool_invocations(interview_id, limit=limit)
        return {"invocations": invocations}
    except Exception as exc:
        logger.error("Failed to get tool invocations for interview %s: %s", interview_id, exc)
        return _error(f"获取工具调用记录失败: {str(exc)}")
