"""보안 유틸리티 모듈"""

from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models import User, UserRole


# 비밀번호 해싱용 CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 인증 리프레시
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호를 해시된 값과 비교합니다.
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
        
    Returns:
        bool: 비밀번호가 일치하는지 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    비밀번호를 해싱합니다.
    
    Args:
        password: 해싱할 평문 비밀번호
        
    Returns:
        str: 해시된 비밀번호
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 접근 토큰을 생성합니다.
    
    Args:
        data: 토큰에 포함될 데이터 (user_id, email, role 등)
        expires_delta: 토큰 유효기간
        
    Returns:
        str: 생성된 JWT 토큰
        
    Example:
        >>> token = create_access_token(data={"sub": "user@example.com", "role": "pm"})
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    JWT 토큰을 검증하고 현재 사용자를 가져옵니다.
    
    Args:
        token: JWT 토큰
        db: 데이터베이스 세션
        
    Returns:
        User: 인증된 사용자
        
    Raises:
        HTTPException: 토큰이 invalid 한 경우
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    활성화된 현재 사용자를 가져옵니다.
    
    Args:
        current_user: 현재 사용자
        
    Returns:
        User: 활성화된 사용자
        
    Raises:
        HTTPException: 사용자가 비활성화된 경우
    """
    # 사용자가 활성화되어 있는지 확인 (예: deleted_at 필드가 없는 경우)
    if current_user.role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    관리자 권한을 가진 현재 사용자를 가져옵니다.
    
    Args:
        current_user: 현재 사용자
        
    Returns:
        User: 관리자 권한을 가진 사용자
        
    Raises:
        HTTPException: 사용자가 관리자가 아닌 경우
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
