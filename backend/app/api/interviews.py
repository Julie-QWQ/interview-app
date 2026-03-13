"""FastAPI routes for interview lifecycle management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.utils import (
    _build_history_export,
    _infer_candidate_name_from_resume,
    _normalize_skill_domain,
    finalize_expression_analysis,
)
from app.db import database
from app.models.schemas import (
    CreateInterviewRequest,
    InterviewDetailResponse,
    InterviewResponse,
    InterviewStatus,
    MessageResponse,
    MessageType,
)
from app.services.ai_service import get_ai_service
from app.services.interview_orchestrator import get_interview_orchestrator
from app.services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/interviews")
def create_interview(payload: dict = Body(default_factory=dict)):
    try:
        interview_req = CreateInterviewRequest(**payload)

        position_plugin = database.get_profile_plugin(interview_req.position_profile_id)
        interviewer_plugin = database.get_profile_plugin(interview_req.interviewer_profile_id)
        if not position_plugin:
            return _error("岗位画像不存在", status_code=400)
        if not interviewer_plugin:
            return _error("面试官画像不存在", status_code=400)

        position_cfg = position_plugin.get("config") or {}
        interviewer_cfg = interviewer_plugin.get("config") or {}
        skill_req = position_cfg.get("skill_requirements") or {}

        interview_id = database.create_interview(
            {
                "candidate_name": _infer_candidate_name_from_resume(interview_req.resume_text or ""),
                "position": position_plugin.get("name") or "技术岗位",
                "skill_domain": _normalize_skill_domain(position_cfg.get("skill_domain")),
                "skills": skill_req.get("core_skills") or ["综合能力"],
                "experience_level": position_cfg.get("experience_level")
                or interviewer_cfg.get("preferred_level")
                or "中级",
                "duration_minutes": interview_req.duration_minutes,
                "additional_requirements": interview_req.additional_requirements,
                "resume_file_id": interview_req.resume_file_id,
                "resume_text": interview_req.resume_text,
            }
        )

        try:
            database.apply_interview_profile(
                interview_id,
                interview_req.position_profile_id,
                interview_req.interviewer_profile_id,
                {},
            )
        except Exception:
            database.delete_interview(interview_id)
            return _error("Profile binding failed and interview creation was rolled back")

        interview = database.get_interview(interview_id)
        return JSONResponse(status_code=201, content=InterviewResponse(**interview).model_dump(mode="json"))
    except ValidationError as exc:
        return _error(str(exc), status_code=400)
    except Exception as exc:
        logger.error("Failed to create interview: %s", exc)
        return _error("Internal server error")


@router.get("/interviews")
def list_interviews(status: str | None = None, limit: int = 50, offset: int = 0):
    try:
        interviews = database.list_interviews(limit=limit, offset=offset, status=status)
        return [InterviewResponse(**item).model_dump(mode="json") for item in interviews]
    except Exception as exc:
        logger.error("Failed to list interviews: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}")
def get_interview(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)

        messages = database.get_messages(interview_id)
        current_stage = interview.get("current_stage")
        stage_progress = None
        if current_stage and interview["status"] == InterviewStatus.IN_PROGRESS:
            try:
                stage_progress = get_ai_service().get_interview_progress(
                    messages,
                    current_stage,
                    interview.get("duration_minutes", 30),
                    interview_config=interview,
                )
            except Exception:
                logger.warning("Failed to compute stage progress", exc_info=True)

        interview_without_stage = {
            key: value
            for key, value in interview.items()
            if key not in {"current_stage", "current_message_id"}
        }
        detail = InterviewDetailResponse(
            **interview_without_stage,
            messages=[MessageResponse(**message).model_dump(mode="json") for message in messages],
            current_stage=current_stage,
            stage_progress=stage_progress,
            current_message_id=interview.get("current_message_id"),
        )
        return detail.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to get interview: %s", exc)
        return _error("Internal server error")


@router.delete("/interviews/{interview_id}")
def delete_interview(interview_id: int):
    try:
        if not database.delete_interview(interview_id):
            return _error("Interview not found", status_code=404)
        return {"message": "删除成功"}
    except Exception as exc:
        logger.error("Failed to delete interview: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/start")
def start_interview(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        if interview["status"] not in [InterviewStatus.CREATED, InterviewStatus.IN_PROGRESS]:
            return _error("Invalid interview status", status_code=400)

        messages = database.get_messages(interview_id)
        is_retry = len(messages) > 0 and interview["status"] == InterviewStatus.IN_PROGRESS
        if not is_retry:
            database.update_interview_status(interview_id, InterviewStatus.IN_PROGRESS)
            database.update_interview_stage(interview_id, prompt_service.get_first_stage())

        trace_id = get_interview_orchestrator().new_trace_id()
        welcome_message = get_ai_service().start_interview(interview, trace_id=trace_id)
        message_id = database.create_message(interview_id, MessageType.ASSISTANT, welcome_message)
        database.update_interview_current_message(interview_id, message_id)
        first_stage = prompt_service.get_first_stage()
        return {
            "message": "Interview started",
            "trace_id": trace_id,
            "welcome_message": welcome_message,
            "welcome_audio": None,
            "message_id": message_id,
            "current_stage": first_stage,
        }
    except Exception as exc:
        logger.error("Failed to start interview: %s", exc)
        return _error("Internal server error")


@router.post("/interviews/{interview_id}/complete")
def complete_interview(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        if interview["status"] != InterviewStatus.IN_PROGRESS:
            return _error("面试未进行中", status_code=400)

        current_message_id = interview.get("current_message_id")
        if not current_message_id:
            return _error("当前消息路径不存在，无法导出历史对话", status_code=400)

        export_payload = _build_history_export(interview_id, current_message_id)
        report_payload = finalize_expression_analysis(interview_id)
        database.update_interview_status(interview_id, InterviewStatus.COMPLETED)
        return {
            "message": "面试已完成",
            "history_export": export_payload,
            "expression_report": report_payload,
        }
    except Exception as exc:
        logger.error("Failed to complete interview: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}/history-export")
def export_interview_history(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        current_message_id = interview.get("current_message_id")
        if not current_message_id:
            return _error("当前消息路径不存在，无法导出历史对话", status_code=400)
        return _build_history_export(interview_id, current_message_id)
    except Exception as exc:
        logger.error("Failed to export history: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}/progress")
def get_interview_progress(interview_id: int):
    try:
        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)
        current_message_id = interview.get("current_message_id")
        messages = (
            database.get_message_path(interview_id, current_message_id)
            if current_message_id
            else database.get_messages(interview_id)
        )
        current_stage = interview.get("current_stage", prompt_service.get_first_stage())
        return get_ai_service().get_interview_progress(
            messages,
            current_stage,
            interview.get("duration_minutes", 30),
            interview_config=interview,
        )
    except Exception as exc:
        logger.error("Failed to get interview progress: %s", exc)
        return _error("Internal server error")


@router.put("/interviews/{interview_id}/current-message")
def update_current_message(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        message_id = payload.get("message_id")
        if not message_id:
            return _error("message_id is required", status_code=400)
        messages = database.get_messages(interview_id)
        if not any(message["id"] == message_id for message in messages):
            return _error("Message not found", status_code=404)
        if not database.update_interview_current_message(interview_id, message_id):
            return _error("更新失败")
        return {"message": "更新成功"}
    except Exception as exc:
        logger.error("Failed to update current message: %s", exc)
        return _error("Internal server error")
