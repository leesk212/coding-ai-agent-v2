"""Pydantic 스키마 정의"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """사용자 기본 스키마"""
    
    email: EmailStr = Field(..., description="이메일")
    name: str = Field(..., min_length=1, max_length=100, description="이름")
    role: str = Field(..., description="사용자 역할 (pm, admin)")
    
    class Config:
        """Pydantic 설정"""
        from_attributes = True


class UserCreate(UserBase):
    """사용자 생성 스키마"""
    
    password: str = Field(..., min_length=6, description="비밀번호 (최소 6 자리)")
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """사용자 업데이트 스키마"""
    
    email: Optional[EmailStr] = Field(None, description="이메일")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="이름")
    role: Optional[str] = Field(None, description="사용자 역할")
    
    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """사용자 응답 스키마"""
    
    id: int = Field(..., description="사용자 ID")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """토큰 응답 스키마"""
    
    access_token: str = Field(..., description="JWT 접근 토큰")
    token_type: str = Field(..., description="토큰 타입")
    expires_in: int = Field(..., description="만료 시간 (분)")


class UserLogin(BaseModel):
    """사용자 로그인 스키마"""
    
    email: EmailStr = Field(..., description="이메일")
    password: str = Field(..., description="비밀번호")
