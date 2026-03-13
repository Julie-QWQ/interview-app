"""FastAPI routes for interview snapshots."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.db import database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def _serialize_datetime(obj):
    if isinstance(obj, dict):
        return {key: _serialize_datetime(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_serialize_datetime(item) for item in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


@router.post("/interviews/{interview_id}/snapshots")
def create_snapshot(interview_id: int, payload: dict = Body(default_factory=dict)):
    try:
        name = payload.get("name")
        description = payload.get("description", "")
        if not name:
            return _error("快照名称不能为空", status_code=400)

        interview = database.get_interview(interview_id)
        if not interview:
            return _error("Interview not found", status_code=404)

        messages = database.get_messages(interview_id)
        snapshot_content = {
            "interview": _serialize_datetime(dict(interview)),
            "messages": _serialize_datetime(messages),
            "current_stage": interview.get("current_stage"),
            "created_at": interview.get("created_at").isoformat() if interview.get("created_at") else None,
        }
        snapshot_id = database.create_snapshot(
            {
                "interview_id": interview_id,
                "name": name,
                "description": description,
                "snapshot_data": snapshot_content,
            }
        )
        return JSONResponse(
            status_code=201,
            content={"message": "创建快照成功", "snapshot_id": snapshot_id},
        )
    except Exception as exc:
        logger.error("Failed to create snapshot: %s", exc)
        return _error("Internal server error")


@router.get("/interviews/{interview_id}/snapshots")
def list_snapshots(interview_id: int):
    try:
        snapshots = database.get_snapshots(interview_id)
        result = []
        for snapshot in snapshots:
            snapshot_data = snapshot.get("snapshot_data", {}) or {}
            if isinstance(snapshot_data, str):
                import json

                snapshot_data = json.loads(snapshot_data)
            result.append(
                {
                    "id": snapshot["id"],
                    "name": snapshot["name"],
                    "description": snapshot["description"],
                    "created_at": snapshot["created_at"],
                    "message_count": len(snapshot_data.get("messages", [])),
                }
            )
        return result
    except Exception as exc:
        logger.error("Failed to list snapshots: %s", exc)
        return _error("Internal server error")


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(snapshot_id: int):
    try:
        snapshot = database.get_snapshot(snapshot_id)
        if not snapshot:
            return _error("Snapshot not found", status_code=404)

        snapshot_data = snapshot.get("snapshot_data", {}) or {}
        if isinstance(snapshot_data, str):
            import json

            snapshot_data = json.loads(snapshot_data)

        return {
            "id": snapshot["id"],
            "name": snapshot["name"],
            "description": snapshot["description"],
            "created_at": snapshot["created_at"],
            "data": snapshot_data,
        }
    except Exception as exc:
        logger.error("Failed to get snapshot: %s", exc)
        return _error("Internal server error")


@router.post("/snapshots/{snapshot_id}/load")
def load_snapshot(snapshot_id: int):
    try:
        snapshot = database.get_snapshot(snapshot_id)
        if not snapshot:
            return _error("Snapshot not found", status_code=404)

        snapshot_data = snapshot.get("snapshot_data", {}) or {}
        if isinstance(snapshot_data, str):
            import json

            snapshot_data = json.loads(snapshot_data)
        original_interview_id = snapshot_data["interview"]["id"]
        return {
            "message": "加载快照成功",
            "snapshot_id": snapshot_id,
            "original_interview_id": original_interview_id,
            "data": snapshot_data,
        }
    except Exception as exc:
        logger.error("Failed to load snapshot: %s", exc)
        return _error("Internal server error")


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: int):
    try:
        success = database.delete_snapshot(snapshot_id)
        if not success:
            return _error("Snapshot not found", status_code=404)
        return {"message": "快照删除成功"}
    except Exception as exc:
        logger.error("Failed to delete snapshot: %s", exc)
        return _error("Internal server error")
