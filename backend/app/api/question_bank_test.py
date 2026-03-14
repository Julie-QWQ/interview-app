"""Test API endpoints for Question Bank Tool integration.

These endpoints provide manual testing capabilities for the question bank service integration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from app.services.interview_orchestrator import QuestionBankAdapter, LearningResourceAdapter, ToolExecutionContext
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test")


def _error(message: str, status_code: int = 500) -> JSONResponse:
    """Create error response."""
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/question-bank/search")
def test_question_search(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Test question search functionality.

    Request body:
    {
        "position": "java_backend",
        "type": "technical",
        "difficulty": 3,
        "tags": "Spring,Redis",
        "query": "Spring Bean生命周期",
        "size": 5
    }
    """
    try:
        # 使用配置中的真实外部接口URL
        adapter_settings = {
            "tools": {
                "providers": {
                    "question_bank": {
                        "enabled": True,
                        "mode": "url",
                        "url": "http://10.179.224.63:8004/api",  # 外部真实接口
                        "timeout_seconds": 10,
                        "headers": {},
                    }
                }
            }
        }

        adapter = QuestionBankAdapter(adapter_settings)

        # Build request
        context = ToolExecutionContext(
            trace_id="test-search",
            interview_id=0,
            stage="technical_questions",
            trigger="stage_enter",
            interview_config={
                "position": payload.get("position", "java_backend"),
                "difficulty_level": payload.get("difficulty", 3),
                "skills": payload.get("tags", "").split(",") if payload.get("tags") else [],
            },
            conversation_slice=[],
            current_user_message=payload.get("query"),
            progress_info=None,
        )

        request = adapter.build_request(context)

        # Update request params with payload
        request["params"].update({
            "type": payload.get("type", "technical"),
            "size": payload.get("size", 5),
        })

        # Execute request
        result = adapter.call(request, timeout_seconds=10)

        if result.status == "success":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "summary": result.summary,
                    "questions": result.structured_payload.get("questions", []),
                    "count": result.structured_payload.get("count", 0),
                    "meta": result.meta,
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "errors": result.errors,
                    "summary": result.summary,
                }
            )

    except Exception as exc:
        logger.error("Question search test failed: %s", exc)
        return _error(f"Question search test failed: {str(exc)}")


@router.get("/question-bank/followup/{question_id}")
def test_followup_hints(question_id: int):
    """Test follow-up hints functionality.

    Path parameter:
    - question_id: The question ID to get follow-up hints for
    """
    try:
        adapter_settings = {
            "tools": {
                "providers": {
                    "question_bank": {
                        "enabled": True,
                        "mode": "url",
                        "url": "http://10.179.224.63:8004/api",  # 外部真实接口
                        "timeout_seconds": 10,
                    }
                }
            }
        }

        adapter = QuestionBankAdapter(adapter_settings)

        # Build follow-up request
        import requests

        url = f"http://10.179.224.63:8004/api/question/{question_id}/followup"  # 外部真实接口
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == 200:
            hints_data = data.get("data", {})
            hints = hints_data.get("followUpHints", [])

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "question_id": question_id,
                    "hints": hints,
                    "count": len(hints),
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": data.get("message", "Unknown error"),
                }
            )

    except Exception as exc:
        logger.error("Follow-up hints test failed: %s", exc)
        return _error(f"Follow-up hints test failed: {str(exc)}")


@router.get("/question-bank/knowledge/search")
def test_knowledge_search(
    query: str = Query(..., description="Search query"),
    position: str = Query("java_backend", description="Position filter"),
    size: int = Query(3, description="Number of results"),
):
    """Test knowledge document search (RAG).

    Query parameters:
    - query: Search query (required)
    - position: Position filter (default: java_backend)
    - size: Number of results (default: 3)
    """
    try:
        import requests

        url = "http://10.179.224.63:8004/api/knowledge/search"  # 外部真实接口
        params = {
            "query": query,
            "position": position,
            "size": size,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == 200:
            documents = data.get("data", [])

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "query": query,
                    "documents": documents,
                    "count": len(documents),
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": data.get("message", "Unknown error"),
                }
            )

    except Exception as exc:
        logger.error("Knowledge search test failed: %s", exc)
        return _error(f"Knowledge search test failed: {str(exc)}")


@router.get("/question-bank/health")
def test_question_bank_health():
    """Test question bank service health and configuration."""
    try:
        adapter_settings = {
            "tools": {
                "providers": {
                    "question_bank": {
                        "enabled": True,
                        "mode": "url",
                        "url": "http://localhost:8004/api",
                        "timeout_seconds": 5,
                    }
                }
            }
        }

        adapter = QuestionBankAdapter(adapter_settings)

        # Check provider status
        status = adapter.provider_status()

        # Test basic connectivity
        import requests

        health_url = "http://10.179.224.63:8004/api/question/search"  # 外部真实接口
        try:
            response = requests.get(
                health_url,
                params={"position": "java_backend", "size": 1},
                timeout=5
            )
            service_available = response.status_code == 200
        except Exception:
            service_available = False

        return JSONResponse(
            status_code=200,
            content={
                "adapter_status": "ok" if adapter.is_enabled() else "disabled",
                "provider_status": status,
                "service_available": service_available,
                "supported_stages": list(adapter.supported_stages),
                "supported_triggers": list(adapter.supported_triggers),
                "configuration": {
                    "tool_name": adapter.tool_name,
                    "default_ttl_seconds": adapter.default_ttl_seconds,
                    "service_url": "http://10.179.224.63:8004/api",  # 外部真实接口
                }
            }
        )

    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return _error(f"Health check failed: {str(exc)}")


@router.get("/learning-resource/recommend")
def test_learning_resource_recommend(
    user_id: int = Query(None, description="User ID for personalized recommendation"),
    position: str = Query("java_backend", description="Position filter"),
    tags: str = Query(None, description="Skill tags, comma separated"),
    resource_type: str = Query(None, description="Resource type: article/video/book/project"),
    size: int = Query(5, description="Number of results"),
):
    """Test learning resource recommendation (新版API v1.1).

    Query parameters:
    - user_id: 用户ID；传入时优先按薄弱技能（actualScore < 60）推荐，忽略 tags
    - position: 岗位枚举值（必填）
    - tags: 知识点标签，逗号分隔；userId 无薄弱技能时生效
    - resource_type: 资源类型 article/video/book/project
    - size: 返回数量（默认5）

    新版API特性：
    ⚠ 推荐优先级：① userId 薄弱技能 → ② tags 标签 → ③ position 兜底
    """
    try:
        import requests

        url = "http://10.179.224.63:8004/api/resource/recommend"  # 外部真实接口
        params = {
            "position": position,
            "size": size,
        }

        # 按优先级添加参数
        if user_id:
            params["userId"] = user_id
        elif tags:
            params["tags"] = tags

        if resource_type:
            params["type"] = resource_type

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("code") == 200:
            resources = data.get("data", [])

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": data.get("message", "success"),
                    "resources": resources,
                    "count": len(resources),
                    "params": params,  # 显示实际使用的参数
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "code": data.get("code"),
                    "message": data.get("message", "Unknown error"),
                }
            )

    except Exception as exc:
        logger.error("Learning resource recommendation test failed: %s", exc)
        return _error(f"Learning resource recommendation test failed: {str(exc)}")