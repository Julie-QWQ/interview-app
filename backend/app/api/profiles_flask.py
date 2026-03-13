"""FastAPI routes and helpers for profile plugin management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.db import database
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


LEGACY_INTERVIEWER_PROMPT_MAP = {
    "analytical": "你是一位分析型技术面试官。",
    "guided": "你是一位引导型技术面试官。",
    "behavioral": "你是一位行为导向型面试官。",
}


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def normalize_interviewer_config(config: dict[str, Any] | None, plugin_id: str | None = None) -> dict[str, Any]:
    config = dict(config or {})
    style = config.get("style") or {}
    defaults = settings.interviewer_meta_map.get(plugin_id, {})
    preset = settings.interviewer_preset_map.get(plugin_id, {})
    preset_config = preset.get("config") or {}
    prompt = (
        config.get("prompt")
        or config.get("prompt_template")
        or LEGACY_INTERVIEWER_PROMPT_MAP.get(style.get("questioning_style"), "")
    )
    return {
        "prompt": prompt,
        "difficulty": config.get("difficulty") or style.get("difficulty") or defaults.get("difficulty", "standard"),
        "style_tone": config.get("style_tone") or defaults.get("style_tone", "balanced"),
        "avatar_id": config.get("avatar_id") or preset_config.get("avatar_id") or settings.default_interviewer_avatar_id,
        "vcn": config.get("vcn") or preset_config.get("vcn") or settings.default_interviewer_vcn,
        "image_url": (
            config.get("image_url")
            or preset_config.get("image_url")
            or config.get("display_image_url")
            or preset_config.get("display_image_url")
            or settings.default_interviewer_display_image_url
        ),
        "display_image_url": (
            config.get("display_image_url")
            or config.get("image_url")
            or preset_config.get("display_image_url")
            or preset_config.get("image_url")
            or settings.default_interviewer_display_image_url
        ),
    }


def normalize_plugin(plugin: dict[str, Any] | None) -> dict[str, Any] | None:
    if not plugin:
        return plugin
    normalized = dict(plugin)
    if normalized.get("type") == "interviewer":
        normalized["config"] = normalize_interviewer_config(normalized.get("config"), normalized.get("plugin_id"))
    return normalized


def normalize_interview_profile_payload(profile: dict[str, Any] | None) -> dict[str, Any] | None:
    if not profile:
        return profile
    normalized = dict(profile)
    normalized["interviewer_config"] = normalize_interviewer_config(
        normalized.get("interviewer_config"),
        normalized.get("interviewer_plugin_id"),
    )
    return normalized


@router.get("/profiles/plugins")
def list_plugins(
    type: str | None = Query(default=None),
    is_system: bool | None = Query(default=None),
):
    try:
        plugins = database.list_profile_plugins(plugin_type=type, is_system=is_system)
        return {"success": True, "data": [normalize_plugin(plugin) for plugin in plugins]}
    except Exception as exc:
        logger.error("Failed to list plugins: %s", exc)
        return _error("获取插件列表失败")


@router.post("/profiles/plugins")
def create_plugin(payload: dict = Body(default_factory=dict)):
    try:
        plugin_id = payload.get("plugin_id")
        existing = database.get_profile_plugin(plugin_id)
        if existing:
            return _error("插件 ID 已存在", status_code=400)
        if payload.get("type") == "interviewer":
            payload["config"] = normalize_interviewer_config(payload.get("config"))
        database.create_profile_plugin(payload)
        return JSONResponse(
            status_code=201,
            content={"success": True, "message": "创建成功", "data": {"plugin_id": plugin_id}},
        )
    except Exception as exc:
        logger.error("Failed to create plugin: %s", exc)
        return _error("创建插件失败")


@router.get("/profiles/plugins/{plugin_id}")
def get_plugin(plugin_id: str):
    try:
        plugin = database.get_profile_plugin(plugin_id)
        if not plugin:
            return _error("插件不存在", status_code=404)
        return {"success": True, "data": normalize_plugin(plugin)}
    except Exception as exc:
        logger.error("Failed to get plugin: %s", exc)
        return _error("获取插件详情失败")


@router.put("/profiles/plugins/{plugin_id}")
def update_plugin(plugin_id: str, payload: dict = Body(default_factory=dict)):
    try:
        existing = database.get_profile_plugin(plugin_id)
        if not existing:
            return _error("插件不存在", status_code=404)
        if existing["is_system"]:
            return _error("系统预设插件不允许修改", status_code=403)
        if existing.get("type") == "interviewer":
            payload["config"] = normalize_interviewer_config(payload.get("config"))
        success = database.update_profile_plugin(plugin_id, payload)
        if not success:
            return _error("更新失败")
        return {"success": True, "message": "更新成功"}
    except Exception as exc:
        logger.error("Failed to update plugin: %s", exc)
        return _error("更新插件失败")


@router.delete("/profiles/plugins/{plugin_id}")
def delete_plugin(plugin_id: str):
    try:
        existing = database.get_profile_plugin(plugin_id)
        if not existing:
            return _error("插件不存在", status_code=404)
        if existing["is_system"]:
            return _error("系统预设插件不允许删除", status_code=403)
        success = database.delete_profile_plugin(plugin_id)
        if not success:
            return _error("删除失败")
        return {"success": True, "message": "删除成功"}
    except Exception as exc:
        logger.error("Failed to delete plugin: %s", exc)
        return _error("删除插件失败")


@router.post("/profiles/interviews/{interview_id}/apply")
def apply_profiles(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        position_plugin_id = payload.get("position_plugin_id")
        interviewer_plugin_id = payload.get("interviewer_plugin_id")
        custom_config = payload.get("custom_config")

        position_plugin = database.get_profile_plugin(position_plugin_id)
        if not position_plugin:
            return _error(f"岗位插件 {position_plugin_id} 不存在", status_code=404)
        interviewer_plugin = database.get_profile_plugin(interviewer_plugin_id)
        if not interviewer_plugin:
            return _error(f"面试官插件 {interviewer_plugin_id} 不存在", status_code=404)

        profile_id = database.apply_interview_profile(
            interview_id,
            position_plugin_id,
            interviewer_plugin_id,
            custom_config,
        )
        return {"success": True, "message": "应用成功", "data": {"profile_id": profile_id}}
    except Exception as exc:
        logger.error("Failed to apply profiles: %s", exc)
        return _error("应用画像失败")


@router.get("/profiles/interviews/{interview_id}")
def get_interview_profiles(interview_id: int):
    try:
        profile = database.get_interview_profile(interview_id)
        if not profile:
            return _error("该面试未配置画像", status_code=404)
        return {"success": True, "data": normalize_interview_profile_payload(profile)}
    except Exception as exc:
        logger.error("Failed to get interview profiles: %s", exc)
        return _error("获取面试画像失败")


def register_profile_routes(_api_bp) -> None:
    """Compatibility no-op for legacy bootstrap."""
    logger.info("Profile routes are served by FastAPI routers")
