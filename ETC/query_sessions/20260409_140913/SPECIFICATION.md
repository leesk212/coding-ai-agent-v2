# PMS - Specification Driven Development 명세서

## 1. 프로젝트 설정 명세서

### 1.1 프로젝트 구조 생성 (TSK-001)

**명세:**
- FastAPI 기반의 프로젝트 디렉토리 구조 생성
- 테스트 가능한 모듈 구조로 구성

**구체적 요구사항:**
```
pms/
├── app/
│   ├── __init__.py          # 패키지 초기화
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── config.py            # 설정 관리 모듈
│   ├── db.py                # 데이터베이스 세션 관리
│   ├── models/              # SQLAlchemy 모델
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── project.py
│   ├── schemas/             # Pydantic 스키마
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── project.py
│   ├── routers/             # API 라우터
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── projects.py
│   ├── services/            # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   └── project_service.py
│   ├── tests/               # 단위 테스트
│   │   ├── __init__.py
│   │   ├── conftest.py      # pytest 고정Fixture
│   │   ├── test_user.py
│   │   └── test_project.py
│   └── utils/               # 유틸리티
│       ├── __init__.py
│       └── security.py
├── tests/                   # 통합 테스트
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

**검증 기준:**
- `pytest --version` 실행 시 pytest 정상 동작
- `python -m app.main` 실행 시 FastAPI 서버 시작

---

### 1.2 의존성 설정 (TSK-002)

**명세:**
- `requirements.txt` 파일 생성
- 모든 필요한 라이브러리 명시

**구체적 요구사항:**
```txt
# 백엔드
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.13.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# 테스트
pytest==7.4.3
pytest-cov==4.1.0
httpx==0.25.2
pytest-asyncio==0.21.1

# 프론트엔드 (React)
# package.json 에서 관리
```

**검증 기준:**
- `pip install -r requirements.txt` 성공
- 모든 라이브러리 import 가능

---

### 1.3 데이터베이스 설정 (TSK-003)

**명세:**
- SQLAlchemy 2.0 스타일로 데이터베이스 설정
- 세션 관리 모듈 구현

**구체적 요구사항:**
```python
# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite 설정 (개발 환경)
SQLALCHEMY_DATABASE_URL = "sqlite:///./pms.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**검증 기준:**
- `get_db()` 호출 시 SQLAlchemy 세션 반환
- 데이터베이스 파일 생성 확인

---

### 1.4 설정 파일 생성 (TSK-004)

**명세:**
- 환경 변수 관리 설정
- 설정 모듈 구현

**구체적 요구사항:**
```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    
    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./pms.db"
    
    # JWT 설정
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """설정을 캐시하여 반환"""
    return Settings()

settings = get_settings()
```

```env
# .env
DATABASE_URL=sqlite:///./pms.db
SECRET_KEY=super-secret-key-for-development-only
DEBUG=True
```

**검증 기준:**
- `get_settings().SECRET_KEY` 값 정상 반환
- 환경 변수 로드 확인

---

## 2. 데이터베이스 모델 명세서

### 2.1 User 모델 (TSK-101)

**명세:**
- 사용자 정보 저장
- 역할 기반 권한 관리

**구체적 요구사항:**
```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.db import Base

class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), default="USER", nullable=False)  # USER, ADMIN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**검증 기준:**
- User 테이블 생성 확인
- 이메일 중복 제약 조건 적용 확인

---

### 2.2 User 스키마 (TSK-102)

**명세:**
- Pydantic 스키마로 입력/출력 검증

**구체적 요구사항:**
```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """기본 사용자 스키마"""
    email: EmailStr
    name: str

class UserCreate(UserBase):
    """사용자 생성 스키마"""
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 8 자 이상이어야 합니다')
        return v

class UserUpdate(BaseModel):
    """사용자 업데이트 스키마"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(UserBase):
    """사용자 응답 스키마"""
    id: int
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserInDB(UserBase):
    """데이터베이스 내 사용자 스키마 (비밀번호 포함)"""
    id: int
    password_hash: str
    role: str
    is_active: bool
```

**검증 기준:**
- EmailStr 유효성 검사 통과
- 비밀번호 8 자 이상 검증 통과
- 모델 변환 `from_attributes=True` 정상 동작

---

### 2.3 Project 모델 (TSK-201)

**명세:**
- 프로젝트 정보 저장
- Soft delete 지원

**구체적 요구사항:**
```python
# app/models/project.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base
from enum import Enum

class ProjectStatus(str, Enum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"

class Project(Base):
    """프로젝트 모델"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(50), unique=True, index=True, nullable=False)
    project_name = Column(String(200), nullable=False)
    client = Column(String(200), nullable=False)  # 고객사
    designer = Column(String(100), nullable=False)  # 설계자
    developers = Column(Text, nullable=False)  # 개발자 목록 (JSON)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), default=ProjectStatus.PLANNING, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # 관계
    creator = relationship("User", foreign_keys=[created_by])
```

**검증 기준:**
- Projects 테이블 생성 확인
- foreign_key 제약 조건 적용 확인
- project_code 유니크 인덱스 적용 확인

---

### 2.4 Project 스키마 (TSK-202)

**명세:**
- 프로젝트 입력/출력 스키마 정의

**구체적 요구사항:**
```python
# app/schemas/project.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"

class ProjectBase(BaseModel):
    """기본 프로젝트 스키마"""
    project_name: str = Field(..., min_length=1, max_length=200)
    client: str = Field(..., min_length=1, max_length=200)
    designer: str = Field(..., min_length=1, max_length=100)
    developers: List[str] = Field(default_factory=list)
    start_date: datetime
    end_date: datetime

class ProjectCreate(ProjectBase):
    """프로젝트 생성 스키마"""
    project_code: Optional[str] = None
    
    @validator('end_date')
    def end_date_after_start(cls, v, values):
        if 'start_date' in values.data and v < values.data['start_date']:
            raise ValueError('종료일은 시작일보다 늦어야 합니다')
        return v

class ProjectUpdate(BaseModel):
    """프로젝트 업데이트 스키마"""
    project_name: Optional[str] = Field(None, min_length=1, max_length=200)
    client: Optional[str] = Field(None, min_length=1, max_length=200)
    designer: Optional[str] = Field(None, min_length=1, max_length=100)
    developers: Optional[List[str]] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ProjectResponse(ProjectBase):
    """프로젝트 응답 스키마"""
    id: int
    project_code: str
    status: ProjectStatus
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ProjectListResponse(ProjectResponse):
    """프로젝트 목록 응답"""
    total_count: int
    page: int
    page_size: int
```

**검증 기준:**
- 날짜 유효성 검사 통과 (종료일 >= 시작일)
- 필드 길이 검증 통과
- 모델 변환 정상 동작

---

## 3. 인증 시스템 명세서

### 3.1 비밀번호 해싱 (TSK-302)

**명세:**
- bcrypt 를 사용한 비밀번호 해싱 및 검증

**구체적 요구사항:**
```python
# app/utils/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)
```

**검증 기준:**
- `verify_password("test1234", get_password_hash("test1234"))` → True
- `verify_password("wrong", get_password_hash("test1234"))` → False

---

### 3.2 JWT 토큰 생성 (TSK-301)

**명세:**
- JWT 토큰 생성 및 검증

**구체적 요구사항:**
```python
# app/utils/jwt.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """액세스 토큰 디코딩"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

**검증 기준:**
- 토큰 생성 시 exp_claim 포함
- 토큰 디코딩 정상 동작
- 유효하지 않은 토큰은 None 반환

---

### 3.3 인증 서비스 (TSK-303, TSK-304)

**명세:**
- 로그인/로그아웃 API 구현

**구체적 요구사항:**
```python
# app/services/auth_service.py
from datetime import timedelta
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User
from app.db import get_db
from app.utils.security import verify_password, get_password_hash
from app.utils.jwt import create_access_token
from app.config import settings

class AuthService:
    """인증 서비스"""
    
    @staticmethod
    async def register_user(user_data: UserCreate, db) -> UserResponse:
        """사용자 등록"""
        # 이메일 중복 체크
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("이미 사용 중인 이메일입니다")
        
        # 비밀번호 해싱
        hashed_password = get_password_hash(user_data.password)
        
        # 사용자 생성
        db_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            name=user_data.name,
            role="USER"
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            role=db_user.role,
            is_active=db_user.is_active,
            created_at=db_user.created_at
        )
    
    @staticmethod
    async def login_user(email: str, password: str, db):
        """사용자 로그인"""
        # 사용자 조회
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("존재하지 않는 이메일입니다")
        
        # 비밀번호 검증
        if not verify_password(password, user.password_hash):
            raise ValueError("비밀번호가 일치하지 않습니다")
        
        # 토큰 생성
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at
            )
        }
```

**검증 기준:**
- 올바른 인증정보로 로그인 시 토큰 반환
- 잘못된 인증정보 시 ValueError 발생
- 이메일 중복 시 ValueError 발생

---

## 4. API 명세서

### 4.1 로그인 API (TSK-401)

**명세:**
- POST /api/v1/auth/login
- 이메일/비밀번호로 JWT 토큰 발급

**구체적 요구사항:**
```python
# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=dict)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    사용자 로그인
    
    - **email**: 사용자 이메일
    - **password**: 사용자 비밀번호
    
    JWT 액세스 토큰과 사용자 정보를 반환합니다.
    """
    try:
        result = await AuthService.login_user(form_data.username, form_data.password, db)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout")
async def logout():
    """
    로그아웃
    
    클라이언트는 토큰을 폐기해야 합니다.
    """
    return {"message": "로그아웃 되었습니다"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(db: Session = Depends(get_db)):
    """
    현재 로그인한 사용자 정보 조회
    
    JWT 토큰에서 사용자 정보를 추출하여 반환합니다.
    """
    # TODO: JWT 토큰 인증 로직 추가
    pass
```

**검증 기준:**
- 올바른 인증정보 → 200 OK + JWT 토큰
- 잘못된 인증정보 → 401 UNAUTHORIZED
- Swagger 문서 자동 생성

---

### 4.2 프로젝트 생성 API (TSK-410)

**명세:**
- POST /api/v1/projects
- 새 프로젝트 생성

**구체적 요구사항:**
```python
# app/routers/projects.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    새 프로젝트 생성
    
    - **project_name**: 프로젝트명 (필수, 1~200 자)
    - **project_code**: 프로젝트코드 (선택, 자동 생성)
    - **client**: 고객사 (필수)
    - **designer**: 설계자 (필수)
    - **developers**: 개발자 목록 (선택)
    - **start_date**: 시작일 (필수)
    - **end_date**: 종료일 (필수, 시작일 이후)
    
    생성된 프로젝트 정보를 반환합니다.
    """
    try:
        # TODO: 현재 로그인한 사용자 ID 가져오기
        created_by = 1  # 임시
        
        project = await ProjectService.create_project(
            db=db,
            project_data=project_data,
            created_by=created_by
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

**검증 기준:**
- 유효한 프로젝트 데이터 → 201 Created + 프로젝트 정보
- 중복 프로젝트코드 → 400 BAD_REQUEST
- 날짜 유효성 실패 → 422 UNPROCESSABLE_ENTITY

---

### 4.3 프로젝트 목록 조회 API (TSK-411)

**명세:**
- GET /api/v1/projects
- 필터링된 프로젝트 목록 조회

**구체적 요구사항:**
```python
@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 10,
    status: str = None,
    client: str = None,
    db: Session = Depends(get_db)
):
    """
    프로젝트 목록 조회
    
    - **skip**: 건너뛸 항목 수 (기본: 0)
    - **limit**: 최대 항목 수 (기본: 10)
    - **status**: 프로젝트 상태 (필터)
    - **client**: 고객사 (필터)
    
    필터링된 프로젝트 목록을 반환합니다.
    """
    # TODO: 프로젝트 목록 조회 로직
    pass
```

**검증 기준:**
- 기본 필터 적용 시 10 개 프로젝트 반환
- 상태 필터 적용 시 해당 상태 프로젝트만 반환
- 페이지네이션 정상 동작

---

## 5. 프론트엔드 명세서

### 5.1 로그인 페이지 (TSK-510)

**명세:**
- React 기반 로그인 컴포넌트
- 이메일/비밀번호 입력 및 검증

**구체적 요구사항:**
```jsx
// src/pages/Login.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await axios.post('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      localStorage.setItem('token', response.data.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || '로그인에 실패했습니다.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-10 bg-white rounded-lg shadow">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            PMS 로그인
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="이메일 주소"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                비밀번호
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="비밀번호"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              로그인
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
```

**검증 기준:**
- 이메일/비밀번호 입력 시 버튼 활성화
- 유효하지 않은 이메일 형식 시 경고 표시
- 로그인 성공 → 대시보드로 리디렉션
- 로그인 실패 → 에러 메시지 표시

---

### 5.2 프로젝트 등록 페이지 (TSK-512)

**명세:**
- 폼 기반 프로젝트 등록
- 실시간 유효성 검사

**구체적 요구사항:**
```jsx
// src/pages/CreateProject.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const CreateProject = () => {
  const [formData, setFormData] = useState({
    project_name: '',
    client: '',
    designer: '',
    developers: [],
    start_date: '',
    end_date: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleDeveloperChange = (e, index) => {
    const newDevelopers = [...formData.developers];
    newDevelopers[index] = e.target.value;
    setFormData({ ...formData, developers: newDevelopers });
  };

  const addDeveloper = () => {
    setFormData({
      ...formData,
      developers: [...formData.developers, '']
    });
  };

  const removeDeveloper = (index) => {
    const newDevelopers = formData.developers.filter((_, i) => i !== index);
    setFormData({ ...formData, developers: newDevelopers });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // 유효성 검사
    if (new Date(formData.end_date) <= new Date(formData.start_date)) {
      setError('종료일은 시작일보다 늦어야 합니다.');
      return;
    }

    try {
      const response = await axios.post('/api/v1/projects', formData, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      setSuccess('프로젝트가 등록되었습니다.');
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || '등록에 실패했습니다.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">프로젝트 등록</h1>
      
      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-800 rounded">
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-4 bg-green-100 text-green-800 rounded">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            프로젝트명 *
          </label>
          <input
            type="text"
            required
            minLength={1}
            maxLength={200}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            value={formData.project_name}
            onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            고객사 *
          </label>
          <input
            type="text"
            required
            minLength={1}
            maxLength={200}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            value={formData.client}
            onChange={(e) => setFormData({ ...formData, client: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            설계자 *
          </label>
          <input
            type="text"
            required
            minLength={1}
            maxLength={100}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            value={formData.designer}
            onChange={(e) => setFormData({ ...formData, designer: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            개발자
          </label>
          {formData.developers.map((developer, index) => (
            <div key={index} className="flex gap-2 mt-2">
              <input
                type="text"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                value={developer}
                onChange={(e) => handleDeveloperChange(e, index)}
                placeholder={`개발자 ${index + 1}`}
              />
              {formData.developers.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeDeveloper(index)}
                  className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                >
                  제거
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={addDeveloper}
            className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            개발자 추가
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              시작일 *
            </label>
            <input
              type="date"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              종료일 *
            </label>
            <input
              type="date"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
            />
          </div>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            className="flex-1 px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            등록
          </button>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="flex-1 px-6 py-3 bg-gray-300 text-gray-800 font-medium rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            취소
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateProject;
```

**검증 기준:**
- 필수 필드 비어있을 때提交 방지
- 종료일 < 시작일 경우 에러 표시
- 개발자 추가/제거 정상 동작
- API 호출 성공 → 대시보드로 리디렉션

---

## 6. 간트 차트 명세서

### 6.1 React Gantt 설치 (TSK-520)

**명세:**
- react-gantt-timeline 라이브러리 설치 및 설정

**구체적 요구사항:**
```bash
# npm install
npm install react-gantt-timeline date-fns
```

**검증 기준:**
- 라이브러리 설치 완료 확인
- import 정상 동작

---

### 6.2 간트 차트 컴포넌트 (TSK-521, TSK-522, TSK-523)

**명세:**
- 프로젝트 일정을 간트 차트로 시각화
- 드래그 앤 드롭으로 일정 수정

**구체적 요구사항:**
```jsx
// src/components/GanttChart.jsx
import React, { useState, useEffect } from 'react';
import { Gantt } from 'react-gantt-timeline';
import 'react-gantt-timeline/dist/index.css';
import axios from 'axios';

const GanttChart = ({ projectId }) => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await axios.get(`/api/v1/gantt/projects`, {
          params: { project_id: projectId },
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        setTasks(response.data.tasks);
      } catch (error) {
        console.error('간트 차트 데이터 조회 실패:', error);
      } finally {
        setLoading(false);
      }
    };

    if (projectId) {
      fetchTasks();
    }
  }, [projectId]);

  const handleDrag = async (task, newStart, newEnd) => {
    try {
      await axios.post(
        '/api/v1/gantt/schedule/update',
        {
          task_id: task.id,
          start_date: newStart,
          end_date: newEnd
        },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      // UI 업데이트
      setTasks(prevTasks =>
        prevTasks.map(t =>
          t.id === task.id
            ? { ...t, start: newStart, end: newEnd }
            : t
        )
      );
    } catch (error) {
      console.error('일정 수정 실패:', error);
      alert('일정 수정에 실패했습니다.');
    }
  };

  if (loading) {
    return <div className="p-4">로딩 중...</div>;
  }

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">프로젝트 간트 차트</h2>
      <Gantt
        tasks={tasks}
        onTaskMove={handleDrag}
        viewMode="Day"
        language="ko"
        dayStart={6} // 일요일 시작
        columnWidth={150}
        barHeight={30}
        barBorderRadius={3}
      />
    </div>
  );
};

export default GanttChart;
```

**검증 기준:**
- 프로젝트 일정 표시
- 드래그 앤 드롭으로 일정 이동
- 일정 변경 시 API 호출
- 에러 발생 시 사용자에게 알림

---

## 7. 테스트 명세서 (TDD)

### 7.1 사용자 모델 테스트 (TSK-601)

**명세:**
- User 모델의 CRUD 연동 테스트

**구체적 요구사항:**
```python
# app/tests/test_user.py
import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import get_password_hash

@pytest.fixture
def db_session(mocker):
    """데이터베이스 세션Fixture"""
    mock_session = mocker.Mock(spec=Session)
    return mock_session

@pytest.fixture
def test_user(db_session):
    """테스트용 사용자"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("test1234"),
        name="Test User",
        role="USER"
    )
    db_session.add.return_value = None
    db_session.commit.return_value = None
    return user

def test_user_creation(test_user):
    """사용자 생성 테스트"""
    assert test_user.email == "test@example.com"
    assert test_user.name == "Test User"
    assert test_user.role == "USER"

def test_user_password_hashing(test_user):
    """비밀번호 해싱 테스트"""
    from app.utils.security import verify_password
    assert verify_password("test1234", test_user.password_hash) is True
    assert verify_password("wrong", test_user.password_hash) is False
```

**검증 기준:**
- pytest 실행 시 모든 테스트 통과
- 100% 테스트 커버리지 달성

---

### 7.2 프로젝트 생성 API 테스트 (TSK-605)

**명세:**
- 프로젝트 생성 API E2E 테스트

**구체적 요구사항:**
```python
# app/tests/test_project.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.utils.security import get_password_hash

# 테스트 데이터베이스
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_pms.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def client():
    """테스트 클라이언트"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user():
    """테스트 사용자"""
    db = TestingSessionLocal()
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("test1234"),
        name="Test User",
        role="USER"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

def test_create_project(client, test_user):
    """프로젝트 생성 테스트"""
    from app.utils.jwt import create_access_token
    
    # 토큰 생성
    token = create_access_token(data={"sub": str(test_user.id)})
    
    project_data = {
        "project_name": "Test Project",
        "client": "Test Client",
        "designer": "Test Designer",
        "developers": ["dev1", "dev2"],
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-12-31T23:59:59"
    }
    
    response = client.post(
        "/api/v1/projects/",
        json=project_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["project_name"] == "Test Project"
    assert data["client"] == "Test Client"
    assert len(data["developers"]) == 2
```

**검증 기준:**
- 모든 API 테스트 통과
- 201 Created 응답 확인
- 데이터 유효성 검증 확인

---

이 명세서는 SDD (Specification Driven Development) 방식으로 작성되었으며, 각 명세는 구체적인 요구사항과 검증 기준을 포함합니다. 다음 단계인 TDD 기반 개발에서는 이 명세서를 기반으로 테스트 코드를 먼저 작성한 후 구현을 진행합니다.
