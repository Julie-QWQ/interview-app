"""FastAPI routes for expression analysis."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.api.utils import _parse_optional_timestamp, _serialize_expression_report, finalize_expression_analysis
from app.db import database
from app.services.expression_analyzer_service import get_expression_analyzer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.get("/expression/config")
def get_expression_config(request: Request):
    try:
        settings = request.app.state.settings
        return settings.expression_analysis_config
    except Exception as exc:
        logger.error("Failed to get expression config: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/expression/audio-segments")
def upload_expression_audio_segment(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        if not database.get_interview(interview_id):
            return _error("Interview not found", status_code=404)
        segment_id = str(payload.get("segment_id") or "").strip()
        if not segment_id:
            return _error("segment_id is required", status_code=400)

        normalized_metrics = get_expression_analyzer_service().normalize_audio_segment(payload)
        database.upsert_expression_feature_segment(
            {
                "interview_id": interview_id,
                "feature_type": "audio",
                "segment_key": segment_id,
                "stage": payload.get("stage"),
                "source": payload.get("source") or "manual_voice",
                "started_at": _parse_optional_timestamp(payload.get("client_started_at") or payload.get("started_at")),
                "ended_at": _parse_optional_timestamp(payload.get("client_ended_at") or payload.get("ended_at")),
                "metrics": normalized_metrics,
            }
        )
        return {"message": "audio segment recorded", "segment_id": segment_id, "feature_type": "audio"}
    except Exception as exc:
        logger.error("Failed to upload audio expression segment: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/expression/video-windows")
def upload_expression_video_window(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        if not database.get_interview(interview_id):
            return _error("Interview not found", status_code=404)
        window_id = str(payload.get("window_id") or "").strip()
        if not window_id:
            return _error("window_id is required", status_code=400)

        normalized_metrics = get_expression_analyzer_service().normalize_video_window(payload)
        database.upsert_expression_feature_segment(
            {
                "interview_id": interview_id,
                "feature_type": "video",
                "segment_key": window_id,
                "stage": payload.get("stage"),
                "source": payload.get("source") or "camera",
                "started_at": _parse_optional_timestamp(payload.get("started_at")),
                "ended_at": _parse_optional_timestamp(payload.get("ended_at")),
                "metrics": normalized_metrics,
            }
        )
        return {"message": "video window recorded", "window_id": window_id, "feature_type": "video"}
    except Exception as exc:
        logger.error("Failed to upload video expression window: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/expression/finalize")
def finalize_expression_report(interview_id: int):
    try:
        if not database.get_interview(interview_id):
            return _error("Interview not found", status_code=404)
        return finalize_expression_analysis(interview_id)
    except Exception as exc:
        logger.error("Failed to finalize expression report: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}/expression-report")
def get_expression_report(interview_id: int):
    try:
        if not database.get_interview(interview_id):
            return _error("Interview not found", status_code=404)
        report = database.get_expression_analysis_report(interview_id)
        if not report:
            return _error("Expression report not found", status_code=404)
        return _serialize_expression_report(report)
    except Exception as exc:
        logger.error("Failed to get expression report: %s", exc)
        return _error("Internal server error")
