from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
import uuid

from app.core.database import Base


class UserRole(str, enum.Enum):
    """
    사용자 역할 열거형.
    
    Attributes:
        ADMIN: 관리자 역할 (모든 권한 보유)
        USER: 일반 사용자 역할
    """
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """
    사용자 엔티티 모델.
    
    Attributes:
        id: 사용자 고유 ID (UUID)
        email: 이메일 (고유, 인증용)
        password: 해시된 비밀번호
        role: 사용자 역할 (admin, user)
        created_at: 생성 일시
        updated_at: 수정 일시
        projects: 사용자가 생성한 프로젝트 목록
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    projects = relationship("Project", foreign_keys="Project.created_by", back_populates="creator")
    updated_projects = relationship("Project", foreign_keys="Project.updated_by", back_populates="updater")


class Project(Base):
    """
    프로젝트 엔티티 모델.
    
    Attributes:
        id: 프로젝트 고유 ID (UUID)
        name: 프로젝트명
        code: 프로젝트 코드
        client: 고객사명
        designer: 디자이너 이름
        developers: 개발자 목록 (콤마 구분)
        start_date: 프로젝트 시작일
        end_date: 프로젝트 마감일
        created_by: 생성자 ID
        updated_by: 업데이트자 ID
        created_at: 생성 일시
        updated_at: 수정 일시
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, index=True, nullable=False)
    client = Column(String(255), nullable=False)
    designer = Column(String(255), nullable=False)
    developers = Column(String(500), default="")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 설정
    creator = relationship("User", foreign_keys=[created_by], back_populates="projects")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_projects")
