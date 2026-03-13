"""
TTS (Text-to-Speech) 服务
使用 Edge-TTS 将文本转换为语音

支持输出格式:
- MP3 (base64) - 用于浏览器播放
- PCM (raw bytes) - 用于阿里云 Avatar Dialog
"""
import edge_tts
import asyncio
import base64
import re
import io
from typing import Optional, List, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class TTSService:
    """Edge-TTS 语音合成服务"""

    # 可用的中文音色
    VOICES = {
        'female': 'zh-CN-XiaoxiaoNeural',  # 女声(默认)
        'male': 'zh-CN-YunyangNeural',      # 男声
    }

    def __init__(self, voice: Optional[str] = None):
        """
        初始化 TTS 服务

        Args:
            voice: 音色名称,默认为女声
        """
        configured_voice = voice
        if configured_voice is None:
            try:
                from config.settings import settings
                configured_voice = settings.get('voice.tts_voice', 'male')
            except Exception:
                configured_voice = 'male'

        self.voice = self.VOICES.get(configured_voice, configured_voice)

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

    def batch_text_to_speech(self, texts: List[str], voice: Optional[str] = None) -> List[Optional[str]]:
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

    async def text_to_pcm_async(self, text: str, voice: Optional[str] = None,
                                sample_rate: int = 16000) -> bytes:
        """
        异步文本转 PCM 音频

        Args:
            text: 要转换的文本
            voice: 音色,不指定则使用默认音色
            sample_rate: 采样率 (16000, 24000, 32000, 48000)

        Returns:
            PCM 格式的音频数据 (16bit, 单声道)

        Raises:
            Exception: TTS 生成失败时抛出异常
        """
        voice = voice or self.voice

        try:
            # 使用 Edge-TTS 生成音频
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b''

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            # 将 MP3 转换为 PCM
            pcm_data = await self._convert_mp3_to_pcm(audio_data, sample_rate)
            logger.info(f"TTS PCM 生成成功,文本长度: {len(text)}, PCM 大小: {len(pcm_data)} bytes")
            return pcm_data

        except Exception as e:
            logger.error(f"TTS PCM 生成失败: {str(e)}")
            raise

    def text_to_pcm(self, text: str, voice: Optional[str] = None,
                    sample_rate: int = 16000) -> bytes:
        """
        同步文本转 PCM 音频

        Args:
            text: 要转换的文本
            voice: 音色,不指定则使用默认音色
            sample_rate: 采样率

        Returns:
            PCM 格式的音频数据
        """
        try:
            return asyncio.run(self.text_to_pcm_async(text, voice, sample_rate))
        except Exception as e:
            logger.error(f"TTS PCM 同步调用失败: {str(e)}")
            raise

    async def _convert_mp3_to_pcm(self, mp3_data: bytes, sample_rate: int = 16000) -> bytes:
        """
        将 MP3 音频转换为 PCM 格式

        Args:
            mp3_data: MP3 音频数据
            sample_rate: 目标采样率

        Returns:
            PCM 音频数据 (16bit, 单声道)
        """
        try:
            # 尝试使用 pydub 进行转换
            from pydub import AudioSegment

            # 从 MP3 数据加载音频
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))

            # 转换为目标格式: 16kHz, 单声道, 16bit
            audio = audio.set_frame_rate(sample_rate)
            audio = audio.set_channels(1)
            audio = audio.set_sample_width(2)  # 16bit = 2 bytes

            # 导出为 PCM
            pcm_data = audio.raw_data
            return pcm_data

        except ImportError:
            # 如果没有 pydub,尝试使用 ffmpeg
            logger.warning("pydub 未安装,尝试使用 ffmpeg 进行音频转换")
            return await self._convert_mp3_to_pcm_ffmpeg(mp3_data, sample_rate)

        except Exception as e:
            logger.error(f"音频转换失败: {str(e)}")
            raise

    async def _convert_mp3_to_pcm_ffmpeg(self, mp3_data: bytes, sample_rate: int = 16000) -> bytes:
        """
        使用 ffmpeg 将 MP3 转换为 PCM

        Args:
            mp3_data: MP3 音频数据
            sample_rate: 目标采样率

        Returns:
            PCM 音频数据
        """
        import subprocess

        try:
            # 使用 ffmpeg 进行转换
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', 'pipe:0',  # 从 stdin 读取 MP3
                '-f', 's16le',   # PCM 16bit 小端
                '-acodec', 'pcm_s16le',
                '-ar', str(sample_rate),  # 采样率
                '-ac', '1',      # 单声道
                'pipe:1'         # 输出到 stdout
            ]

            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 发送 MP3 数据并获取 PCM 数据
            pcm_data, stderr = await process.communicate(input=mp3_data)

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise Exception(f"ffmpeg 转换失败: {error_msg}")

            return pcm_data

        except FileNotFoundError:
            raise Exception("ffmpeg 未安装,无法进行音频转换。请安装 ffmpeg 或 pydub")

        except Exception as e:
            logger.error(f"ffmpeg 转换失败: {str(e)}")
            raise


# 全局 TTS 服务实例
_tts_service = None


def get_tts_service() -> TTSService:
    """获取全局 TTS 服务实例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
