from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL 연결 설정
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/pms_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    데이터베이스 세션을 생성합니다.
    
    Yields:
        Database session object
    
    Note:
        Generator 함수로 사용되어 with 문이나 yield-after 로직에서
        자동 자원 정리가 보장됩니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
