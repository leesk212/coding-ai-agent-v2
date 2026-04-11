"""Pydantic 스키마 정의"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import date, datetime
from app.models import UserRole, ProjectStatus


# ==================== User Schemas ====================

class UserBase(BaseModel):
    """사용자 기본 스키마"""
    
    email: EmailStr = Field(..., description="사용자 이메일")
    name: str = Field(..., min_length=1, max_length=100, description="사용자 이름")
    role: UserRole = Field(UserRole.PM, description="사용자 역할")
    
    class Config:
        from_attributes = True


class UserCreate(UserBase):
    """사용자 생성 스키마"""
    
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8 자리)")
    
    @validator('password')
    def password_strength(cls, v: str) -> str:
        """비밀문 강도 검증"""
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8 자리여야 합니다')
        return v


class UserUpdate(BaseModel):
    """사용자 업데이트 스키마"""
    
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """사용자 응답 스키마"""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """사용자 로그인 스키마"""
    
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT 토큰 스키마"""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """JWT 토큰 데이터 스키마"""
    
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None


# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    """프로젝트 기본 스키마"""
    
    name: str = Field(..., min_length=1, max_length=200, description="프로젝트 이름")
    code: str = Field(..., min_length=1, max_length=50, description="프로젝트 코드")
    client: str = Field(..., min_length=1, max_length=200, description="고객사")
    designer: Optional[str] = Field(None, max_length=100, description="설계자")
    developers: Optional[List[str]] = Field(None, description="개발자 목록")
    start_date: date = Field(..., description="시작 날짜")
    end_date: date = Field(..., description="종료 날짜")
    status: ProjectStatus = Field(ProjectStatus.PLANNING, description="프로젝트 상태")
    description: Optional[str] = Field(None, description="프로젝트 설명")
    
    @validator('end_date')
    def end_date_after_start(cls, v: date, values: dict) -> date:
        """종료일은 시작일 이후여야 합니다"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('종료일은 시작일 이후여야 합니다')
        return v


class ProjectCreate(ProjectBase):
    """프로젝트 생성 스키마"""
    pass


class ProjectUpdate(BaseModel):
    """프로젝트 업데이트 스키마"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    client: Optional[str] = Field(None, min_length=1, max_length=200)
    designer: Optional[str] = Field(None, max_length=100)
    developers: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    """프로젝트 응답 스키마"""
    
    id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답 스키마"""
    
    total: int
    items: List[ProjectResponse]


# ==================== Task Schemas (Gantt) ====================

class TaskBase(BaseModel):
    """태스크 기본 스키마"""
    
    name: str = Field(..., min_length=1, max_length=200, description="태스크 이름")
    description: Optional[str] = Field(None, description="태스크 설명")
    start_date: date = Field(..., description="시작 날짜")
    end_date: date = Field(..., description="종료 날짜")
    status: ProjectStatus = Field(ProjectStatus.PLANNING, description="태스크 상태")
    progress: int = Field(0, ge=0, le=100, description="진행률 (0-100)")
    assignee_id: Optional[int] = Field(None, description="할당자 ID")
    priority: str = Field("medium", description="우선순위 (low, medium, high)")
    
    @validator('end_date')
    def end_date_after_start(cls, v: date, values: dict) -> date:
        """종료일은 시작일 이후여야 합니다"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('종료일은 시작일 이후여야 합니다')
        return v


class TaskCreate(TaskBase):
    """태스크 생성 스키마"""
    pass


class TaskUpdate(BaseModel):
    """태스크 업데이트 스키마"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    assignee_id: Optional[int] = None
    priority: Optional[str] = None


class TaskResponse(TaskBase):
    """태스크 응답 스키마"""
    
    id: int
    project_id: int
    
    class Config:
        from_attributes = True


class GanttChartEntry(BaseModel):
    """간트 차트 항목 스키마"""
    
    id: int
    name: str
    start_date: date
    end_date: date
    progress: int
    status: ProjectStatus
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None


class GanttChartData(BaseModel):
    """간트 차트 데이터 스키마"""
    
    project_id: int
    project_name: str
    project_start: date
    project_end: date
    tasks: List[GanttChartEntry]


# ==================== Auth Schemas ====================

class AuthToken(BaseModel):
    """인증 토큰 스키마"""
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
