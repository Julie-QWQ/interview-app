"""
Prompt配置管理模块
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class PromptConfigType(str, Enum):
    """Prompt配置类型"""
    STAGE_TEMPLATE = "stage_template"      # 阶段模板
    SKILL_DOMAIN = "skill_domain"          # 技能领域
    CUSTOM_INSTRUCTION = "custom"           # 自定义指令


class StagePromptConfig(BaseModel):
    """阶段Prompt配置"""
    stage: str = Field(..., description="阶段标识 (welcome/technical/scenario/closing)")
    name: str = Field(..., description="阶段名称")
    description: str = Field(..., description="阶段描述")
    max_turns: int = Field(..., ge=1, le=20, description="最大轮次")
    min_turns: int = Field(..., ge=1, le=20, description="最小轮次")
    time_allocation: int = Field(..., ge=1, le=60, description="时间分配（分钟）")
    system_instruction: str = Field(..., description="系统指令内容")
    enabled: bool = Field(default=True, description="是否启用")


class SkillDomainConfig(BaseModel):
    """技能领域配置"""
    domain: str = Field(..., description="领域标识 (frontend/backend/fullstack/ai_ml/data_engineering/other)")
    name: str = Field(..., description="领域名称")
    context: str = Field(..., description="领域上下文说明")
    focus_areas: List[str] = Field(default_factory=list, description="重点考察领域")
    enabled: bool = Field(default=True, description="是否启用")


class InterviewPromptConfig(BaseModel):
    """面试Prompt配置总览"""
    base_system_prompt: str = Field(
        default="你是一位专业的技术面试官，具有丰富的招聘经验。",
        description="基础系统提示"
    )
    stages: Dict[str, StagePromptConfig] = Field(
        default_factory=dict,
        description="各阶段配置"
    )
    skill_domains: Dict[str, SkillDomainConfig] = Field(
        default_factory=dict,
        description="技能领域配置"
    )

    def get_stage_config(self, stage: str) -> Optional[StagePromptConfig]:
        """获取指定阶段配置"""
        return self.stages.get(stage)

    def get_skill_domain_config(self, domain: str) -> Optional[SkillDomainConfig]:
        """获取指定技能领域配置"""
        return self.skill_domains.get(domain)

    def get_enabled_stages(self) -> List[str]:
        """获取所有启用的阶段"""
        return [s for s, cfg in self.stages.items() if cfg.enabled]

    def get_enabled_domains(self) -> List[str]:
        """获取所有启用的技能领域"""
        return [d for d, cfg in self.skill_domains.items() if cfg.enabled]


# 默认配置
DEFAULT_PROMPT_CONFIG = InterviewPromptConfig(
    base_system_prompt="你是一位专业的技术面试官，具有丰富的招聘经验。你的任务是进行技术面试，评估候选人的技术能力、问题解决能力和沟通能力。",
    stages={
        "welcome": StagePromptConfig(
            stage="welcome",
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
        "technical": StagePromptConfig(
            stage="technical",
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
        "scenario": StagePromptConfig(
            stage="scenario",
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
        "closing": StagePromptConfig(
            stage="closing",
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
- 感谢候选人参与面试"""
        )
    },
    skill_domains={
        "frontend": SkillDomainConfig(
            domain="frontend",
            name="前端开发",
            context="前端开发领域关注：HTML/CSS/JavaScript基础、框架应用（React/Vue/Angular）、性能优化、工程化、用户体验等。",
            focus_areas=[
                "核心概念理解（闭包、原型链、异步编程等）",
                "框架原理和使用经验",
                "前端工程化和构建工具",
                "性能优化实践",
                "跨浏览器兼容性处理"
            ]
        ),
        "backend": SkillDomainConfig(
            domain="backend",
            name="后端开发",
            context="后端开发领域关注：编程语言、数据库、API设计、系统架构、性能优化、安全等。",
            focus_areas=[
                "编程语言基础和高级特性",
                "数据库设计和优化",
                "RESTful API设计规范",
                "缓存、消息队列等中间件使用",
                "系统安全和防护"
            ]
        ),
        "fullstack": SkillDomainConfig(
            domain="fullstack",
            name="全栈开发",
            context="全栈开发需要同时掌握前端和后端技能，理解整个Web应用的开发流程。",
            focus_areas=[
                "前后端技术栈的整合能力",
                "全栈开发经验",
                "系统设计能力",
                "DevOps基础知识",
                "项目规划和实施能力"
            ]
        )
    }
)
