"""
数字人服务封装 - API 版本
集成 Duix.Avatar 云端 API 实现音频驱动的唇形同步
"""
import requests
import asyncio
import logging
import os
import base64
from typing import Optional

logger = logging.getLogger(__name__)


class DigitalHumanServiceAPI:
    """数字人服务类 - Duix.Avatar API 版本"""

    def __init__(self):
        # API 配置
        self.api_base = os.getenv('DUIX_API_BASE', 'https://api.duix.com/v1')
        self.api_key = os.getenv('DUIX_API_KEY', '')

        # 默认头像
        self.default_avatar = os.getenv(
            'DEFAULT_AVATAR',
            'assets/avatar/default-interviewer.png'
        )

        # 是否启用
        self.enabled = os.getenv('ENABLE_DIGITAL_HUMAN', 'false').lower() == 'true'

        if self.enabled and not self.api_key:
            logger.warning("DUIX_API_KEY 未配置,数字人功能将被禁用")
            self.enabled = False

    async def generate_talking_avatar(
        self,
        audio_base64: str,
        avatar_image: Optional[str] = None,
        text: Optional[str] = None
    ) -> dict:
        """
        使用 Duix.Avatar API 生成说话头像视频

        Args:
            audio_base64: base64编码的音频数据
            avatar_image: 数字人形象图片路径(可选)
            text: 原始文本(可选,某些 API 支持直接文本生成)

        Returns:
            {
                'success': bool,
                'video_url': str,  # 视频 URL
                'generation_time': float,
                'error': str (如果失败)
            }
        """
        if not self.enabled:
            return {
                'success': False,
                'error': '数字人功能未启用或未配置 API Key'
            }

        try:
            # 根据是否提供文本,选择不同的 API 端点
            if text:
                # 方案 1: 从文本直接生成 (TTS + 数字人一体)
                return await self._generate_from_text_api(text, avatar_image)
            else:
                # 方案 2: 从已有音频生成视频
                return await self._generate_from_audio_api(audio_base64, avatar_image)

        except Exception as e:
            error_msg = f"Duix.Avatar API 调用异常: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    async def _generate_from_text_api(
        self,
        text: str,
        avatar_image: Optional[str] = None
    ) -> dict:
        """
        调用文本生成视频 API

        API 端点示例: POST /video/generate/from_text
        请求体:
        {
            "text": "你好,我是面试官",
            "avatar": "default_interviewer.png",
            "voice": "ziming",
            "quality": "high"
        }
        """
        url = f"{self.api_base}/video/generate/from_text"

        payload = {
            "text": text,
            "avatar": avatar_image or self.default_avatar,
            "voice": "ziming",  # 或使用 Edge-TTS 生成的音频
            "quality": "high",
            "fps": 25,
            "callback_url": None  # 如果需要异步回调
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"调用 Duix.Avatar API 生成视频, 文本长度: {len(text)}")

        response = await asyncio.to_thread(
            requests.post,
            url,
            json=payload,
            headers=headers,
            timeout=120  # 2分钟超时
        )

        return self._parse_response(response)

    async def _generate_from_audio_api(
        self,
        audio_base64: str,
        avatar_image: Optional[str] = None
    ) -> dict:
        """
        调用音频生成视频 API

        API 端点示例: POST /video/generate/from_audio
        请求体:
        {
            "audio": "<base64_encoded_audio>",
            "avatar": "default_interviewer.png",
            "quality": "high"
        }
        """
        url = f"{self.api_base}/video/generate/from_audio"

        payload = {
            "audio": audio_base64,
            "avatar": avatar_image or self.default_avatar,
            "quality": "high",
            "fps": 25
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"调用 Duix.Avatar API 生成视频, 音频长度: {len(audio_base64)}")

        response = await asyncio.to_thread(
            requests.post,
            url,
            json=payload,
            headers=headers,
            timeout=120
        )

        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> dict:
        """
        解析 API 响应

        成功响应示例:
        {
            "code": 0,
            "message": "success",
            "data": {
                "video_url": "https://cdn.duix.com/videos/xxx.mp4",
                "video_id": "vid_xxx",
                "generation_time": 3.5
            }
        }

        失败响应示例:
        {
            "code": 1001,
            "message": "API Key 无效",
            "data": null
        }
        """
        if response.status_code == 200:
            try:
                result = response.json()

                # 根据实际 API 响应结构调整
                if result.get('code') == 0 or result.get('success'):
                    data = result.get('data', result)
                    video_url = data.get('video_url')

                    logger.info(f"数字人视频生成成功: {video_url}")

                    return {
                        'success': True,
                        'video_url': video_url,
                        'video_id': data.get('video_id'),
                        'generation_time': data.get('generation_time', 0)
                    }
                else:
                    error_msg = result.get('message', 'Unknown error')
                    logger.error(f"Duix.Avatar API 返回错误: {error_msg}")
                    return {
                        'success': False,
                        'error': f"API 错误: {error_msg}"
                    }

            except Exception as e:
                logger.error(f"解析 API 响应失败: {e}")
                return {
                    'success': False,
                    'error': f'响应解析失败: {str(e)}'
                }
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_detail = response.json().get('message', '')
                error_msg += f" - {error_detail}"
            except:
                pass

            logger.error(f"Duix.Avatar API 请求失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

    def health_check(self) -> bool:
        """
        检查 API 可用性

        API 端点示例: GET /health 或 /status
        """
        if not self.enabled:
            return False

        try:
            url = f"{self.api_base}/health"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                return True
            else:
                logger.debug(f"Duix.Avatar API 健康检查失败: {response.status_code}")
                return False

        except Exception as e:
            logger.debug(f"Duix.Avatar API 健康检查异常: {e}")
            return False


# 全局单例
_digital_human_service_api = None


def get_digital_human_service_api() -> DigitalHumanServiceAPI:
    """获取数字人服务实例 (API 版本)"""
    global _digital_human_service_api
    if _digital_human_service_api is None:
        _digital_human_service_api = DigitalHumanServiceAPI()
    return _digital_human_service_api
