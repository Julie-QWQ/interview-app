"""
数字人服务适配器
自动选择使用本地服务还是云端 API
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DigitalHumanAdapter:
    """
    数字人服务适配器
    根据配置自动选择使用本地服务或云端 API
    """

    def __init__(self):
        # 检测使用哪种模式
        self.mode = self._detect_mode()
        self.service = None
        self._init_service()

        logger.info(f"数字人服务模式: {self.mode}")

    def _detect_mode(self) -> str:
        """
        检测使用的服务模式

        优先级:
        1. 如果配置了 DUIX_API_KEY,使用 API 模式 (云端)
        2. 如果配置了 WAV2LIP_URL,使用 Wav2Lip 模式 (轻量级本地)
        3. 如果配置了 DUIX_VIDEO_URL 或 HEYGEM_URL,使用本地服务模式 (高性能本地)
        4. 否则禁用
        """
        if os.getenv('DUIX_API_KEY'):
            return 'api'
        elif os.getenv('WAV2LIP_URL'):
            return 'wav2lip'
        elif os.getenv('DUIX_VIDEO_URL') or os.getenv('HEYGEM_URL'):
            return 'local'
        else:
            return 'disabled'

    def _init_service(self):
        """初始化对应的服务实例"""
        if self.mode == 'api':
            from app.services.digital_human_service_api import get_digital_human_service_api
            self.service = get_digital_human_service_api()
        elif self.mode == 'wav2lip':
            from app.services.digital_human_service_wav2lip import get_digital_human_service_wav2lip
            self.service = get_digital_human_service_wav2lip()
        elif self.mode == 'local':
            from app.services.digital_human_service import get_digital_human_service
            self.service = get_digital_human_service()
        else:
            logger.warning("数字人服务未启用")
            self.service = None

    async def generate_talking_avatar(
        self,
        audio_base64: str,
        avatar_image: Optional[str] = None,
        text: Optional[str] = None
    ) -> dict:
        """
        生成说话头像视频 (自动路由到对应的服务)

        Args:
            audio_base64: base64编码的音频数据
            avatar_image: 数字人形象图片路径(可选)
            text: 原始文本(可选)

        Returns:
            {
                'success': bool,
                'video_url': str,
                'generation_time': float,
                'error': str (如果失败)
            }
        """
        if not self.service:
            return {
                'success': False,
                'error': '数字人服务未启用'
            }

        # 调用对应的服务
        return await self.service.generate_talking_avatar(
            audio_base64=audio_base64,
            avatar_image=avatar_image,
            text=text
        )

    def health_check(self) -> bool:
        """检查服务健康状态"""
        if not self.service:
            return False

        return self.service.health_check()

    def get_mode(self) -> str:
        """获取当前模式"""
        return self.mode


# 全局单例
_adapter = None


def get_digital_human_service() -> DigitalHumanAdapter:
    """
    获取数字人服务实例

    自动选择使用本地服务或云端 API

    使用示例:
        service = get_digital_human_service()
        result = await service.generate_talking_avatar(
            audio_base64=audio_data,
            text="你好"
        )

        print(f"使用模式: {service.get_mode()}")
        if result['success']:
            print(f"视频URL: {result['video_url']}")
    """
    global _adapter
    if _adapter is None:
        _adapter = DigitalHumanAdapter()
    return _adapter
