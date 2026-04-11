# PMS 프로젝트 - 상세 개발 명세서

## 1. 개요
본 명세서는 PRD 를 기반으로 한 상세 개발 가이드라인을 제공한다. 모든 개발 작업은 SDD(Specification Driven Development) 및 TDD(Test Driven Development) 원칙에 따른다.

---

## 2. 프로젝트 구조

### 2.1 디렉토리 구조
```
pms-project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   └── mission.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   └── mission.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── projects.py
│   │   │   │   └── missions.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_user.py
│   │       ├── test_project.py
│   │       └── conftest.py
│   ├── alembic/
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── auth.ts
│   │   │   ├── projects.ts
│   │   │   └── missions.ts
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   └── Loading.tsx
│   │   │   └── layout/
│   │   │       ├── Header.tsx
│   │   │       └── Sidebar.tsx
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ProjectList.tsx
│   │   │   ├── ProjectDetail.tsx
│   │   │   ├── ProjectForm.tsx
│   │   │   └── GanttChart.tsx
│   │   ├── store/
│   │   │   ├── slices/
│   │   │   │   ├── authSlice.ts
│   │   │   │   ├── projectSlice.ts
│   │   │   │   └── uiSlice.ts
│   │   │   └── index.ts
│   │   ├── utils/
│   │   │   ├── axios.ts
│   │   │   └── validation.ts
│   │   ├── types/
│   │   │   ├── user.ts
│   │   │   └── project.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 3. 데이터베이스 명세

### 3.1 User 테이블

#### 3.1.1 스키마
| 필드명 | 데이터형 | 제약조건 | 설명 |
|--------|---------|---------|------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | 사용자 고유 식별자 |
| email | VARCHAR(255) | UNIQUE, NOT NULL | 이메일 (로그인 ID) |
| password_hash | VARCHAR(255) | NOT NULL | 해시된 비밀번호 |
| name | VARCHAR(100) | NOT NULL | 사용자 이름 |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'PM' | 역할 (PM, ADMIN) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 업데이트일 |

#### 3.1.2 인덱스
- `idx_user_email` ON user(email)
- `idx_user_role` ON user(role)

#### 3.1.3 SQLAlchemy 모델
```python
# app/models/user.py
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="PM", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계
    projects = relationship("Project", back_populates="created_by", foreign_keys="Project.created_by")
    missions = relationship("Mission", back_populates="assigned_to", foreign_keys="Mission.assigned_to")
```

---

### 3.2 Project 테이블

#### 3.2.1 스키마
| 필드명 | 데이터형 | 제약조건 | 설명 |
|--------|---------|---------|------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | 프로젝트 고유 식별자 |
| project_code | VARCHAR(20) | UNIQUE, NOT NULL | 프로젝트 코드 (고유) |
| project_name | VARCHAR(50) | NOT NULL | 프로젝트명 |
| client | VARCHAR(100) | NOT NULL | 고객사 |
| designer | VARCHAR(50) | NOT NULL | 설계자 |
| developers | TEXT | NULLABLE | 개발자 (콤마 구분) |
| start_date | DATE | NOT NULL | 프로젝트 시작일 |
| end_date | DATE | NOT NULL | 프로젝트 종료일 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'planning' | 상태 (planning, in_progress, completed, on_hold) |
| created_by | VARCHAR(36) | NOT NULL, FK -> user(id) | 생성자 ID |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 업데이트일 |
| deleted_at | TIMESTAMP | NULLABLE | 논리적 삭제일 |

#### 3.2.2 인덱스
- `idx_project_code` ON project(project_code)
- `idx_project_status` ON project(status)
- `idx_project_start_date` ON project(start_date)
- `idx_project_end_date` ON project(end_date)
- `idx_project_created_by` ON project(created_by)
- `idx_project_deleted_at` ON project(deleted_at) WHERE deleted_at IS NOT NULL

#### 3.2.3 제약조건
- CHECK: end_date >= start_date
- CHECK: status IN ('planning', 'in_progress', 'completed', 'on_hold')

#### 3.2.4 SQLAlchemy 모델
```python
# app/models/project.py
from sqlalchemy import Column, String, DateTime, Text, Date, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.database import Base

class Project(Base):
    __tablename__ = "projects"
    
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="check_end_date_after_start"),
        CheckConstraint("status IN ('planning', 'in_progress', 'completed', 'on_hold')", name="check_valid_status"),
    )
    
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    project_code = Column(String(20), unique=True, index=True, nullable=False)
    project_name = Column(String(50), nullable=False)
    client = Column(String(100), nullable=False)
    designer = Column(String(50), nullable=False)
    developers = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="planning", index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # 관계
    created_by_user = relationship("User", back_populates="projects", foreign_keys=[created_by])
    missions = relationship("Mission", back_populates="project", cascade="all, delete-orphan")
```

---

### 3.3 Mission 테이블 (옵션)

#### 3.3.1 스키마
| 필드명 | 데이터형 | 제약조건 | 설명 |
|--------|---------|---------|------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | 미션 고유 식별자 |
| project_id | VARCHAR(36) | NOT NULL, FK -> project(id) | 프로젝트 ID |
| title | VARCHAR(200) | NOT NULL | 미션 제목 |
| description | TEXT | NULLABLE | 미션 설명 |
| start_date | DATE | NOT NULL | 시작일 |
| end_date | DATE | NOT NULL | 종료일 |
| progress | INTEGER | NOT NULL, DEFAULT 0, CHECK(0 <= progress <= 100) | 진행률 (0-100) |
| assigned_to | VARCHAR(36) | NULLABLE, FK -> user(id) | 담당자 ID |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 업데이트일 |

#### 3.3.2 인덱스
- `idx_mission_project_id` ON mission(project_id)
- `idx_mission_assigned_to` ON mission(assigned_to)

#### 3.3.3 제약조건
- CHECK: end_date >= start_date
- CHECK: progress >= 0 AND progress <= 100

#### 3.3.4 SQLAlchemy 모델
```python
# app/models/mission.py
from sqlalchemy import Column, String, DateTime, Text, Date, ForeignKey, CheckConstraint, Integer, func
from sqlalchemy.orm import relationship
from app.database import Base

class Mission(Base):
    __tablename__ = "missions"
    
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="check_mission_end_date_after_start"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="check_valid_progress"),
    )
    
    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 관계
    project = relationship("Project", back_populates="missions")
    assigned_to_user = relationship("User", back_populates="missions", foreign_keys=[assigned_to])
```

---

## 4. API 명세

### 4.1 인증 (Authentication) API

#### 4.1.1 사용자 등록 (POST /api/v1/auth/register)

**요청 헤더**:
```
Content-Type: application/json
```

**요청 바디**:
```json
{
  "email": "pm@example.com",
  "password": "SecurePass123!",
  "name": "홍길동",
  "role": "PM"
}
```

**검증 규칙**:
- email: 이메일 형식, 3-255 자, 중복 불가
- password: 최소 8 자, 대문자 1 개 이상, 소문자 1 개 이상, 숫자 1 개 이상, 특수문자 1 개 이상
- name: 2-100 자
- role: "PM" 또는 "ADMIN" (기본값: "PM")

**응답 (201 Created)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "pm@example.com",
  "name": "홍길동",
  "role": "PM",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**에러 응답**:
```json
// 400 Bad Request - 유효성 검사 실패
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "email must be unique",
      "type": "value_error"
    }
  ]
}

// 422 Unprocessable Entity - 비밀번호 조건 불만족
{
  "detail": "Password must be at least 8 characters with uppercase, lowercase, number, and special character"
}
```

#### 4.1.2 로그인 (POST /api/v1/auth/login)

**요청 바디**:
```json
{
  "email": "pm@example.com",
  "password": "SecurePass123!"
}
```

**응답 (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "pm@example.com",
    "name": "홍길동",
    "role": "PM"
  }
}
```

**에러 응답**:
```json
// 401 Unauthorized - 이메일 또는 비밀번호 오류
{
  "detail": "Incorrect email or password"
}

// 401 Unauthorized - 비활성화된 계정
{
  "detail": "User account is deactivated"
}
```

#### 4.1.3 현재 사용자 정보 조회 (GET /api/v1/auth/me)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "pm@example.com",
  "name": "홍길동",
  "role": "PM",
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### 4.2 프로젝트 (Project) API

#### 4.2.1 프로젝트 목록 조회 (GET /api/v1/projects)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**쿼리 파라미터**:
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| page | integer | 아니요 | 1 | 페이지 번호 (1 이상) |
| page_size | integer | 아니요 | 10 | 페이지 크기 (1-100) |
| search | string | 아니요 | - | 검색어 (프로젝트명, 코드, 고객사) |
| status | string | 아니요 | - | 상태 필터 |
| start_date_from | date | 아니요 | - | 시작일 범위를부터 |
| start_date_to | date | 아니요 | - | 시작일 범위를 Until |
| client | string | 아니요 | - | 고객사 이름 필터 |

**예시**:
```
GET /api/v1/projects?page=1&page_size=20&status=in_progress&search=웹
```

**응답 (200 OK)**:
```json
{
  "total": 45,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "project_code": "PROJ-001",
      "project_name": "웹사이트 리뉴얼",
      "client": "삼성전자",
      "designer": "김설계",
      "developers": "이개발, 박프론트",
      "start_date": "2025-01-01",
      "end_date": "2025-06-30",
      "status": "in_progress",
      "created_at": "2024-12-01T09:00:00Z"
    }
  ]
}
```

#### 4.2.2 프로젝트 상세 조회 (GET /api/v1/projects/{id})

**경로 파라미터**:
- id: UUID 문자열

**응답 (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "project_code": "PROJ-001",
  "project_name": "웹사이트 리뉴얼",
  "client": "삼성전자",
  "designer": "김설계",
  "developers": "이개발, 박프론트",
  "start_date": "2025-01-01",
  "end_date": "2025-06-30",
  "status": "in_progress",
  "created_by": {
    "id": "110e8400-e29b-41d4-a716-446655440001",
    "name": "홍길동"
  },
  "created_at": "2024-12-01T09:00:00Z",
  "updated_at": "2025-01-10T14:30:00Z",
  "missions": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "title": "UI/UX 설계",
      "start_date": "2025-01-01",
      "end_date": "2025-02-15",
      "progress": 80
    }
  ]
}
```

#### 4.2.3 프로젝트 등록 (POST /api/v1/projects)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**요청 바디**:
```json
{
  "project_code": "PROJ-002",
  "project_name": "모바일 앱 개발",
  "client": "SK텔레콤",
  "designer": "김설계2",
  "developers": "이개발, 박프론트, 정백엔드",
  "start_date": "2025-02-01",
  "end_date": "2025-08-31",
  "status": "planning"
}
```

**검증 규칙**:
- project_code: 2-20 자, 고유, 영문/숫자/하이픈 허용
- project_name: 1-50 자, 필수
- client: 1-100 자, 필수
- designer: 1-50 자, 필수
- developers: 0-200 자, 선택 (콤마 구분)
- start_date: 현재일 이후, 필수
- end_date: start_date 이후, 필수
- status: "planning", "in_progress", "completed", "on_hold" 중 하나

**응답 (201 Created)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "project_code": "PROJ-002",
  "project_name": "모바일 앱 개발",
  "client": "SK텔레콤",
  "designer": "김설계2",
  "developers": "이개발, 박프론트, 정백엔드",
  "start_date": "2025-02-01",
  "end_date": "2025-08-31",
  "status": "planning",
  "created_by": "110e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**에러 응답**:
```json
// 400 Bad Request - 중복 프로젝트 코드
{
  "detail": "Project code 'PROJ-002' already exists"
}

// 422 Unprocessable Entity - 유효성 검사 실패
{
  "detail": [
    {
      "loc": ["body", "end_date"],
      "msg": "end_date must be after start_date",
      "type": "value_error"
    }
  ]
}
```

#### 4.2.4 프로젝트 수정 (PUT /api/v1/projects/{id})

**경로 파라미터**:
- id: UUID 문자열

**요청 바디** (모든 필드 선택적):
```json
{
  "project_name": "모바일 앱 개발 (수정)",
  "status": "in_progress",
  "end_date": "2025-09-30"
}
```

**응답 (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "project_code": "PROJ-002",
  "project_name": "모바일 앱 개발 (수정)",
  "client": "SK텔레콤",
  "designer": "김설계2",
  "developers": "이개발, 박프론트, 정백엔드",
  "start_date": "2025-02-01",
  "end_date": "2025-09-30",
  "status": "in_progress",
  "updated_at": "2025-01-20T15:45:00Z"
}
```

#### 4.2.5 프로젝트 삭제 (DELETE /api/v1/projects/{id})

**경로 파라미터**:
- id: UUID 문자열

**응답 (204 No Content)**:
```
(Empty response body)
```

**에러 응답**:
```json
// 404 Not Found - 프로젝트 없음
{
  "detail": "Project not found"
}
```

#### 4.2.6 프로젝트 통계 조회 (GET /api/v1/projects/stats)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 (200 OK)**:
```json
{
  "total_projects": 45,
  "active_projects": 20,
  "completed_projects": 15,
  "on_hold_projects": 5,
  "planning_projects": 5,
  "projects_by_client": [
    {"client": "삼성전자", "count": 10},
    {"client": "SK텔레콤", "count": 8},
    {"client": "LG전자", "count": 7}
  ],
  "monthly_stats": [
    {"month": "2025-01", "created": 5, "completed": 3},
    {"month": "2025-02", "created": 3, "completed": 2}
  ]
}
```

---

## 5. 프론트엔드 명세

### 5.1 페이지 구조

#### 5.1.1 로그인 페이지 (/login)
- **필드**: 이메일, 비밀번호
- **기능**: 
  - 실시간 유효성 검사
  - 비밀번호 확인 토글
  - "아이디/비밀번호 찾기" 링크
- **테스트 시나리오**:
  - 유효한 creds 로 로그인 성공
  - 잘못된 credentials 로 로그인 실패
  - 공란 입력 시 유효성 오류 표시

#### 5.1.2 프로젝트 목록 페이지 (/projects)
- **표시 필드**: 프로젝트명, 코드, 고객사, 시작일, 종료일, 상태, 진행률
- **기능**:
  - 검색 (프로젝트명, 코드, 고객사)
  - 상태 필터
  - 날짜 범위 필터
  - 정렬 (날짜, 프로젝트명)
  - 페이지네이션 (10/20/50 개/페이지)
  - 새 프로젝트 등록 버튼
  - 프로젝트 상세 보기 링크
- **테스트 시나리오**:
  - 검색어 입력 시 필터링 적용
  - 상태 필터 변경 시 목록 업데이트
  - 페이지네이션 정상 작동

#### 5.1.3 프로젝트 상세 페이지 (/projects/:id)
- **섹션**:
  1. 프로젝트 정보 (기본 정보, 생성자, 생성일, 업데이트일)
  2. 간트 차트
  3. 미션 목록 (있을 경우)
  4. 수정/삭제 버튼
- **기능**:
  - 상태 배지 표시 (색상별: planning=회색, in_progress=파랑, completed=초록, on_hold=주황)
  - 간트 차트에서 기간 클릭 시 미션 추가 모달
  - 수정 버튼 클릭 시 프로젝트 formul 에 이동
  - 삭제 버튼 클릭 시 확인 모달 표시
- **테스트 시나리오**:
  - 프로젝트 ID 로 정확한 데이터 조회
  - 간트 차트 정상 렌더링
  - 삭제 시 확인 모달 표시 후 삭제

#### 5.1.4 프로젝트 등록/수정 페이지 (/projects/create, /projects/:id/edit)
- **필드**:
  - 프로젝트코드 (필수, 2-20 자)
  - 프로젝트명 (필수, 1-50 자)
  - 고객사 (필수, 1-100 자)
  - 설계자 (필수, 1-50 자)
  - 개발자 (선택, 0-200 자, 콤마 구분)
  - 시작일 (필수, 날짜 picker)
  - 종료일 (필수, 날짜 picker, 시작일 이후)
  - 상태 (필수, select)
- **기능**:
  - 실시간 유효성 검사
  - 시작일 선택 시 종료일 최소값 자동 설정
  - 코드 중복 확인 (blur 시)
  - 저장 시 로딩 표시
  - 저장 성공 시 목록으로 이동
  - 저장 실패 시 에러 메시지 표시
- **테스트 시나리오**:
  - 모든 필드 입력 후 저장 성공
  - 중복 코드 입력 시 경고
  - 종료일이 시작일 이전일 경우 에러

#### 5.1.5 대시보드 페이지 (/dashboard)
- **위젯**:
  1. 총 프로젝트 수 카드
  2. 진행 중 프로젝트 수 카드
  3. 완료 프로젝트 수 카드
  4. 진행률 차트 (프로젝트 상태별)
  5. 고객사별 프로젝트 분포 차트
  6. 월간 통계 차트
- **기능**:
  - 데이터 자동 갱신 (30 초 간격)
  - 차트 호버 시 툴팁 표시
  - 차트 클릭 시 상세 페이지로 이동
- **테스트 시나리오**:
  - 로그인 시 자동 리디렉션
  - 통계 데이터 정확성 검증

#### 5.1.6 간트 차트 컴포넌트
- **라이브러리**: dhtmlxGantt (프로 버전) 또는 Viser (오픈소스)
- **기능**:
  - 월/주/일 뷰 전환
  - 프로젝트 막대 표시 (상태별 색상)
  - 마일스톤 표시
  - 진행률 표시 (배 안에 %)
  - 드래그 앤 드롭으로 일정 수정
  - 더블 클릭으로 미션 추가/수정
  - 기간 선택 시 확대/축소
  - 툴팁에 프로젝트 정보 표시
- **테스트 시나리오**:
  - 프로젝트 데이터로 차트 렌더링
  - 뷰 모드 전환 정상 작동
  - 드래그 앤 드롭 시 API 호출

---

## 6. 상태 관리 명세

### 6.1 Auth Slice

**상태**:
```typescript
interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}
```

**액션**:
- `login(email, password)`: 로그인 실행
- `logout()`: 로그아웃
- `register(userData)`: 사용자 등록
- `fetchCurrentUser()`: 현재 사용자 정보 조회
- `clearError()`: 에러 클리어

### 6.2 Project Slice

**상태**:
```typescript
interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
  };
  filters: {
    search: string;
    status: string;
    startDateFrom: string;
    startDateTo: string;
    client: string;
  };
}
```

**액션**:
- `fetchProjects(params)`: 프로젝트 목록 조회
- `fetchProject(id)`: 프로젝트 상세 조회
- `createProject(data)`: 프로젝트 등록
- `updateProject(id, data)`: 프로젝트 수정
- `deleteProject(id)`: 프로젝트 삭제
- `setFilters(filters)`: 필터 설정
- `changePage(page)`: 페이지 변경

### 6.3 UI Slice

**상태**:
```typescript
interface UIState {
  loading: boolean;
  error: string | null;
  modal: {
    isOpen: boolean;
    type: 'confirm' | 'alert' | 'form' | null;
    content: any;
  };
}
```

**액션**:
- `showLoading()`: 로딩 표시
- `hideLoading()`: 로딩 숨김
- `showError(message)`: 에러 표시
- `hideError()`: 에러 숨김
- `openModal(config)`: 모달 열기
- `closeModal()`: 모달 닫기

---

## 7. 테스트 명세

### 7.1 백엔드 테스트 범위

#### 7.1.1 단위 테스트 (Unit Test)
- **모델 테스트**: 
  - 생성, 업데이트, 검증 로직
  - 관계 설정 검증
- **서비스 로직 테스트**:
  - 비즈니스 로직
  - 유효성 검사
- **유틸리티 함수 테스트**:
  - 토큰 생성/검증
  - 비밀번호 해싱

#### 7.1.2 통합 테스트 (Integration Test)
- **API 엔드포인트 테스트**:
  - 정상 응답 (200, 201)
  - 에러 응답 (400, 401, 404, 422)
  - 인증/권한 검증
- **DB 상호작용 테스트**:
  - CRUD 연산
  - 쿼리 파라미터 필터링
  - 페이지네이션

#### 7.1.3 테스트 커버리지 목표
- 전체: 80% 이상
- 모델: 90% 이상
- API: 85% 이상
- 유틸리티: 95% 이상

### 7.2 프론트엔드 테스트 범위

#### 7.2.1 단위 테스트
- **컴포넌트 테스트**:
  - 렌더링 검증
  - 이벤트 핸들링
  - 상태 변화
- ** 유틸리티 함수 테스트**:
  - 검증 로직
  - 데이터 변환

#### 7.2.2 통합 테스트
- **상태 관리 테스트**:
  - Slice 액션
  - Thunk 함수
- **API 연동 테스트**:
  - Axios 인스턴스
  - 인터셉터

#### 7.2.3 E2E 테스트
- **플레이스홀더 시나리오**:
  - 로그인 → 프로젝트 목록 조회 → 프로젝트 등록 → 수정 → 삭제
  - 대시보드 데이터 확인
  - 간트 차트 상호작용

### 7.3 테스트 도구
- **백엔드**: pytest, pytest-cov, Faker, pytest-asyncio
- **프론트엔드**: Jest, React Testing Library, MSW (Mock Service Worker)
- **E2E**: Playwright 또는 Cypress

---

## 8. 보안 명세

### 8.1 인증/인가
- JWT 토큰 만료 시간: 30 분
- 리프레시 토큰: 7 일
- 비밀번호 최소 길이: 8 자
- 비밀번호 정책: 대/소문자, 숫자, 특수문자 포함
- RBAC:
  - PM: CRUD (자신 프로젝트만)
  - ADMIN: 전체 CRUD + 사용자 관리

### 8.2 입력 검증
- SQL 인젝션 방지: SQLAlchemy ORM 사용
- XSS 방지: 출력 인코딩, Content-Security-Policy
- CSRF 방지: SameSite 쿠키, CSRF 토큰
- XSS/스크립트 삽입 차단: 입력값 필터링

### 8.3 API 보안
- HTTPS 강제
- Rate limiting: 100 요청/분 (IP 기준)
- CORS 설정: 허용된 도메인만
- 헤더 보안: X-Content-Type-Options, X-Frame-Options

---

## 9. 성능 명세

### 9.1 백엔드
- API 응답 시간: P95 200ms 이내
- DB 쿼리 최적화: 인덱스 활용, N+1 문제 방지
- 캐싱: Redis (세션, 자주 참조 데이터)
- 연결 풀링: SQLAlchemy 연결 풀 20 개

### 9.2 프론트엔드
- 초기 로딩 시간: 3 초 이내
- 코드 스플리팅: 라우트 기반
- 이미지 최적화: WebP 형식, 지연 로딩
- 메모이제이션: React.memo, useMemo, useCallback

---

## 10. 배포 명세

### 10.1 개발 환경
- 로컬 개발: Docker Compose
- 데이터베이스: PostgreSQL 15
- 시크릿 관리: 환경 변수

### 10.2 프로덕션
- 컨테이너: Docker
- 오케스트레이션: Kubernetes
- CI/CD: GitHub Actions
- 모니터링: Prometheus, Grafana
- 로그: ELK Stack

### 10.3 데이터 백업
- 일일 백업 (자동)
- 30 일 유지
- 복원 테스트 분기별

---

## 부록

### A. 에러 코드 정의
| 코드 | 설명 | HTTP 상태 |
|------|------|----------|
| AUTH_001 | 로그인 실패 (잘못된 creds) | 401 |
| AUTH_002 | 토큰 만료 | 401 |
| AUTH_003 | 권한 없음 | 403 |
| PROJECT_001 | 프로젝트 없음 | 404 |
| PROJECT_002 | 중복 프로젝트 코드 | 400 |
| VALIDATION_001 | 유효성 검사 실패 | 422 |

### B. API 버전 관리
- 현재 버전: v1
- 버전 경로: /api/v1/*
- 변경 시 새 버전 증가 (v2)

### C. 참고 문서
- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- Material-UI: https://mui.com/
- React Router: https://reactrouter.com/
