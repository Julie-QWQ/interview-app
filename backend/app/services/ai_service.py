"""AI conversation service."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterator, Union

import openai
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from app.models.interview_stage import InterviewProgress, stage_config_from_model
from app.services.interview_orchestrator import ToolExecutionContext, get_interview_orchestrator
from app.services.prompt_service import prompt_service
from app.types.ai_types import (
    ChatMessage,
    LLMConfig,
    ChatCompletionOptions,
    InterviewConfig,
    ProgressInfo,
    OrchestratedContext,
)

logger = logging.getLogger(__name__)

# 类型别名
MessageDict = Dict[str, str]
MessagesList = List[MessageDict]
LlmResponse = str
LlmStreamResponse = Iterator[ChatCompletionChunk]


class AIService:
    """AI conversation service."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.prompts_log_path: Path = Path(__file__).resolve().parents[2] / "logs" / "prompts.log"
        self.client: openai.OpenAI = openai.OpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
        )

    def _log_prompt_payload(
        self,
        request_type: str,
        model: str,
        messages: MessagesList,
        **kwargs: Any,
    ) -> None:
        """Append prompt payload to backend/logs/prompts.log before sending to LLM."""
        try:
            self.prompts_log_path.parent.mkdir(parents=True, exist_ok=True)
            payload: Dict[str, Any] = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "request_type": request_type,
                "trace_id": kwargs.pop("trace_id", None),
                "model": model,
                "messages": messages,
                "params": kwargs,
            }
            with open(self.prompts_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False))
                fh.write("\n")
        except Exception as log_error:
            logger.warning("Failed to write prompts.log: %s", log_error)

    def _get_llm_runtime_config(self) -> Dict[str, Any]:
        """Load runtime LLM config from prompt settings."""
        try:
            return prompt_service.get_llm_config() or {}
        except Exception as exc:
            logger.warning("Failed to load LLM runtime config, fallback to defaults: %s", exc)
            return {}

    def _build_progress_manager(self, interview_config: Dict[str, Any]) -> InterviewProgress:
        stage_models = prompt_service.get_stage_configs()
        runtime_stages = [stage_config_from_model(stage) for stage in stage_models]
        return InterviewProgress(runtime_stages, interview_config.get("duration_minutes", 30))

    def _prepare_llm_call_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trace_id": kwargs.get("trace_id"),
            "tool_context": kwargs.get("tool_context") or {},
            "tool_observations": kwargs.get("tool_observations") or [],
            "prefetch_tasks": kwargs.get("prefetch_tasks") or [],
        }

    def _build_orchestration_context(
        self,
        *,
        interview_config: dict,
        conversation_history: List[dict],
        stage: str,
        trigger: str,
        progress_info: Dict,
        trace_id: str,
    ) -> ToolExecutionContext:
        latest_user_message = ""
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                latest_user_message = msg.get("content") or ""
                break

        return ToolExecutionContext(
            trace_id=trace_id,
            interview_id=int(interview_config.get("id") or 0),
            stage=stage,
            trigger=trigger,
            interview_config=interview_config,
            conversation_slice=conversation_history[-12:],
            resume_text=interview_config.get("resume_text"),
            current_user_message=latest_user_message or None,
            progress_info=progress_info,
        )

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """Send non-streaming chat completion request."""
        try:
            llm_config = self._get_llm_runtime_config()
            model_override = llm_config.get("model_override") or ""

            model = kwargs.get("model") or model_override or self.settings.ai_model
            temperature = kwargs.get("temperature", llm_config.get("temperature", self.settings.ai_temperature))
            max_tokens = kwargs.get("max_tokens", llm_config.get("max_tokens", 2000))
            top_p = kwargs.get("top_p", llm_config.get("top_p", 1.0))
            frequency_penalty = kwargs.get("frequency_penalty", llm_config.get("frequency_penalty", 0.0))
            presence_penalty = kwargs.get("presence_penalty", llm_config.get("presence_penalty", 0.0))

            self._log_prompt_payload(
                request_type="chat_completion",
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=False,
                **self._prepare_llm_call_kwargs(kwargs),
            )

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("AI request failed: %s", exc)
            raise

    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        """Send streaming chat completion request."""
        try:
            llm_config = self._get_llm_runtime_config()
            model_override = llm_config.get("model_override") or ""

            model = kwargs.get("model") or model_override or self.settings.ai_model
            temperature = kwargs.get("temperature", llm_config.get("temperature", self.settings.ai_temperature))
            max_tokens = kwargs.get("max_tokens", llm_config.get("max_tokens", 2000))
            top_p = kwargs.get("top_p", llm_config.get("top_p", 1.0))
            frequency_penalty = kwargs.get("frequency_penalty", llm_config.get("frequency_penalty", 0.0))
            presence_penalty = kwargs.get("presence_penalty", llm_config.get("presence_penalty", 0.0))

            self._log_prompt_payload(
                request_type="chat_completion_stream",
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=True,
                **self._prepare_llm_call_kwargs(kwargs),
            )

            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            logger.error("AI streaming request failed: %s", exc)
            raise

    def start_interview(
        self,
        interview_config: Dict[str, Any],
        *,
        trace_id: Optional[str] = None,
    ) -> str:
        """Start interview and get opening question."""
        progress_manager = self._build_progress_manager(interview_config)
        first_stage = progress_manager.get_first_stage()
        stage_config = progress_manager.get_stage_info(first_stage)
        progress_info = progress_manager.calculate_progress(0, first_stage)
        trace_id = trace_id or get_interview_orchestrator().new_trace_id()

        orchestration_context = self._build_orchestration_context(
            interview_config=interview_config,
            conversation_history=[],
            stage=first_stage,
            trigger="interview_start",
            progress_info=progress_info,
            trace_id=trace_id,
        )
        tool_context = get_interview_orchestrator().orchestrate(orchestration_context)

        system_prompt = (
            prompt_service.create_interviewer_prompt_builder(interview_config)
            .with_stage_instruction(stage_config.system_instruction)
            .with_progress(progress_info, current_turn=0)
            .with_tool_context(
                tool_context.tool_context_blocks,
                summary=tool_context.tool_summary,
                constraints=tool_context.tool_constraints,
                combined=tool_context.tool_context_combined,
            )
            .build()
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始面试，先做自我介绍并提出第一个问题。"},
        ]
        return self.chat_completion(
            messages,
            trace_id=trace_id,
            tool_context=tool_context.tool_context_blocks,
            tool_observations=tool_context.tool_observations,
            prefetch_tasks=tool_context.prefetch_tasks,
        )

    def continue_interview(
        self,
        interview_config: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        current_stage: Optional[str] = None,
        *,
        previous_stage: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> str:
        """Continue interview with stage-aware orchestration."""
        progress_manager = self._build_progress_manager(interview_config)
        current_turn = len([msg for msg in conversation_history if msg["role"] == "assistant"])
        stage = current_stage or progress_manager.determine_stage(current_turn)
        stage_config = progress_manager.get_stage_info(stage)
        progress_info = progress_manager.calculate_progress(current_turn, stage)
        trace_id = trace_id or get_interview_orchestrator().new_trace_id()
        trigger = "stage_enter" if previous_stage and previous_stage != stage else "user_turn"

        orchestration_context = self._build_orchestration_context(
            interview_config=interview_config,
            conversation_history=conversation_history,
            stage=stage,
            trigger=trigger,
            progress_info=progress_info,
            trace_id=trace_id,
        )
        tool_context = get_interview_orchestrator().orchestrate(orchestration_context)

        system_prompt = (
            prompt_service.create_interviewer_prompt_builder(interview_config)
            .with_stage_instruction(stage_config.system_instruction)
            .with_progress(progress_info, current_turn=current_turn)
            .with_tool_context(
                tool_context.tool_context_blocks,
                summary=tool_context.tool_summary,
                constraints=tool_context.tool_constraints,
                combined=tool_context.tool_context_combined,
            )
            .build()
        )

        messages = [{"role": "system", "content": system_prompt}]
        llm_config = self._get_llm_runtime_config()
        context_messages = max(1, int(llm_config.get("context_messages", 20)))
        for msg in conversation_history[-context_messages:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        return self.chat_completion(
            messages,
            trace_id=trace_id,
            tool_context=tool_context.tool_context_blocks,
            tool_observations=tool_context.tool_observations,
            prefetch_tasks=tool_context.prefetch_tasks,
        )

    def continue_interview_stream(
        self,
        interview_config: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        current_stage: Optional[str] = None,
        *,
        previous_stage: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Iterator[str]:
        """Continue interview with stage-aware orchestration (streaming)."""
        progress_manager = self._build_progress_manager(interview_config)
        current_turn = len([msg for msg in conversation_history if msg["role"] == "assistant"])
        stage = current_stage or progress_manager.determine_stage(current_turn)
        stage_config = progress_manager.get_stage_info(stage)
        progress_info = progress_manager.calculate_progress(current_turn, stage)
        trace_id = trace_id or get_interview_orchestrator().new_trace_id()
        trigger = "stage_enter" if previous_stage and previous_stage != stage else "user_turn"

        orchestration_context = self._build_orchestration_context(
            interview_config=interview_config,
            conversation_history=conversation_history,
            stage=stage,
            trigger=trigger,
            progress_info=progress_info,
            trace_id=trace_id,
        )
        tool_context = get_interview_orchestrator().orchestrate(orchestration_context)

        system_prompt = (
            prompt_service.create_interviewer_prompt_builder(interview_config)
            .with_stage_instruction(stage_config.system_instruction)
            .with_progress(progress_info, current_turn=current_turn)
            .with_tool_context(
                tool_context.tool_context_blocks,
                summary=tool_context.tool_summary,
                constraints=tool_context.tool_constraints,
                combined=tool_context.tool_context_combined,
            )
            .build()
        )

        messages = [{"role": "system", "content": system_prompt}]
        llm_config = self._get_llm_runtime_config()
        context_messages = max(1, int(llm_config.get("context_messages", 20)))
        for msg in conversation_history[-context_messages:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        yield from self.chat_completion_stream(
            messages,
            trace_id=trace_id,
            tool_context=tool_context.tool_context_blocks,
            tool_observations=tool_context.tool_observations,
            prefetch_tasks=tool_context.prefetch_tasks,
        )

    def determine_current_stage(
        self,
        interview_config: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        duration_minutes: int = 30,
    ) -> str:
        """Determine current interview stage from conversation history."""
        progress_manager = self._build_progress_manager(
            {"duration_minutes": duration_minutes, **(interview_config or {})}
        )
        current_turn = len([msg for msg in conversation_history if msg["role"] == "assistant"])
        return progress_manager.determine_stage(current_turn)

    def get_interview_progress(
        self,
        conversation_history: List[Dict[str, Any]],
        current_stage: str,
        duration_minutes: int = 30,
        interview_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get interview progress summary."""
        progress_manager = self._build_progress_manager(
            {"duration_minutes": duration_minutes, **(interview_config or {})}
        )
        current_turn = len([msg for msg in conversation_history if msg["role"] == "assistant"])
        return progress_manager.calculate_progress(current_turn, current_stage)






_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get global AI service instance."""
    if _ai_service is None:
        raise RuntimeError("AI service not initialized")
    return _ai_service


def init_ai_service(settings):
    """Initialize global AI service instance."""
    global _ai_service
    _ai_service = AIService(settings)

