"""Prompt and tool configuration models."""

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


class ToolProviderConfig(BaseModel):
    """HTTP provider config for one external tool."""

    description: str = Field(default="", description="工具描述")
    mode: str = Field(default="url", description="工具执行模式：url 或 llm")
    enabled: bool = Field(default=False, description="是否启用该工具")
    url: str = Field(default="", description="工具 HTTP 地址")
    headers: Dict[str, str] = Field(default_factory=dict, description="附加请求头")


class ToolPromptConfig(BaseModel):
    """Prompt config for one tool."""

    system_prompt: str = Field(default="", description="工具 system prompt")
    user_prompt_template: str = Field(default="", description="工具 user prompt 模板")
    context_label: str = Field(default="", description="工具结果注入主 prompt 时的标题")
    result_prompt_template: str = Field(default="", description="工具结果转换为主 prompt 上下文的模板")


class SmartReplyActionConfig(BaseModel):
    """One configurable smart-reply action."""

    action_key: str = Field(..., description="行为唯一标识")
    enabled: bool = Field(default=True, description="是否启用")
    label: str = Field(default="", description="行为展示名")
    description: str = Field(default="", description="行为说明")
    utterance_templates: List[str] = Field(default_factory=list, description="候选语料")


class SmartReplyCatalogConfig(BaseModel):
    """Configurable action catalog for smart reply engine."""

    actions: List[SmartReplyActionConfig] = Field(default_factory=list, description="行为列表")


class StageToolBindingConfig(BaseModel):
    """Tool binding config for one interview stage."""

    trigger_map: Dict[str, List[str]] = Field(default_factory=dict, description="触发器到工具列表的映射")
    cache_only: bool = Field(default=False, description="是否只使用缓存结果")


class ToolTimeoutConfig(BaseModel):
    """Timeout config for tool orchestration."""

    chat_seconds: float = Field(default=5.0, ge=0.1, le=30.0, description="对话链路超时")
    prefetch_seconds: float = Field(default=4.0, ge=0.1, le=60.0, description="预取链路超时")


class ToolCacheConfig(BaseModel):
    """Cache config for tool orchestration."""

    question_bank_top_k: int = Field(default=5, ge=1, le=50, description="题库检索 Top K")
    followup_top_k: int = Field(default=3, ge=1, le=20, description="追问建议 Top K")
    smart_reply_ttl_seconds: int = Field(default=60, ge=0, le=3600, description="智能回复缓存秒数")


class ToolsRuntimeConfig(BaseModel):
    """Top-level tools config."""

    providers: Dict[str, ToolProviderConfig] = Field(default_factory=dict, description="工具提供方配置")
    tool_prompts: Dict[str, ToolPromptConfig] = Field(default_factory=dict, description="工具 prompt 配置")
    bindings: Dict[str, StageToolBindingConfig] = Field(default_factory=dict, description="阶段工具绑定配置")
    timeouts: ToolTimeoutConfig = Field(default_factory=ToolTimeoutConfig, description="工具超时配置")
    cache: ToolCacheConfig = Field(default_factory=ToolCacheConfig, description="工具缓存配置")
    smart_reply_catalog: SmartReplyCatalogConfig = Field(default_factory=SmartReplyCatalogConfig, description="智能回复行为目录")


class InterviewPromptConfig(BaseModel):
    """Top-level prompt config."""

    base_system_prompt: str = Field(
        default="你是一位专业的技术面试官，具有丰富的招聘经验。你的任务是进行技术面试，评估候选人的技术能力、问题解决能力和沟通能力。",
        description="基础系统提示",
    )
    interviewer_style_prompt: str = Field(
        default=(
            "请严格遵守以下说话规则：\n\n"
            "【角色定位】\n"
            "- 你是一位真实面试官，正在进行正式模拟面试。\n"
            "- 你说话应当自然、简洁、克制、口语化，像真实的人类面试官。\n"
            "- 你需要根据候选人的回答动态追问，而不是机械地轮流提问。\n\n"
            "【语言风格】\n"
            "- 每次回复尽量简短，通常控制在 1~3 句。\n"
            "- 优先使用短句、口语句、自然提问句，不要长篇大论。\n"
            "- 允许少量自然口语过渡词，例如“好”“嗯”“行”“等一下”“我追问一下”“展开说说”。\n"
            "- 不要每次都使用完整、正式、书面化的表达。\n"
            "- 不要像主持人、老师或客服一样说话。\n\n"
            "【禁止事项】\n"
            "- 不要频繁说“感谢你的回答”“非常好”“非常不错”“很好，请继续”。\n"
            "- 不要总是总结候选人刚才的话。\n"
            "- 不要主动替候选人补全答案。\n"
            "- 不要主动给出答题思路、标准答案或教学式提示。\n"
            "- 不要把问题包装成很长的说明。\n"
            "- 不要使用“接下来我将从……几个方面进行提问”这类强书面语。\n"
            "- 不要频繁使用“请你详细介绍一下……”这类机械句式。\n"
            "- 不要把自己说成 AI、助手、语言模型。\n\n"
            "【对话行为】\n"
            "- 如果候选人回答太泛，直接要求具体化。\n"
            "- 如果候选人只讲团队成果，追问其个人贡献。\n"
            "- 如果候选人声称效果很好，追问证据、指标或实验结果。\n"
            "- 如果候选人跑题，直接拉回问题本身。\n"
            "- 如果候选人回答较好，可以继续深挖边界条件、失败情况、替代方案。\n"
            "- 每轮只推进一个主要问题点，不要一次问太多。\n\n"
            "【真实面试官风格】\n"
            "你更像这样说话：\n"
            "- “你具体做了哪部分？”\n"
            "- “展开说说这个细节。”\n"
            "- “这个结论怎么证明？”\n"
            "- “你说效果提升了，提升多少？”\n"
            "- “先别讲团队整体，讲你自己做的。”\n"
            "- “这个回答有点泛，拿例子说。”\n"
            "- “我打断一下，回到刚才那个问题。”\n"
            "- “如果线上延迟很高，你怎么处理？”\n\n"
            "你不要像这样说话：\n"
            "- “感谢你的精彩回答，接下来我想从系统设计、模型优化和工程部署三个维度进一步考察你的综合能力。”\n"
            "- “你的回答比较全面，但仍然可以从更多角度展开说明。”\n"
            "- “请你详细介绍一下你在该项目中承担的职责以及遇到的挑战。”\n\n"
            "请始终保持：\n"
            "自然、简洁、真实、克制、有追问感、有面试压力感，但不过度攻击。"
        ),
        description="面试官基本说话风格",
    )
    interviewer_system_template: str = Field(
        default="",
        description="面试官 system prompt 的 Jinja2 模板；为空时使用仓库默认模板",
    )
    tool_context_template: str = Field(
        default=(
            "{% for item in tool_context_items %}\n"
            "### {{ item.context_label }}\n"
            "{{ item.prompt_context }}\n"
            "{% if not loop.last %}\n\n{% endif %}"
            "{% endfor %}"
        ),
        description="工具结果组合后注入主 prompt 的 Jinja2 模板",
    )
    stages: Dict[str, StagePromptConfig] = Field(default_factory=dict, description="各阶段配置")
    llm: LLMRuntimeConfig = Field(default_factory=LLMRuntimeConfig, description="LLM 对话参数")
    tools: ToolsRuntimeConfig = Field(default_factory=ToolsRuntimeConfig, description="工具编排配置")

    def get_stage_config(self, stage: str) -> Optional[StagePromptConfig]:
        return self.stages.get(stage)

    def get_enabled_stages(self) -> List[str]:
        return [stage_key for stage_key, cfg in self.stages.items() if cfg.enabled]


def _default_smart_reply_actions() -> List[SmartReplyActionConfig]:
    return [
        SmartReplyActionConfig(
            action_key="ask_new_question",
            label="提新问题",
            description="当前回答已足够，可以切入下一个问题。",
            utterance_templates=[
                "我们进入下一个问题。",
                "这个点我了解了，接下来想换个角度问你。",
            ],
        ),
        SmartReplyActionConfig(
            action_key="probe_detail",
            label="追细节",
            description="继续深挖技术细节、方案细节或实现细节。",
            utterance_templates=[
                "你把这一部分的具体实现再展开讲讲。",
                "这里的关键细节是什么？请具体说明。",
            ],
        ),
        SmartReplyActionConfig(
            action_key="probe_contribution",
            label="追个人贡献",
            description="聚焦候选人在项目中的个人职责和实际产出。",
            utterance_templates=[
                "这里你个人具体负责了哪一部分？",
                "这个结果里，哪些是你亲自推动完成的？",
            ],
        ),
        SmartReplyActionConfig(
            action_key="challenge",
            label="质疑",
            description="对模糊、可疑或前后不一致的表述进行挑战。",
            utterance_templates=[
                "这个说法我想再核实一下，你的依据是什么？",
                "如果按你这个方案执行，风险点会在哪里？",
            ],
        ),
        SmartReplyActionConfig(
            action_key="clarify",
            label="澄清",
            description="候选人表达模糊、跳跃或缺少关键信息时先澄清。",
            utterance_templates=[
                "我先确认一下，你刚才的意思是？",
                "这里我理解得还不够清楚，你能换个方式再说一遍吗？",
            ],
        ),
        SmartReplyActionConfig(
            action_key="refocus",
            label="拉回主线",
            description="用户跑题、回避或信息噪声过多时拉回目标问题。",
            utterance_templates=[
                "我们先回到刚才那个核心问题。",
                "先聚焦在你刚提到的这个关键点上。",
            ],
        ),
        SmartReplyActionConfig(
            action_key="transition",
            label="转场",
            description="当前话题可以收束，准备切换到新的主题或阶段。",
            utterance_templates=[
                "这个部分先到这里，我们切到下一个主题。",
                "我想从另一个维度继续了解你。",
            ],
        ),
        SmartReplyActionConfig(
            action_key="close",
            label="收尾",
            description="当前轮次或阶段适合做简短收束。",
            utterance_templates=[
                "这个问题我了解得差不多了，我们做个小结。",
                "好的，这部分先收一下。",
            ],
        ),
    ]


def _default_tool_prompts() -> Dict[str, ToolPromptConfig]:
    return {
        "resume_analyzer": ToolPromptConfig(
            context_label="简历分析",
            result_prompt_template="{{ raw_prompt_context }}",
        ),
        "question_bank_retriever": ToolPromptConfig(
            context_label="题库检索",
            result_prompt_template="{{ raw_prompt_context }}",
        ),
        "followup_engine": ToolPromptConfig(
            context_label="追问建议",
            result_prompt_template="{{ raw_prompt_context }}",
        ),
        "smart_reply_engine": ToolPromptConfig(
            system_prompt=(
                "You are a smart interview action selector.\n"
                "Choose exactly one next interviewer action.\n"
                "Return JSON only with keys: action_key, action_label, rationale, utterance.\n"
                "Requirements:\n"
                "- action_key must be one of the allowed actions.\n"
                "- utterance must be one natural interviewer sentence in Chinese.\n"
                "- Keep rationale concise.\n"
                "- Prefer the provided utterance templates, but you may rewrite naturally.\n"
                "- Do not output markdown or code fences."
            ),
            user_prompt_template=(
                "stage: {{ stage }}\n"
                "latest_user_message: {{ latest_user_message or '(empty)' }}\n"
                "recent_messages:\n{{ recent_messages_text }}\n\n"
                "allowed_actions:\n{{ allowed_actions_text }}\n\n"
                "Choose the best next action for the interviewer."
            ),
            context_label="智能回复建议",
            result_prompt_template=(
                "- 建议行为: {{ structured_payload.action_label or structured_payload.action_key }}\n"
                "- 行为标识: {{ structured_payload.action_key }}\n"
                "- 行为意图: {{ structured_payload.rationale or '结合候选人最新回答决定下一步最合适的动作。' }}\n"
                "- 推荐语料: {{ structured_payload.utterance }}\n"
                "- 使用约束: 你可以自然改写推荐语料，但必须遵循该行为意图，单轮只执行一个主动作。"
            ),
        ),
    }


DEFAULT_PROMPT_CONFIG = InterviewPromptConfig(
    base_system_prompt="你是一位专业的技术面试官，具有丰富的招聘经验。你的任务是进行技术面试，评估候选人的技术能力、问题解决能力和沟通能力。",
    interviewer_style_prompt=InterviewPromptConfig.model_fields["interviewer_style_prompt"].default,
    interviewer_system_template="",
    tool_context_template=InterviewPromptConfig.model_fields["tool_context_template"].default,
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
    tools=ToolsRuntimeConfig(
        providers={
            "resume_analyzer": ToolProviderConfig(
                description="解析候选人简历，提取背景亮点、风险点和待核验项。",
                mode="url",
                enabled=False,
                url="",
                headers={},
            ),
            "question_bank_retriever": ToolProviderConfig(
                description="根据岗位、技能和阶段检索题库，返回候选题目与考察点。",
                mode="url",
                enabled=False,
                url="",
                headers={},
            ),
            "followup_engine": ToolProviderConfig(
                description="结合候选人当前回答生成追问建议、深挖方向和避免重复点。",
                mode="url",
                enabled=False,
                url="",
                headers={},
            ),
            "smart_reply_engine": ToolProviderConfig(
                description="判断面试官下一步行为，并返回对应语料建议。",
                mode="llm",
                enabled=False,
                url="",
                headers={},
            ),
        },
        tool_prompts=_default_tool_prompts(),
        bindings={
            "welcome": StageToolBindingConfig(
                trigger_map={"interview_start": ["resume_analyzer"]},
                cache_only=False,
            ),
            "technical": StageToolBindingConfig(
                trigger_map={
                    "stage_enter": ["question_bank_retriever"],
                    "user_turn": ["question_bank_retriever", "followup_engine", "smart_reply_engine"],
                },
                cache_only=False,
            ),
            "scenario": StageToolBindingConfig(
                trigger_map={
                    "stage_enter": ["question_bank_retriever"],
                    "user_turn": ["question_bank_retriever", "followup_engine", "smart_reply_engine"],
                },
                cache_only=False,
            ),
            "closing": StageToolBindingConfig(
                trigger_map={},
                cache_only=True,
            ),
        },
        timeouts=ToolTimeoutConfig(chat_seconds=5.0, prefetch_seconds=4.0),
        cache=ToolCacheConfig(question_bank_top_k=5, followup_top_k=3, smart_reply_ttl_seconds=60),
        smart_reply_catalog=SmartReplyCatalogConfig(actions=_default_smart_reply_actions()),
    ),
)
