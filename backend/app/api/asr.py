"""FastAPI routes for speech recognition."""

from __future__ import annotations

import logging
import time
from datetime import datetime

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from werkzeug.utils import secure_filename

from app.services.asr_service import get_asr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

MAX_AUDIO_SIZE = 25 * 1024 * 1024


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/asr/transcribe")
async def transcribe_audio(
    audio: UploadFile | None = File(default=None),
    segment_id: str = Form(default=""),
    client_started_at: str = Form(default=""),
    client_ended_at: str = Form(default=""),
    source: str = Form(default="manual_voice"),
):
    request_started_at = time.time()
    logger.info(
        "ASR transcribe request: segment_id=%s source=%s audio=%s filename=%s",
        segment_id or "-",
        source,
        "present" if audio else "missing",
        audio.filename if audio else "N/A"
    )

    try:
        asr_service = get_asr_service()
        if not asr_service:
            logger.error("ASR service not initialized")
            return _error("ASR service unavailable", status_code=503)

        logger.info(f"ASR service type: {type(asr_service).__name__}")

        if audio is None:
            logger.error("No audio file in request")
            return _error("Audio file not found", status_code=400)
        if not audio.filename:
            logger.error("Audio file has no filename")
            return _error("No audio file selected", status_code=400)

        audio_data = await audio.read()
        audio_size = len(audio_data)
        logger.info("Audio data received: size=%d bytes (%.2f MB)", audio_size, audio_size / (1024 * 1024))

        if audio_size == 0:
            logger.error("Audio file is empty")
            return _error("Audio file is empty", status_code=400)
        if audio_size > MAX_AUDIO_SIZE:
            logger.error("Audio file too large: %d bytes > %d bytes", audio_size, MAX_AUDIO_SIZE)
            return _error(
                f"Audio file must not exceed {MAX_AUDIO_SIZE // (1024 * 1024)}MB",
                status_code=400,
            )

        filename = secure_filename(audio.filename or "")
        audio_format = "wav"
        if "." in filename:
            audio_format = filename.rsplit(".", 1)[-1].lower()

        logger.info("Starting ASR transcription: format=%s service=%s", audio_format, type(asr_service).__name__)

        text = await run_in_threadpool(asr_service.transcribe, audio_data, audio_format)
        trimmed_text = (text or "").strip()
        text_length = len(trimmed_text)

        logger.info("ASR transcription completed: text_length=%d preview=%s",
                   text_length, trimmed_text[:50] if trimmed_text else "(empty)")

        client_duration_ms = None
        if client_started_at and client_ended_at:
            try:
                started = datetime.fromisoformat(client_started_at.replace("Z", "+00:00"))
                ended = datetime.fromisoformat(client_ended_at.replace("Z", "+00:00"))
                client_duration_ms = max(int((ended - started).total_seconds() * 1000), 0)
            except ValueError:
                logger.warning("Invalid client timestamps for ASR segment %s", segment_id or "-")

        should_auto_send = bool(trimmed_text and len(trimmed_text) >= 8)
        if trimmed_text in {"啊", "哦", "嗯", "额", "唉", "呃"}:
            should_auto_send = False

        elapsed_ms = int((time.time() - request_started_at) * 1000)
        logger.info(
            "ASR result: segment_id=%s source=%s text_length=%s duration_ms=%s elapsed_ms=%s should_auto_send=%s",
            segment_id or "-",
            source,
            text_length,
            client_duration_ms,
            elapsed_ms,
            should_auto_send
        )
        return {
            "text": trimmed_text,
            "text_length": text_length,
            "duration_ms": client_duration_ms,
            "empty_audio": False,
            "should_auto_send": should_auto_send,
            "segment_id": segment_id or None,
            "source": source,
        }
    except Exception as exc:
        logger.error("ASR transcription failed: %s", exc, exc_info=True)
        return _error("ASR transcription failed")


@router.get("/asr/status")
def get_asr_status():
    try:
        asr_service = get_asr_service()
        if asr_service:
            return {
                "available": True,
                "provider": type(asr_service).__name__,
                "message": "ASR service available",
            }
        return JSONResponse(
            status_code=503,
            content={"available": False, "provider": None, "message": "ASR service unavailable"},
        )
    except Exception as exc:
        logger.error("Failed to get ASR status: %s", exc)
        return _error("Internal server error")
