"""pytest 설정 및 공용 Fixture"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.models import User
from app.main import app
from app.utils.security import get_password_hash
from fastapi.testclient import TestClient


# 테스트용 데이터베이스 엔진
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_pms.db"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    테스트 데이터베이스 세션 Fixture
    
    각 테스트 함수마다 새 세션을 생성하고, 테스트 종료 시 롤백합니다.
    """
    # 테이블 생성
    Base.metadata.create_all(bind=test_engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session):
    """
    테스트 HTTP 클라이언트 Fixture
    
    FastAPI 테스트 클라이언트를 생성하고, get_db override 를 적용합니다.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    """
    테스트용 사용자 생성 Fixture
    
    인증 없이 사용할 수 있는 일반 사용자입니다.
    """
    user = User(
        id=1,
        email="test@example.com",
        password=get_password_hash("testpassword123"),
        name="Test User",
        role="pm"
    )
    return user


@pytest.fixture
def test_admin_user():
    """
    테스트용 관리자 사용자 생성 Fixture
    
    관리자 권한을 가진 사용자입니다.
    """
    admin = User(
        id=2,
        email="admin@example.com",
        password=get_password_hash("adminpassword123"),
        name="Admin User",
        role="admin"
    )
    return admin
