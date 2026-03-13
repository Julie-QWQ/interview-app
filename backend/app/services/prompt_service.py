"""Prompt management service backed by config files."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.db import database
from app.models.prompt_config import DEFAULT_PROMPT_CONFIG, InterviewPromptConfig
from app.services.prompt_builder import PromptTemplateBuilder
from config.settings import settings


LEGACY_INTERVIEWER_PROMPT_MAP = {
    "analytical": "你是一位分析型技术面试官。重点追问技术原理、方案取舍、边界条件和性能影响。提问直接，允许适度施压，但不要失去礼貌。",
    "guided": "你是一位引导型技术面试官。擅长循序渐进地提问，在候选人表达不清时帮助其聚焦，但不要直接给答案。",
    "behavioral": "你是一位行为导向型面试官。重点要求候选人结合真实项目经历，说明背景、行动、结果和个人贡献。",
}

class PromptService:
    """Prompt service backed by YAML config and Jinja2 templates."""

    def __init__(self, prompts_dir: str | None = None, config_path: str | None = None):
        base_dir = Path(__file__).resolve().parents[2]
        self.prompts_dir = Path(prompts_dir) if prompts_dir else base_dir / "prompts"
        self.config_path = Path(config_path) if config_path else base_dir / "config" / "config.yaml"
        self.template_name = "interviewer_system_prompt.j2"
        self.default_template_name = "interviewer_system_prompt.default.j2"
        self.environment = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @staticmethod
    def _normalize_config_data(config_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not config_data:
            return DEFAULT_PROMPT_CONFIG.model_dump()

        normalized = DEFAULT_PROMPT_CONFIG.model_dump()
        for key, value in config_data.items():
            if value is not None:
                normalized[key] = value

        raw_tools = config_data.get("tools") or {}
        normalized_tools = {
            **normalized.get("tools", {}),
            **raw_tools,
        }

        default_tools = DEFAULT_PROMPT_CONFIG.model_dump().get("tools", {})
        default_providers = default_tools.get("providers") or {}
        raw_providers = raw_tools.get("providers") or {}
        normalized_tools["providers"] = {
            **default_providers,
            **raw_providers,
        }
        default_tool_prompts = default_tools.get("tool_prompts") or {}
        raw_tool_prompts = raw_tools.get("tool_prompts") or {}
        normalized_tools["tool_prompts"] = {
            **default_tool_prompts,
            **raw_tool_prompts,
        }
        smart_reply_provider = normalized_tools["providers"].get("smart_reply_engine") or {}
        default_smart_reply_provider = default_providers.get("smart_reply_engine") or {}
        if not str(smart_reply_provider.get("url") or "").strip():
            normalized_tools["providers"]["smart_reply_engine"] = {
                **smart_reply_provider,
                "url": default_smart_reply_provider.get("url", ""),
            }

        default_bindings = default_tools.get("bindings") or {}
        raw_bindings = raw_tools.get("bindings") or {}
        normalized_bindings = {}
        for stage_key, default_binding in default_bindings.items():
            raw_binding = raw_bindings.get(stage_key) or {}
            default_trigger_map = default_binding.get("trigger_map") or {}
            raw_trigger_map = raw_binding.get("trigger_map") or {}
            merged_trigger_map = {}
            for trigger_key, tool_names in default_trigger_map.items():
                raw_tool_names = list(raw_trigger_map.get(trigger_key) or [])
                merged_list = list(raw_tool_names)
                for tool_name in tool_names:
                    if tool_name not in merged_list:
                        merged_list.append(tool_name)
                merged_trigger_map[trigger_key] = merged_list
            for trigger_key, tool_names in raw_trigger_map.items():
                if trigger_key not in merged_trigger_map:
                    merged_trigger_map[trigger_key] = list(tool_names or [])
            normalized_bindings[stage_key] = {
                **default_binding,
                **raw_binding,
                "trigger_map": merged_trigger_map,
            }
        for stage_key, raw_binding in raw_bindings.items():
            if stage_key not in normalized_bindings:
                normalized_bindings[stage_key] = raw_binding
        normalized_tools["bindings"] = normalized_bindings

        normalized["tools"] = normalized_tools
        return normalized

    def _load_file_config(self) -> InterviewPromptConfig:
        raw_config = settings.get_all()
        ai_config = raw_config.get("ai") or {}
        prompt_config_data = {
            "base_system_prompt": raw_config.get("base_system_prompt")
            or DEFAULT_PROMPT_CONFIG.base_system_prompt,
            "interviewer_style_prompt": raw_config.get("interviewer_style_prompt")
            or DEFAULT_PROMPT_CONFIG.interviewer_style_prompt,
            "tool_context_template": raw_config.get("tool_context_template")
            or DEFAULT_PROMPT_CONFIG.tool_context_template,
            "stages": raw_config.get("stages")
            or {key: value.model_dump() for key, value in DEFAULT_PROMPT_CONFIG.stages.items()},
            "llm": raw_config.get("llm")
            or {
                **DEFAULT_PROMPT_CONFIG.llm.model_dump(),
                "temperature": ai_config.get("temperature", DEFAULT_PROMPT_CONFIG.llm.temperature),
                "model_override": ai_config.get("model", ""),
            },
            "tools": raw_config.get("tools")
            or DEFAULT_PROMPT_CONFIG.tools.model_dump(),
        }
        return InterviewPromptConfig(**self._normalize_config_data(prompt_config_data))

    def _build_file_config_payload(self, config: InterviewPromptConfig) -> dict:
        payload = config.model_dump()
        payload.pop("interviewer_system_template", None)
        return payload

    def _write_config_file(self, config: InterviewPromptConfig) -> None:
        current = settings.get_all()
        prompt_payload = self._build_file_config_payload(config)
        merged = {
            **current,
            **prompt_payload,
        }
        settings.replace_all(merged)

    def _template_path(self) -> Path:
        return self.prompts_dir / self.template_name

    def _default_template_path(self) -> Path:
        return self.prompts_dir / self.default_template_name

    def _load_file_template_source(self) -> str:
        return self._template_path().read_text(encoding="utf-8")

    def _load_default_template_source(self) -> str:
        default_path = self._default_template_path()
        if default_path.exists():
            return default_path.read_text(encoding="utf-8")
        return self._load_file_template_source()

    def get_default_interviewer_system_template(self) -> str:
        return self._load_default_template_source()

    def get_prompt_config_data(self) -> Dict[str, Any]:
        config = self._load_file_config()
        config_data = config.model_dump()
        config_data["interviewer_system_template"] = self.get_active_interviewer_system_template()
        return config_data

    def get_default_prompt_config_data(self) -> Dict[str, Any]:
        config_data = DEFAULT_PROMPT_CONFIG.model_dump()
        config_data["interviewer_system_template"] = self.get_default_interviewer_system_template()
        return config_data

    def get_active_interviewer_system_template(self, config: Optional[InterviewPromptConfig] = None) -> str:
        _ = config
        return self._load_file_template_source()

    def save_prompt_config(self, config: InterviewPromptConfig) -> None:
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        template_source = (config.interviewer_system_template or "").strip() or self.get_default_interviewer_system_template()
        self._template_path().write_text(template_source, encoding="utf-8")
        self._write_config_file(config)
        self.reload_prompts()

    def reset_prompt_config(self) -> Dict[str, Any]:
        default_config = deepcopy(DEFAULT_PROMPT_CONFIG)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self._template_path().write_text(self.get_default_interviewer_system_template(), encoding="utf-8")
        self._write_config_file(default_config)
        self.reload_prompts()
        return self.get_default_prompt_config_data()

    def _load_template(self):
        try:
            return self.environment.get_template(self.template_name)
        except TemplateNotFound as exc:
            raise FileNotFoundError(f"Prompt template not found: {self._template_path()}") from exc

    @staticmethod
    def _normalize_position_profile(profile: Optional[dict]) -> Optional[Dict[str, Any]]:
        if not profile:
            return None

        config = profile.get("position_config") or {}
        skill_req = config.get("skill_requirements") or {}
        normalized = {
            "name": profile.get("position_name") or "",
            "description": profile.get("position_description") or "",
            "core_skills": skill_req.get("core_skills") or [],
            "ability_weights": config.get("ability_weights") or {},
        }
        return normalized if any(normalized.values()) else None

    @staticmethod
    def _normalize_interviewer_profile(profile: Optional[dict]) -> Optional[Dict[str, Any]]:
        if not profile:
            return None

        config = profile.get("interviewer_config") or {}
        style = config.get("style") or {}
        defaults = settings.interviewer_meta_map.get(profile.get("interviewer_plugin_id"), {})
        prompt = (
            config.get("prompt")
            or config.get("prompt_template")
            or LEGACY_INTERVIEWER_PROMPT_MAP.get(style.get("questioning_style"), "")
        )
        normalized = {
            "name": profile.get("interviewer_name") or "",
            "description": profile.get("interviewer_description") or "",
            "prompt": prompt,
            "difficulty": config.get("difficulty") or style.get("difficulty") or defaults.get("difficulty", "standard"),
            "style_tone": config.get("style_tone") or defaults.get("style_tone", "balanced"),
        }

        has_content = any(
            [
                normalized["name"],
                normalized["description"],
                normalized["prompt"],
                style,
            ]
        )
        return normalized if has_content else None

    @staticmethod
    def _normalize_interview_context(interview_config: Optional[dict]) -> Dict[str, Any]:
        interview_config = interview_config or {}
        return {
            "position": interview_config.get("position", "未指定"),
            "skills": interview_config.get("skills") or [],
            "experience_level": interview_config.get("experience_level", "中级"),
            "additional_requirements": interview_config.get("additional_requirements", ""),
        }

    def create_interviewer_prompt_builder(
        self,
        interview_config: Optional[dict],
        *,
        use_db_config: bool = True,
    ) -> PromptTemplateBuilder:
        _ = use_db_config

        config = self._load_file_config()
        interview_id = (interview_config or {}).get("id")
        interview_profile = database.get_interview_profile(interview_id) if interview_id else None

        return (
            PromptTemplateBuilder(self._load_template())
            .with_base_system_prompt(config.base_system_prompt)
            .with_interviewer_style_prompt(config.interviewer_style_prompt)
            .with_position_profile(self._normalize_position_profile(interview_profile))
            .with_interviewer_profile(self._normalize_interviewer_profile(interview_profile))
            .with_interview(self._normalize_interview_context(interview_config))
        )

    def get_interviewer_system_prompt(self, interview_config: dict, use_db_config: bool = True) -> str:
        return self.create_interviewer_prompt_builder(
            interview_config,
            use_db_config=use_db_config,
        ).build()

    def get_stage_instruction(self, stage: str) -> str:
        config = self._load_file_config()
        stage_config = config.get_stage_config(stage)
        return stage_config.system_instruction if stage_config else ""

    def get_stage_configs(self) -> list:
        """Return enabled stage configs in execution order."""
        config = self._load_file_config()
        stage_items = list(config.stages.values())
        default_order_map = {
            "welcome": 1,
            "technical": 2,
            "scenario": 3,
            "closing": 4,
        }
        stage_items.sort(
            key=lambda s: (
                getattr(s, "order", 0) if getattr(s, "order", 0) > 0 else default_order_map.get(s.stage, 999),
                s.stage,
            )
        )
        enabled = [s for s in stage_items if s.enabled]
        return enabled or stage_items

    def get_first_stage(self) -> str:
        stages = self.get_stage_configs()
        return stages[0].stage if stages else "welcome"

    def get_llm_config(self) -> dict:
        config = self._load_file_config()
        return config.llm.model_dump()

    def get_tools_config(self) -> dict:
        config = self._load_file_config()
        return config.tools.model_dump()

    def get_tool_prompt_config(self, tool_name: str) -> dict:
        tools = self.get_tools_config() or {}
        return (tools.get("tool_prompts") or {}).get(tool_name, {}) or {}

    def get_interview_welcome_message(self, interview_config: dict) -> str:
        return (
            f"你好 {interview_config.get('candidate_name', '候选人')}，\n\n"
            f"欢迎参加 {interview_config.get('position', '技术岗位')} 的面试。"
            f"本次面试预计 {interview_config.get('duration_minutes', 30)} 分钟。\n"
            f"重点考察技能：{', '.join(interview_config.get('skills', []))}\n\n"
            "我们开始吧，请先简单介绍一下你自己。"
        )

    def reload_prompts(self):
        settings.reload()
        self.environment.cache.clear()
        return None


prompt_service = PromptService()
