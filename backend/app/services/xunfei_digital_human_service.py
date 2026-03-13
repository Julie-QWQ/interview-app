"""
讯飞 2D 数字人服务。
前端 Web SDK 直接处理鉴权和 WebSocket 连接，后端只负责提供会话配置。
"""
import logging
import os
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class XunfeiDigitalHumanService:
    """讯飞数字人服务配置提供器。"""

    def __init__(self, settings=None):
        from config.settings import settings as default_settings

        self.settings = settings or default_settings

        self.app_id = os.getenv("XUNFEI_APP_ID", "")
        self.api_key = os.getenv("XUNFEI_API_KEY", "")
        self.api_secret = os.getenv("XUNFEI_API_SECRET", "")
        self.scene_id = os.getenv("XUNFEI_SCENE_ID", "default")

        self.default_avatar_id = self.settings.default_interviewer_avatar_id
        self.default_vcn_id = self.settings.default_interviewer_vcn
        self.sample_rate = self.settings.get("digital_human.xunfei.sample_rate", 16000)

        self.enabled = bool(self.app_id and self.api_key and self.api_secret)
        if not self.enabled:
            logger.warning("讯飞数字人配置不完整，服务将不可用")

    def initialize_session(
        self,
        avatar_id: Optional[str] = None,
        vcn: Optional[str] = None,
        interview_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        _ = interview_id

        if not self.enabled:
            return {
                "success": False,
                "error": "讯飞数字人服务未启用或配置不完整",
            }

        try:
            session_id = str(uuid.uuid4())
            avatar_id = avatar_id or self.default_avatar_id
            vcn = vcn or self.default_vcn_id

            config = {
                "appId": self.app_id,
                "apiKey": self.api_key,
                "apiSecret": self.api_secret,
                "sceneId": self.scene_id,
                "avatarId": avatar_id,
                "vcn": vcn,
                "sampleRate": self.sample_rate,
            }

            logger.info("讯飞数字人会话配置生成成功: session_id=%s, avatar_id=%s", session_id, avatar_id)
            return {
                "success": True,
                "session_id": session_id,
                "avatar_id": avatar_id,
                "config": config,
            }
        except Exception as exc:
            error_msg = f"生成讯飞数字人会话配置失败: {exc}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

    async def stream_audio(self, audio_data: bytes, end_of_speech: bool = False) -> Dict[str, Any]:
        _ = (audio_data, end_of_speech)
        return {"success": True}

    async def interrupt_speech(self) -> Dict[str, Any]:
        return {"success": True}

    async def destroy_session(self) -> Dict[str, Any]:
        return {"success": True}

    def health_check(self) -> bool:
        return self.enabled and bool(self.app_id and self.api_key and self.api_secret)


_xunfei_digital_human_service = None


def get_xunfei_digital_human_service() -> XunfeiDigitalHumanService:
    global _xunfei_digital_human_service
    if _xunfei_digital_human_service is None:
        _xunfei_digital_human_service = XunfeiDigitalHumanService()
    return _xunfei_digital_human_service


def init_xunfei_digital_human_service(settings):
    global _xunfei_digital_human_service
    _ = settings
    _xunfei_digital_human_service = XunfeiDigitalHumanService()
    logger.info("讯飞数字人服务已初始化")
