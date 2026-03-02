"""
画像插件模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship

from app.db.database import Base


class ProfilePlugin(Base):
    """画像插件表"""
    __tablename__ = "profile_plugins"

    id = Column(Integer, primary_key=True, index=True)
    plugin_id = Column(String(50), unique=True, index=True, nullable=False, comment="插件唯一标识")
    type = Column(String(20), nullable=False, comment="插件类型: position/interviewer")
    name = Column(String(100), nullable=False, comment="插件名称")
    description = Column(Text, comment="插件描述")
    is_system = Column(Boolean, default=False, comment="是否系统预设")
    config = Column(JSON, comment="插件配置数据")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<ProfilePlugin({self.type}: {self.name})>"


class InterviewProfile(Base):
    """面试与画像关联表"""
    __tablename__ = "interview_profiles"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, nullable=False, comment="面试ID")
    position_plugin_id = Column(String(50), comment="岗位画像插件ID")
    interviewer_plugin_id = Column(String(50), comment="面试官画像插件ID")
    custom_config = Column(JSON, comment="自定义配置(覆盖预设)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<InterviewProfile(interview_id={self.interview_id})>"
