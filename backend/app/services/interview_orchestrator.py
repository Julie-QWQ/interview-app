"""Interview tool orchestration for stage-aware external integrations."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from jinja2 import BaseLoader, Environment

from app.db import database
from app.services.prompt_service import prompt_service

logger = logging.getLogger(__name__)


def _safe_json(data: Any) -> Any:
    try:
        json.dumps(data, ensure_ascii=False)
        return data
    except Exception:
        return str(data)


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def _trim_text(value: str, limit: int = 1200) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _hash_recent_messages(messages: List[Dict[str, Any]], limit: int = 6) -> str:
    normalized = [
        {
            "role": item.get("role"),
            "content": item.get("content"),
        }
        for item in (messages or [])[-limit:]
    ]
    return _hash_text(json.dumps(normalized, ensure_ascii=False, sort_keys=True))


@dataclass
class ToolExecutionContext:
    trace_id: str
    interview_id: int
    stage: str
    trigger: str
    interview_config: Dict[str, Any]
    conversation_slice: List[Dict[str, Any]] = field(default_factory=list)
    resume_text: str | None = None
    current_user_message: str | None = None
    progress_info: Dict[str, Any] | None = None


@dataclass
class ToolResult:
    status: str
    summary: str = ""
    structured_payload: Dict[str, Any] = field(default_factory=dict)
    prompt_context: str = ""
    cache_ttl_seconds: int = 300
    meta: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedToolResult:
    tool_name: str
    status: str
    context_key: str
    summary: str = ""
    prompt_context: str = ""
    structured_payload: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    cache_ttl_seconds: int = 300
    cache_hit: bool = False


@dataclass
class StageToolPolicy:
    stage: str
    trigger_map: Dict[str, List[str]]
    cache_only: bool = False


@dataclass
class OrchestratedPromptContext:
    trace_id: str
    tool_context_blocks: Dict[str, str] = field(default_factory=dict)
    tool_context_combined: str = ""
    tool_structured_context: Dict[str, Any] = field(default_factory=dict)
    tool_observations: List[Dict[str, Any]] = field(default_factory=list)
    prefetch_tasks: List[Dict[str, Any]] = field(default_factory=list)
    tool_summary: str = ""
    tool_constraints: List[str] = field(default_factory=list)


class ExternalToolAdapter:
    tool_name = ""
    supported_stages: set[str] = set()
    supported_triggers: set[str] = set()
    default_ttl_seconds = 300

    def __init__(self, settings):
        self.settings = settings

    def _tools_config(self) -> Dict[str, Any]:
        try:
            return prompt_service.get_tools_config() or {}
        except Exception:
            return self.settings.get("tools", {}) or {}

    def _provider_config(self) -> Dict[str, Any]:
        return (self._tools_config().get("providers") or {}).get(self.tool_name, {}) or {}

    def _tool_prompt_config(self) -> Dict[str, Any]:
        return (self._tools_config().get("tool_prompts") or {}).get(self.tool_name, {}) or {}

    def _provider_mode(self) -> str:
        mode = str((self._provider_config().get("mode") or "url")).strip().lower()
        return mode if mode in {"url", "llm"} else "url"

    def _provider_prompt_config(self) -> Dict[str, Any]:
        if self._provider_mode() != "llm":
            return {}
        prompt_cfg = self._tool_prompt_config()
        provider_prompt = {
            "system_prompt": str(prompt_cfg.get("system_prompt") or "").strip(),
            "user_prompt_template": str(prompt_cfg.get("user_prompt_template") or "").strip(),
        }
        return {key: value for key, value in provider_prompt.items() if value}

    def is_enabled(self) -> bool:
        status = self.provider_status()
        return status["reason"] == "ready"

    def provider_status(self) -> Dict[str, Any]:
        cfg = self._provider_config()
        enabled = bool(cfg.get("enabled"))
        url = str(cfg.get("url") or "").strip()
        mode = self._provider_mode()
        if not cfg:
            reason = "provider_missing"
        elif not enabled:
            reason = "provider_disabled"
        elif mode == "llm":
            reason = "ready"
        elif not url:
            reason = "provider_missing_url"
        else:
            reason = "ready"
        return {
            "reason": reason,
            "enabled": enabled,
            "has_url": bool(url),
            "url": url,
            "mode": mode,
        }

    def get_timeout_seconds(self, trigger: str) -> float:
        default_timeouts = self._tools_config().get("timeouts") or {}
        if trigger in {"interview_start", "stage_enter"}:
            return float(default_timeouts.get("prefetch_seconds", 4.0))
        return float(default_timeouts.get("chat_seconds", 5.0))

    def build_context_key(self, context: ToolExecutionContext) -> str:
        return context.stage

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        return {}

    def build_request(self, context: ToolExecutionContext) -> Dict[str, Any]:
        interview = context.interview_config or {}
        recent_messages = [
            {
                "role": msg.get("role"),
                "content": msg.get("content"),
            }
            for msg in context.conversation_slice[-6:]
        ]
        payload = {
            "trace_id": context.trace_id,
            "interview_id": context.interview_id,
            "tool_name": self.tool_name,
            "stage": context.stage,
            "trigger": context.trigger,
            "candidate": {
                "name": interview.get("candidate_name"),
                "experience_level": interview.get("experience_level"),
            },
            "interview": {
                "position": interview.get("position"),
                "skill_domain": interview.get("skill_domain"),
                "skills": interview.get("skills") or [],
                "additional_requirements": interview.get("additional_requirements"),
            },
            "resume": {
                "file_id": interview.get("resume_file_id"),
                "text": context.resume_text or interview.get("resume_text"),
            },
            "conversation": {
                "latest_user_message": context.current_user_message,
                "recent_messages": recent_messages,
                "current_stage": context.stage,
            },
            "params": {
                **self.build_params(context),
            },
        }
        provider_prompt = self._provider_prompt_config()
        if provider_prompt:
            payload["params"]["tool_prompt"] = provider_prompt
        return payload

    def call(self, payload: Dict[str, Any], *, timeout_seconds: float) -> ToolResult:
        if self._provider_mode() == "llm":
            body = self.call_llm(payload, timeout_seconds=timeout_seconds)
            return self.normalize(body, latency_ms=0)

        cfg = self._provider_config()
        headers = {"Content-Type": "application/json"}
        headers.update(cfg.get("headers") or {})
        start = time.perf_counter()
        response = requests.post(
            cfg["url"],
            json=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        response.raise_for_status()
        body = response.json()
        return self.normalize(body, latency_ms=latency_ms)

    def call_llm(self, payload: Dict[str, Any], *, timeout_seconds: float) -> Dict[str, Any]:
        _ = timeout_seconds
        prompt_cfg = self._provider_prompt_config()
        system_prompt = str(prompt_cfg.get("system_prompt") or "").strip()
        user_prompt_template = str(prompt_cfg.get("user_prompt_template") or "").strip()
        if not system_prompt or not user_prompt_template:
            raise ValueError(f"LLM tool {self.tool_name} requires system_prompt and user_prompt_template")

        template_env = Environment(loader=BaseLoader(), autoescape=False, trim_blocks=True, lstrip_blocks=True)
        user_prompt = template_env.from_string(user_prompt_template).render(**self._llm_prompt_context(payload)).strip()

        from app.services.ai_service import get_ai_service

        response_text = get_ai_service().chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            trace_id=payload.get("trace_id"),
        )
        return self._normalize_llm_body(response_text)

    def _llm_prompt_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        conversation = payload.get("conversation") or {}
        recent_messages = conversation.get("recent_messages") or []
        recent_messages_text = "\n".join(
            [
                f"{str(msg.get('role') or 'unknown')}: {str(msg.get('content') or '').strip()}"
                for msg in recent_messages
                if str(msg.get("content") or "").strip()
            ]
        ) or "(empty)"
        return {
            "trace_id": payload.get("trace_id"),
            "tool_name": payload.get("tool_name"),
            "stage": payload.get("stage"),
            "trigger": payload.get("trigger"),
            "candidate": payload.get("candidate") or {},
            "interview": payload.get("interview") or {},
            "resume": payload.get("resume") or {},
            "conversation": conversation,
            "params": payload.get("params") or {},
            "latest_user_message": conversation.get("latest_user_message") or "",
            "recent_messages": recent_messages,
            "recent_messages_text": recent_messages_text,
        }

    @staticmethod
    def _normalize_llm_body(response_text: str) -> Dict[str, Any]:
        text = str(response_text or "").strip()
        if not text:
            return {
                "status": "error",
                "summary": "",
                "structured_payload": {},
                "prompt_context": "",
                "cache_ttl_seconds": 0,
                "errors": ["LLM tool returned empty content"],
            }

        try:
            parsed = json.loads(text)
        except Exception:
            return {
                "status": "success",
                "summary": "",
                "structured_payload": {},
                "prompt_context": text,
                "cache_ttl_seconds": 0,
                "errors": [],
            }

        if isinstance(parsed, dict):
            return {
                "status": parsed.get("status") or "success",
                "summary": str(parsed.get("summary") or ""),
                "structured_payload": parsed.get("structured_payload") or {},
                "prompt_context": str(parsed.get("prompt_context") or ""),
                "cache_ttl_seconds": int(parsed.get("cache_ttl_seconds") or 0),
                "errors": [str(item) for item in (parsed.get("errors") or [])],
                "meta": parsed.get("meta") or {},
            }

        return {
            "status": "success",
            "summary": "",
            "structured_payload": {},
            "prompt_context": text,
            "cache_ttl_seconds": 0,
            "errors": [],
        }

    def normalize(self, body: Dict[str, Any], *, latency_ms: int) -> ToolResult:
        status = (body or {}).get("status") or "success"
        raw_meta = body.get("meta") if isinstance(body, dict) else {}
        meta = raw_meta if isinstance(raw_meta, dict) else {}
        meta = {**meta, "latency_ms": latency_ms}
        return ToolResult(
            status=status,
            summary=str((body or {}).get("summary") or ""),
            structured_payload=(body or {}).get("structured_payload") or {},
            prompt_context=_trim_text(str((body or {}).get("prompt_context") or "")),
            cache_ttl_seconds=int((body or {}).get("cache_ttl_seconds") or self.default_ttl_seconds),
            meta=meta,
            errors=[str(item) for item in ((body or {}).get("errors") or [])],
            raw_response=body if isinstance(body, dict) else {"raw_response": body},
        )


class ResumeAnalyzerAdapter(ExternalToolAdapter):
    tool_name = "resume_analyzer"
    supported_stages = {"welcome"}
    supported_triggers = {"interview_start"}
    default_ttl_seconds = 3600

    def build_context_key(self, context: ToolExecutionContext) -> str:
        resume_text = context.resume_text or context.interview_config.get("resume_text") or ""
        return f"resume:{_hash_text(resume_text or str(context.interview_id))}"


class QuestionBankRetrieverAdapter(ExternalToolAdapter):
    tool_name = "question_bank_retriever"
    supported_stages = {"technical", "scenario"}
    supported_triggers = {"stage_enter", "user_turn"}
    default_ttl_seconds = 900

    def build_context_key(self, context: ToolExecutionContext) -> str:
        interview = context.interview_config or {}
        base = "|".join(
            [
                context.stage,
                interview.get("position") or "",
                ",".join(interview.get("skills") or []),
            ]
        )
        return f"question_bank:{_hash_text(base)}"

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        return {
            "top_k": int((self._tools_config().get("cache") or {}).get("question_bank_top_k", 5)),
            "question_mode": "scenario" if context.stage == "scenario" else "technical",
            "need_followup": False,
        }


class FollowupEngineAdapter(ExternalToolAdapter):
    tool_name = "followup_engine"
    supported_stages = {"technical", "scenario"}
    supported_triggers = {"user_turn"}
    default_ttl_seconds = 60

    def build_context_key(self, context: ToolExecutionContext) -> str:
        seed = "|".join(
            [
                context.stage,
                context.current_user_message or "",
                str(context.progress_info.get("overall_turn") if context.progress_info else ""),
            ]
        )
        return f"followup:{_hash_text(seed)}"

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        return {
            "top_k": int((self._tools_config().get("cache") or {}).get("followup_top_k", 3)),
            "question_mode": context.stage,
            "need_followup": True,
        }


class SmartReplyEngineAdapter(ExternalToolAdapter):
    tool_name = "smart_reply_engine"
    supported_stages = {"technical", "scenario"}
    supported_triggers = {"user_turn"}
    default_ttl_seconds = 60

    def build_context_key(self, context: ToolExecutionContext) -> str:
        seed = "|".join(
            [
                context.stage,
                context.current_user_message or "",
                str(context.progress_info.get("overall_turn") if context.progress_info else ""),
                _hash_recent_messages(context.conversation_slice),
            ]
        )
        return f"smart_reply:{_hash_text(seed)}"

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        tools_config = self._tools_config()
        catalog = (tools_config.get("smart_reply_catalog") or {}).get("actions") or []
        allowed_actions = [
            item.get("action_key")
            for item in catalog
            if item.get("enabled", True) and item.get("action_key")
        ]
        return {
            "response_mode": "single_action",
            "question_mode": context.stage,
            "smart_reply_catalog": catalog,
            "allowed_actions": allowed_actions,
        }

    def call_llm(self, payload: Dict[str, Any], *, timeout_seconds: float) -> Dict[str, Any]:
        _ = timeout_seconds
        from app.services.smart_reply_service import smart_reply_service

        return smart_reply_service.execute(payload)

    def normalize(self, body: Dict[str, Any], *, latency_ms: int) -> ToolResult:
        base_result = super().normalize(body, latency_ms=latency_ms)
        payload = base_result.structured_payload if isinstance(base_result.structured_payload, dict) else {}
        action_key = str(payload.get("action_key") or "").strip()
        action_label = str(payload.get("action_label") or "").strip()
        rationale = _trim_text(str(payload.get("rationale") or ""), limit=500)
        utterance = _trim_text(str(payload.get("utterance") or ""), limit=500)
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

        errors = list(base_result.errors)
        if not action_key:
            errors.append("structured_payload.action_key is required")
        if not utterance:
            errors.append("structured_payload.utterance is required")

        if errors:
            return ToolResult(
                status="error",
                summary=base_result.summary,
                structured_payload={
                    "action_key": action_key,
                    "action_label": action_label,
                    "rationale": rationale,
                    "utterance": utterance,
                    "metadata": metadata,
                },
                prompt_context="",
                cache_ttl_seconds=0,
                meta=base_result.meta,
                errors=errors,
                raw_response=base_result.raw_response,
            )

        return ToolResult(
            status=base_result.status,
            summary=base_result.summary,
            structured_payload={
                "action_key": action_key,
                "action_label": action_label,
                "rationale": rationale,
                "utterance": utterance,
                "metadata": metadata,
            },
            prompt_context=base_result.prompt_context,
            cache_ttl_seconds=int(
                (body or {}).get("cache_ttl_seconds")
                or (self._tools_config().get("cache") or {}).get("smart_reply_ttl_seconds", self.default_ttl_seconds)
            ),
            meta=base_result.meta,
            errors=[],
            raw_response=base_result.raw_response,
        )


class QuestionBankAdapter(ExternalToolAdapter):
    """Simplified Question Bank adapter for RAG service integration."""

    tool_name = "question_bank"
    supported_stages = {
        "technical_questions",
        "behavioral_questions",
        "project_discussion",
        "scenario_analysis",
    }
    supported_triggers = {
        "stage_enter",
        "user_message",
        "interview_end",
    }
    default_ttl_seconds = 600

    def build_context_key(self, context: ToolExecutionContext) -> str:
        interview = context.interview_config or {}
        position = interview.get("position", "general")
        difficulty = interview.get("difficulty_level", "3")
        return f"questions:{context.stage}:{position}:{difficulty}"

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        interview = context.interview_config or {}

        # Map position
        position_map = {
            "java": "java_backend",
            "java_backend": "java_backend",
            "frontend": "web_frontend",
            "web": "web_frontend",
            "algorithm": "algorithm",
        }
        position = interview.get("position", "java_backend")
        mapped_position = position_map.get(position.lower(), "java_backend")

        params = {"position": mapped_position}

        # Map stage to question type
        stage_type_map = {
            "technical_questions": "technical",
            "behavioral_questions": "behavioral",
            "project_discussion": "project",
            "scenario_analysis": "scenario",
        }
        if context.stage in stage_type_map:
            params["type"] = stage_type_map[context.stage]

        # Add difficulty
        difficulty = interview.get("difficulty_level")
        if difficulty:
            try:
                params["difficulty"] = int(difficulty)
            except (ValueError, TypeError):
                params["difficulty"] = 3

        # Add skills/tags
        skills = interview.get("skills") or []
        if skills:
            if isinstance(skills, list):
                params["tags"] = ",".join(str(s) for s in skills)
            else:
                params["tags"] = str(skills)

        return params

    def build_request(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Build request for question bank service."""
        base_url = self._provider_config().get("url", "http://localhost:8004/api")

        if context.trigger == "stage_enter":
            # Question search
            params = self.build_params(context)
            params["size"] = params.get("size", 5)

            if context.current_user_message:
                params["query"] = context.current_user_message[:200]

            return {
                "method": "GET",
                "url": f"{base_url}/question/search",
                "params": params,
            }
        elif context.trigger == "user_message":
            # Follow-up hints (extract question ID from conversation)
            last_qid = self._extract_last_question_id(context)
            if last_qid:
                return {
                    "method": "GET",
                    "url": f"{base_url}/question/{last_qid}/followup",
                    "params": {},
                }
        elif context.trigger == "interview_end":
            # Feedback submission
            return {
                "method": "POST",
                "url": f"{base_url}/question/feedback",
                "body": self._build_feedback_body(context),
            }

        return {"method": "GET", "url": f"{base_url}/question/search", "params": {}}

    def _extract_last_question_id(self, context: ToolExecutionContext) -> Optional[int]:
        """Extract last question ID from conversation."""
        for msg in reversed(context.conversation_slice):
            if msg.get("role") == "assistant":
                metadata = msg.get("metadata") or {}
                qid = metadata.get("question_id")
                if qid:
                    try:
                        return int(qid)
                    except (ValueError, TypeError):
                        pass
        return None

    def _build_feedback_body(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Build feedback submission body."""
        interview = context.interview_config or {}
        scores = {}

        if context.progress_info:
            assessments = context.progress_info.get("assessments") or []
            if assessments:
                last_assessment = assessments[-1]
                scores = {
                    "question_id": last_assessment.get("question_id"),
                    "score": last_assessment.get("score", 5),
                }

        return {
            "userId": interview.get("user_id") or interview.get("candidate_id"),
            "questionId": scores.get("question_id"),
            "interviewId": str(context.interview_id),
            "score": scores.get("score"),
        }

    def call(self, payload: Dict[str, Any], *, timeout_seconds: float) -> ToolResult:
        """Execute API call to question bank service."""
        try:
            method = payload.get("method", "GET")
            url = payload.get("url", "")
            params = payload.get("params", {})
            body = payload.get("body")

            headers = {"Content-Type": "application/json"}
            headers.update(self._provider_config().get("headers") or {})

            start_time = time.perf_counter()

            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=timeout_seconds)
            elif method == "POST":
                response = requests.post(url, json=body, headers=headers, timeout=timeout_seconds)
            else:
                return ToolResult(status="error", errors=[f"Unsupported method: {method}"])

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response.raise_for_status()

            return self._parse_response(response.json(), latency_ms)

        except requests.exceptions.Timeout:
            return ToolResult(status="timeout", errors=["Request timeout"])
        except Exception as e:
            return ToolResult(status="error", errors=[str(e)])

    def _parse_response(self, body: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse question bank service response."""
        code = body.get("code", 500)
        data = body.get("data")

        if code != 200:
            return ToolResult(
                status="error",
                errors=[f"Error {code}: {body.get('message', '')}"],
                raw_response=body,
            )

        # Handle question list
        if isinstance(data, list) and data:
            if "text" in data[0]:  # Questions
                return self._parse_questions(data, latency_ms)
            elif "content" in data[0]:  # Knowledge documents
                return self._parse_documents(data, latency_ms)

        # Handle follow-up hints
        if isinstance(data, dict) and "followUpHints" in data:
            return self._parse_followup(data, latency_ms)

        return ToolResult(status="success", summary="Request completed")

    def _parse_questions(self, questions: List[Dict], latency_ms: int) -> ToolResult:
        """Parse question list response."""
        if not questions:
            return ToolResult(status="success", summary="No questions found")

        summaries = [f"- Q{q.get('id')}: {q.get('text', 'N/A')[:60]}..." for q in questions[:3]]
        summary = f"Retrieved {len(questions)} questions:\n" + "\n".join(summaries)

        # Build prompt context
        context_parts = ["Available Questions:\n"]
        for i, q in enumerate(questions[:10], 1):
            context_parts.append(
                f"{i}. [{q.get('code', 'N/A')}] {q.get('text', 'N/A')}\n"
                f"   Difficulty: {q.get('difficulty', 'N/A')}\n"
                f"   Tags: {', '.join(q.get('tags') or [])}\n"
            )

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={"questions": questions, "count": len(questions)},
            prompt_context="\n".join(context_parts),
            meta={"latency_ms": latency_ms, "question_count": len(questions)},
        )

    def _parse_followup(self, data: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse follow-up hints response."""
        hints = data.get("followUpHints") or []
        if not hints:
            return ToolResult(status="success", summary="No follow-up hints available")

        summary = "Follow-up suggestions:\n" + "\n".join(f"- {h}" for h in hints[:5])
        context = "Suggested Follow-up Questions:\n" + "\n".join(f"- {h}" for h in hints)

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={"hints": hints},
            prompt_context=context,
            meta={"latency_ms": latency_ms, "hint_count": len(hints)},
        )

    def _parse_documents(self, documents: List[Dict], latency_ms: int) -> ToolResult:
        """Parse knowledge documents response."""
        if not documents:
            return ToolResult(status="success", summary="No documents found")

        summaries = [f"- {doc.get('title', 'Untitled')} (tags: {', '.join(doc.get('tags') or [])})" for doc in documents[:3]]
        summary = f"RAG retrieved {len(documents)} documents:\n" + "\n".join(summaries)

        # Build knowledge context
        context_parts = ["Relevant Knowledge:\n"]
        for i, doc in enumerate(documents[:5], 1):
            context_parts.append(
                f"Document {i}: {doc.get('title', 'Untitled')}\n"
                f"Tags: {', '.join(doc.get('tags') or [])}\n"
                f"Content:\n{doc.get('content', '')[:1000]}...\n"
            )

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={"documents": documents, "doc_count": len(documents)},
            prompt_context="\n".join(context_parts),
            meta={"latency_ms": latency_ms, "doc_count": len(documents)},
        )


class LearningResourceAdapter(ExternalToolAdapter):
    """学习资源推荐适配器 - 新版API v1.1支持."""

    tool_name = "learning_resource"
    supported_stages = {"interview_end", "growth_recommendation"}
    supported_triggers = {"interview_end", "user_request"}
    default_ttl_seconds = 3600  # 学习资源缓存1小时

    def build_context_key(self, context: ToolExecutionContext) -> str:
        interview = context.interview_config or {}
        user_id = interview.get("user_id", interview.get("candidate_id", "unknown"))
        position = interview.get("position", "java_backend")
        skills = interview.get("skills", [])
        return f"resources:{user_id}:{position}:{','.join(skills)}"

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        interview = context.interview_config or {}

        # 岗位枚举映射
        position_map = {
            "java": "java_backend",
            "java_backend": "java_backend",
            "frontend": "web_frontend",
            "web": "web_frontend",
            "algorithm": "algorithm",
        }
        position = interview.get("position", "java_backend")
        mapped_position = position_map.get(position.lower(), "java_backend")

        params = {"position": mapped_position}  # 新版API: 必填参数

        # 用户ID（优先按薄弱技能推荐）
        user_id = interview.get("user_id", interview.get("candidate_id"))
        if user_id:
            params["userId"] = user_id

        # 技能标签（userId无薄弱技能时生效）
        skills = interview.get("skills") or []
        if skills:
            if isinstance(skills, list):
                params["tags"] = ",".join(str(s) for s in skills)
            else:
                params["tags"] = str(skills)

        # 资源类型（可选）
        resource_type = context.progress_info.get("resource_type") if context.progress_info else None
        if resource_type:
            params["type"] = resource_type

        return params

    def build_request(self, context: ToolExecutionContext) -> Dict[str, Any]:
        base_url = self._provider_config().get("url", "http://localhost:8004")
        params = self.build_params(context)

        return {
            "method": "GET",
            "url": f"{base_url}/api/resource/recommend",
            "params": params,
        }

    def call(self, payload: Dict[str, Any], *, timeout_seconds: float) -> ToolResult:
        """执行学习资源推荐请求."""
        try:
            method = payload.get("method", "GET")
            url = payload.get("url", "")
            params = payload.get("params", {})

            headers = {"Content-Type": "application/json"}
            headers.update(self._provider_config().get("headers") or {})

            start_time = time.perf_counter()

            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=timeout_seconds)
            else:
                return ToolResult(status="error", errors=[f"Unsupported method: {method}"])

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response.raise_for_status()

            return self._parse_response(response.json(), latency_ms)

        except requests.exceptions.Timeout:
            return ToolResult(status="timeout", errors=["Request timeout"])
        except Exception as e:
            return ToolResult(status="error", errors=[str(e)])

    def _parse_response(self, body: Dict[str, Any], latency_ms: int) -> ToolResult:
        """解析学习资源推荐响应."""
        code = body.get("code", 500)
        data = body.get("data")

        if code != 200:
            return ToolResult(
                status="error",
                errors=[f"Error {code}: {body.get('message', '')}"],
                raw_response=body,
            )

        resources = data if isinstance(data, list) else []
        if not resources:
            return ToolResult(status="success", summary="No learning resources found")

        summaries = [f"- {r.get('title', 'Untitled')} ({r.get('type', 'resource')})" for r in resources[:3]]
        summary = f"Found {len(resources)} learning resources:\n" + "\n".join(summaries)

        # 构建推荐上下文
        context_parts = ["Recommended Learning Resources:\n"]
        for i, res in enumerate(resources[:10], 1):
            context_parts.append(
                f"{i}. {res.get('title', 'Untitled')}\n"
                f"   Type: {res.get('type', 'N/A')}\n"
                f"   Platform: {res.get('platform', 'N/A')}\n"
                f"   Difficulty: {res.get('difficulty', 'N/A')}/5\n"
                f"   Description: {res.get('description', 'N/A')[:100]}...\n"
                f"   URL: {res.get('url', 'N/A')}\n"
            )

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={"resources": resources, "count": len(resources)},
            prompt_context="\n".join(context_parts),
            meta={"latency_ms": latency_ms, "resource_count": len(resources)},
        )


class GenericToolAdapter(ExternalToolAdapter):
    """Fallback adapter for providers configured from the frontend."""

    def __init__(self, settings, tool_name: str):
        super().__init__(settings)
        self.tool_name = tool_name


class ToolRegistry:
    def __init__(self, settings):
        self.settings = settings
        # 延迟导入避免循环依赖
        from app.services.resume_analyzer_adapter import ResumeAnalyzerAdapter

        self._adapters = {
            "resume_analyzer": ResumeAnalyzerAdapter(settings),
            "question_bank_retriever": QuestionBankRetrieverAdapter(settings),
            "question_bank": QuestionBankAdapter(settings),  # Built-in RAG adapter
            "followup_engine": FollowupEngineAdapter(settings),
            "smart_reply_engine": SmartReplyEngineAdapter(settings),
            "learning_resource": LearningResourceAdapter(settings),  # 新版API学习资源推荐
        }

    def _tools_config(self) -> Dict[str, Any]:
        try:
            return prompt_service.get_tools_config() or {}
        except Exception:
            return self.settings.get("tools", {}) or {}

    def _load_policies(self) -> Dict[str, StageToolPolicy]:
        configured = self._tools_config().get("bindings") or {}
        defaults = {
            "welcome": StageToolPolicy("welcome", {"interview_start": ["resume_analyzer"]}),
            "technical": StageToolPolicy(
                "technical",
                {
                    "stage_enter": ["question_bank"],  # Use new RAG-based adapter
                    "user_turn": ["question_bank", "followup_engine", "smart_reply_engine"],
                },
            ),
            "behavioral": StageToolPolicy(
                "behavioral",
                {
                    "stage_enter": ["question_bank"],
                    "user_turn": ["question_bank", "followup_engine", "smart_reply_engine"],
                },
            ),
            "project_discussion": StageToolPolicy(
                "project_discussion",
                {
                    "stage_enter": ["question_bank"],
                    "user_turn": ["question_bank", "followup_engine", "smart_reply_engine"],
                },
            ),
            "scenario_analysis": StageToolPolicy(
                "scenario_analysis",
                {
                    "stage_enter": ["question_bank"],
                    "user_turn": ["question_bank", "followup_engine", "smart_reply_engine"],
                },
            ),
            "scenario": StageToolPolicy(
                "scenario",
                {
                    "stage_enter": ["question_bank_retriever"],
                    "user_turn": ["question_bank_retriever", "followup_engine", "smart_reply_engine"],
                },
            ),
            "closing": StageToolPolicy("closing", {}, cache_only=True),
        }

        for stage, policy in defaults.items():
            stage_cfg = configured.get(stage) or {}
            if stage_cfg:
                policy.trigger_map = {
                    trigger: list(tool_names)
                    for trigger, tool_names in (stage_cfg.get("trigger_map") or policy.trigger_map).items()
                }
                policy.cache_only = bool(stage_cfg.get("cache_only", policy.cache_only))

        return defaults

    def get_policy(self, stage: str) -> StageToolPolicy:
        return self._load_policies().get(stage, StageToolPolicy(stage, {}))

    def get_adapter(self, tool_name: str) -> Optional[ExternalToolAdapter]:
        return self._adapters.get(tool_name) or GenericToolAdapter(self.settings, tool_name)

    def list_tools_for(self, stage: str, trigger: str) -> List[ExternalToolAdapter]:
        policy = self.get_policy(stage)
        adapters: List[ExternalToolAdapter] = []
        for tool_name in policy.trigger_map.get(trigger, []):
            adapter = self.get_adapter(tool_name)
            if adapter:
                adapters.append(adapter)
        return adapters


class InterviewOrchestrator:
    def __init__(self, settings):
        self.settings = settings
        self.registry = ToolRegistry(settings)
        self.logs_path = Path(__file__).resolve().parents[2] / "logs" / "tools.log"
        self.prefetch_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tool-prefetch")
        self._prefetch_lock = threading.Lock()

    def new_trace_id(self) -> str:
        return str(uuid.uuid4())

    def orchestrate(self, context: ToolExecutionContext) -> OrchestratedPromptContext:
        policy = self.registry.get_policy(context.stage)
        result = OrchestratedPromptContext(trace_id=context.trace_id)

        if policy.cache_only:
            self._hydrate_cached_blocks(context, result)
            return result

        adapters = self.registry.list_tools_for(context.stage, context.trigger)
        for adapter in adapters:
            normalized = self._resolve_tool(context, adapter)
            if not normalized:
                continue
            if normalized.structured_payload:
                result.tool_structured_context[adapter.tool_name] = normalized.structured_payload
            rendered_prompt_context = self._render_tool_prompt_context(
                adapter.tool_name,
                raw_prompt_context=normalized.prompt_context,
                structured_payload=normalized.structured_payload,
                summary=normalized.summary,
                meta=normalized.meta,
            )
            if rendered_prompt_context:
                result.tool_context_blocks[adapter.tool_name] = rendered_prompt_context
            result.tool_observations.append(
                {
                    "tool_name": adapter.tool_name,
                    "status": normalized.status,
                    "cache_hit": normalized.cache_hit,
                    "meta": normalized.meta,
                    "errors": normalized.errors,
                }
            )

        if not result.tool_context_blocks:
            self._hydrate_cached_blocks(context, result)

        summaries = [
            obs["tool_name"]
            for obs in result.tool_observations
            if obs.get("status") == "success"
        ]
        if summaries:
            result.tool_summary = "已注入工具上下文: " + ", ".join(summaries)
            result.tool_constraints = [
                "工具返回是外部模块提供的辅助信息，优先用于追问、校验和控制面试节奏，不要逐字复述接口输出。",
                "如果工具上下文与候选人最新回答冲突，以最新对话为准，并继续追问澄清。",
            ]

        result.tool_context_combined = self._compose_tool_context_combined(
            result.tool_context_blocks,
            result.tool_structured_context,
        )
        result.prefetch_tasks = self._schedule_prefetch(context)
        return result

    def _hydrate_cached_blocks(self, context: ToolExecutionContext, result: OrchestratedPromptContext) -> None:
        cached_rows = database.list_interview_tool_contexts(context.interview_id)
        for row in cached_rows:
            tool_name = row.get("tool_name")
            raw_prompt_context = (row.get("prompt_context") or "").strip()
            structured_payload = row.get("structured_payload") or {}
            if structured_payload and tool_name not in result.tool_structured_context:
                result.tool_structured_context[tool_name] = structured_payload
            if tool_name not in result.tool_context_blocks:
                rendered_prompt_context = self._render_tool_prompt_context(
                    tool_name,
                    raw_prompt_context=raw_prompt_context,
                    structured_payload=structured_payload,
                    summary="",
                    meta={},
                )
                if rendered_prompt_context:
                    result.tool_context_blocks[tool_name] = rendered_prompt_context

        if result.tool_context_blocks and not result.tool_summary:
            result.tool_summary = "已复用缓存工具上下文"
            result.tool_constraints = [
                "工具上下文来自缓存结果，回答时注意结合当前轮对话进行更新。",
            ]

        result.tool_context_combined = self._compose_tool_context_combined(
            result.tool_context_blocks,
            result.tool_structured_context,
        )

    def _render_tool_prompt_context(
        self,
        tool_name: str,
        *,
        raw_prompt_context: str,
        structured_payload: Optional[Dict[str, Any]] = None,
        summary: str = "",
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        structured_payload = structured_payload or {}
        meta = meta or {}
        tools_config = prompt_service.get_tools_config() or {}
        tool_prompt_map = (tools_config.get("tool_prompts") or {}) if isinstance(tools_config, dict) else {}
        prompt_cfg = tool_prompt_map.get(tool_name) or {}
        template_source = str(prompt_cfg.get("result_prompt_template") or "").strip()
        raw_prompt_context = str(raw_prompt_context or "").strip()

        if not template_source:
            return raw_prompt_context

        try:
            environment = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
            rendered = environment.from_string(template_source).render(
                tool_name=tool_name,
                structured_payload=structured_payload,
                raw_prompt_context=raw_prompt_context,
                summary=summary,
                meta=meta,
            )
            rendered_text = str(rendered or "").strip()
            return rendered_text or raw_prompt_context
        except Exception as exc:
            logger.warning("Failed to render result_prompt_template: tool=%s error=%s", tool_name, exc)
            return raw_prompt_context

    def _compose_tool_context_combined(
        self,
        tool_context_blocks: Dict[str, str],
        tool_structured_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not tool_context_blocks:
            return ""

        tool_structured_context = tool_structured_context or {}
        config_data = prompt_service.get_prompt_config_data() or {}
        tools_config = prompt_service.get_tools_config() or {}
        tool_prompt_map = (tools_config.get("tool_prompts") or {}) if isinstance(tools_config, dict) else {}
        items: List[Dict[str, Any]] = []
        for tool_name, block in tool_context_blocks.items():
            text = str(block or "").strip()
            if not text:
                continue
            prompt_cfg = tool_prompt_map.get(tool_name) or {}
            label = str(prompt_cfg.get("context_label") or tool_name).strip() or tool_name
            items.append(
                {
                    "tool_name": tool_name,
                    "context_label": label,
                    "prompt_context": text,
                    "structured_payload": tool_structured_context.get(tool_name) or {},
                }
            )

        if not items:
            return ""

        template_source = str(config_data.get("tool_context_template") or "").strip()
        if not template_source:
            template_source = (
                "{% for item in tool_context_items %}\n"
                "### {{ item.context_label }}\n"
                "{{ item.prompt_context }}\n"
                "{% if not loop.last %}\n\n{% endif %}"
                "{% endfor %}"
            )

        try:
            environment = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True)
            rendered = environment.from_string(template_source).render(
                tool_context_items=items,
                tool_context=tool_context_blocks,
            )
            return rendered.strip()
        except Exception as exc:
            logger.warning("Failed to render tool_context_template: %s", exc)
            return "\n\n".join(f"### {item['context_label']}\n{item['prompt_context']}" for item in items)

    def _resolve_tool(
        self,
        context: ToolExecutionContext,
        adapter: ExternalToolAdapter,
    ) -> Optional[NormalizedToolResult]:
        context_key = adapter.build_context_key(context)
        cached = database.get_interview_tool_context(
            context.interview_id,
            context.stage,
            adapter.tool_name,
            context_key,
        )
        if cached:
            normalized = NormalizedToolResult(
                tool_name=adapter.tool_name,
                status="success",
                context_key=context_key,
                summary="",
                prompt_context=(cached.get("prompt_context") or "").strip(),
                structured_payload=cached.get("structured_payload") or {},
                meta={"expires_at": cached.get("expires_at").isoformat() if cached.get("expires_at") else None},
                errors=[],
                cache_ttl_seconds=0,
                cache_hit=True,
            )
            self._record_invocation(
                context=context,
                adapter=adapter,
                request_payload=adapter.build_request(context),
                response_payload={
                    "status": "success",
                    "summary": "cache_hit",
                    "structured_payload": normalized.structured_payload,
                    "prompt_context": normalized.prompt_context,
                    "cache_ttl_seconds": 0,
                    "meta": normalized.meta,
                    "errors": [],
                },
                status="success",
                latency_ms=0,
                cache_hit=True,
            )
            return normalized

        if not adapter.is_enabled():
            provider_status = adapter.provider_status()
            self._record_invocation(
                context=context,
                adapter=adapter,
                request_payload=adapter.build_request(context),
                response_payload={
                    "status": "skipped",
                    "reason": provider_status["reason"],
                    "provider": {
                        "enabled": provider_status["enabled"],
                        "has_url": provider_status["has_url"],
                    },
                },
                status="skipped",
                latency_ms=0,
                cache_hit=False,
            )
            return None

        payload = adapter.build_request(context)
        try:
            tool_result = adapter.call(payload, timeout_seconds=adapter.get_timeout_seconds(context.trigger))
        except Exception as exc:
            logger.warning("Tool call failed: tool=%s trace_id=%s error=%s", adapter.tool_name, context.trace_id, exc)
            self._record_invocation(
                context=context,
                adapter=adapter,
                request_payload=payload,
                response_payload={"status": "error", "errors": [str(exc)]},
                status="error",
                latency_ms=0,
                cache_hit=False,
            )
            return None

        normalized = NormalizedToolResult(
            tool_name=adapter.tool_name,
            status=tool_result.status,
            context_key=context_key,
            summary=tool_result.summary,
            prompt_context=tool_result.prompt_context,
            structured_payload=tool_result.structured_payload,
            meta=tool_result.meta,
            errors=tool_result.errors,
            cache_ttl_seconds=max(0, int(tool_result.cache_ttl_seconds or adapter.default_ttl_seconds)),
            cache_hit=False,
        )

        self._record_invocation(
            context=context,
            adapter=adapter,
            request_payload=payload,
            response_payload=tool_result.raw_response or {
                "status": tool_result.status,
                "summary": tool_result.summary,
                "structured_payload": tool_result.structured_payload,
                "prompt_context": tool_result.prompt_context,
                "cache_ttl_seconds": tool_result.cache_ttl_seconds,
                "meta": tool_result.meta,
                "errors": tool_result.errors,
            },
            status=tool_result.status,
            latency_ms=int(tool_result.meta.get("latency_ms", 0) or 0),
            cache_hit=False,
        )

        if normalized.status == "success" and (normalized.prompt_context or normalized.structured_payload):
            expires_at = datetime.utcnow() + timedelta(seconds=normalized.cache_ttl_seconds or adapter.default_ttl_seconds)
            database.upsert_interview_tool_context(
                {
                    "interview_id": context.interview_id,
                    "stage": context.stage,
                    "tool_name": adapter.tool_name,
                    "context_key": context_key,
                    "prompt_context": normalized.prompt_context,
                    "structured_payload": normalized.structured_payload,
                    "expires_at": expires_at,
                }
            )

        return normalized

    def _record_invocation(
        self,
        *,
        context: ToolExecutionContext,
        adapter: ExternalToolAdapter,
        request_payload: Dict[str, Any],
        response_payload: Dict[str, Any],
        status: str,
        latency_ms: int,
        cache_hit: bool,
    ) -> None:
        row = {
            "trace_id": context.trace_id,
            "interview_id": context.interview_id,
            "stage": context.stage,
            "trigger": context.trigger,
            "tool_name": adapter.tool_name,
            "request_payload": _safe_json(request_payload),
            "response_payload": _safe_json(response_payload),
            "status": status,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
        }
        database.create_tool_invocation(row)
        try:
            self.logs_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"timestamp": datetime.utcnow().isoformat(timespec="seconds"), **row}
            with self.logs_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False))
                fh.write("\n")
        except Exception as exc:
            logger.warning("Failed to write tools.log: %s", exc)

    def _schedule_prefetch(self, context: ToolExecutionContext) -> List[Dict[str, Any]]:
        next_stage = self._next_stage(context.stage)
        if not next_stage:
            return []

        prefetch_tasks: List[Dict[str, Any]] = []
        if next_stage in {"technical", "scenario"}:
            task = {
                "tool_name": "question_bank_retriever",
                "stage": next_stage,
                "trigger": "stage_enter",
            }
            prefetch_tasks.append(task)
            with self._prefetch_lock:
                self.prefetch_executor.submit(self._run_prefetch, context, next_stage)
        return prefetch_tasks

    def _run_prefetch(self, source_context: ToolExecutionContext, next_stage: str) -> None:
        prefetch_context = ToolExecutionContext(
            trace_id=f"{source_context.trace_id}:prefetch:{next_stage}",
            interview_id=source_context.interview_id,
            stage=next_stage,
            trigger="stage_enter",
            interview_config=source_context.interview_config,
            conversation_slice=source_context.conversation_slice[-6:],
            resume_text=source_context.resume_text,
            current_user_message=source_context.current_user_message,
            progress_info=source_context.progress_info,
        )
        for adapter in self.registry.list_tools_for(next_stage, "stage_enter"):
            try:
                self._resolve_tool(prefetch_context, adapter)
            except Exception as exc:
                logger.debug("Prefetch failed: stage=%s tool=%s error=%s", next_stage, adapter.tool_name, exc)

    @staticmethod
    def _next_stage(current_stage: str) -> Optional[str]:
        stages = [stage.stage for stage in prompt_service.get_stage_configs()]
        try:
            index = stages.index(current_stage)
        except ValueError:
            return None
        if index + 1 >= len(stages):
            return None
        return stages[index + 1]


_interview_orchestrator: Optional[InterviewOrchestrator] = None


def init_interview_orchestrator(settings) -> None:
    global _interview_orchestrator
    _interview_orchestrator = InterviewOrchestrator(settings)


def get_interview_orchestrator() -> InterviewOrchestrator:
    if _interview_orchestrator is None:
        raise RuntimeError("Interview orchestrator not initialized")
    return _interview_orchestrator
