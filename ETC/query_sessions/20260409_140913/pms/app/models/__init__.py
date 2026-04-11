"""데이터베이스 모델 정의"""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import datetime
from app.db import Base


class UserRole(str, enum.Enum):
    """사용자 역할 열거형"""
    PM = "pm"
    ADMIN = "admin"


class ProjectStatus(str, enum.Enum):
    """프로젝트 상태 열거형"""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class User(Base):
    """
    사용자 모델
    
    Attributes:
        id: 사용자 기본 키
        email: 사용자 이메일 (고유값)
        password: 해시된 비밀번호
        name: 사용자 이름
        role: 사용자 역할 (PM 또는 ADMIN)
        created_at: 생성일시
        updated_at: 업데이트일시
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.PM)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    projects = relationship("Project", back_populates="creator")
    assigned_projects = relationship("ProjectMember", back_populates="user")


class Project(Base):
    """
    프로젝트 모델
    
    Attributes:
        id: 프로젝트 기본 키
        name: 프로젝트 이름
        code: 프로젝트 코드 (고유값)
        client: 고객사 이름
        designer: 설계자 이름
        start_date: 시작 날짜
        end_date: 종료 날짜
        status: 프로젝트 상태
        description: 프로젝트 설명
        creator_id: 생성자 ID (외래키)
        created_at: 생성일시
        updated_at: 업데이트일시
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    client = Column(String(200), nullable=False)
    designer = Column(String(100))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING)
    description = Column(Text)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    creator = relationship("User", foreign_keys=[creator_id])
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    """
    프로젝트 멤버 연결 모델
    
    Attributes:
        id: 기본 키
        project_id: 프로젝트 ID (외래키)
        user_id: 사용자 ID (외래키)
        role: 프로젝트 내 역할
        joined_at: 가입일시
    """
    __tablename__ = "project_members"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(100))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="assigned_projects")


class Task(Base):
    """
    태스크 모델 (Gantt Chart 를 위한)
    
    Attributes:
        id: 태스크 기본 키
        project_id: 프로젝트 ID (외래키)
        name: 태스크 이름
        description: 태스크 설명
        status: 태스크 상태
        start_date: 시작 날짜
        end_date: 종료 날짜
        progress: 진행률 (0-100)
        assignee_id: 할당자 ID
        parent_task_id: 부모 태스크 ID (네스트드 태스크)
        priority: 우선순위
    """
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    progress = Column(Integer, default=0)
    assignee_id = Column(Integer, ForeignKey("users.id"))
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    priority = Column(String(20), default="medium")
    
    # Relationship
    project = relationship("Project", backref="tasks")
    assignee = relationship("User", foreign_keys=[assignee_id])
    subtasks = relationship("Task", backref="parent", remote_side=[id], cascade="all, delete-orphan")
