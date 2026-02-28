"""
AI对话服务
"""
import openai
import json
import logging
from typing import List, Dict, Optional
from .prompt_service import prompt_service

logger = logging.getLogger(__name__)


class AIService:
    """AI对话服务"""

    def __init__(self, settings):
        self.settings = settings
        self.client = openai.OpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url
        )

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        发起聊天完成请求

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数

        Returns:
            AI回复内容
        """
        try:
            response = self.client.chat.completions.create(
                model=kwargs.get('model', self.settings.ai_model),
                messages=messages,
                temperature=kwargs.get('temperature', self.settings.ai_temperature),
                max_tokens=kwargs.get('max_tokens', 2000)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI请求失败: {e}")
            raise

    def start_interview(self, interview_config: dict) -> str:
        """开始面试，获取开场问题"""
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始面试，先做自我介绍并提出第一个问题。"}
        ]

        return self.chat_completion(messages)

    def continue_interview(self, interview_config: dict, conversation_history: List[dict]) -> str:
        """继续面试对话"""
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话
        for msg in conversation_history[-20:]:  # 只保留最近20条消息
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        return self.chat_completion(messages)

    def evaluate_interview(self, interview_config: dict, conversation_history: List[dict]) -> dict:
        """评估面试表现"""
        system_prompt = prompt_service.get_evaluator_system_prompt()

        # 构建对话摘要
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history
        ])

        user_prompt = f"""
        请根据以下面试对话内容，评估候选人的表现。

        面试配置：
        - 职位：{interview_config.get('position')}
        - 技能：{', '.join(interview_config.get('skills', []))}
        - 经验级别：{interview_config.get('experience_level', '中级')}

        面试对话：
        {conversation_text}

        请按照系统提示中的格式返回JSON格式的评估报告。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.settings.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # 评估时使用较低的温度以获得更稳定的结果
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            logger.error(f"评估失败: {e}")
            # 返回默认评估
            return {
                "overall_score": 70,
                "dimension_scores": {
                    "technical": 70,
                    "problem_solving": 70,
                    "communication": 70,
                    "learning_potential": 70
                },
                "strengths": ["完成面试"],
                "weaknesses": ["评估系统暂时不可用"],
                "recommendation": "需要进一步评估",
                "feedback": "评估系统暂时不可用，请人工评估。"
            }


# 全局实例（稍后在应用初始化时创建）
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取AI服务实例"""
    if _ai_service is None:
        raise RuntimeError("AI服务未初始化")
    return _ai_service


def init_ai_service(settings):
    """初始化AI服务"""
    global _ai_service
    _ai_service = AIService(settings)
