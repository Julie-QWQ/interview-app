"""
数据模型和Schema定义
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """消息类型"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InterviewStatus(str, Enum):
    """面试状态"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SkillDomain(str, Enum):
    """技能领域"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    AI_ML = "ai_ml"
    DATA_ENGINEERING = "data_engineering"
    OTHER = "other"


# ==================== 请求模型 ====================

class CreateInterviewRequest(BaseModel):
    """创建面试请求"""
    candidate_name: str = Field(..., description="候选人姓名")
    position: str = Field(..., description="面试职位")
    skill_domain: SkillDomain = Field(..., description="技能领域")
    skills: List[str] = Field(..., description="技能列表", min_items=1)
    experience_level: str = Field(default="中级", description="经验级别：初级/中级/高级")
    duration_minutes: int = Field(default=30, description="预计面试时长（分钟）", ge=15, le=120)
    additional_requirements: Optional[str] = Field(None, description="额外要求")


class ChatMessage(BaseModel):
    """聊天消息"""
    content: str = Field(..., description="消息内容")


# ==================== 响应模型 ====================

class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: MessageType
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class InterviewResponse(BaseModel):
    """面试响应"""
    id: int
    candidate_name: str
    position: str
    skill_domain: SkillDomain
    skills: List[str]
    experience_level: str
    status: InterviewStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InterviewDetailResponse(InterviewResponse):
    """面试详情响应（包含消息）"""
    messages: List[MessageResponse]
    current_stage: Optional[str] = None
    stage_progress: Optional[dict] = None


class InterviewProgressResponse(BaseModel):
    """面试进度响应"""
    current_stage: str
    stage_name: str
    stage_description: str
    turn_in_stage: int
    stage_max_turns: int
    stage_progress: int
    overall_turn: int
    overall_progress: int
    remaining_turns: int


class EvaluationResponse(BaseModel):
    """评估响应"""
    interview_id: int
    overall_score: int
    dimension_scores: dict
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    feedback: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 数据库模型 ====================

class Interview:
    """面试数据模型（用于ORM）"""
    def __init__(self, id=None, candidate_name=None, position=None, skill_domain=None,
                 skills=None, experience_level=None, duration_minutes=None,
                 additional_requirements=None, status=InterviewStatus.CREATED):
        self.id = id
        self.candidate_name = candidate_name
        self.position = position
        self.skill_domain = skill_domain
        self.skills = skills or []
        self.experience_level = experience_level
        self.duration_minutes = duration_minutes
        self.additional_requirements = additional_requirements
        self.status = status
        self.created_at = datetime.utcnow()
        self.updated_at = None
        self.completed_at = None

    def to_dict(self):
        return {
            'id': self.id,
            'candidate_name': self.candidate_name,
            'position': self.position,
            'skill_domain': self.skill_domain,
            'skills': self.skills,
            'experience_level': self.experience_level,
            'duration_minutes': self.duration_minutes,
            'additional_requirements': self.additional_requirements,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'completed_at': self.completed_at
        }


class Message:
    """消息数据模型"""
    def __init__(self, id=None, interview_id=None, role=MessageType.ASSISTANT,
                 content=None):
        self.id = id
        self.interview_id = interview_id
        self.role = role
        self.content = content
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'interview_id': self.interview_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp
        }
