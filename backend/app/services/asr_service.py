"""
ASR service adapters.
"""
import base64
import hashlib
import hmac
import logging
import os
import tempfile
from typing import Optional

import openai
import requests

logger = logging.getLogger(__name__)


class ASRService:
    """Base ASR service."""

    def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        raise NotImplementedError


class SiliconFlowASRService(ASRService):
    """SiliconFlow ASR service with empty-result fallback retry."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "FunAudioLLM/SenseVoiceSmall",
        fallback_model: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = (fallback_model or "").strip()
        self.asr_url = f"{self.base_url}/audio/transcriptions"

        logger.info(
            "SiliconFlow ASR initialized: model=%s, fallback_model=%s",
            self.model,
            self.fallback_model or "-",
        )

    def _request_transcription(self, temp_path: str, format: str, model: str) -> tuple[requests.Response, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        with open(temp_path, "rb") as audio_file:
            files = {
                "file": (f"audio.{format}", audio_file, f"audio/{format}")
            }
            data = {
                "model": model
            }
            response = requests.post(
                self.asr_url,
                headers=headers,
                files=files,
                data=data,
                timeout=30,
            )

        trace_id = response.headers.get("x-siliconcloud-trace-id", "")
        return response, trace_id

    def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        temp_path = ""
        try:
            logger.info(
                "Starting ASR transcription: size=%s bytes, format=%s, primary_model=%s, fallback_model=%s",
                len(audio_data),
                format,
                self.model,
                self.fallback_model or "-",
            )

            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            models_to_try = [self.model]
            if self.fallback_model and self.fallback_model != self.model:
                models_to_try.append(self.fallback_model)

            last_error = None
            for model_name in models_to_try:
                response, trace_id = self._request_transcription(temp_path, format, model_name)
                logger.info(
                    "ASR API response: status=%s, model=%s, trace_id=%s",
                    response.status_code,
                    model_name,
                    trace_id or "-",
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(
                        "ASR API returned error: model=%s, trace_id=%s, body=%s",
                        model_name,
                        trace_id or "-",
                        error_msg,
                    )
                    last_error = Exception(f"ASR API 错误: {response.status_code} - {error_msg}")
                    continue

                result = response.json()
                text = (result.get("text", "") or "").strip()

                if text:
                    logger.info(
                        "ASR transcription succeeded: model=%s, trace_id=%s, text_length=%s, preview=%s",
                        model_name,
                        trace_id or "-",
                        len(text),
                        text[:100],
                    )
                    return text

                logger.warning(
                    "ASR returned empty text: model=%s, trace_id=%s, response=%s",
                    model_name,
                    trace_id or "-",
                    result,
                )

            if last_error:
                raise last_error

            return ""

        except Exception as e:
            logger.error("ASR transcription failed: %s", e, exc_info=True)
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)


# 从简化版导入阿里云ASR
from app.services.alibabacloud_asr_simple import AlibabaASRService

class OpenAIASRService(ASRService):
    """OpenAI-compatible ASR service."""

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "whisper-1"):
        self.api_key = api_key
        self.model = model

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = openai.OpenAI(**client_kwargs)
        logger.info("OpenAI ASR initialized: model=%s", model)

    def transcribe(self, audio_data: bytes, format: str = "wav") -> str:
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            with open(temp_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language="zh",
                )

            text = response.text
            logger.info("OpenAI ASR transcription succeeded: text_length=%s", len(text))
            return text

        except Exception as e:
            logger.error("OpenAI ASR transcription failed: %s", e)
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)


_asr_service: Optional[ASRService] = None


def init_asr_service(settings) -> ASRService:
    global _asr_service

    logger.info("=" * 60)
    logger.info("ASR Service Initialization Started")
    logger.info("=" * 60)

    if not getattr(settings, "asr_enabled", True):
        logger.warning("ASR disabled in configuration")
        _asr_service = None
        return None

    api_key = getattr(settings, "asr_api_key", None)
    logger.info(f"ASR API Key: {'***present***' if api_key else '***missing***'}")

    if not api_key:
        logger.error("ASR API key missing, cannot initialize ASR service")
        _asr_service = None
        return None

    base_url = getattr(settings, "asr_base_url", None)
    model = getattr(settings, "asr_model", "whisper-1")
    fallback_model = getattr(settings, "asr_fallback_model", "")

    logger.info(
        "ASR Configuration: model=%s, fallback_model=%s, base_url=%s",
        model,
        fallback_model or "(none)",
        base_url,
    )

    # 检测是否为阿里云ASR（使用nls-gateway端点）
    if "aliyun" in base_url or "nls-gateway" in base_url or "nls-meta" in base_url:
        logger.info("Detected Alibaba Cloud ASR configuration")

        app_key = getattr(settings, "asr_app_key", None)
        token = getattr(settings, "asr_token", None)

        logger.info(f"Alibaba Cloud ASR - app_key: {'***present***' if app_key else '***missing***'}")
        logger.info(f"Alibaba Cloud ASR - token: {'***present***' if token else '***missing***'}")
        logger.info(f"DEBUG - token value: '{token}', type: {type(token)}, len: {len(token) if token else 0}")

        if not app_key:
            logger.error("阿里云ASR需要 app_key（从环境变量 ALIBABA_ASR_APP_KEY 获取）")
            _asr_service = None
            return None

        if not token:
            logger.warning(
                "阿里云ASR未配置 token（从环境变量 ALIBABA_ASR_TOKEN 获取），"
                "请访问 https://nls-portal.console.aliyun.com/ 获取Token"
            )

        logger.info(
            "使用阿里云ASR - 一句话识别API（实时同步）, "
            f"app_key={app_key[:8]}..., token={'***configured***' if token else '***missing***'}"
        )

        try:
            _asr_service = AlibabaASRService(
                api_key="unused",  # 不再使用，保留兼容性
                api_secret="unused",  # 不再使用，保留兼容性
                app_key=app_key,
                base_url=base_url,
                model=model,
                language=getattr(settings, "asr_language", "zh-CN"),
                format=getattr(settings, "asr_format", "wav"),
                sample_rate=getattr(settings, "asr_sample_rate", 16000),
                enable_punctuation=getattr(settings, "asr_enable_punctuation", True),
                enable_inverse_text_normalization=getattr(settings, "asr_enable_inverse_text_normalization", True),
                enable_voice_detection=getattr(settings, "asr_enable_voice_detection", False),
                token=token or "",  # 传入token（如果配置文件中有的话）
            )
            logger.info("ASR Service initialized successfully: type=AlibabaASRService")
            logger.info(f"ASR Service config: sample_rate={getattr(settings, 'asr_sample_rate', 16000)}, "
                       f"format={getattr(settings, 'asr_format', 'wav')}, "
                       f"language={getattr(settings, 'asr_language', 'zh-CN')}")
        except Exception as e:
            logger.error(f"Failed to initialize Alibaba Cloud ASR service: {e}", exc_info=True)
            _asr_service = None
            return None
    elif "siliconflow.cn" in base_url or "api.siliconflow" in base_url:
        _asr_service = SiliconFlowASRService(
            api_key=api_key,
            base_url=base_url,
            model=model,
            fallback_model=fallback_model,
        )
    else:
        _asr_service = OpenAIASRService(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )

    return _asr_service


def get_asr_service() -> Optional[ASRService]:
    """获取ASR服务实例"""
    if _asr_service is None:
        logger.warning("ASR service requested but not initialized")
    else:
        logger.debug(f"ASR service retrieved: {type(_asr_service).__name__}")
    return _asr_service
