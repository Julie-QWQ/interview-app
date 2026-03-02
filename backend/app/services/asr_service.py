"""
ASR (自动语音识别) 服务
支持多种 ASR 提供商
"""
import logging
import os
import tempfile
from typing import Optional, Callable
import requests
import openai

logger = logging.getLogger(__name__)


class ASRService:
    """ASR 服务基类"""

    def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """转录音频为文本"""
        raise NotImplementedError


class SiliconFlowASRService(ASRService):
    """使用 SiliconFlow API 进行语音识别"""

    def __init__(self, api_key: str, base_url: str = "https://api.siliconflow.cn/v1", model: str = "FunAudioLLM/SenseVoiceSmall"):
        """
        初始化 SiliconFlow ASR 服务

        Args:
            api_key: SiliconFlow API 密钥
            base_url: API 基础 URL
            model: ASR 模型名称 (默认 FunAudioLLM/SenseVoiceSmall)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model

        # SiliconFlow ASR API 端点
        self.asr_url = f"{self.base_url}/audio/transcriptions"

        logger.info(f"SiliconFlow ASR 服务初始化成功, model={model}")

    def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """
        转录音频为文本

        Args:
            audio_data: 音频数据(字节)
            format: 音频格式 (wav, mp3, etc.)

        Returns:
            识别出的文本
        """
        try:
            logger.info(f"开始 ASR 识别, 音频大小: {len(audio_data)} bytes, 格式: {format}, 模型: {self.model}")

            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                suffix=f".{format}",
                delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            logger.debug(f"临时文件: {temp_path}")

            # 准备请求 - SiliconFlow 使用 OpenAI 兼容格式
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            # 打开音频文件
            with open(temp_path, "rb") as audio_file:
                files = {
                    "file": (f"audio.{format}", audio_file, f"audio/{format}")
                }

                data = {
                    "model": self.model  # 使用配置的模型
                }

                logger.debug(f"发送请求到: {self.asr_url}")
                logger.debug(f"模型: {self.model}")

                # 发送请求
                response = requests.post(
                    self.asr_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=30
                )

            # 清理临时文件
            os.remove(temp_path)

            logger.info(f"API 响应状态码: {response.status_code}")

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"ASR API 返回错误: {error_msg}")
                raise Exception(f"ASR API 错误: {response.status_code} - {error_msg}")

            result = response.json()
            logger.debug(f"解析后的 JSON: {result}")

            # SiliconFlow 的响应格式 (兼容 OpenAI)
            text = result.get("text", "")

            if not text:
                logger.warning("API 返回的 text 字段为空")
                logger.warning(f"完整响应: {result}")
            else:
                logger.info(f"ASR 识别成功, 文本长度: {len(text)}, 内容: {text[:100]}...")

            return text

        except Exception as e:
            logger.error(f"ASR 识别失败: {e}", exc_info=True)
            raise


class OpenAIASRService(ASRService):
    """使用 OpenAI Whisper API 进行语音识别"""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "whisper-1"):
        """
        初始化 OpenAI ASR 服务

        Args:
            api_key: OpenAI API 密钥
            base_url: API 基础 URL (用于兼容其他服务)
            model: 模型名称 (默认 whisper-1)
        """
        self.api_key = api_key
        self.model = model

        # 配置 OpenAI 客户端
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = openai.OpenAI(**client_kwargs)
        logger.info(f"OpenAI ASR 服务初始化成功, model={model}")

    def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        """
        转录音频为文本

        Args:
            audio_data: 音频数据(字节)
            format: 音频格式 (wav, mp3, etc.)

        Returns:
            识别出的文本
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                suffix=f".{format}",
                delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            # 打开音频文件
            with open(temp_path, "rb") as audio_file:
                # 调用 Whisper API
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="zh"  # 中文
                )

                text = response.text
                logger.info(f"ASR 识别成功, 文本长度: {len(text)}")
                return text

        except Exception as e:
            logger.error(f"ASR 识别失败: {e}")
            raise
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)


# 全局 ASR 服务实例
_asr_service: Optional[ASRService] = None


def init_asr_service(settings) -> ASRService:
    """
    初始化 ASR 服务

    Args:
        settings: Settings 配置对象 (来自 config.settings)
    """
    global _asr_service

    # 检查是否启用 ASR
    if not getattr(settings, 'asr_enabled', True):
        logger.info("ASR 功能已禁用")
        _asr_service = None
        return None

    # 从配置对象获取 ASR 配置
    api_key = getattr(settings, 'asr_api_key', None)
    if not api_key:
        logger.warning("未配置 API 密钥,ASR 功能将不可用")
        _asr_service = None
        return None

    base_url = getattr(settings, 'asr_base_url', None)
    model = getattr(settings, 'asr_model', 'whisper-1')

    logger.info(f"初始化 ASR 服务: model={model}, base_url={base_url}")

    # 根据 base_url 自动选择服务类型
    if 'siliconflow.cn' in base_url or 'api.siliconflow' in base_url:
        # 使用 SiliconFlow ASR 服务
        _asr_service = SiliconFlowASRService(
            api_key=api_key,
            base_url=base_url,
            model=model  # 传递模型名称
        )
    else:
        # 使用 OpenAI 兼容的 ASR 服务
        _asr_service = OpenAIASRService(
            api_key=api_key,
            base_url=base_url,
            model=model
        )

    return _asr_service


def get_asr_service() -> Optional[ASRService]:
    """获取 ASR 服务实例"""
    return _asr_service
