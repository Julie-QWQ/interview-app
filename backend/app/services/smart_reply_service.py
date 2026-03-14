"""Smart reply provider service."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from jinja2 import BaseLoader, Environment

from app.services.ai_service import get_ai_service
from app.services.prompt_service import prompt_service

logger = logging.getLogger(__name__)


class SmartReplyService:
    """Generate the next interviewer action for smart reply tool calls."""

    def __init__(self) -> None:
        self.template_env = Environment(loader=BaseLoader(), autoescape=False, trim_blocks=True, lstrip_blocks=True)

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        conversation = payload.get("conversation") or {}
        params = payload.get("params") or {}
        latest_user_message = str(conversation.get("latest_user_message") or "").strip()
        recent_messages = conversation.get("recent_messages") or []
        stage = str(payload.get("stage") or conversation.get("current_stage") or "technical").strip() or "technical"
        response_mode = str(params.get("response_mode") or "single_action").strip()
        if response_mode != "single_action":
            return self._error_response("Only response_mode=single_action is supported.")

        catalog = self._select_catalog(params)
        if not catalog:
            return self._error_response("No enabled smart reply actions are available.")

        fallback = self._fallback_result(latest_user_message, recent_messages, catalog)
        try:
            llm_result = self._generate_with_llm(
                payload=payload,
                latest_user_message=latest_user_message,
                recent_messages=recent_messages,
                stage=stage,
                catalog=catalog,
                trace_id=payload.get("trace_id"),
            )
        except Exception as exc:
            logger.warning("Smart reply LLM generation failed, fallback applied: %s", exc)
            llm_result = None

        structured = self._normalize_result(llm_result, catalog) if llm_result else None
        if not structured:
            structured = fallback

        logger.info(
            "Smart reply selected: trace_id=%s stage=%s action_key=%s action_label=%s utterance=%s strategy=%s",
            payload.get("trace_id"),
            stage,
            structured.get("action_key"),
            structured.get("action_label"),
            structured.get("utterance"),
            (structured.get("metadata") or {}).get("strategy", "unknown"),
        )

        return {
            "status": "success",
            "summary": f"Suggested next action: {structured['action_label']}",
            "structured_payload": structured,
            "cache_ttl_seconds": int(
                (prompt_service.get_tools_config().get("cache") or {}).get("smart_reply_ttl_seconds", 60)
            ),
            "errors": [],
        }

    def _select_catalog(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = params.get("smart_reply_catalog") or []
        allowed = {str(item).strip() for item in (params.get("allowed_actions") or []) if str(item).strip()}
        catalog: List[Dict[str, Any]] = []
        for item in actions:
            if not isinstance(item, dict):
                continue
            action_key = str(item.get("action_key") or "").strip()
            if not action_key:
                continue
            if allowed and action_key not in allowed:
                continue
            if not item.get("enabled", True):
                continue
            catalog.append(
                {
                    "action_key": action_key,
                    "label": str(item.get("label") or action_key).strip(),
                    "description": str(item.get("description") or "").strip(),
                    "utterance_templates": [
                        str(template).strip()
                        for template in (item.get("utterance_templates") or [])
                        if str(template).strip()
                    ],
                }
            )
        return catalog

    def _generate_with_llm(
        self,
        *,
        payload: Dict[str, Any],
        latest_user_message: str,
        recent_messages: List[Dict[str, Any]],
        stage: str,
        catalog: List[Dict[str, Any]],
        trace_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        prompt_cfg = self._tool_prompt_config(payload)
        prompt_context = self._build_prompt_context(payload, latest_user_message, recent_messages, stage, catalog)

        system_prompt = (
            str(prompt_cfg.get("system_prompt") or "").strip()
            or prompt_service.get_tool_prompt_config("smart_reply_engine").get("system_prompt", "")
        )
        user_prompt_template = (
            str(prompt_cfg.get("user_prompt_template") or "").strip()
            or prompt_service.get_tool_prompt_config("smart_reply_engine").get("user_prompt_template", "")
        )

        if not system_prompt or not user_prompt_template:
            return None

        user_prompt = self.template_env.from_string(user_prompt_template).render(**prompt_context).strip()
        response = get_ai_service().chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            trace_id=trace_id,
        )
        return self._parse_json_object(response)

    def _tool_prompt_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        params = payload.get("params") or {}
        configured = params.get("tool_prompt") or {}
        default_cfg = prompt_service.get_tool_prompt_config("smart_reply_engine")
        return {
            **default_cfg,
            **(configured if isinstance(configured, dict) else {}),
        }

    def _build_prompt_context(
        self,
        payload: Dict[str, Any],
        latest_user_message: str,
        recent_messages: List[Dict[str, Any]],
        stage: str,
        catalog: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        actions_text = "\n".join(
            [
                (
                    f"- action_key: {item['action_key']}\n"
                    f"  label: {item['label']}\n"
                    f"  description: {item['description'] or 'N/A'}\n"
                    f"  utterance_templates: {json.dumps(item['utterance_templates'], ensure_ascii=False)}"
                )
                for item in catalog
            ]
        )
        recent_messages_text = "\n".join(
            [
                f"{str(msg.get('role') or 'unknown')}: {str(msg.get('content') or '').strip()}"
                for msg in recent_messages[-6:]
                if str(msg.get("content") or "").strip()
            ]
        ) or "(empty)"

        return {
            "trace_id": payload.get("trace_id"),
            "stage": stage,
            "latest_user_message": latest_user_message,
            "recent_messages": recent_messages,
            "recent_messages_text": recent_messages_text,
            "allowed_actions_text": actions_text,
            "catalog": catalog,
            "candidate": payload.get("candidate") or {},
            "interview": payload.get("interview") or {},
            "conversation": payload.get("conversation") or {},
            "params": payload.get("params") or {},
        }

    def _normalize_result(self, result: Dict[str, Any], catalog: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(result, dict):
            return None
        by_key = {item["action_key"]: item for item in catalog}
        action_key = str(result.get("action_key") or "").strip()
        action = by_key.get(action_key)
        if not action:
            return None
        utterance = str(result.get("utterance") or "").strip()
        if not utterance:
            utterance = action["utterance_templates"][0] if action["utterance_templates"] else action["label"]
        rationale = str(result.get("rationale") or "").strip() or action["description"] or "Selected based on the latest answer."
        return {
            "action_key": action["action_key"],
            "action_label": str(result.get("action_label") or "").strip() or action["label"],
            "rationale": rationale,
            "utterance": utterance,
            "metadata": {
                "source": "interview-service",
                "strategy": "llm",
            },
        }

    def _fallback_result(
        self,
        latest_user_message: str,
        recent_messages: List[Dict[str, Any]],
        catalog: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        lowered = (latest_user_message or "").strip().lower()
        candidate = self._find_action(catalog, "clarify")
        rationale = "The answer is short or unclear, so clarify before moving on."

        if not lowered:
            candidate = self._find_action(catalog, "clarify") or catalog[0]
        elif any(token in lowered for token in ["什么意思", "什么", "没听懂", "再说", "刚才"]):
            candidate = self._find_action(catalog, "clarify") or catalog[0]
            rationale = "The candidate is asking for clarification."
        elif len(latest_user_message.strip()) <= 6:
            candidate = self._find_action(catalog, "clarify") or catalog[0]
            rationale = "The answer is too short, so clarify first."
        elif any(token in lowered for token in ["团队", "我们", "一起"]):
            candidate = self._find_action(catalog, "probe_contribution") or self._find_action(catalog, "probe_detail") or catalog[0]
            rationale = "The answer mentions team-level work, so ask about personal contribution."
        elif any(token in lowered for token in ["提升", "优化", "效果", "%", "效率"]):
            candidate = self._find_action(catalog, "challenge") or self._find_action(catalog, "probe_detail") or catalog[0]
            rationale = "The answer claims an outcome, so ask for evidence or risk details."
        elif self._recent_assistant_question_count(recent_messages) >= 2:
            candidate = self._find_action(catalog, "refocus") or self._find_action(catalog, "clarify") or catalog[0]
            rationale = "The conversation needs to be pulled back to the main line."
        else:
            candidate = self._find_action(catalog, "probe_detail") or catalog[0]
            rationale = "A detail-oriented follow-up is the safest next step."

        utterance = candidate["utterance_templates"][0] if candidate["utterance_templates"] else candidate["label"]
        return {
            "action_key": candidate["action_key"],
            "action_label": candidate["label"],
            "rationale": rationale,
            "utterance": utterance,
            "metadata": {
                "source": "interview-service",
                "strategy": "fallback",
            },
        }

    @staticmethod
    def _find_action(catalog: List[Dict[str, Any]], action_key: str) -> Optional[Dict[str, Any]]:
        for item in catalog:
            if item["action_key"] == action_key:
                return item
        return None

    @staticmethod
    def _recent_assistant_question_count(recent_messages: List[Dict[str, Any]]) -> int:
        count = 0
        for item in recent_messages[-4:]:
            if str(item.get("role") or "") == "assistant" and "?" in str(item.get("content") or ""):
                count += 1
        return count

    @staticmethod
    def _parse_json_object(content: str) -> Optional[Dict[str, Any]]:
        text = str(content or "").strip()
        if not text:
            return None
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None

    @staticmethod
    def _error_response(message: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "summary": "",
            "structured_payload": {},
            "cache_ttl_seconds": 0,
            "errors": [message],
        }


_smart_reply_service: Optional[SmartReplyService] = None


def get_smart_reply_service() -> SmartReplyService:
    """Get global smart reply service instance."""
    global _smart_reply_service
    if _smart_reply_service is None:
        _smart_reply_service = SmartReplyService()
    return _smart_reply_service


# Module-level convenience instance for direct import
smart_reply_service = get_smart_reply_service()
