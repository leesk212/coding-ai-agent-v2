"""SQLAlchemy 모델 정의"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db import Base


class UserRole(str, enum.Enum):
    """사용자 역할 열거형"""
    
    PM = "pm"
    ADMIN = "admin"


class ProjectStatus(str, enum.Enum):
    """프로젝트 상태 열거형"""
    
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    """
    사용자 모델
    
    사용자 정보를 저장합니다.
    """
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.PM)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # 관계
    projects = relationship("Project", back_populates="creator", lazy="joined")
    tasks = relationship("Task", back_populates="assignee", lazy="joined")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"


class Project(Base):
    """
    프로젝트 모델
    
    프로젝트 정보를 저장합니다.
    """
    
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    client = Column(String(200), nullable=False)
    designer = Column(String(200), nullable=False)
    developers = Column(String(500), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING)
    description = Column(String(1000), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # 관계
    creator = relationship("User", back_populates="projects", foreign_keys=[creator_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan", lazy="joined")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', code='{self.code}')>"


class Task(Base):
    """
    태스크 모델
    
    프로젝트 태스크 정보를 저장합니다.
    """
    
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING)
    progress = Column(Integer, default=0, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # 관계
    project = relationship("Project", back_populates="tasks", lazy="joined")
    assignee = relationship("User", back_populates="tasks", foreign_keys=[assignee_id], lazy="joined")
    subtasks = relationship("Task", back_populates="parent", foreign_keys=[parent_task_id], lazy="joined")
    parent = relationship("Task", back_populates="subtasks", remote_side=[id], lazy="joined")
    
    def __repr__(self):
        return f"<Task(id={self.id}, name='{self.name}', project_id={self.project_id})>"
