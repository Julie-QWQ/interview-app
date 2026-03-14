"""FastAPI application entrypoint for the interview service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _initialize_runtime(settings_obj: Any) -> None:
    """
    Initialize database and singleton services for the live app.

    This function is called during application startup and initializes:
    - Database connection pool
    - Default profiles
    - AI/ASR/Digital Human services
    """
    database_url = getattr(settings_obj, "database_url", None)
    if not database_url:
        return

    from .db.database import init_db, init_default_profiles, close_all_connections
    from .services.ai_service import init_ai_service
    from .services.asr_service import init_asr_service
    from .services.expression_analyzer_service import init_expression_analyzer_service
    from .services.interview_orchestrator import init_interview_orchestrator
    from .services.xunfei_digital_human_service import init_xunfei_digital_human_service

    # 初始化数据库连接池
    # 生产环境建议根据实际负载调整连接数
    min_conn = getattr(settings_obj, "db_min_connections", 2)
    max_conn = getattr(settings_obj, "db_max_connections", 10)

    init_db(
        database_url,
        min_connections=min_conn,
        max_connections=max_conn
    )

    # 注册关闭钩子，确保连接池正确关闭
    import atexit
    atexit.register(close_all_connections)

    # 初始化其他服务
    init_default_profiles()
    init_ai_service(settings_obj)
    init_asr_service(settings_obj)
    init_expression_analyzer_service(settings_obj)
    init_interview_orchestrator(settings_obj)
    init_xunfei_digital_human_service(settings_obj)


def create_app(
    *,
    settings_obj: Any | None = None,
) -> FastAPI:
    """Create the official ASGI application."""
    if settings_obj is None:
        from config.settings import settings as settings_obj

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan manager."""
        # 启动时初始化
        _initialize_runtime(settings_obj)

        # 运行应用
        yield

        # 关闭时清理（虽然 atexit 会处理，但这里显式调用更好）
        from .db.database import close_all_connections
        try:
            close_all_connections()
        except Exception as e:
            # 日志记录错误但不影响关闭流程
            import logging
            logging.getLogger(__name__).warning(f"Error closing database connections: {e}")

    app = FastAPI(
        title=getattr(settings_obj, "app_name", "interview-service"),
        version=getattr(settings_obj, "app_version", "0.1.0"),
        lifespan=lifespan,
    )
    app.state.settings = settings_obj

    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    get_method = getattr(settings_obj, "get", None)
    if callable(get_method):
        allow_methods = list(get_method("cors.methods", allow_methods))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(getattr(settings_obj, "cors_origins", ["*"])),
        allow_credentials=True,
        allow_methods=allow_methods,
        allow_headers=["*"],
    )

    from .api.asr import router as asr_router
    from .api.configs import router as configs_router
    from .api.digital_human import router as digital_human_router
    from .api.expressions import router as expressions_router
    from .api.interviews import router as interviews_router
    from .api.messages import router as messages_router
    from .api.profiles import router as profiles_router
    from .api.profiles_flask import router as profile_plugins_router
    from .api.snapshots import router as snapshots_router
    from .api.test_routes import router as test_routes_router
    from .api.tools import router as tools_router
    from .api.voice import router as voice_router
    from .api.question_bank_test import router as question_bank_test_router
    from .api.resume_analyzer_test import router as resume_analyzer_test_router

    app.include_router(configs_router)
    app.include_router(voice_router)
    app.include_router(asr_router)
    app.include_router(interviews_router)
    app.include_router(messages_router)
    app.include_router(expressions_router)
    app.include_router(tools_router)
    app.include_router(test_routes_router)
    app.include_router(digital_human_router)
    app.include_router(snapshots_router)
    app.include_router(profiles_router)
    app.include_router(profile_plugins_router)
    # Test routes for external tools - uncomment to enable
    app.include_router(question_bank_test_router)
    app.include_router(resume_analyzer_test_router)

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "interview-service"}

    @app.get("/api/health")
    def api_health() -> dict[str, str]:
        return {"status": "healthy", "service": "interview-service-api"}
    return app
