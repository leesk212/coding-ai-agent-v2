"""프로젝트 Pydantic 스키마"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ProjectStatus(str, Enum):
    """프로젝트 상태 열거형"""
    
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectBase(BaseModel):
    """프로젝트 기본 스키마"""
    
    name: str = Field(..., min_length=1, max_length=200, description="프로젝트명")
    code: str = Field(..., min_length=1, max_length=50, description="프로젝트 코드")
    client: str = Field(..., min_length=1, max_length=200, description="고객사")
    designer: str = Field(..., min_length=1, max_length=200, description="설계자")
    developers: Optional[str] = Field(None, description="개발자 목록 (쉼표 구분)")
    start_date: date = Field(..., description="시작일")
    end_date: date = Field(..., description="종료일")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING, description="프로젝트 상태")
    description: Optional[str] = Field(None, description="프로젝트 설명")
    
    @validator('end_date')
    def end_date_must_be_after_start(cls, v, values):
        """종료일은 시작일 이후여야 함"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('종료일은 시작일 이후여야 합니다.')
        return v
    
    class Config:
        from_attributes = True


class ProjectCreate(ProjectBase):
    """프로젝트 생성 스키마"""
    
    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    """프로젝트 업데이트 스키마"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="프로젝트명")
    code: Optional[str] = Field(None, min_length=1, max_length=50, description="프로젝트 코드")
    client: Optional[str] = Field(None, min_length=1, max_length=200, description="고객사")
    designer: Optional[str] = Field(None, min_length=1, max_length=200, description="설계자")
    developers: Optional[str] = Field(None, description="개발자 목록")
    start_date: Optional[date] = Field(None, description="시작일")
    end_date: Optional[date] = Field(None, description="종료일")
    status: Optional[ProjectStatus] = Field(None, description="프로젝트 상태")
    description: Optional[str] = Field(None, description="프로젝트 설명")
    
    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    """프로젝트 응답 스키마"""
    
    id: int = Field(..., description="프로젝트 ID")
    creator_id: int = Field(..., description="생성자 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답 스키마"""
    
    total: int = Field(..., description="총 프로젝트 수")
    items: List[ProjectResponse] = Field(..., description="프로젝트 목록")


class GanttChartEntry(BaseModel):
    """간트 차트 항목 스키마"""
    
    id: int = Field(..., description="태스크 ID")
    name: str = Field(..., description="태스크명")
    start_date: date = Field(..., description="시작일")
    end_date: date = Field(..., description="종료일")
    progress: int = Field(default=0, ge=0, le=100, description="진행률 (%)")
    status: str = Field(..., description="상태")
    assignee_id: Optional[int] = Field(None, description="담당자 ID")
    parent_id: Optional[int] = Field(None, description="부모 태스크 ID")


class GanttChartData(BaseModel):
    """간트 차트 데이터 스키마"""
    
    project_id: int = Field(..., description="프로젝트 ID")
    project_name: str = Field(..., description="프로젝트명")
    project_start: date = Field(..., description="프로젝트 시작일")
    project_end: date = Field(..., description="프로젝트 종료일")
    tasks: List[GanttChartEntry] = Field(..., description="태스크 목록")
