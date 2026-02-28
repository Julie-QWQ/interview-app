"""
Prompt管理服务
"""
import yaml
from pathlib import Path
from typing import Optional


class PromptService:
    """Prompt管理服务"""

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self.prompts_dir = Path(prompts_dir)
        self._prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """加载所有prompt配置"""
        prompt_file = self.prompts_dir / "system_prompts.yaml"
        if not prompt_file.exists():
            return {}

        with open(prompt_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_interviewer_system_prompt(self, interview_config: dict) -> str:
        """获取面试官系统提示"""
        base_prompt = self._prompts.get('interviewer', {}).get('system', '')

        # 根据技能领域添加特定上下文
        skill_domain = interview_config.get('skill_domain', 'fullstack')
        domain_context = self._prompts.get('skill_domains', {}).get(skill_domain, {}).get('context', '')

        # 构建完整的系统提示
        full_prompt = base_prompt

        if domain_context:
            full_prompt += f"\n\n## 本次面试领域：{skill_domain}\n{domain_context}"

        # 添加面试配置信息
        full_prompt += f"\n\n## 本次面试配置：\n"
        full_prompt += f"- 职位：{interview_config.get('position', '未指定')}\n"
        full_prompt += f"- 技能：{', '.join(interview_config.get('skills', []))}\n"
        full_prompt += f"- 经验级别：{interview_config.get('experience_level', '中级')}\n"

        if interview_config.get('additional_requirements'):
            full_prompt += f"\n## 额外要求：\n{interview_config['additional_requirements']}\n"

        return full_prompt

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
