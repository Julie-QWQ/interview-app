"""
AI对话服务
"""
import openai
import json
import logging
from typing import List, Dict, Optional
from .prompt_service import prompt_service
from app.models.interview_stage import InterviewStage, InterviewProgress, STAGE_CONFIGS

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

    def chat_completion_stream(self, messages: List[Dict[str, str]], **kwargs):
        """
        发起流式聊天完成请求

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            str: 每次生成的文本片段
        """
        try:
            stream = self.client.chat.completions.create(
                model=kwargs.get('model', self.settings.ai_model),
                messages=messages,
                temperature=kwargs.get('temperature', self.settings.ai_temperature),
                max_tokens=kwargs.get('max_tokens', 2000),
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"AI流式请求失败: {e}")
            raise

    def start_interview(self, interview_config: dict) -> str:
        """开始面试，获取开场问题"""
        # 获取基础系统提示
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)
        
        # 添加开场阶段的系统指令
        stage_config = STAGE_CONFIGS[InterviewStage.WELCOME]
        system_prompt += f"\n\n{stage_config.system_instruction}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始面试，先做自我介绍并提出第一个问题。"}
        ]

        return self.chat_completion(messages)

    def continue_interview(self, interview_config: dict, conversation_history: List[dict], 
                          current_stage: str = None) -> str:
        """继续面试对话（带阶段感知）"""
        # 获取基础系统提示
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)
        
        # 确定当前阶段
        progress_manager = InterviewProgress(interview_config.get('duration_minutes', 30))
        current_turn = len([m for m in conversation_history if m['role'] == 'assistant'])
        
        if current_stage:
            # 如果传入了当前阶段，使用它
            stage = InterviewStage(current_stage)
        else:
            # 否则根据轮次自动判断
            stage = progress_manager.determine_stage(current_turn)
        
        # 添加当前阶段的系统指令
        stage_config = STAGE_CONFIGS[stage]
        system_prompt += f"\n\n{stage_config.system_instruction}"
        
        # 添加进度信息
        progress_info = progress_manager.calculate_progress(current_turn, stage)
        system_prompt += f"""

【面试进度信息】
- 当前阶段：{progress_info['stage_name']}（第 {current_turn} 轮对话）
- 本阶段进度：{progress_info['turn_in_stage']}/{progress_info['stage_max_turns']} 问题
- 总体进度：{progress_info['overall_progress']}%
- 剩余轮次：约 {progress_info['remaining_turns']} 轮

请根据进度合理控制节奏和内容深度。"""

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话
        for msg in conversation_history[-20:]:  # 只保留最近20条消息
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        return self.chat_completion(messages)

    def continue_interview_stream(self, interview_config: dict, conversation_history: List[dict],
                                  current_stage: str = None):
        """继续面试对话（流式输出，带阶段感知）"""
        # 获取基础系统提示
        system_prompt = prompt_service.get_interviewer_system_prompt(interview_config)
        
        # 确定当前阶段
        progress_manager = InterviewProgress(interview_config.get('duration_minutes', 30))
        current_turn = len([m for m in conversation_history if m['role'] == 'assistant'])
        
        if current_stage:
            stage = InterviewStage(current_stage)
        else:
            stage = progress_manager.determine_stage(current_turn)
        
        # 添加当前阶段的系统指令
        stage_config = STAGE_CONFIGS[stage]
        system_prompt += f"\n\n{stage_config.system_instruction}"
        
        # 添加进度信息
        progress_info = progress_manager.calculate_progress(current_turn, stage)
        system_prompt += f"""

【面试进度信息】
- 当前阶段：{progress_info['stage_name']}（第 {current_turn} 轮对话）
- 本阶段进度：{progress_info['turn_in_stage']}/{progress_info['stage_max_turns']} 问题
- 总体进度：{progress_info['overall_progress']}%
- 剩余轮次：约 {progress_info['remaining_turns']} 轮

请根据进度合理控制节奏和内容深度。"""

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话
        for msg in conversation_history[-20:]:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        yield from self.chat_completion_stream(messages)

    def determine_current_stage(self, conversation_history: List[dict], 
                                duration_minutes: int = 30) -> InterviewStage:
        """
        根据对话历史确定当前应该处于的阶段
        
        Returns:
            InterviewStage 枚举值
        """
        progress_manager = InterviewProgress(duration_minutes)
        current_turn = len([m for m in conversation_history if m['role'] == 'assistant'])
        return progress_manager.determine_stage(current_turn)

    def get_interview_progress(self, conversation_history: List[dict], 
                              current_stage: str, duration_minutes: int = 30) -> dict:
        """获取面试进度信息"""
        progress_manager = InterviewProgress(duration_minutes)
        stage = InterviewStage(current_stage)
        current_turn = len([m for m in conversation_history if m['role'] == 'assistant'])
        return progress_manager.calculate_progress(current_turn, stage)

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
