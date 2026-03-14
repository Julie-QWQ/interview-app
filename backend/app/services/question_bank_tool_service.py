"""Question Bank RAG Tool Adapter for interview service integration.

This module provides integration with the external question bank service (question-service)
for question retrieval, follow-up hints, answer feedback, and knowledge document search.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from app.services.interview_orchestrator import (
    ExternalToolAdapter,
    ToolExecutionContext,
    ToolResult,
)

logger = logging.getLogger(__name__)


class QuestionBankToolAdapter(ExternalToolAdapter):
    """Adapter for question bank RAG service integration.

    Supports:
    - Question search and retrieval
    - Follow-up hints for deeper questioning
    - Answer feedback submission for adaptive difficulty
    - Knowledge document search (RAG)
    """

    tool_name = "question_bank"
    supported_stages = {
        "technical_questions",
        "behavioral_questions",
        "project_discussion",
        "scenario_analysis",
    }
    supported_triggers = {
        "stage_enter",  # Pre-fetch questions when entering a stage
        "user_message",  # Get follow-ups after user answers
        "interview_end",  # Submit final feedback
    }
    default_ttl_seconds = 600  # Cache questions for 10 minutes

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self._service_base_url: str = ""
        self._timeout: float = 5.0

    def _get_service_base_url(self) -> str:
        """Get the base URL for question bank service."""
        if not self._service_base_url:
            cfg = self._provider_config()
            url = cfg.get("url", "http://localhost:8004/api").rstrip("/")
            self._service_base_url = url
        return self._service_base_url

    def _get_timeout(self) -> float:
        """Get request timeout in seconds."""
        cfg = self._provider_config()
        return float(cfg.get("timeout_seconds", 5.0))

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests."""
        cfg = self._provider_config()
        headers = {"Content-Type": "application/json"}
        # Add custom headers from config
        custom_headers = cfg.get("headers") or {}
        headers.update(custom_headers)
        return headers

    def build_context_key(self, context: ToolExecutionContext) -> str:
        """Build cache key for tool context.

        Key structure: {stage}:{position}:{difficulty}:{topic}
        """
        interview = context.interview_config or {}
        position = interview.get("position", "general")
        difficulty = interview.get("difficulty_level", "3")
        trigger = context.trigger

        # For different triggers, use different cache keys
        if trigger == "stage_enter":
            # Cache questions by stage and position
            return f"questions:{context.stage}:{position}:{difficulty}"
        elif trigger == "user_message":
            # Cache follow-ups by conversation hash
            recent_hash = self._hash_conversation(context.conversation_slice)
            return f"followup:{context.stage}:{recent_hash}"
        else:
            return f"{context.stage}:{trigger}"

    def _hash_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Hash recent conversation for cache key."""
        import hashlib
        import json

        recent = [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in (messages or [])[-3:]  # Last 3 messages
        ]
        normalized = json.dumps(recent, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8]

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Build request parameters based on trigger type."""
        params = {}
        interview = context.interview_config or {}

        # Common parameters
        params["position"] = self._map_position(interview.get("position"))

        # Stage-specific parameters
        if context.stage == "technical_questions":
            params["type"] = "technical"
        elif context.stage == "behavioral_questions":
            params["type"] = "behavioral"
        elif context.stage == "project_discussion":
            params["type"] = "project"
        elif context.stage == "scenario_analysis":
            params["type"] = "scenario"

        # Difficulty level
        difficulty = interview.get("difficulty_level")
        if difficulty:
            try:
                params["difficulty"] = int(difficulty)
            except (ValueError, TypeError):
                params["difficulty"] = 3  # Default medium difficulty

        # Skills/tags
        skills = interview.get("skills") or []
        if skills:
            if isinstance(skills, list):
                params["tags"] = ",".join(str(s) for s in skills)
            else:
                params["tags"] = str(skills)

        return params

    def _map_position(self, position: Optional[str]) -> str:
        """Map interview position to question service position enum."""
        if not position:
            return "java_backend"  # Default

        position_map = {
            "java": "java_backend",
            "java_backend": "java_backend",
            "frontend": "web_frontend",
            "web": "web_frontend",
            "web_frontend": "web_frontend",
            "algorithm": "algorithm",
            "algo": "algorithm",
        }

        position_lower = position.lower().strip()
        return position_map.get(position_lower, "java_backend")

    def build_request(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Build request payload for question bank service.

        Different triggers generate different API calls:
        - stage_enter: Search questions
        - user_message: Get follow-up hints
        - interview_end: Submit feedback
        """
        trigger = context.trigger
        base_url = self._get_service_base_url()

        if trigger == "stage_enter":
            return self._build_search_request(context, base_url)
        elif trigger == "user_message":
            return self._build_followup_request(context, base_url)
        elif trigger == "interview_end":
            return self._build_feedback_request(context, base_url)
        else:
            # Default: question search
            return self._build_search_request(context, base_url)

    def _build_search_request(self, context: ToolExecutionContext, base_url: str) -> Dict[str, Any]:
        """Build question search request."""
        params = self.build_params(context)

        # Add search-specific parameters
        params["size"] = params.get("size", 5)  # Default 5 questions

        # Build query from conversation context
        if context.current_user_message:
            # Extract key topics from user message for semantic search
            params["query"] = context.current_user_message[:200]  # Limit query length

        # Check for previously asked questions
        asked_questions = self._get_asked_question_ids(context)
        if asked_questions:
            params["excludeIds"] = ",".join(str(qid) for qid in asked_questions)

        return {
            "method": "GET",
            "url": urljoin(base_url, "/question/search"),
            "params": params,
        }

    def _build_followup_request(self, context: ToolExecutionContext, base_url: str) -> Dict[str, Any]:
        """Build follow-up hints request."""
        # Get the last question ID from conversation
        last_question_id = self._extract_last_question_id(context)

        if not last_question_id:
            return {
                "method": "GET",
                "url": urljoin(base_url, "/question/0/followup"),
                "error": "No question ID found in conversation",
            }

        return {
            "method": "GET",
            "url": urljoin(base_url, f"/question/{last_question_id}/followup"),
            "params": {},
        }

    def _build_feedback_request(self, context: ToolExecutionContext, base_url: str) -> Dict[str, Any]:
        """Build feedback submission request."""
        interview = context.interview_config or {}

        # Extract scores from conversation or progress info
        scores = self._extract_assessment_scores(context)

        return {
            "method": "POST",
            "url": urljoin(base_url, "/question/feedback"),
            "body": {
                "userId": interview.get("user_id") or interview.get("candidate_id"),
                "questionId": scores.get("question_id"),
                "interviewId": str(context.interview_id),
                "score": scores.get("score"),
            },
        }

    def _get_asked_question_ids(self, context: ToolExecutionContext) -> List[int]:
        """Extract IDs of previously asked questions from conversation."""
        question_ids = []

        for msg in context.conversation_slice:
            # Look for question IDs in AI messages
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Assuming question IDs are stored in metadata or parsed from content
                metadata = msg.get("metadata") or {}
                qid = metadata.get("question_id")
                if qid:
                    try:
                        question_ids.append(int(qid))
                    except (ValueError, TypeError):
                        pass

        return question_ids

    def _extract_last_question_id(self, context: ToolExecutionContext) -> Optional[int]:
        """Extract the most recent question ID from conversation."""
        asked_ids = self._get_asked_question_ids(context)
        return asked_ids[-1] if asked_ids else None

    def _extract_assessment_scores(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Extract assessment scores from progress info."""
        scores = {}

        if context.progress_info:
            assessments = context.progress_info.get("assessments") or []
            if assessments:
                last_assessment = assessments[-1]
                scores = {
                    "question_id": last_assessment.get("question_id"),
                    "score": last_assessment.get("score", 5),
                }

        return scores

    def call(self, payload: Dict[str, Any], *, timeout_seconds: float) -> ToolResult:
        """Execute the API call to question bank service."""
        method = payload.get("method", "GET")
        url = payload.get("url", "")
        params = payload.get("params", {})
        body = payload.get("body")

        headers = self._build_headers()

        try:
            start_time = time.perf_counter()

            if method == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout_seconds,
                )
            elif method == "POST":
                response = requests.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=timeout_seconds,
                )
            else:
                return ToolResult(
                    status="error",
                    errors=[f"Unsupported HTTP method: {method}"],
                )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response.raise_for_status()

            return self._parse_response(response.json(), latency_ms)

        except requests.exceptions.Timeout:
            logger.error(f"Question bank service timeout: {url}")
            return ToolResult(
                status="timeout",
                errors=["Question bank service timeout"],
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Question bank service error: {e}")
            return ToolResult(
                status="error",
                errors=[str(e)],
            )
        except Exception as e:
            logger.error(f"Unexpected error calling question bank: {e}")
            return ToolResult(
                status="error",
                errors=[str(e)],
            )

    def _parse_response(self, body: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse question bank service response into ToolResult."""
        code = body.get("code", 500)
        message = body.get("message", "")
        data = body.get("data")

        if code != 200:
            return ToolResult(
                status="error",
                errors=[f"Question bank error {code}: {message}"],
                raw_response=body,
            )

        # Handle different response types
        if isinstance(data, list):
            # Question search results
            if data and isinstance(data[0], dict):
                if "text" in data[0]:  # Question list
                    return self._parse_question_list(data, latency_ms)
                elif "content" in data[0]:  # Knowledge documents
                    return self._parse_knowledge_documents(data, latency_ms)

        # Follow-up hints
        if isinstance(data, dict) and "followUpHints" in data:
            return self._parse_followup_hints(data, latency_ms)

        # Generic success response
        return ToolResult(
            status="success",
            summary=message or "Request completed",
            structured_payload={"data": data},
            raw_response=body,
        )

    def _parse_question_list(self, questions: List[Dict], latency_ms: int) -> ToolResult:
        """Parse question list response."""
        if not questions:
            return ToolResult(
                status="success",
                summary="No questions found",
                structured_payload={"questions": []},
            )

        # Build summary and context
        question_summaries = []
        for q in questions[:3]:  # First 3 questions
            question_summaries.append(
                f"- Q{q.get('id')}: {q.get('text', 'N/A')[:60]}..."
            )

        summary = f"Retrieved {len(questions)} questions:\n" + "\n".join(question_summaries)

        # Build prompt context for AI
        prompt_context = self._build_question_prompt_context(questions)

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={
                "questions": questions,
                "count": len(questions),
            },
            prompt_context=prompt_context,
            meta={
                "latency_ms": latency_ms,
                "question_count": len(questions),
            },
        )

    def _parse_followup_hints(self, data: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse follow-up hints response."""
        hints = data.get("followUpHints") or []

        if not hints:
            return ToolResult(
                status="success",
                summary="No follow-up hints available",
                structured_payload={"hints": []},
            )

        summary = f"Follow-up suggestions:\n" + "\n".join(f"- {h}" for h in hints[:5])

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={"hints": hints},
            prompt_context=self._build_followup_prompt_context(hints),
            meta={"latency_ms": latency_ms, "hint_count": len(hints)},
        )

    def _parse_knowledge_documents(self, documents: List[Dict], latency_ms: int) -> ToolResult:
        """Parse knowledge documents (RAG) response."""
        if not documents:
            return ToolResult(
                status="success",
                summary="No knowledge documents found",
                structured_payload={"documents": []},
            )

        doc_summaries = []
        for doc in documents[:3]:
            title = doc.get("title", "Untitled")
            tags = doc.get("tags") or []
            doc_summaries.append(f"- {title} (tags: {', '.join(tags)})")

        summary = f"RAG retrieved {len(documents)} documents:\n" + "\n".join(doc_summaries)

        # Build knowledge context for AI
        knowledge_context = self._build_knowledge_prompt_context(documents)

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={"documents": documents},
            prompt_context=knowledge_context,
            meta={"latency_ms": latency_ms, "doc_count": len(documents)},
        )

    def _build_question_prompt_context(self, questions: List[Dict]) -> str:
        """Build prompt context from questions for AI."""
        context_parts = ["Available Questions:\n"]

        for i, q in enumerate(questions[:10], 1):  # Max 10 questions
            context_parts.append(
                f"{i}. [{q.get('code', 'N/A')}] {q.get('text', 'N/A')}\n"
                f"   Difficulty: {q.get('difficulty', 'N/A')}\n"
                f"   Tags: {', '.join(q.get('tags') or [])}\n"
                f"   Key Points: {', '.join(q.get('keyPoints') or [])}\n"
            )

        return "\n".join(context_parts)

    def _build_followup_prompt_context(self, hints: List[str]) -> str:
        """Build prompt context from follow-up hints."""
        return "Suggested Follow-up Questions:\n" + "\n".join(f"- {h}" for h in hints)

    def _build_knowledge_prompt_context(self, documents: List[Dict]) -> str:
        """Build prompt context from knowledge documents for RAG."""
        context_parts = ["Relevant Knowledge:\n"]

        for i, doc in enumerate(documents[:5], 1):  # Max 5 documents
            context_parts.append(
                f"Document {i}: {doc.get('title', 'Untitled')}\n"
                f"Tags: {', '.join(doc.get('tags') or [])}\n"
                f"Content:\n{doc.get('content', '')[:1000]}...\n"  # Limit content length
            )

        return "\n".join(context_parts)


def create_question_bank_adapter(settings: Dict[str, Any]) -> QuestionBankToolAdapter:
    """Factory function to create question bank adapter."""
    return QuestionBankToolAdapter(settings)