"""
TTS (Text-to-Speech) 服务
使用 Edge-TTS 将文本转换为语音
"""
import edge_tts
import asyncio
import base64
import re
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class TTSService:
    """Edge-TTS 语音合成服务"""

    # 可用的中文音色
    VOICES = {
        'female': 'zh-CN-XiaoxiaoNeural',  # 女声(默认)
        'male': 'zh-CN-YunyangNeural',      # 男声
    }

    def __init__(self, voice: str = None):
        """
        初始化 TTS 服务

        Args:
            voice: 音色名称,默认为女声
        """
        self.voice = voice or self.VOICES['female']

    async def text_to_speech_async(self, text: str, voice: Optional[str] = None) -> str:
        """
        异步文本转语音,返回 base64 编码的音频

        Args:
            text: 要转换的文本
            voice: 音色,不指定则使用默认音色

        Returns:
            base64 编码的音频数据

        Raises:
            Exception: TTS 生成失败时抛出异常
        """
        voice = voice or self.voice

        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b''

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            # 转换为 base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            logger.info(f"TTS 生成成功,文本长度: {len(text)}, 音频大小: {len(audio_data)} bytes")
            return audio_base64

        except Exception as e:
            logger.error(f"TTS 生成失败: {str(e)}")
            raise

    def text_to_speech(self, text: str, voice: Optional[str] = None) -> str:
        """
        同步文本转语音

        Args:
            text: 要转换的文本
            voice: 音色,不指定则使用默认音色

        Returns:
            base64 编码的音频数据
        """
        try:
            return asyncio.run(self.text_to_speech_async(text, voice))
        except Exception as e:
            logger.error(f"TTS 同步调用失败: {str(e)}")
            raise

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """
        将文本分割成句子

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        # 中文句子分隔符
        separators = ['。', '！', '？', '；', '\n', '.', '!', '?', ';']

        # 首先按换行符分割
        lines = text.split('\n')
        sentences = []

        for line in lines:
            if not line.strip():
                continue

            # 按分隔符分割
            current = ""
            for char in line:
                current += char
                if char in separators:
                    if current.strip():
                        sentences.append(current.strip())
                    current = ""

            # 添加剩余内容
            if current.strip():
                sentences.append(current.strip())

        return sentences

    def batch_text_to_speech(self, texts: List[str], voice: Optional[str] = None) -> List[str]:
        """
        批量文本转语音

        Args:
            texts: 文本列表
            voice: 音色

        Returns:
            base64 编码的音频数据列表
        """
        results = []
        for text in texts:
            try:
                audio = self.text_to_speech(text, voice)
                results.append(audio)
            except Exception as e:
                logger.error(f"批量 TTS 失败: {str(e)}")
                results.append(None)  # 失败时返回 None
        return results


# 全局 TTS 服务实例
_tts_service = None


def get_tts_service() -> TTSService:
    """获取全局 TTS 服务实例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
