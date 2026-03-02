"""
AI conversation service.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import openai

from .prompt_service import prompt_service
from app.models.interview_stage import InterviewProgress, stage_config_from_model

logger = logging.getLogger(__name__)


class AIService:
    """AI conversation service."""

    def __init__(self, settings):
        self.settings = settings
        self.prompts_log_path = Path(__file__).resolve().parents[2] / "logs" / "prompts.log"
        self.client = openai.OpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
        )

    def _log_prompt_payload(self, request_type: str, model: str, messages: List[Dict[str, str]], **kwargs):
        """Append prompt payload to backend/logs/prompts.log before sending to LLM."""
        try:
            self.prompts_log_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "request_type": request_type,
                "model": model,
                "messages": messages,
                "params": kwargs,
            }
            with open(self.prompts_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False))
                f.write("\n")
        except Exception as log_error:
            logger.warning(f"Failed to write prompts.log: {log_error}")

    def _get_llm_runtime_config(self) -> Dict:
        """Load runtime LLM config from prompt settings."""
        try:
            return prompt_service.get_llm_config() or {}
        except Exception as e:
            logger.warning(f"Failed to load LLM runtime config, fallback to defaults: {e}")
            return {}

    def _build_progress_manager(self, interview_config: dict) -> InterviewProgress:
        stage_models = prompt_service.get_stage_configs()
        runtime_stages = [stage_config_from_model(s) for s in stage_models]
        return InterviewProgress(runtime_stages, interview_config.get("duration_minutes", 30))

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
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
        except Exception as e:
            logger.error(f"AI request failed: {e}")
            raise

    def chat_completion_stream(self, messages: List[Dict[str, str]], **kwargs):
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

        except Exception as e:
            logger.error(f"AI streaming request failed: {e}")
            raise

    def start_interview(self, interview_config: dict) -> str:
        """Start interview and get opening question."""
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)
        progress_manager = self._build_progress_manager(interview_config)
        first_stage = progress_manager.get_first_stage()
        stage_config = progress_manager.get_stage_info(first_stage)
        system_prompt += f"\n\n{stage_config.system_instruction}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始面试，先做自我介绍并提出第一个问题。"},
        ]

        return self.chat_completion(messages)

    def continue_interview(self, interview_config: dict, conversation_history: List[dict], current_stage: str = None) -> str:
        """Continue interview with stage awareness."""
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)

        progress_manager = self._build_progress_manager(interview_config)
        current_turn = len([m for m in conversation_history if m["role"] == "assistant"])

        if current_stage:
            stage = current_stage
        else:
            stage = progress_manager.determine_stage(current_turn)

        stage_config = progress_manager.get_stage_info(stage)
        system_prompt += f"\n\n{stage_config.system_instruction}"

        progress_info = progress_manager.calculate_progress(current_turn, stage)
        system_prompt += f"""

【面试进度信息】
- 当前阶段：{progress_info['stage_name']}（第 {current_turn} 轮对话）
- 本阶段进度：{progress_info['turn_in_stage']}/{progress_info['stage_max_turns']} 问题
- 总体进度：{progress_info['overall_progress']}%
- 剩余轮次：约 {progress_info['remaining_turns']} 轮

请根据进度合理控制节奏和内容深度。"""

        messages = [{"role": "system", "content": system_prompt}]
        llm_config = self._get_llm_runtime_config()
        context_messages = max(1, int(llm_config.get("context_messages", 20)))

        for msg in conversation_history[-context_messages:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        return self.chat_completion(messages)

    def continue_interview_stream(
        self,
        interview_config: dict,
        conversation_history: List[dict],
        current_stage: str = None,
    ):
        """Continue interview with stage awareness (streaming)."""
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)

        progress_manager = self._build_progress_manager(interview_config)
        current_turn = len([m for m in conversation_history if m["role"] == "assistant"])

        if current_stage:
            stage = current_stage
        else:
            stage = progress_manager.determine_stage(current_turn)

        stage_config = progress_manager.get_stage_info(stage)
        system_prompt += f"\n\n{stage_config.system_instruction}"

        progress_info = progress_manager.calculate_progress(current_turn, stage)
        system_prompt += f"""

【面试进度信息】
- 当前阶段：{progress_info['stage_name']}（第 {current_turn} 轮对话）
- 本阶段进度：{progress_info['turn_in_stage']}/{progress_info['stage_max_turns']} 问题
- 总体进度：{progress_info['overall_progress']}%
- 剩余轮次：约 {progress_info['remaining_turns']} 轮

请根据进度合理控制节奏和内容深度。"""

        messages = [{"role": "system", "content": system_prompt}]
        llm_config = self._get_llm_runtime_config()
        context_messages = max(1, int(llm_config.get("context_messages", 20)))

        for msg in conversation_history[-context_messages:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        yield from self.chat_completion_stream(messages)

    def determine_current_stage(self, interview_config: dict, conversation_history: List[dict], duration_minutes: int = 30) -> str:
        """Determine current interview stage from conversation history."""
        progress_manager = self._build_progress_manager(
            {"duration_minutes": duration_minutes, **(interview_config or {})}
        )
        current_turn = len([m for m in conversation_history if m["role"] == "assistant"])
        return progress_manager.determine_stage(current_turn)

    def get_interview_progress(
        self,
        conversation_history: List[dict],
        current_stage: str,
        duration_minutes: int = 30,
        interview_config: dict = None,
    ) -> dict:
        """Get interview progress summary."""
        progress_manager = self._build_progress_manager(
            {"duration_minutes": duration_minutes, **(interview_config or {})}
        )
        current_turn = len([m for m in conversation_history if m["role"] == "assistant"])
        return progress_manager.calculate_progress(current_turn, current_stage)

    def evaluate_interview(self, interview_config: dict, conversation_history: List[dict]) -> dict:
        """Evaluate interview performance."""
        system_prompt = prompt_service.get_evaluator_system_prompt()

        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])

        user_prompt = f"""
        请根据以下面试对话内容，评估候选人的表现。

        面试配置：
        - 职位：{interview_config.get('position')}
        - 技能：{', '.join(interview_config.get('skills', []))}
        - 经验级别：{interview_config.get('experience_level', '中级')}

        面试对话：
        {conversation_text}

        请按照系统提示中的格式返回 JSON 格式的评估报告。
        """

        try:
            llm_config = self._get_llm_runtime_config()
            model = (llm_config.get("model_override") or "").strip() or self.settings.ai_model
            eval_temperature = llm_config.get("evaluation_temperature", 0.3)
            max_tokens = llm_config.get("max_tokens", 2000)
            top_p = llm_config.get("top_p", 1.0)
            frequency_penalty = llm_config.get("frequency_penalty", 0.0)
            presence_penalty = llm_config.get("presence_penalty", 0.0)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            self._log_prompt_payload(
                request_type="evaluate_interview",
                model=model,
                messages=messages,
                temperature=eval_temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                response_format={"type": "json_object"},
                stream=False,
            )

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=eval_temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            logger.error(f"Interview evaluation failed: {e}")
            return {
                "overall_score": 70,
                "dimension_scores": {
                    "technical": 70,
                    "problem_solving": 70,
                    "communication": 70,
                    "learning_potential": 70,
                },
                "strengths": ["完成面试"],
                "weaknesses": ["评估系统暂时不可用"],
                "recommendation": "需要进一步评估",
                "feedback": "评估系统暂时不可用，请人工评估。",
            }


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
