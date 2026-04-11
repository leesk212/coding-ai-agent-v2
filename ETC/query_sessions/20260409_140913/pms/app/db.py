"""데이터베이스 설정 모듈"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator
from app.config import settings


class Base(DeclarativeBase):
    """Base 클래스 for SQLAlchemy models"""
    pass


# SQLite 데이터베이스 URL 설정
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    데이터베이스 세션을 생성하고 종료합니다.
    
    Yields:
        SQLAlchemy database session
        
    Example:
        >>> def endpoint(db: Session = Depends(get_db)):
        ...     user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
