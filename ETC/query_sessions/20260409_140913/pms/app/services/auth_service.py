"""인증 서비스"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate, UserUpdate
from app.utils.security import verify_password, get_password_hash


class AuthService:
    """
    사용자 인증 서비스
    
    사용자 생성, 조회, 인증 관련 비즈니스 로직을 처리합니다.
    """
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """
        새 사용자를 생성합니다.
        
        Args:
            db: 데이터베이스 세션
            user: 사용자 생성 데이터
            
        Returns:
            User: 생성된 사용자
            
        Raises:
            HTTPException: 이메일이 이미 존재하는 경우
        """
        # 이메일 중복 체크
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 비밀번호 해싱
        hashed_password = get_password_hash(user.password)
        
        # 사용자 생성
        db_user = User(
            email=user.email,
            name=user.name,
            role=user.role,
            password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """
        이메일로 사용자를 조회합니다.
        
        Args:
            db: 데이터베이스 세션
            email: 이메일
            
        Returns:
            User | None: 사용자 또는 None
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user(db: Session, user_id: int) -> User | None:
        """
        ID 로 사용자를 조회합니다.
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            
        Returns:
            User | None: 사용자 또는 None
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | bool:
        """
        사용자를 인증합니다.
        
        Args:
            db: 데이터베이스 세션
            email: 이메일
            password: 비밀번호
            
        Returns:
            User | bool: 인증된 사용자 또는 False
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False
        if not verify_password(password, user.password):
            return False
        return user
