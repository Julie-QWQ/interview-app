"""Type definitions for ASR service."""

from typing import Tuple, Optional
from dataclasses import dataclass
import requests


@dataclass
class ASRResult:
    """ASR transcription result."""
    text: str
    model_used: str
    trace_id: str
    is_fallback: bool = False
    latency_ms: int = 0


@dataclass
class ASRConfig:
    """ASR service configuration."""
    api_key: str
    base_url: str
    model: str
    fallback_model: str = ""
    timeout: int = 30


ASRResponseTuple = Tuple[requests.Response, str]
