"""Type definitions for AI service."""

from typing import Dict, List, Optional, Any, Iterator, Union
from typing_extensions import TypedDict
from dataclasses import dataclass


class ChatMessage(TypedDict):
    """Chat message structure."""
    role: str
    content: str


class LLMConfig(TypedDict):
    """LLM runtime configuration."""
    model_override: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    context_messages: int


class ChatCompletionOptions(TypedDict, total=False):
    """Options for chat completion."""
    model: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float
    trace_id: Optional[str]
    tool_context: Optional[Dict[str, Any]]
    tool_observations: Optional[List[Dict[str, Any]]]
    prefetch_tasks: Optional[List[Dict[str, Any]]]


@dataclass
class InterviewConfig:
    """Interview configuration."""
    id: Optional[int]
    candidate_name: Optional[str]
    position: Optional[str]
    experience_level: Optional[str]
    skill_domain: Optional[str]
    skills: Optional[List[str]]
    additional_requirements: Optional[str]
    resume_text: Optional[str]
    resume_file_id: Optional[str]
    duration_minutes: int


@dataclass
class ProgressInfo:
    """Interview progress information."""
    current_stage: str
    stage_name: str
    overall_turn: int
    stage_turn: int
    estimated_total_turns: int
    stage_max_turns: int
    time_elapsed_minutes: float
    time_remaining_minutes: float
    progress_percentage: float


class ToolContextBlock(TypedDict):
    """Tool context block."""
    tool_name: str
    summary: str
    prompt_context: str
    structured_payload: Dict[str, Any]


@dataclass
class OrchestratedContext:
    """Orchestrated tool context."""
    trace_id: str
    tool_context_blocks: Dict[str, str]
    tool_context_combined: str
    tool_structured_context: Dict[str, Any]
    tool_observations: List[Dict[str, Any]]
    prefetch_tasks: List[Dict[str, Any]]
    tool_summary: str
    tool_constraints: List[str]
