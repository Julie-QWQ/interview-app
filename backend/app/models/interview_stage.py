"""
面试阶段管理模块
"""
from enum import Enum
from typing import Dict, List
from dataclasses import dataclass


class InterviewStage(Enum):
    """面试阶段枚举"""
    WELCOME = "welcome"           # 开场介绍
    TECHNICAL = "technical"       # 技术问题
    SCENARIO = "scenario"         # 情景问题
    CLOSING = "closing"           # 结束阶段


@dataclass
class StageConfig:
    """阶段配置"""
    name: str                     # 阶段名称
    description: str              # 阶段描述
    max_turns: int                # 最大轮次
    min_turns: int                # 最小轮次
    time_allocation: int          # 时间分配（分钟）
    system_instruction: str       # 系统指令


# 阶段配置表
STAGE_CONFIGS: Dict[InterviewStage, StageConfig] = {
    InterviewStage.WELCOME: StageConfig(
        name="开场介绍",
        description="欢迎候选人，介绍面试流程，了解基本背景",
        max_turns=2,
        min_turns=1,
        time_allocation=2,
        system_instruction="""【当前阶段：开场介绍】

任务目标：
1. 欢迎候选人，做简短自我介绍
2. 介绍本次面试的流程和时间安排
3. 引导候选人进行自我介绍
4. 提出第一个开放性问题

注意事项：
- 保持友好、专业的态度
- 让候选人感到放松
- 第一个问题要简单、开放，便于候选人展开"""
    ),

    InterviewStage.TECHNICAL: StageConfig(
        name="技术问题",
        description="针对岗位技能进行深入的技术考察",
        max_turns=10,
        min_turns=5,
        time_allocation=18,
        system_instruction="""【当前阶段：技术问题】

任务目标：
1. 深入考察候选人的技术能力
2. 涵盖理论知识和实际应用
3. 根据候选人回答深度调整问题难度
4. 评估技术广度和深度

提问策略：
- 从基础概念开始，逐步深入
- 结合候选人提到的项目经验提问
- 适时追问"为什么"和"如何"
- 可以要求候选人举例说明

进度控制：
- 预计问 5-10 个技术问题
- 根据回答质量调整问题数量
- 如果候选人基础较弱，可以适当减少深度问题"""
    ),

    InterviewStage.SCENARIO: StageConfig(
        name="情景问题",
        description="提供实际工作场景，评估问题解决思路",
        max_turns=5,
        min_turns=2,
        time_allocation=8,
        system_instruction="""【当前阶段：情景问题】

任务目标：
1. 提供实际工作场景让候选人分析
2. 评估问题解决思路和方法
3. 考察系统设计和架构能力
4. 评估沟通和表达能力

场景类型：
- 系统设计题（如设计一个XX系统）
- 问题排查题（如遇到XX问题如何排查）
- 方案选型题（如如何选择技术栈）
- 代码优化题（如如何优化这段代码）

注意事项：
- 场景要具体、有挑战性
- 关注候选人的分析思路
- 允许候选人提问澄清需求
- 评估解决方案的合理性"""
    ),

    InterviewStage.CLOSING: StageConfig(
        name="结束阶段",
        description="总结候选人表现，给出评估，询问候选人问题",
        max_turns=3,
        min_turns=2,
        time_allocation=2,
        system_instruction="""【当前阶段：结束阶段】

任务目标：
1. 简要总结候选人的表现
2. 给出初步的正面反馈
3. 询问候选人是否有问题
4. 礼貌地结束面试

总结要点：
- 提及候选人的 2-3 个亮点
- 保持正面、鼓励的态度
- 不要给出明确的录用/拒绝结论（这是评估系统的工作）
- 感谢候选人参与面试

结束话术示例：
"今天的面试就到这里。你在XX方面表现不错，对XX问题的理解很深入。有什么问题想问我吗？好的，感谢你的时间，我们会尽快反馈结果。"
"""
    ),
}


class InterviewProgress:
    """面试进度管理器"""

    def __init__(self, total_duration_minutes: int = 30):
        self.total_duration_minutes = total_duration_minutes

    def determine_stage(self, current_turn: int, elapsed_minutes: float = None) -> InterviewStage:
        """
        根据当前轮次确定面试阶段

        Args:
            current_turn: 当前对话轮次（从0开始）
            elapsed_minutes: 已用时间（可选）

        Returns:
            当前应该处于的阶段
        """
        # 基于轮次的阶段判断
        if current_turn == 0:
            return InterviewStage.WELCOME
        elif current_turn <= STAGE_CONFIGS[InterviewStage.WELCOME].max_turns:
            # 还在开场阶段
            return InterviewStage.WELCOME
        elif current_turn <= (STAGE_CONFIGS[InterviewStage.WELCOME].max_turns +
                            STAGE_CONFIGS[InterviewStage.TECHNICAL].max_turns):
            # 技术问题阶段
            return InterviewStage.TECHNICAL
        elif current_turn <= (STAGE_CONFIGS[InterviewStage.WELCOME].max_turns +
                            STAGE_CONFIGS[InterviewStage.TECHNICAL].max_turns +
                            STAGE_CONFIGS[InterviewStage.SCENARIO].max_turns):
            # 情景问题阶段
            return InterviewStage.SCENARIO
        else:
            # 结束阶段
            return InterviewStage.CLOSING

    def get_stage_info(self, stage: InterviewStage) -> StageConfig:
        """获取阶段配置"""
        return STAGE_CONFIGS[stage]

    def calculate_progress(self, current_turn: int, stage: InterviewStage) -> Dict:
        """
        计算面试进度

        Returns:
            包含进度信息的字典
        """
        # 计算当前阶段的总轮次
        turns_before_stage = 0
        for s in [InterviewStage.WELCOME, InterviewStage.TECHNICAL, InterviewStage.SCENARIO]:
            if s == stage:
                break
            turns_before_stage += STAGE_CONFIGS[s].max_turns

        stage_config = STAGE_CONFIGS[stage]
        turn_in_stage = max(0, current_turn - turns_before_stage)
        stage_progress = min(100, int((turn_in_stage / stage_config.max_turns) * 100))

        # 计算总体进度
        total_max_turns = sum(c.max_turns for c in STAGE_CONFIGS.values())
        overall_progress = min(100, int((current_turn / total_max_turns) * 100))

        return {
            "current_stage": stage.value,
            "stage_name": stage_config.name,
            "stage_description": stage_config.description,
            "turn_in_stage": turn_in_stage,
            "stage_max_turns": stage_config.max_turns,
            "stage_progress": stage_progress,
            "overall_turn": current_turn,
            "overall_progress": overall_progress,
            "remaining_turns": total_max_turns - current_turn,
        }
