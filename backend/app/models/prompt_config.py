"""Prompt configuration models."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PromptConfigType(str, Enum):
    """Prompt configuration type."""

    STAGE_TEMPLATE = "stage_template"
    CUSTOM_INSTRUCTION = "custom"


class StagePromptConfig(BaseModel):
    """Stage-level prompt config."""

    stage: str = Field(..., description="阶段标识")
    name: str = Field(..., description="阶段名称")
    description: str = Field(..., description="阶段描述")
    max_turns: int = Field(..., ge=1, le=20, description="最大轮次")
    min_turns: int = Field(..., ge=1, le=20, description="最小轮次")
    time_allocation: int = Field(..., ge=1, le=60, description="时间分配（分钟）")
    system_instruction: str = Field(..., description="阶段系统指令")
    enabled: bool = Field(default=True, description="是否启用")
    order: int = Field(default=0, ge=0, description="阶段顺序")


class LLMRuntimeConfig(BaseModel):
    """Runtime config for LLM conversations."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="对话温度")
    max_tokens: int = Field(default=2000, ge=100, le=8000, description="最大输出 token")
    context_messages: int = Field(default=20, ge=1, le=100, description="保留上下文消息条数")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-P")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")
    model_override: str = Field(default="", description="可选模型覆盖，为空则使用系统模型")
    evaluation_temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="评估温度")


class InterviewPromptConfig(BaseModel):
    """Top-level prompt config."""

    base_system_prompt: str = Field(
        default="你是一位专业的技术面试官，具有丰富的招聘经验。你的任务是进行技术面试，评估候选人的技术能力、问题解决能力和沟通能力。",
        description="基础系统提示",
    )
    stages: Dict[str, StagePromptConfig] = Field(default_factory=dict, description="各阶段配置")
    llm: LLMRuntimeConfig = Field(default_factory=LLMRuntimeConfig, description="LLM 对话参数")

    def get_stage_config(self, stage: str) -> Optional[StagePromptConfig]:
        return self.stages.get(stage)

    def get_enabled_stages(self) -> List[str]:
        return [s for s, cfg in self.stages.items() if cfg.enabled]


DEFAULT_PROMPT_CONFIG = InterviewPromptConfig(
    base_system_prompt="你是一位专业的技术面试官，具有丰富的招聘经验。你的任务是进行技术面试，评估候选人的技术能力、问题解决能力和沟通能力。",
    stages={
        "welcome": StagePromptConfig(
            stage="welcome",
            name="开场介绍",
            description="欢迎候选人、介绍流程并开启对话",
            max_turns=2,
            min_turns=1,
            time_allocation=2,
            system_instruction="友好开场，鼓励候选人简洁自我介绍并进入第一个问题。",
            order=1,
        ),
        "technical": StagePromptConfig(
            stage="technical",
            name="技术问题",
            description="围绕岗位核心技能进行深入考察",
            max_turns=10,
            min_turns=5,
            time_allocation=18,
            system_instruction="根据回答深度逐步追问，关注技术理解与工程实践。",
            order=2,
        ),
        "scenario": StagePromptConfig(
            stage="scenario",
            name="情景问题",
            description="给出实际场景，评估分析与解决问题能力",
            max_turns=5,
            min_turns=2,
            time_allocation=8,
            system_instruction="用真实工作情景提问，重点看思路、权衡和决策。",
            order=3,
        ),
        "closing": StagePromptConfig(
            stage="closing",
            name="结束阶段",
            description="总结表现并礼貌收尾",
            max_turns=3,
            min_turns=2,
            time_allocation=2,
            system_instruction="简要总结亮点，给出积极反馈并结束面试。",
            order=4,
        ),
    },
)
