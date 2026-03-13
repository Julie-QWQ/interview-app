"""Builder for assembling prompt template context incrementally."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, Optional

from jinja2 import Template


class PromptTemplateBuilder:
    """Incrementally build prompt context and render a Jinja2 template."""

    def __init__(self, template: Template):
        self._template = template
        self._context: Dict[str, Any] = {
            "base_system_prompt": "",
            "position_profile": None,
            "interviewer_profile": None,
            "interviewer_style_prompt": "",
            "interview": {
                "position": "未指定",
                "skills": [],
                "experience_level": "中级",
                "additional_requirements": "",
            },
            "stage": {
                "system_instruction": "",
            },
            "progress": None,
            "tool_context": {},
            "tool_context_combined": "",
            "tool_summary": "",
            "tool_constraints": [],
        }

    def with_base_system_prompt(self, value: str) -> "PromptTemplateBuilder":
        self._context["base_system_prompt"] = value or ""
        return self

    def with_position_profile(self, value: Optional[Dict[str, Any]]) -> "PromptTemplateBuilder":
        self._context["position_profile"] = deepcopy(value) if value else None
        return self

    def with_interviewer_profile(self, value: Optional[Dict[str, Any]]) -> "PromptTemplateBuilder":
        self._context["interviewer_profile"] = deepcopy(value) if value else None
        return self

    def with_interviewer_style_prompt(self, value: str) -> "PromptTemplateBuilder":
        self._context["interviewer_style_prompt"] = value or ""
        return self

    def with_interview(self, value: Optional[Dict[str, Any]]) -> "PromptTemplateBuilder":
        interview = deepcopy(self._context["interview"])
        if value:
            interview.update(value)
        interview["skills"] = interview.get("skills") or []
        self._context["interview"] = interview
        return self

    def with_stage(self, value: Optional[Dict[str, Any]]) -> "PromptTemplateBuilder":
        stage = deepcopy(self._context["stage"])
        if value:
            stage.update(value)
        self._context["stage"] = stage
        return self

    def with_stage_instruction(self, instruction: str) -> "PromptTemplateBuilder":
        return self.with_stage({"system_instruction": instruction or ""})

    def with_progress(
        self,
        value: Optional[Dict[str, Any]],
        *,
        current_turn: Optional[int] = None,
    ) -> "PromptTemplateBuilder":
        if not value:
            self._context["progress"] = None
            return self

        progress = deepcopy(value)
        if current_turn is not None:
            progress["current_turn"] = current_turn
        self._context["progress"] = progress
        return self

    def with_tool_context(
        self,
        value: Optional[Dict[str, str]],
        *,
        summary: str = "",
        constraints: Optional[list[str]] = None,
        combined: str = "",
    ) -> "PromptTemplateBuilder":
        self._context["tool_context"] = deepcopy(value) if value else {}
        self._context["tool_context_combined"] = combined or ""
        self._context["tool_summary"] = summary or ""
        self._context["tool_constraints"] = list(constraints or [])
        return self

    def build(self) -> str:
        rendered = self._template.render(**self._context)
        rendered = re.sub(r"\n{3,}", "\n\n", rendered)
        return rendered.strip()
