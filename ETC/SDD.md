# PMS (Project Management System) - 개발 명세서 (SDD)

## 1. 개요

### 1.1 문서 목적
본 명세서는 PMS 프로젝트의 기술적 구현 방식을 상세히 정의한다. Spec Driven Development 접근법을 기반으로 하며, TDD(Test Driven Development) 방식으로 개발을 수행한다.

### 1.2 프로젝트 구조
```
pms/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── project.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── project.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   └── project_service.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── projects.py
│   │   ├── database.py
│   │   └── exceptions.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_user.py
│   │   ├── test_project.py
│   │   └── test_auth.py
│   ├── requirements.txt
│   └── pytest.ini
└── frontend/
    └── (React 애플리케이션)
```

## 2. 기술 스택 상세

### 2.1 백엔드
- **Python**: 3.9 이상
- **FastAPI**: 0.104.1
- **SQLAlchemy**: 2.0.23
- **Pydantic**: 2.5.0
- **Pytest**: 7.4.3
- **pytest-asyncio**: 0.21.1
- **python-jose**: 3.3.0
- **passlib**: 1.7.4
- **bcrypt**: 4.1.0

### 2.2 데이터베이스
- **SQLite** (개발 환경)
- **PostgreSQL** (프로덕션)

## 3. 데이터 모델 명세

### 3.1 User 모델

```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="USER")  # USER, ADMIN, EXECUTIVE
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    projects = relationship("Project", back_populates="created_by_user")
```

**제약사항**:
- `username`: 고유값, 공백 불가, 최대 50 자
- `email`: 고유값, 이메일 형식, 최대 100 자
- `role`: 고정 값 (USER, ADMIN, EXECUTIVE) 중 하나
- `hashed_password`: BCrypt 해시값 (60 자)

### 3.2 Project 모델

```python
# app/models/project.py
from sqlalchemy import Column, Integer, String, Date, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class ProjectStatus(enum.Enum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(100), nullable=False, index=True)
    project_code = Column(String(20), unique=True, nullable=False, index=True)
    client_name = Column(String(50), nullable=False)
    designer = Column(String(50), nullable=False)
    developers = Column(Text)  # JSON 배열 문자열
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="PLANNING")
    progress = Column(Integer, default=0)  # 0-100
    is_deleted = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    created_by_user = relationship("User", back_populates="projects")
```

**제약사항**:
- `project_name`: 최대 100 자
- `project_code`: 대문자 영문/숫자, 최대 20 자
- `client_name`: 최대 50 자
- `designer`: 최대 50 자
- `developers`: JSON 배열 (예: `["개발자 1", "개발자 2"]`)
- `start_date`, `end_date`: 유효한 날짜, end_date >= start_date
- `status`: 고정 값 중 하나
- `progress`: 0 이상 100 이하 정수
- `created_by`: User ID (참조 무결성)

## 4. API 명세

### 4.1 인증 API

#### 4.1.1 로그인
**Endpoint**: `POST /api/auth/login`

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "string",
    "email": "string",
    "role": "USER"
  }
}
```

**Error Response**:
- `401 Unauthorized`: 잘못된 인증정보
- `422 Validation Error`: 유효성 검사 실패

#### 4.1.2 현재 사용자 정보 조회
**Endpoint**: `GET /api/auth/me`

**Headers**:
```
Authorization: Bearer {token}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "string",
  "email": "string",
  "role": "USER"
}
```

### 4.2 프로젝트 API

#### 4.2.1 프로젝트 등록
**Endpoint**: `POST /api/projects`

**Headers**:
```
Authorization: Bearer {token}
```

**Request Body**:
```json
{
  "project_name": "프로젝트명",
  "project_code": "PRJ001",
  "client_name": "고객사명",
  "designer": "설계자명",
  "developers": ["개발자 1", "개발자 2"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "project_name": "프로젝트명",
  "project_code": "PRJ001",
  "client_name": "고객사명",
  "designer": "설계자명",
  "developers": ["개발자 1", "개발자 2"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "status": "PLANNING",
  "progress": 0,
  "created_by": 1,
  "created_at": "2024-01-01T00:00:00"
}
```

**Error Response**:
- `400 Bad Request`: 중복 project_code
- `422 Validation Error`: 유효성 검사 실패
  - `start_date` 이후 `end_date` 필요
  - `progress` 범위 초과

#### 4.2.2 프로젝트 목록 조회
**Endpoint**: `GET /api/projects`

**Query Parameters**:
- `page`: 페이지 번호 (기본값: 1)
- `page_size`: 페이지 크기 (기본값: 10, 최대: 100)
- `search`: 검색어 (프로젝트명, 코드, 고객사)
- `status`: 필터 상태

**Response** (200 OK):
```json
{
  "items": [...],
  "total": 50,
  "page": 1,
  "page_size": 10,
  "total_pages": 5
}
```

#### 4.2.3 프로젝트 상세 조회
**Endpoint**: `GET /api/projects/{project_id}`

**Response** (200 OK):
```json
{
  "id": 1,
  "project_name": "프로젝트명",
  "project_code": "PRJ001",
  "client_name": "고객사명",
  "designer": "설계자명",
  "developers": ["개발자 1", "개발자 2"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "status": "IN_PROGRESS",
  "progress": 50,
  "created_by": 1,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-06-01T00:00:00"
}
```

**Error Response**:
- `404 Not Found`: 프로젝트 존재하지 않음

#### 4.2.4 프로젝트 수정
**Endpoint**: `PUT /api/projects/{project_id}`

**Request Body** (선택 항목):
```json
{
  "project_name": "수정된 프로젝트명",
  "client_name": "수정된 고객사",
  "designer": "수정된 설계자",
  "developers": ["새 개발자"],
  "start_date": "2024-02-01",
  "end_date": "2025-01-31",
  "status": "COMPLETED",
  "progress": 100
}
```

**Response** (200 OK): 수정된 프로젝트 정보

**Error Response**:
- `403 Forbidden`: 권한 없음 (자신의 프로젝트만 수정 가능)
- `404 Not Found`: 프로젝트 존재하지 않음

#### 4.2.5 프로젝트 삭제
**Endpoint**: `DELETE /api/projects/{project_id}`

**Response** (200 OK):
```json
{
  "message": "프로젝트가 성공적으로 삭제되었습니다."
}
```

**Error Response**:
- `403 Forbidden`: 권한 없음
- `400 Bad Request`: 진행 중인 프로젝트는 삭제 불가

### 4.3 간트 차트 데이터 API

#### 4.3.1 간트 차트 데이터 조회
**Endpoint**: `GET /api/gantt`

**Query Parameters**:
- `year`: 년도 (기본값: 현재 년도)
- `month`: 월 (기본값: 현재 월)

**Response** (200 OK):
```json
{
  "tasks": [
    {
      "id": 1,
      "name": "프로젝트명",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "progress": 50,
      "status": "IN_PROGRESS",
      "color": "#3b82f6"
    }
  ]
}
```

## 5. 도메인 비즈니스 로직

### 5.1 프로젝트 유효성 검사

#### 5.1.1 프로젝트 코드 유효성
- 영문 대문자 (A-Z) 와 숫자 (0-9) 만 허용
- 길이: 1~20 자리
- 예: `PRJ001`, `DEV2024A`

#### 5.1.2 일정 유효성
- `end_date` >= `start_date`
- 시작일과 종료일은 유효한 날짜여야 함
- 미래 날짜 또는 과거 날짜 모두 허용

#### 5.1.3 진행률 유효성
- 범위: 0~100
- 정수만 허용

#### 5.1.4 중복 검사
- `project_code` 는 전역적으로 고유해야 함
- `username` 과 `email` 은 전역적으로 고유

### 5.2 권한 체크 로직

#### 5.2.1 프로젝트 등록
- 인증된 사용자만 가능
- 모든 역할 (USER, ADMIN, EXECUTIVE) 허용

#### 5.2.2 프로젝트 목록 조회
- 모든 인증된 사용자 가능
- USER: 자신의 프로젝트만 조회
- ADMIN, EXECUTIVE: 모든 프로젝트 조회

#### 5.2.3 프로젝트 수정/삭제
- **자신의 프로젝트**: REGISTERED 사용자만 수정/삭제 가능
- **타인의 프로젝트**: ADMIN, EXECUTIVE 만 수정/삭제 가능
- **진행 중인 프로젝트**: DELETE 제한 (ADMIN 만 가능)

### 5.3 자동 업데이트

#### 5.3.1 진행률 자동 계산
- `start_date` ~ `현재일` ~ `end_date` 기준 진행률 자동 계산
- 수동 업데이트 가능

#### 5.3.2 상태 자동 변경
- `현재일` > `end_date` 이고 `progress` < 100: `CANCELLED`
- `progress` == 100: `COMPLETED`

## 6. 예외 처리 명세

### 6.1 커스텀 예외 클래스

```python
# app/exceptions.py
class BaseAppException(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class ProjectNotFoundException(BaseAppException):
    def __init__(self, project_id: int):
        super().__init__(
            message=f"프로젝트 ID {project_id}를 찾을 수 없습니다.",
            code="PROJECT_NOT_FOUND",
            status_code=404
        )

class DuplicateProjectCodeException(BaseAppException):
    def __init__(self, project_code: str):
        super().__init__(
            message=f"중복된 프로젝트 코드: {project_code}",
            code="DUPLICATE_PROJECT_CODE",
            status_code=400
        )

class UnauthorizedException(BaseAppException):
    def __init__(self, message: str = "권한이 없습니다."):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=403
        )

class InvalidDateRangeException(BaseAppException):
    def __init__(self):
        super().__init__(
            message="종료일은 시작일 이후여야 합니다.",
            code="INVALID_DATE_RANGE",
            status_code=422
        )

class InvalidProgressException(BaseAppException):
    def __init__(self):
        super().__init__(
            message="진행률은 0~100 사이여야 합니다.",
            code="INVALID_PROGRESS",
            status_code=422
        )

class ActiveProjectCannotDeleteException(BaseAppException):
    def __init__(self, project_id: int):
        super().__init__(
            message=f"진행 중인 프로젝트 ID {project_id}는 삭제할 수 없습니다.",
            code="ACTIVE_PROJECT_CANNOT_DELETE",
            status_code=400
        )
```

### 6.2 예외 처리 전략

- HTTP 4xx: 클라이언트 오류 (유효성 검사, 권한 없음)
- HTTP 5xx: 서버 오류 (데이터베이스, 내부 로직)
- 모든 예외는 로거에 기록됨

## 7. 테스트 명세

### 7.1 테스트 범위

#### 7.1.1 유닛 테스트
- 서비스 레이어 로직
- 유효성 검사
- 도메인 비즈니스 규칙

#### 7.1.2 통합 테스트
- API 엔드포인트
- 데이터베이스 연동
- 인증/인가

#### 7.1.3 코드 커버리지
- 라인 커버리지: 80% 이상
- 분기 커버리지: 70% 이상

### 7.2 테스트 툴

- **pytest**: 테스트 프레임워크
- **pytest-asyncio**: 비동기 테스트
- **pytest-cov**: 코드 커버리지 측정
- **httpx**: HTTP 클라이언트 테스트
- **SQLAlchemy**: 테스트용 인메모리 DB

### 7.3 테스트 데이터 (Fixture)

```python
# tests/conftest.py
@pytest.fixture
def valid_project_data():
    return {
        "project_name": "테스트 프로젝트",
        "project_code": "PRJ001",
        "client_name": "테스트 고객사",
        "designer": "테스트 설계자",
        "developers": ["개발자 1"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }

@pytest.fixture
def test_user():
    return User(
        username="testuser",
        email="test@example.com",
        hashed_password=bcrypt.hashpw("password".encode(), bcrypt.gensalt()),
        role="USER"
    )
```

## 8. 설정 및 환경 변수

### 8.1 환경 변수

```bash
# .env
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### 8.2 설정 클래스

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## 9. 폴더 구조 상세

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 인스턴스, 라우터 등록
│   ├── config.py               # 설정 관리
│   ├── database.py             # DB 세션 관리
│   ├── exceptions.py           # 커스텀 예외 클래스
│   │
│   ├── models/                 # SQLAlchemy 모델
│   │   ├── __init__.py
│   │   ├── user.py             # User 모델
│   │   └── project.py          # Project 모델
│   │
│   ├── schemas/                # Pydantic 스키마
│   │   ├── __init__.py
│   │   ├── user.py             # User 스키마
│   │   └── project.py          # Project 스키마
│   │
│   ├── services/               # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── user_service.py     # 사용자 서비스
│   │   └── project_service.py  # 프로젝트 서비스
│   │
│   └── routers/                # API 엔드포인트
│       ├── __init__.py
│       ├── auth.py             # 인증 라우터
│       └── projects.py         # 프로젝트 라우터
│
├── tests/                      # 테스트 코드
│   ├── __init__.py
│   ├── conftest.py             # pytest 설정, fixture
│   ├── test_user.py            # 사용자 테스트
│   ├── test_project.py         # 프로젝트 테스트
│   ├── test_auth.py            # 인증 테스트
│   └── test_gantt.py           # 간트 차트 테스트
│
├── requirements.txt            # 의존성
└── pytest.ini                  # pytest 설정
```

## 10. 개발 일정

| 날짜 | 작업 | 산출물 |
|------|------|--------|
| Day 1 | 프로젝트 설정, DB 모델 | db_model |
| Day 2-3 | 사용자 서비스, 인증 | test_user, test_auth |
| Day 4-6 | 프로젝트 서비스, API | test_project, api_endpoints |
| Day 7 | 간트 차트 API | test_gantt |
| Day 8 | 통합 테스트, 커버리지 | coverage_report |
| Day 9 | 문서화, 최종 검토 | README, API_docs |
| Day 10 | 배포 준비 | deployment_guide |

## 11. 품질 보증

### 11.1 코드 스타일
- **black**: 포맷터 (line-length=88)
- **flake8**: 린터
- **isort**: import 정렬

### 11.2 Git 컨벤션
- **commit 메시지**: Conventional Commits
- **branch 전략**: Git Flow
- **PR 리뷰**: 최소 1 명 승인 필요

## 12. 배포 가이드

### 12.1 개발 환경
```bash
# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
pytest --cov=app --cov-report=html

# 서버 실행
uvicorn app.main:app --reload
```

### 12.2 프로덕션 환경
```bash
# 환경 변수 설정
export DATABASE_URL=postgresql://user:pass@host:5432/pms

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Nginx 설정
# upstream pms {
#     server 127.0.0.1:8000;
# }
```

## 13. 참고 문헌

- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- SQLAlchemy 공식 문서: https://docs.sqlalchemy.org/
- Pydantic 공식 문서: https://docs.pydantic.dev/
- pytest 공식 문서: https://docs.pytest.org/
