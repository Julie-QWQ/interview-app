"""Prompt management service."""

from pathlib import Path

from app.db import database
from app.models.prompt_config import DEFAULT_PROMPT_CONFIG, InterviewPromptConfig


class PromptService:
    """Prompt service backed by DB config."""

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self.prompts_dir = Path(prompts_dir)
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        prompt_file = self.prompts_dir / "system_prompts.yaml"
        if not prompt_file.exists():
            return {}

        import yaml

        with open(prompt_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_db_config(self) -> InterviewPromptConfig:
        config_data = database.get_prompt_config("default")
        if config_data:
            return InterviewPromptConfig(**config_data)
        return DEFAULT_PROMPT_CONFIG

    @staticmethod
    def _format_position_profile(profile: dict) -> str:
        if not profile:
            return "未配置岗位画像。"

        lines = []
        if profile.get("position_name"):
            lines.append(f"- 画像名称：{profile.get('position_name')}")
        if profile.get("position_description"):
            lines.append(f"- 画像描述：{profile.get('position_description')}")

        config = profile.get("position_config") or {}
        skill_req = config.get("skill_requirements") or {}
        core_skills = skill_req.get("core_skills") or []
        if core_skills:
            lines.append(f"- 核心技能：{', '.join(core_skills)}")

        ability_weights = config.get("ability_weights") or {}
        if ability_weights:
            weight_text = "、".join([f"{k}:{v}" for k, v in ability_weights.items()])
            lines.append(f"- 能力权重：{weight_text}")

        if not lines:
            return "岗位画像已绑定，但缺少详细配置。"
        return "\n".join(lines)

    @staticmethod
    def _format_interviewer_profile(profile: dict) -> str:
        if not profile:
            return "未配置面试官画像。"

        lines = []
        if profile.get("interviewer_name"):
            lines.append(f"- 画像名称：{profile.get('interviewer_name')}")
        if profile.get("interviewer_description"):
            lines.append(f"- 画像描述：{profile.get('interviewer_description')}")

        config = profile.get("interviewer_config") or {}
        style = config.get("style") or {}
        if style:
            lines.append(
                "- 提问风格："
                f"{style.get('questioning_style', 'standard')} / "
                f"节奏:{style.get('pace', 'moderate')} / "
                f"严格度:{style.get('strictness', '0.5')}"
            )

        characteristics = config.get("characteristics") or []
        if characteristics:
            lines.append(f"- 画像特征：{', '.join(characteristics)}")

        if not lines:
            return "面试官画像已绑定，但缺少详细配置。"
        return "\n".join(lines)

    def get_interviewer_system_prompt(self, interview_config: dict, use_db_config: bool = True) -> str:
        config = None
        if use_db_config:
            config = self._load_db_config()
            base_prompt = config.base_system_prompt
        else:
            base_prompt = self._prompts.get("interviewer", {}).get("system", "")

        interview_id = interview_config.get("id")
        interview_profile = database.get_interview_profile(interview_id) if interview_id else None

        if interview_profile:
            base_prompt += "\n\n## 本次面试领域：岗位画像\n"
            base_prompt += self._format_position_profile(interview_profile)
            base_prompt += "\n\n## 本次面试配置：面试官画像\n"
            base_prompt += self._format_interviewer_profile(interview_profile)
        else:
            # 插件式模型下，画像应始终存在；若缺失，仅保留通用兜底提示
            base_prompt += "\n\n## 本次面试领域：岗位画像\n- 未绑定岗位画像（使用通用技术面试策略）"
            base_prompt += "\n\n## 本次面试配置：面试官画像\n- 未绑定面试官画像（使用默认提问风格）"

        base_prompt += "\n\n## 面试基础参数：\n"
        base_prompt += f"- 职位：{interview_config.get('position', '未指定')}\n"
        base_prompt += f"- 技能：{', '.join(interview_config.get('skills', []))}\n"
        base_prompt += f"- 经验级别：{interview_config.get('experience_level', '中级')}\n"

        if interview_config.get("additional_requirements"):
            base_prompt += f"\n## 额外要求：\n{interview_config['additional_requirements']}\n"

        return base_prompt

    def get_stage_instruction(self, stage: str) -> str:
        config = self._load_db_config()
        stage_config = config.get_stage_config(stage)
        return stage_config.system_instruction if stage_config else ""

    def get_stage_configs(self) -> list:
        """Return enabled stage configs in execution order."""
        config = self._load_db_config()
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
        config = self._load_db_config()
        return config.llm.model_dump()

    def get_evaluator_system_prompt(self) -> str:
        return self._prompts.get("evaluator", {}).get("system", "")

    def get_interview_welcome_message(self, interview_config: dict) -> str:
        return (
            f"你好 {interview_config.get('candidate_name', '候选人')}，\n\n"
            f"欢迎参加 {interview_config.get('position', '技术岗位')} 的面试。"
            f"本次面试预计 {interview_config.get('duration_minutes', 30)} 分钟。\n\n"
            f"重点考察技能：{', '.join(interview_config.get('skills', []))}\n\n"
            "我们开始吧，请先简单介绍一下你自己。"
        )

    def reload_prompts(self):
        self._prompts = self._load_prompts()


prompt_service = PromptService()
