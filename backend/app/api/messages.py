"""FastAPI routes for interview chat and streaming chat."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Body
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from app.api.utils import _pop_ready_segments
from app.db import database
from app.models.schemas import InterviewStatus, MessageType
from app.services.ai_service import get_ai_service
from app.services.interview_orchestrator import get_interview_orchestrator
from app.services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def _create_sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/interviews/{interview_id}/chat")
async def chat(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        user_message = payload.get("content")
        parent_id = payload.get("parent_id")
        branch_id = payload.get("branch_id", "main")

        if not user_message:
            return _error("Message content cannot be empty", status_code=400)

        interview = await run_in_threadpool(database.get_interview, interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        if interview["status"] != InterviewStatus.IN_PROGRESS:
            return _error("Interview is not in progress", status_code=400)

        user_message_id = await run_in_threadpool(
            database.create_message,
            interview_id,
            MessageType.USER,
            user_message,
            parent_id=parent_id,
            branch_id=branch_id,
        )
        messages = await run_in_threadpool(database.get_message_path, interview_id, user_message_id)

        ai_service = get_ai_service()
        trace_id = get_interview_orchestrator().new_trace_id()
        new_stage = await run_in_threadpool(
            ai_service.determine_current_stage,
            interview,
            messages,
            interview.get("duration_minutes", 30),
        )
        current_stage = interview.get("current_stage", prompt_service.get_first_stage())
        if new_stage != current_stage:
            await run_in_threadpool(database.update_interview_stage, interview_id, new_stage)

        ai_response = await run_in_threadpool(
            ai_service.continue_interview,
            interview,
            messages,
            current_stage=new_stage,
            previous_stage=current_stage,
            trace_id=trace_id,
        )
        ai_message_id = await run_in_threadpool(
            database.create_message,
            interview_id,
            MessageType.ASSISTANT,
            ai_response,
            parent_id=user_message_id,
            branch_id=branch_id,
        )
        await run_in_threadpool(database.update_interview_current_message, interview_id, ai_message_id)

        progress_info = await run_in_threadpool(
            ai_service.get_interview_progress,
            messages,
            new_stage,
            interview.get("duration_minutes", 30),
            interview_config=interview,
        )
        return {
            "trace_id": trace_id,
            "role": MessageType.ASSISTANT,
            "content": ai_response,
            "current_stage": new_stage,
            "progress": progress_info,
        }
    except Exception as exc:
        logger.error("Failed to continue interview: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/chat/stream")
async def chat_stream(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        user_message = payload.get("content")
        parent_id = payload.get("parent_id")
        branch_id = payload.get("branch_id", "main")
        enable_tts = payload.get("enable_tts", True)

        if not user_message:
            return _error("Message content cannot be empty", status_code=400)

        interview = await run_in_threadpool(database.get_interview, interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        if interview["status"] != InterviewStatus.IN_PROGRESS:
            return _error("Interview is not in progress", status_code=400)

        user_message_id = await run_in_threadpool(
            database.create_message,
            interview_id,
            MessageType.USER,
            user_message,
            parent_id=parent_id,
            branch_id=branch_id,
        )
        messages = await run_in_threadpool(database.get_message_path, interview_id, user_message_id)
        assistant_message_id = await run_in_threadpool(
            database.create_message,
            interview_id,
            MessageType.ASSISTANT,
            "",
            parent_id=user_message_id,
            branch_id=branch_id,
        )
        await run_in_threadpool(database.update_interview_current_message, interview_id, assistant_message_id)

        ai_service = get_ai_service()
        trace_id = get_interview_orchestrator().new_trace_id()
        new_stage = await run_in_threadpool(
            ai_service.determine_current_stage,
            interview,
            messages,
            interview.get("duration_minutes", 30),
        )
        current_stage = interview.get("current_stage", prompt_service.get_first_stage())
        if new_stage != current_stage:
            await run_in_threadpool(database.update_interview_stage, interview_id, new_stage)

        stream = ai_service.continue_interview_stream(
            interview,
            messages,
            current_stage=new_stage,
            previous_stage=current_stage,
            trace_id=trace_id,
        )

        async def generate() -> AsyncIterator[str]:
            full_response = ""
            sentence_buffer = ""
            segment_index = 0
            tts_service = None
            if enable_tts:
                from app.services.tts_service import get_tts_service

                tts_service = get_tts_service()

            async def emit_segment_events(segment_text: str) -> AsyncIterator[str]:
                nonlocal segment_index
                clean_text = (segment_text or "").strip()
                if not clean_text:
                    return

                current_segment_index = segment_index
                segment_index += 1

                if enable_tts and tts_service:
                    try:
                        audio_base64 = await tts_service.text_to_speech_async(clean_text)
                        yield _create_sse_event(
                            {
                                "type": "audio_ready",
                                "message_id": assistant_message_id,
                                "segment_index": current_segment_index,
                                "content": clean_text,
                                "audio": audio_base64,
                            }
                        )
                    except Exception as exc:
                        logger.exception("TTS segment generation failed")
                        yield _create_sse_event(
                            {
                                "type": "audio_ready",
                                "message_id": assistant_message_id,
                                "segment_index": current_segment_index,
                                "content": clean_text,
                                "audio": None,
                                "error": str(exc),
                            }
                        )

            try:
                async for chunk in iterate_in_threadpool(stream):
                    full_response += chunk
                    sentence_buffer += chunk
                    yield _create_sse_event(
                        {"type": "text_chunk", "message_id": assistant_message_id, "content": chunk}
                    )
                    ready_segments, sentence_buffer = _pop_ready_segments(sentence_buffer)
                    for segment_text in ready_segments:
                        async for event in emit_segment_events(segment_text):
                            yield event

                if sentence_buffer.strip():
                    async for event in emit_segment_events(sentence_buffer.strip()):
                        yield event
                    await asyncio.sleep(0.2)

                await run_in_threadpool(database.update_message_content, assistant_message_id, full_response)
                progress_info = await run_in_threadpool(
                    ai_service.get_interview_progress,
                    messages,
                    new_stage,
                    interview.get("duration_minutes", 30),
                    interview_config=interview,
                )
                yield _create_sse_event(
                    {
                        "type": "done",
                        "done": True,
                        "trace_id": trace_id,
                        "message_id": assistant_message_id,
                        "current_stage": new_stage,
                        "progress": progress_info,
                    }
                )
            except Exception:
                logger.exception("Streaming interview continuation failed")
                yield _create_sse_event({"error": "Internal server error", "done": True})

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except Exception as exc:
        logger.error("Failed to start streaming interview: %s", exc)
        return _error("Internal server error")
