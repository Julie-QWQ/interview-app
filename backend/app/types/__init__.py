"""Type definitions package."""

from .ai_types import (
    ChatMessage,
    LLMConfig,
    ChatCompletionOptions,
    InterviewConfig,
    ProgressInfo,
    OrchestratedContext,
)

from .asr_types import (
    ASRResult,
    ASRConfig,
    ASRResponseTuple,
)

from .tts_types import (
    VoiceGender,
    AudioFormat,
    TTSConfig,
    TTSResult,
)

__all__ = [
    # AI types
    "ChatMessage",
    "LLMConfig",
    "ChatCompletionOptions",
    "InterviewConfig",
    "ProgressInfo",
    "OrchestratedContext",
    # ASR types
    "ASRResult",
    "ASRConfig",
    "ASRResponseTuple",
    # TTS types
    "VoiceGender",
    "AudioFormat",
    "TTSConfig",
    "TTSResult",
]
