"""Type definitions for TTS service."""

from typing import Optional, Union
from dataclasses import dataclass
from enum import Enum


class VoiceGender(str, Enum):
    """Voice gender options."""
    MALE = "Male"
    FEMALE = "Female"


class AudioFormat(str, Enum):
    """Audio format options."""
    MP3 = "mp3"
    PCM = "pcm"


@dataclass
class TTSConfig:
    """TTS service configuration."""
    voice_gender: VoiceGender
    language: str
    sample_rate: int = 24000
    format: AudioFormat = AudioFormat.MP3


@dataclass
class TTSResult:
    """TTS synthesis result."""
    audio_data: bytes
    format: AudioFormat
    duration_ms: int
    voice_used: str
