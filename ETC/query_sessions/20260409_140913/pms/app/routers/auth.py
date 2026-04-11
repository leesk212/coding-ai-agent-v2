"""인증 라우터"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db import get_db
from app.config import settings
from app.schemas import UserCreate, UserResponse, Token, UserLogin, AuthToken
from app.models import UserRole
from app.services.auth_service import AuthService
from app.utils.security import create_access_token, get_password_hash, get_current_active_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    새 사용자를 등록합니다.
    
    Args:
        user: 사용자 등록 정보
        db: 데이터베이스 세션
        
    Returns:
        UserResponse: 생성된 사용자 정보
        
    Raises:
        HTTPException: 이메일이 이미 존재하는 경우
    """
    db_user = AuthService.create_user(db, user)
    return db_user


@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    사용자 로그인을 수행하고 JWT 토큰을 반환합니다.
    
    Args:
        form_data: OAuth2 로그인 형식 데이터 (email, password)
        db: 데이터베이스 세션
        
    Returns:
        Token: JWT 토큰 정보
        
    Raises:
        HTTPException: 인증 실패 시
    """
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


@app.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자의 정보를 가져옵니다.
    
    Args:
        current_user: 인증된 현재 사용자
        db: 데이터베이스 세션
        
    Returns:
        UserResponse: 사용자 정보
    """
    return current_user
