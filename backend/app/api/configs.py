"""FastAPI routes for prompt and stage configuration."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.prompt_config import InterviewPromptConfig
from app.services.prompt_service import prompt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.get("/prompts/config")
def get_prompt_config():
    try:
        return prompt_service.get_prompt_config_data()
    except Exception as exc:
        logger.error("Failed to get prompt config: %s", exc)
        return _error(str(exc))


@router.post("/prompts/config")
def update_prompt_config(config: InterviewPromptConfig):
    try:
        prompt_service.save_prompt_config(config)
        return {"message": "配置保存成功"}
    except Exception as exc:
        logger.error("Failed to update prompt config: %s", exc)
        return _error(str(exc))


@router.post("/prompts/reset")
def reset_prompt_config():
    try:
        response_config = prompt_service.reset_prompt_config()
        return {"message": "配置已重置", "config": response_config}
    except Exception as exc:
        logger.error("Failed to reset prompt config: %s", exc)
        return _error(str(exc))


@router.get("/stages/config")
def get_stages_config():
    try:
        stage_models = prompt_service.get_stage_configs()
        stages_config = [
            {
                "stage": stage.stage,
                "name": stage.name,
                "description": stage.description,
                "max_turns": stage.max_turns,
                "min_turns": stage.min_turns,
                "time_allocation": stage.time_allocation,
                "system_instruction": stage.system_instruction,
                "enabled": stage.enabled,
                "order": getattr(stage, "order", 0),
            }
            for stage in stage_models
        ]
        return {
            "stages": stages_config,
            "total_duration": sum(stage["time_allocation"] for stage in stages_config),
            "total_max_turns": sum(stage["max_turns"] for stage in stages_config),
        }
    except Exception as exc:
        logger.error("Failed to get stage config: %s", exc)
        return _error("Internal server error")
