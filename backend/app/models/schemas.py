"""Data models and API schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InterviewStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SkillDomain(str, Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    AI_ML = "ai_ml"
    DATA_ENGINEERING = "data_engineering"
    OTHER = "other"


class CreateInterviewRequest(BaseModel):
    """Create interview request for plugin-composition mode."""

    position_profile_id: str = Field(..., description="岗位画像 ID")
    interviewer_profile_id: str = Field(..., description="面试官画像 ID")
    resume_file_id: Optional[str] = Field(None, description="简历文件 ID（可选）")
    resume_text: Optional[str] = Field(None, description="解析后的简历文本（可选）")

    duration_minutes: int = Field(default=30, description="预计面试时长（分钟）", ge=15, le=120)
    additional_requirements: Optional[str] = Field(None, description="额外要求")


class ChatMessage(BaseModel):
    content: str = Field(..., description="消息内容")


class MessageResponse(BaseModel):
    id: int
    role: MessageType
    content: str
    timestamp: datetime
    parent_id: Optional[int] = None
    branch_id: Optional[str] = None
    tree_path: Optional[List[int]] = None
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True


class InterviewResponse(BaseModel):
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
    messages: List[MessageResponse]
    current_stage: Optional[str] = None
    stage_progress: Optional[dict] = None
    current_message_id: Optional[int] = None


class InterviewProgressResponse(BaseModel):
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


class Interview:
    """Interview ORM-like model."""

    def __init__(
        self,
        id=None,
        candidate_name=None,
        position=None,
        skill_domain=None,
        skills=None,
        experience_level=None,
        duration_minutes=None,
        additional_requirements=None,
        status=InterviewStatus.CREATED,
    ):
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
            "id": self.id,
            "candidate_name": self.candidate_name,
            "position": self.position,
            "skill_domain": self.skill_domain,
            "skills": self.skills,
            "experience_level": self.experience_level,
            "duration_minutes": self.duration_minutes,
            "additional_requirements": self.additional_requirements,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }


class Message:
    """Message ORM-like model."""

    def __init__(self, id=None, interview_id=None, role=MessageType.ASSISTANT, content=None):
        self.id = id
        self.interview_id = interview_id
        self.role = role
        self.content = content
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
