"""Resume Analyzer Test Endpoints for development and testing.

This module provides stub endpoints that mock the growth-service resume API
for development and testing purposes. These endpoints return realistic mock data
that matches the expected response format.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.services.interview_orchestrator import ToolExecutionContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test/resume-analyzer", tags=["resume-analyzer-test"])


# Mock resume data
MOCK_RESUMES = {
    1: {
        "id": 1,
        "userId": 1,
        "fileName": "张三_Java开发工程师_简历.pdf",
        "fileType": "pdf",
        "fileSize": 156789,
        "parseStatus": "DONE",
        "rawText": "张三\nJava开发工程师\n5年经验\n\n技能：Java, Spring Boot, MySQL, Redis, Docker, Kubernetes\n\n项目经验：\n1. 电商平台重构\n2. 微服务架构升级\n3. 高并发消息队列系统",
        "parsedJson": {
            "basics": {
                "name": "张三",
                "email": "zhangsan@example.com",
                "phone": "13800138000",
            },
            "skills": [
                "Java",
                "Spring Boot",
                "Spring Cloud",
                "MyBatis",
                "MySQL",
                "Redis",
                "MongoDB",
                "Docker",
                "Kubernetes",
                "Git",
                "Maven",
                "Linux",
                "Nginx",
            ],
            "workExperience": [
                {
                    "company": "某互联网公司",
                    "position": "Java开发工程师",
                    "duration": "2020.03 - 至今",
                    "description": "负责后端开发和系统架构设计",
                },
                {
                    "company": "某软件公司",
                    "position": "初级Java开发",
                    "duration": "2018.07 - 2020.02",
                    "description": "参与企业级应用开发",
                },
            ],
            "projects": [
                {
                    "name": "电商平台微服务重构",
                    "role": "核心开发者",
                    "duration": "2022.01 - 2022.12",
                    "description": "将单体应用重构为微服务架构，提升系统可扩展性和维护性。使用Spring Cloud构建微服务，通过Spring Cloud Gateway实现API网关，使用Consul作为服务注册中心。",
                    "technologies": ["Spring Cloud", "Spring Boot", "Consul", "Gateway", "Redis"],
                    "achievements": [
                        "将系统响应时间从500ms降低到150ms",
                        "提升系统并发处理能力3倍",
                        "实现了服务的自动扩缩容",
                    ],
                },
                {
                    "name": "高并发消息队列系统",
                    "role": "技术负责人",
                    "duration": "2023.01 - 2023.06",
                    "description": "设计和实现基于RocketMQ的高并发消息处理系统，支持订单、支付、通知等业务场景的异步处理。",
                    "technologies": ["RocketMQ", "Spring Boot", "Redis", "Docker"],
                    "achievements": [
                        "系统TPS达到10000+",
                        "消息可靠性达到99.99%",
                        "支持消息轨迹追踪和监控",
                    ],
                },
                {
                    "name": "分布式缓存优化项目",
                    "role": "核心开发者",
                    "duration": "2021.06 - 2021.12",
                    "description": "优化Redis缓存架构，解决缓存穿透、击穿、雪崩等问题，提升系统性能和稳定性。",
                    "technologies": ["Redis", "Spring Cache", "Caffeine"],
                    "achievements": [
                        "缓存命中率从70%提升到95%",
                        "减少数据库查询压力80%",
                        "实现了多级缓存策略",
                    ],
                },
            ],
            "education": [
                {
                    "school": "某理工大学",
                    "degree": "本科",
                    "major": "计算机科学与技术",
                    "duration": "2014.09 - 2018.06",
                },
            ],
        },
        "editedContent": None,
        "createTime": "2024-01-15T10:30:00",
    },
    2: {
        "id": 2,
        "userId": 2,
        "fileName": "李四_前端工程师_简历.docx",
        "fileType": "docx",
        "fileSize": 123456,
        "parseStatus": "DONE",
        "rawText": "李四\n前端开发工程师\n3年经验\n\n技能：Vue.js, React, TypeScript, JavaScript, HTML/CSS",
        "parsedJson": {
            "basics": {
                "name": "李四",
                "email": "lisi@example.com",
                "phone": "13900139000",
            },
            "skills": [
                "Vue.js",
                "React",
                "TypeScript",
                "JavaScript",
                "HTML5",
                "CSS3",
                "Webpack",
                "Vite",
                "Node.js",
            ],
            "workExperience": [
                {
                    "company": "某科技公司",
                    "position": "前端开发工程师",
                    "duration": "2021.03 - 至今",
                    "description": "负责前端页面开发和交互实现",
                }
            ],
            "projects": [
                {
                    "name": "企业管理系统前端重构",
                    "role": "前端负责人",
                    "duration": "2022.06 - 2022.12",
                    "description": "使用Vue3重构传统jQuery项目，提升开发效率和用户体验。",
                    "technologies": ["Vue3", "TypeScript", "Vite", "Element Plus"],
                }
            ],
            "education": [
                {
                    "school": "某大学",
                    "degree": "本科",
                    "major": "软件工程",
                    "duration": "2017.09 - 2021.06",
                }
            ],
        },
        "editedContent": None,
        "createTime": "2024-02-20T14:20:00",
    },
}


@router.get("/health")
async def health_check():
    """Health check endpoint for resume analyzer test service."""
    return {
        "adapter_status": "ok",
        "service_available": False,
        "supported_stages": ["welcome", "technical_questions", "project_discussion", "behavioral_questions"],
        "configuration": {
            "tool_name": "resume_analyzer",
            "service_url": "http://localhost:8003/api/growth",
            "mode": "stub",
        },
    }


@router.get("/resumes")
async def list_resumes(userId: int = 1):
    """Get list of resumes for a user (stub endpoint)."""
    # Filter resumes by userId
    user_resumes = [r for r in MOCK_RESUMES.values() if r["userId"] == userId]

    if not user_resumes:
        # Return empty list instead of 404
        return {
            "code": 200,
            "message": "No resumes found for user",
            "data": [],
        }

    return {
        "code": 200,
        "message": f"Found {len(user_resumes)} resume(s)",
        "data": user_resumes,
    }


@router.get("/resume/{resume_id}")
async def get_resume_detail(resume_id: int):
    """Get detailed resume information (stub endpoint)."""
    resume = MOCK_RESUMES.get(resume_id)

    if not resume:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")

    return {
        "code": 200,
        "message": "Resume retrieved successfully",
        "data": resume,
    }


@router.post("/resume/{resume_id}/parse")
async def parse_resume(resume_id: int):
    """Trigger resume parsing (stub endpoint)."""
    resume = MOCK_RESUMES.get(resume_id)

    if not resume:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")

    # In stub mode, just return the already parsed data
    return {
        "code": 200,
        "message": "Resume parsing completed",
        "data": {
            "resumeId": resume_id,
            "parseStatus": "DONE",
            "parsedJson": resume.get("parsedJson", {}),
        },
    }


@router.post("/resume/upload")
async def upload_resume():
    """Upload resume endpoint (stub implementation)."""
    # In stub mode, return a mock upload result
    return {
        "code": 200,
        "message": "Resume uploaded successfully",
        "data": {
            "id": 999,
            "fileName": "uploaded_resume.pdf",
            "fileType": "pdf",
            "parseStatus": "PENDING",
            "message": "Resume uploaded. Parse endpoint should be called separately.",
        },
    }


def register_test_router(app):
    """Register the test router with the FastAPI app."""
    app.include_router(router)
    logger.info("Resume analyzer test router registered at /api/test/resume-analyzer")


__all__ = ["router", "register_test_router"]
