from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from app.models import UserRole


# User Schemas
class UserBase(BaseModel):
    """
    사용자 공통 스키마.
    """
    email: EmailStr
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    """
    사용자 생성 요청 스키마.
    """
    password: str
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        비밀번호 검증: 최소 8 자 이상.
        """
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8 자 이상이어야 합니다.")
        return v


class UserUpdate(BaseModel):
    """
    사용자 업데이트 요청 스키마.
    """
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < 8:
            raise ValueError("비밀번호는 최소 8 자 이상이어야 합니다.")
        return v


class UserResponse(UserBase):
    """
    사용자 응답 스키마.
    """
    id: int
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """
    사용자 로그인 요청 스키마.
    """
    email: EmailStr
    password: str


# Project Schemas
class ProjectBase(BaseModel):
    """
    프로젝트 공통 스키마.
    """
    name: str
    code: str
    client: str
    designer: str
    developers: Optional[str] = ""
    start_date: datetime
    end_date: datetime
    
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: datetime, info) -> datetime:
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("마감일은 시작일 이후여야 합니다.")
        return v


class ProjectCreate(ProjectBase):
    """
    프로젝트 생성 요청 스키마.
    """
    pass


class ProjectUpdate(BaseModel):
    """
    프로젝트 업데이트 요청 스키마.
    """
    name: Optional[str] = None
    code: Optional[str] = None
    client: Optional[str] = None
    designer: Optional[str] = None
    developers: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is None:
            return v
        if "start_date" in info.data and info.data["start_date"] and v < info.data["start_date"]:
            raise ValueError("마감일은 시작일 이후여야 합니다.")
        return v


class ProjectResponse(BaseModel):
    """
    프로젝트 응답 스키마.
    """
    id: int
    name: str
    code: str
    client: str
    designer: str
    developers: str
    start_date: datetime
    end_date: datetime
    created_by: int
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Gantt Data Schema
class GanttTask(BaseModel):
    """
    간트 차트 태스크 스키마.
    """
    id: int
    name: str
    code: str
    start_date: datetime
    end_date: datetime
    progress: int = 0
    assignee: Optional[str] = None
    
    class Config:
        from_attributes = True


class GanttResponse(BaseModel):
    """
    간트 차트 데이터 응답 스키마.
    """
    tasks: List[GanttTask]
    meta: dict
    
    class Config:
        from_attributes = True


# Auth Token Schema
class Token(BaseModel):
    """
    JWT 토큰 응답 스키마.
    """
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    
    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """
    JWT 토큰 데이터 스키마.
    """
    user_id: Optional[int] = None
    role: Optional[UserRole] = None
