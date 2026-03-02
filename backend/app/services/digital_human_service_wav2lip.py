"""
数字人服务封装 - Wav2Lip 轻量级版本
集成 Wav2Lip 实现音频驱动的唇形同步

硬件要求:
- GPU: GTX 1060 (6GB) 或更高
- 内存: 8GB+
- 硬盘: 20GB

优势:
- 轻量级部署,适合个人开发者
- 唇形同步精准
- 推理速度快 (2-5秒)
"""
import requests
import asyncio
import logging
import os
import base64
from typing import Optional

logger = logging.getLogger(__name__)


class DigitalHumanServiceWav2Lip:
    """数字人服务类 - Wav2Lip 轻量级版本"""

    def __init__(self):
        # Wav2Lip 服务地址 (本地部署)
        self.wav2lip_url = os.getenv('WAV2LIP_URL', 'http://localhost:8080')

        # 默认头像
        self.default_avatar = os.getenv(
            'DEFAULT_AVATAR',
            'assets/avatar/default-interviewer.png'
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
        使用 Wav2Lip 生成说话头像视频

        Args:
            audio_base64: base64编码的音频数据
            avatar_image: 数字人形象图片路径(可选)
            text: 原始文本(此参数 Wav2Lip 不支持,仅保持接口兼容)

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
                'error': '数字人功能未启用'
            }

        if not self.health_check():
            return {
                'success': False,
                'error': 'Wav2Lip 服务不可用'
            }

        try:
            return await self._generate_from_audio(audio_base64, avatar_image)

        except Exception as e:
            error_msg = f"Wav2Lip 服务异常: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    async def _generate_from_audio(
        self,
        audio_base64: str,
        avatar_image: Optional[str] = None
    ) -> dict:
        """
        调用 Wav2Lip API 生成视频

        API 端点: POST /generate
        请求体:
        {
            "audio": "<base64_encoded_audio>",
            "face": "<base64_encoded_image>",
            "fps": 25
        }
        """
        url = f"{self.wav2lip_url}/generate"

        # 准备请求数据
        payload = {
            "audio": audio_base64,
            "face": avatar_image or self.default_avatar,
            "fps": 25,
            "quality": "good"  # fast/good/better
        }

        logger.info(f"调用 Wav2Lip API 生成视频, 音频长度: {len(audio_base64)}")

        response = await asyncio.to_thread(
            requests.post,
            url,
            json=payload,
            timeout=30  # Wav2Lip 比较快,30秒足够
        )

        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> dict:
        """
        解析 Wav2Lip API 响应

        成功响应:
        {
            "success": true,
            "video_url": "/videos/output.mp4",
            "generation_time": 2.5
        }

        失败响应:
        {
            "success": false,
            "error": "错误信息"
        }
        """
        if response.status_code == 200:
            try:
                result = response.json()

                if result.get('success'):
                    video_url = result.get('video_url')

                    # 如果是相对路径,转换为完整 URL
                    if video_url and not video_url.startswith('http'):
                        video_url = f"{self.wav2lip_url}{video_url}"

                    logger.info(f"Wav2Lip 视频生成成功: {video_url}")

                    return {
                        'success': True,
                        'video_url': video_url,
                        'generation_time': result.get('generation_time', 0)
                    }
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Wav2Lip API 返回错误: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg
                    }

            except Exception as e:
                logger.error(f"解析 Wav2Lip 响应失败: {e}")
                return {
                    'success': False,
                    'error': f'响应解析失败: {str(e)}'
                }
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_detail = response.json().get('error', '')
                error_msg += f" - {error_detail}"
            except:
                pass

            logger.error(f"Wav2Lip API 请求失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

    def health_check(self) -> bool:
        """
        检查 Wav2Lip 服务健康状态

        端点: GET /health
        """
        if not self.enabled:
            return False

        try:
            response = requests.get(
                f"{self.wav2lip_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Wav2Lip 健康检查失败: {e}")
            return False


# 全局单例
_wav2lip_service = None


def get_digital_human_service_wav2lip() -> DigitalHumanServiceWav2Lip:
    """获取数字人服务实例 (Wav2Lip 版本)"""
    global _wav2lip_service
    if _wav2lip_service is None:
        _wav2lip_service = DigitalHumanServiceWav2Lip()
    return _wav2lip_service
