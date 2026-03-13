"""FastAPI routes used by frontend test pages."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.services.ai_service import get_ai_service
from app.services.xunfei_digital_human_service import get_xunfei_digital_human_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/test/avatar-session")
def create_test_avatar_session():
    try:
        digital_human_service = get_xunfei_digital_human_service()
        if not digital_human_service.health_check():
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "讯飞数字人服务未启用或配置不完整"},
            )
        result = digital_human_service.initialize_session(interview_id=999999)
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
        logger.error("Failed to create test avatar session: %s", exc)
        return _error("Internal server error")


@router.post("/test/chat")
def test_chat(payload: dict = Body(default_factory=dict)):
    try:
        content = str(payload.get("content", "")).strip()
        raw_history = payload.get("history") or []
        if not content:
            return _error("消息内容不能为空", status_code=400)

        history_messages = []
        for item in raw_history[-12:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            history_content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not history_content:
                continue
            history_messages.append({"role": role, "content": history_content})

        ai_service = get_ai_service()
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业、自然的 AI 面试官。"
                    "请根据已有的对话上下文连续面试，保持话题和追问的连贯性。"
                    "不要把它当成单轮问答，也不要重复已经说过的内容。"
                    "回复要简洁、专业、像真实面试官，控制在 80 字以内。"
                ),
            },
            *history_messages,
            {"role": "user", "content": content},
        ]
        reply = ai_service.chat_completion(messages)

        from app.services.tts_service import get_tts_service

        audio_base64 = get_tts_service().text_to_speech(reply)
        return {"success": True, "reply": reply, "audio": audio_base64}
    except Exception as exc:
        logger.error("Test chat failed: %s", exc)
        return _error("Internal server error")


@router.get("/test/health")
def health_check():
    try:
        from app.services.asr_service import get_asr_service
        from app.services.tts_service import get_tts_service

        services = {}
        try:
            get_ai_service()
            services["ai"] = "ok"
        except Exception:
            services["ai"] = "error"
        try:
            get_asr_service()
            services["asr"] = "ok"
        except Exception:
            services["asr"] = "error"
        try:
            get_tts_service()
            services["tts"] = "ok"
        except Exception:
            services["tts"] = "error"
        try:
            dh_service = get_xunfei_digital_human_service()
            services["digital_human"] = "ok" if dh_service.health_check() else "disabled"
        except Exception:
            services["digital_human"] = "error"

        all_ok = all(status in {"ok", "disabled"} for status in services.values())
        return {"status": "healthy" if all_ok else "degraded", "services": services}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(exc)})
