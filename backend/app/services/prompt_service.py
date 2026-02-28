"""
Prompt管理服务
"""
from pathlib import Path
from typing import Optional
from app.db import database
from app.models.prompt_config import InterviewPromptConfig, DEFAULT_PROMPT_CONFIG


class PromptService:
    """Prompt管理服务（支持数据库配置）"""

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self.prompts_dir = Path(prompts_dir)
        self._prompts = self._load_prompts()
        self._db_config = None

    def _load_prompts(self) -> dict:
        """加载所有prompt配置（从YAML文件，作为备用）"""
        prompt_file = self.prompts_dir / "system_prompts.yaml"
        if not prompt_file.exists():
            return {}

        import yaml
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_db_config(self) -> InterviewPromptConfig:
        """从数据库加载配置"""
        config_data = database.get_prompt_config('default')
        if config_data:
            return InterviewPromptConfig(**config_data)
        return DEFAULT_PROMPT_CONFIG

    def get_interviewer_system_prompt(self, interview_config: dict, use_db_config: bool = True) -> str:
        """获取面试官系统提示"""
        if use_db_config:
            # 使用数据库配置
            config = self._load_db_config()
            base_prompt = config.base_system_prompt
        else:
            # 使用 YAML 文件配置（备用）
            base_prompt = self._prompts.get('interviewer', {}).get('system', '')

        # 根据技能领域添加特定上下文
        skill_domain = interview_config.get('skill_domain', 'fullstack')
        
        if use_db_config:
            domain_config = config.get_skill_domain_config(skill_domain)
            if domain_config:
                base_prompt += f"\n\n## 本次面试领域：{domain_config.name}\n{domain_config.context}"
                if domain_config.focus_areas:
                    base_prompt += f"\n\n重点考察：\n" + "\n".join(f"- {area}" for area in domain_config.focus_areas)
        else:
            # 从 YAML 加载
            domain_context = self._prompts.get('skill_domains', {}).get(skill_domain, {}).get('context', '')
            if domain_context:
                base_prompt += f"\n\n## 本次面试领域：{skill_domain}\n{domain_context}"

        # 添加面试配置信息
        base_prompt += f"\n\n## 本次面试配置：\n"
        base_prompt += f"- 职位：{interview_config.get('position', '未指定')}\n"
        base_prompt += f"- 技能：{', '.join(interview_config.get('skills', []))}\n"
        base_prompt += f"- 经验级别：{interview_config.get('experience_level', '中级')}\n"

        if interview_config.get('additional_requirements'):
            base_prompt += f"\n## 额外要求：\n{interview_config['additional_requirements']}\n"

        return base_prompt

    def get_stage_instruction(self, stage: str) -> str:
        """获取指定阶段的系统指令"""
        config = self._load_db_config()
        stage_config = config.get_stage_config(stage)
        if stage_config:
            return stage_config.system_instruction
        return ""

    def reload_config(self):
        """重新加载配置（从数据库）"""
        self._db_config = None

    def get_evaluator_system_prompt(self) -> str:
        """获取评估系统提示"""
        return self._prompts.get('evaluator', {}).get('system', '')

    def get_interview_welcome_message(self, interview_config: dict) -> str:
        """获取面试开场欢迎消息"""
        return (
            f"你好 {interview_config.get('candidate_name', '候选人')}！\n\n"
            f"欢迎参加{interview_config.get('position', '技术岗位')}的面试。"
            f"我是今天的面试官，这次面试预计将持续{interview_config.get('duration_minutes', 30)}分钟左右。\n\n"
            f"我们将主要考察以下技能领域：{', '.join(interview_config.get('skills', []))}\n\n"
            f"让我们开始吧！首先，请简单介绍一下你自己和你的技术背景。"
        )

    def reload_prompts(self):
        """重新加载prompts"""
        self._prompts = self._load_prompts()


# 全局实例
prompt_service = PromptService()
