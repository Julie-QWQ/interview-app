"""
数字人服务封装
集成 Duix.Avatar API 实现音频驱动的唇形同步
注意: 此服务需要 Duix.Avatar 服务运行在本地 (http://localhost:8383)

Duix.Avatar 提供 3 个服务:
- TTS (端口 18180): 文本转语音
- ASR (端口 10095): 语音识别
- Video Generation (端口 8383): 数字人视频生成
"""
import requests
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class DigitalHumanService:
    """数字人服务类 - 集成 Duix.Avatar"""

    def __init__(self):
        # Duix.Avatar 服务地址
        self.video_url = os.getenv('DUIX_VIDEO_URL', 'http://localhost:8383')
        self.tts_url = os.getenv('DUIX_TTS_URL', 'http://localhost:18180')
        self.asr_url = os.getenv('DUIX_ASR_URL', 'http://localhost:10095')

        # 兼容旧配置
        self.heygem_url = os.getenv('HEYGEM_URL', 'http://localhost:8383')

        # 默认头像
        self.default_avatar = os.getenv(
            'DEFAULT_AVATAR',
            'assets/avatar/default_interviewer.png'
        )

        # 是否启用
        self.enabled = os.getenv('ENABLE_DIGITAL_HUMAN', 'false').lower() == 'true'

    async def generate_talking_avatar(
        self,
        audio_base64: str,
        avatar_image: Optional[str] = None,
        text: Optional[str] = None
    ) -> dict:
        """
        生成说话头像视频

        Args:
            audio_base64: base64编码的音频数据
            avatar_image: 数字人形象图片路径(可选)
            text: 原始文本(可选,用于直接从文本生成)

        Returns:
            {
                'success': bool,
                'video_url': str,  # 视频URL
                'generation_time': float,
                'error': str (如果失败)
            }
        """
        if not self.enabled:
            return {
                'success': False,
                'error': '数字人功能未启用'
            }

        if not self.health_check():
            return {
                'success': False,
                'error': 'Duix.Avatar 服务不可用'
            }

        try:
            # 方案 1: 如果提供了文本,使用一体化 API (推荐)
            if text:
                return await self._generate_from_text(text, avatar_image)

            # 方案 2: 从已有音频生成视频
            return await self._generate_from_audio(audio_base64, avatar_image)

        except Exception as e:
            error_msg = f"数字人服务异常: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    async def _generate_from_text(
        self,
        text: str,
        avatar_image: Optional[str] = None
    ) -> dict:
        """从文本直接生成视频 (TTS + 数字人)"""
        payload = {
            'text': text,
            'avatar': avatar_image or self.default_avatar,
            'fps': 25,
            'quality': 'high'
        }

        logger.info(f"从文本生成数字人视频, 文本长度: {len(text)} 字符")

        response = await asyncio.to_thread(
            requests.post,
            f"{self.video_url}/generate_from_text",
            json=payload,
            timeout=120  # 2分钟超时(TTS + 视频生成)
        )

        return self._parse_response(response)

    async def _generate_from_audio(
        self,
        audio_base64: str,
        avatar_image: Optional[str] = None
    ) -> dict:
        """从音频生成视频"""
        payload = {
            'audio': audio_base64,
            'image': avatar_image or self.default_avatar,
            'fps': 25,
            'quality': 'high'
        }

        logger.info(f"从音频生成数字人视频, 音频长度: {len(audio_base64)} 字符")

        response = await asyncio.to_thread(
            requests.post,
            f"{self.video_url}/generate",
            json=payload,
            timeout=60
        )

        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> dict:
        """解析 API 响应"""
        if response.status_code == 200:
            result = response.json()
            logger.info(f"数字人视频生成成功: {result.get('video_url')}")
            return {
                'success': True,
                'video_url': result.get('video_url'),
                'generation_time': result.get('generation_time', 0)
            }
        else:
            error_msg = f"Duix.Avatar API 错误: {response.status_code}"
            try:
                error_detail = response.json().get('error', '')
                error_msg += f" - {error_detail}"
            except:
                pass
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def health_check(self) -> bool:
        """检查 Duix.Avatar 服务健康状态"""
        if not self.enabled:
            return False

        try:
            # 检查视频生成服务
            response = requests.get(
                f"{self.video_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                return True
        except Exception as e:
            logger.debug(f"Duix.Avatar 视频服务健康检查失败: {e}")

        return False


# 全局单例
_digital_human_service = None


def get_digital_human_service() -> DigitalHumanService:
    """获取数字人服务实例"""
    global _digital_human_service
    if _digital_human_service is None:
        _digital_human_service = DigitalHumanService()
    return _digital_human_service
