# PMS 프로젝트 - 원자 단위 작업 분해

## 1. 프로젝트 설정 및 환경 구축

### 1.1 백엔드 프로젝트 설정
- [ ] FastAPI 프로젝트 구조 생성
- [ ] requirements.txt 작성
- [ ] .env 파일 설정
- [ ] Docker-compose 설정
- [ ] SQLAlchemy 데이터베이스 설정
- [ ] Alembic 마이그레이션 설정

### 1.2 프론트엔드 프로젝트 설정
- [ ] React TypeScript 프로젝트 생성 (Create React App 또는 Vite)
- [ ] Tailwind CSS 설정
- [ ] Redux Toolkit 설정
- [ ] React Router 설정
- [ ] React Query 설정
- [ ] ESLint, Prettier 설정

### 1.3 모바일 프로젝트 설정
- [ ] React Native 프로젝트 생성
- [ ] React Native Web 설정
- [ ] 공통 컴포넌트 구조 설정

---

## 2. 데이터베이스 설계

### 2.1 User 테이블
```python
# 구체적 명세
- id: UUID, PRIMARY KEY, 기본값: uuid4()
- username: VARCHAR(50), UNIQUE, NOT NULL
- email: VARCHAR(100), UNIQUE, NOT NULL
- password_hash: VARCHAR(255), NOT NULL
- role: ENUM('PM', 'ADMIN'), 기본값: 'PM', NOT NULL
- created_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- updated_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- deleted_at: TIMESTAMP, NULL (소프트 삭제)
```

### 2.2 Project 테이블
```python
# 구체적 명세
- id: UUID, PRIMARY KEY, 기본값: uuid4()
- project_name: VARCHAR(100), NOT NULL
- project_code: VARCHAR(50), UNIQUE, NOT NULL
- client_name: VARCHAR(100), NOT NULL
- designer: VARCHAR(50)
- developers: JSON, 기본값: []
- start_date: DATE, NOT NULL
- end_date: DATE, NOT NULL
- progress: INTEGER, 기본값: 0, CHECK (progress >= 0 AND progress <= 100)
- status: ENUM('PLANNING', 'IN_PROGRESS', 'COMPLETED', 'HELD', 'CANCELLED'), 기본값: 'PLANNING', NOT NULL
- created_by: UUID, FOREIGN KEY -> User.id, NOT NULL
- created_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- updated_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- deleted_at: TIMESTAMP, NULL (소프트 삭제)
- INDEX(project_code)
- INDEX(status)
```

### 2.3 ProjectTask 테이블
```python
# 구체적 명세
- id: UUID, PRIMARY KEY, 기본값: uuid4()
- project_id: UUID, FOREIGN KEY -> Project.id, NOT NULL
- task_name: VARCHAR(200), NOT NULL
- task_start_date: DATE, NOT NULL
- task_end_date: DATE, NOT NULL
- task_progress: INTEGER, 기본값: 0, CHECK (task_progress >= 0 AND task_progress <= 100)
- predecessor_ids: JSON, 기본값: []
- assigned_to: UUID, FOREIGN KEY -> User.id (NULL 가능)
- status: ENUM('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED'), 기본값: 'NOT_STARTED', NOT NULL
- created_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- updated_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- INDEX(project_id)
- INDEX(status)
```

### 2.4 AuditLog 테이블
```python
# 구체적 명세
- id: UUID, PRIMARY KEY, 기본값: uuid4()
- entity_type: VARCHAR(50), NOT NULL
- entity_id: UUID, NOT NULL
- action: ENUM('CREATE', 'UPDATE', 'DELETE'), NOT NULL
- changes: JSON, NULL (UPDATE 시 변경 사항 저장)
- user_id: UUID, FOREIGN KEY -> User.id, NOT NULL
- created_at: TIMESTAMP, 기본값: NOW(), NOT NULL
- INDEX(entity_type, entity_id)
- INDEX(user_id)
```

---

## 3. 백엔드 API 개발

### 3.1 인증 시스템

#### 3.1.1 회원가입 API
```python
# 구체적 명세
- Method: POST
- URL: /api/v1/auth/register
- Request Body:
  {
    "username": "string (3-50 자, 영문/숫자/하이픈/언더바)",
    "email": "string (유효한 이메일 형식)",
    "password": "string (최소 8 자, 대문자/소문자/숫자/특수문자 2 가지 이상)"
  }
- Response (201 Created):
  {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "role": "enum",
    "created_at": "datetime"
  }
- Error Responses:
  - 400 Bad Request: 유효성 검사 오류
  - 409 Conflict: 중복된 username 또는 email
- Business Rules:
  - 비밀번호는 BCrypt 로 해시
  - 기본 역할: PM
  - 이메일 형식 검증: RFC 5322 기준
```

#### 3.1.2 로그인 API
```python
# 구체적 명세
- Method: POST
- URL: /api/v1/auth/login
- Request Body:
  {
    "email": "string",
    "password": "string"
  }
- Response (200 OK):
  {
    "access_token": "string (JWT)",
    "refresh_token": "string (JWT)",
    "token_type": "bearer",
    "expires_in": integer (3600 초)
  }
- Error Responses:
  - 401 Unauthorized: 잘못된 이메일 또는 비밀번호
  - 403 Forbidden: 삭제된 계정
- Business Rules:
  - JWT access token 만료 시간: 1 시간
  - JWT refresh token 만료 시간: 7 일
  - 로그인 시 audit log 기록
```

#### 3.1.3 토큰 재발행 API
```python
# 구체적 명세
- Method: POST
- URL: /api/v1/auth/refresh
- Request Body:
  {
    "refresh_token": "string"
  }
- Response (200 OK): 새로운 access_token
- Error Responses:
  - 401 Unauthorized: 유효하지 않은 refresh_token
- Business Rules:
  - 기존 refresh_token 삭제 후 새 token 발급
  - 한 번 사용한 refresh_token 은 재사용 불가
```

#### 3.1.4 로그아웃 API
```python
# 구체적 명세
- Method: POST
- URL: /api/v1/auth/logout
- Request Body:
  {
    "refresh_token": "string"
  }
- Response (200 OK): {"message": "logged out"}
- Error Responses:
  - 401 Unauthorized: 유효하지 않은 refresh_token
- Business Rules:
  - refresh_token 을 블랙리스트에 추가
```

### 3.2 사용자 관리 API

#### 3.2.1 사용자 정보 조회
```python
# 구체적 명세
- Method: GET
- URL: /api/v1/users/{user_id}
- Authorization: 필요 (Admin 또는 본인)
- Response (200 OK):
  {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "role": "enum",
    "created_at": "datetime",
    "projects_count": integer
  }
- Error Responses:
  - 403 Forbidden: 권한 없음
  - 404 Not Found: 존재하지 않는 사용자
```

#### 3.2.2 사용자 목록 조회 (관리자)
```python
# 구체적 명세
- Method: GET
- URL: /api/v1/users
- Query Parameters:
  - page: integer (기본값: 1)
  - page_size: integer (기본값: 20, 최대: 100)
  - role: enum (선택)
  - search: string (선택, username 또는 email)
- Authorization: Admin 만
- Response (200 OK):
  {
    "items": [UserDTO],
    "total": integer,
    "page": integer,
    "page_size": integer,
    "total_pages": integer
  }
```

#### 3.2.3 사용자 정보 수정
```python
# 구체적 명세
- Method: PATCH
- URL: /api/v1/users/{user_id}
- Request Body:
  {
    "username": "string (선택)",
    "email": "string (선택)"
  }
- Authorization: 본인 또는 Admin
- Response (200 OK): 수정된 사용자 정보
- Error Responses:
  - 400 Bad Request: 유효성 검사 오류
  - 409 Conflict: 중복된 username 또는 email
  - 403 Forbidden: 권한 없음
```

#### 3.2.4 사용자 삭제 (소프트 삭제)
```python
# 구체적 명세
- Method: DELETE
- URL: /api/v1/users/{user_id}
- Authorization: Admin 만
- Response (200 OK): {"message": "user deleted"}
- Error Responses:
  - 403 Forbidden: 자신을 삭제하려는 시도
  - 404 Not Found: 존재하지 않는 사용자
- Business Rules:
  - soft delete (deleted_at 설정)
  - 관련 프로젝트는 생성자 정보만 null 로 변경
```

### 3.3 프로젝트 관리 API

#### 3.3.1 프로젝트 목록 조회
```python
# 구체적 명세
- Method: GET
- URL: /api/v1/projects
- Query Parameters:
  - page: integer (기본값: 1)
  - page_size: integer (기본값: 20, 최대: 100)
  - status: enum (선택, 다중 가능)
  - search: string (선택, project_name 또는 client_name 또는 project_code)
  - assignee: uuid (선택, 특정 사용자 관련 프로젝트)
  - sort_by: string (기본값: created_at, options: created_at, start_date, end_date, progress)
  - sort_order: string (기본값: desc, options: asc, desc)
- Authorization: 필요 (로그인한 사용자)
- Response (200 OK):
  {
    "items": [ProjectDTO],
    "total": integer,
    "page": integer,
    "page_size": integer,
    "total_pages": integer
  }
- Business Rules:
  - PM 은 자신의 프로젝트만 조회 가능
  - Admin 은 모든 프로젝트 조회 가능
```

#### 3.3.2 프로젝트 상세 조회
```python
# 구체적 명세
- Method: GET
- URL: /api/v1/projects/{project_id}
- Authorization: 필요 (프로젝트 관련자 또는 Admin)
- Response (200 OK):
  {
    "id": "uuid",
    "project_name": "string",
    "project_code": "string",
    "client_name": "string",
    "designer": "string",
    "developers": ["string"],
    "start_date": "date",
    "end_date": "date",
    "progress": integer,
    "status": "enum",
    "created_by": {
      "id": "uuid",
      "username": "string"
    },
    "created_at": "datetime",
    "updated_at": "datetime",
    "tasks": [TaskDTO]
  }
- Error Responses:
  - 403 Forbidden: 접근 권한 없음
  - 404 Not Found: 존재하지 않는 프로젝트
```

#### 3.3.3 프로젝트 생성
```python
# 구체적 명세
- Method: POST
- URL: /api/v1/projects
- Request Body:
  {
    "project_name": "string (필수, 1-100 자)",
    "project_code": "string (필수, 3-50 자, 고유)",
    "client_name": "string (필수, 1-100 자)",
    "designer": "string (선택, 0-50 자)",
    "developers": ["string"] (선택, 최대 10 명),
    "start_date": "date (필수)",
    "end_date": "date (필수, start_date 이후)"
  }
- Authorization: PM 이상
- Response (201 Created):
  {
    "id": "uuid",
    "project_name": "string",
    "project_code": "string",
    "client_name": "string",
    "designer": "string",
    "developers": ["string"],
    "start_date": "date",
    "end_date": "date",
    "progress": 0,
    "status": "PLANNING",
    "created_by": {...},
    "created_at": "datetime"
  }
- Error Responses:
  - 400 Bad Request: 유효성 검사 오류 (예: end_date < start_date)
  - 409 Conflict: 중복된 project_code
- Business Rules:
  - project_code 생성 후 중복 검사
  - 생성 시 audit log 기록
```

#### 3.3.4 프로젝트 수정
```python
# 구체적 명세
- Method: PATCH
- URL: /api/v1/projects/{project_id}
- Request Body:
  {
    "project_name": "string (선택, 1-100 자)",
    "client_name": "string (선택, 1-100 자)",
    "designer": "string (선택, 0-50 자)",
    "developers": ["string"] (선택, 최대 10 명),
    "start_date": "date (선택)",
    "end_date": "date (선택)",
    "progress": integer (선택, 0-100),
    "status": "enum (선택)"
  }
- Authorization: 프로젝트 생성자 또는 Admin
- Response (200 OK): 수정된 프로젝트 정보
- Error Responses:
  - 400 Bad Request: 유효성 검사 오류
  - 403 Forbidden: 권한 없음
  - 404 Not Found: 존재하지 않는 프로젝트
- Business Rules:
  - 수정 시 변경 사항 audit log 기록
  - end_date 가 start_date 보다 빠르면 오류
  - progress 가 0-100 범위를 벗어나면 오류
```

#### 3.3.5 프로젝트 삭제
```python
# 구체적 명세
- Method: DELETE
- URL: /api/v1/projects/{project_id}
- Authorization: 프로젝트 생성자 또는 Admin
- Response (200 OK): {"message": "project deleted"}
- Error Responses:
  - 403 Forbidden: 권한 없음
  - 404 Not Found: 존재하지 않는 프로젝트
- Business Rules:
  - soft delete (deleted_at 설정)
  - 관련 ProjectTask 도 soft delete
  - 삭제 시 audit log 기록
```

#### 3.3.6 프로젝트 태스크 목록 조회
```python
# 구체적 명세
- Method: GET
- URL: /api/v1/projects/{project_id}/tasks
- Query Parameters:
  - page: integer (기본값: 1)
  - page_size: integer (기본값: 20, 최대: 100)
  - status: enum (선택)
  - assignee: uuid (선택)
  - sort_by: string (기본값: task_start_date, options: task_start_date, task_end_date, task_progress)
  - sort_order: string (기본값: asc, options: asc, desc)
- Authorization: 프로젝트 관련자 또는 Admin
- Response (200 OK):
  {
    "items": [TaskDTO],
    "total": integer,
    "page": integer,
    "page_size": integer,
    "total_pages": integer
  }
```

### 3.4 태스크 관리 API

#### 3.4.1 태스크 생성
```python
# 구체적 명세
- Method: POST
- URL: /api/v1/projects/{project_id}/tasks
- Request Body:
  {
    "task_name": "string (필수, 1-200 자)",
    "task_start_date": "date (필수)",
    "task_end_date": "date (필수, task_start_date 이후)",
    "predecessor_ids": ["uuid"] (선택, 존재하는 태스크 ID),
    "assigned_to": "uuid (선택)",
    "status": "enum (선택, 기본값: NOT_STARTED)"
  }
- Authorization: 프로젝트 생성자 또는 Admin
- Response (201 Created):
  {
    "id": "uuid",
    "project_id": "uuid",
    "task_name": "string",
    "task_start_date": "date",
    "task_end_date": "date",
    "task_progress": 0,
    "predecessor_ids": ["uuid"],
    "assigned_to": {...},
    "status": "enum",
    "created_at": "datetime"
  }
- Error Responses:
  - 400 Bad Request: 유효성 검사 오류
  - 404 Not Found: 존재하지 않는 프로젝트
  - 409 Conflict: 순환 참조 (predecessor_ids)
- Business Rules:
  - predecessor_ids 의 태스크가 존재하는지 검사
  - 순환 참조 검사 (A→B→A 형태 방지)
  - 태스크 생성 시 audit log 기록
```

#### 3.4.2 태스크 수정
```python
# 구체적 명세
- Method: PATCH
- URL: /api/v1/tasks/{task_id}
- Request Body:
  {
    "task_name": "string (선택, 1-200 자)",
    "task_start_date": "date (선택)",
    "task_end_date": "date (선택)",
    "task_progress": integer (선택, 0-100),
    "predecessor_ids": ["uuid"] (선택),
    "assigned_to": "uuid (선택)",
    "status": "enum (선택)"
  }
- Authorization: 태스크 생성자 또는 프로젝트 생성자 또는 Admin
- Response (200 OK): 수정된 태스크 정보
- Error Responses:
  - 400 Bad Request: 유효성 검사 오류
  - 403 Forbidden: 권한 없음
  - 404 Not Found: 존재하지 않는 태스크
- Business Rules:
  - task_end_date < task_start_date 오류
  - task_progress 0-100 범위 검사
  - 수정 시 audit log 기록
```

#### 3.4.3 태스크 삭제
```python
# 구체적 명세
- Method: DELETE
- URL: /api/v1/tasks/{task_id}
- Authorization: 태스크 생성자 또는 프로젝트 생성자 또는 Admin
- Response (200 OK): {"message": "task deleted"}
- Error Responses:
  - 403 Forbidden: 권한 없음
  - 404 Not Found: 존재하지 않는 태스크
- Business Rules:
  - soft delete
  - 삭제 시 audit log 기록
  - 다른 태스크의 predecessor_ids 에서 제거
```

### 3.5 간트 차트 데이터 API

#### 3.5.1 프로젝트 간트 차트 데이터
```python
# 구체적 명세
- Method: GET
- URL: /api/v1/projects/{project_id}/gantt
- Query Parameters:
  - include_subtasks: boolean (기본값: true)
- Authorization: 프로젝트 관련자 또는 Admin
- Response (200 OK):
  {
    "project": {
      "id": "uuid",
      "project_name": "string",
      "start_date": "date",
      "end_date": "date"
    },
    "tasks": [
      {
        "id": "uuid",
        "name": "string",
        "start_date": "date",
        "end_date": "date",
        "progress": integer,
        "status": "enum",
        "predecessors": ["uuid"],
        "children": [{"id": "uuid", "name": "string"}]
      }
    ]
  }
```

---

## 4. 프론트엔드 컴포넌트 개발

### 4.1 인증 관련 컴포넌트

#### 4.1.1 LoginPage 컴포넌트
```python
# 구체적 명세
- 위치: /src/pages/LoginPage
- 필요한 의존성:
  - TextField (TextField)
  - Button (Button)
  - Form (Form)
- 입력 필드:
  - email: email 타입, 필수, placeholder="이메일"
  - password: password 타입, 필수, placeholder="비밀번호"
- 동작:
  - 폼 제출 시 api/auth/login 호출
  - 성공 시 localStorage 에 token 저장, 대시보드로 리다이렉션
  - 실패 시 에러 메시지 표시
- 유효성 검사:
  - email 형식 검사
  - 비밀번호 최소 길이 1 자
- UI:
  - 중앙 정렬된 카드 형태
  - 로딩 상태 표시
  - 에러 메시지 표시
```

#### 4.1.2 RegisterPage 컴포넌트
```python
# 구체적 명세
- 위치: /src/pages/RegisterPage
- 입력 필드:
  - username: text, 필수, placeholder="이름 (3-50 자)"
  - email: email, 필수, placeholder="이메일"
  - password: password, 필수, placeholder="비밀번호 (최소 8 자)"
  - confirmPassword: password, 필수, placeholder="비밀번호 확인"
- 동작:
  - 폼 제출 시 api/auth/register 호출
  - 성공 시 LoginPage 로 리다이렉션
  - 실패 시 에러 메시지 표시
- 유효성 검사:
  - username: 3-50 자, 영문/숫자/하이픈/언더바
  - email: 유효한 이메일 형식
  - password: 최소 8 자
  - password == confirmPassword
```

### 4.2 대시보드 컴포넌트

#### 4.2.1 DashboardPage 컴포넌트
```python
# 구체적 명세
- 위치: /src/pages/DashboardPage
- 표시 항목:
  - OverallStats 카드: 전체 프로젝트 수, 진행중, 완료, 보류, 중단
  - MyProjects 카드: 내가 만든 프로젝트 수
  - AssignedProjects 카드: 내가 할당된 프로젝트 수
  - RecentProjects 목록: 최근 5 개 프로젝트
  - GanttChartPreview: 최근 프로젝트 간트 차트
- API 호출:
  - GET /api/v1/projects (메인 통계용)
  - GET /api/v1/users/me/my-projects
- 상태 관리:
  - React Query 로 데이터 가져오기
  - 로딩 상태, 에러 상태 처리
- UI:
  - 그리드 레이아웃
  - 카드 컴포넌트
  - 반응형 디자인
```

### 4.3 프로젝트 관리 컴포넌트

#### 4.3.1 ProjectListPage 컴포넌트
```python
# 구체적 명세
- 위치: /src/pages/ProjectListPage
- 기능:
  - 프로젝트 목록 표시 (카드 또는 리스트 뷰)
  - 검색 바 (프로젝트명, 프로젝트코드, 고객사)
  - 필터 (상태별)
  - 정렬 (등록일, 시작일, 종료일, 진행률)
  - 페이지네이션
  - 프로젝트 추가 버튼
- UI 구성:
  - SearchBar 컴포넌트
  - FilterBar 컴포넌트
  - ProjectCard 또는 ProjectTableRow 컴포넌트
  - Pagination 컴포넌트
  - AddProjectButton 컴포넌트
- API 호출:
  - GET /api/v1/projects (React Query)
- 상태 관리:
  - 검색어, 필터, 정렬 상태 관리
  - 로딩, 에러 상태 처리
```

#### 4.3.2 ProjectDetailPage 컴포넌트
```python
# 구체적 명세
- 위치: /src/pages/ProjectDetailPage
- 표시 항목:
  - 프로젝트 정보 헤더 (프로젝트명, 코드, 고객사, 진행률)
  - 프로젝트 정보 카드 (설계자, 개발자, 시작일, 종료일)
  - GanttChart 컴포넌트
  - TaskList 컴포넌트
  - 수정/삭제 버튼 (권한에 따라)
- 탭 구성:
  - Overview: 프로젝트 정보, 간트 차트
  - Tasks: 태스크 목록
  - History: 변경 이력
- API 호출:
  - GET /api/v1/projects/{project_id}
  - GET /api/v1/projects/{project_id}/tasks
- 상태 관리:
  - React Query 로 데이터 가져오기
  - 로딩, 에러 상태 처리
```

#### 4.3.3 AddProjectModal 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/Modals/AddProjectModal
- 입력 필드:
  - project_name: text, 필수, placeholder="프로젝트명"
  - project_code: text, 필수, placeholder="프로젝트코드 (영문/숫자/하이픈/언더바)"
  - client_name: text, 필수, placeholder="고객사"
  - designer: text, 선택, placeholder="설계자"
  - developers: multiple text 입력, 선택, 최대 10 명
  - start_date: date, 필수
  - end_date: date, 필수
- 동작:
  - 제출 시 POST /api/v1/projects 호출
  - 성공시 모달 닫고 목록 새로고침
  - 실패 시 에러 메시지 표시
- 유효성 검사:
  - required 필드 검사
  - project_code 형식 검사
  - end_date >= start_date 검사
```

#### 4.3.4 EditProjectModal 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/Modals/EditProjectModal
- 입력 필드: (AddProjectModal 과 유사)
- 동작:
  - 프로젝트 ID 로 데이터 가져오기 (pre-fill)
  - 제출 시 PATCH /api/v1/projects/{project_id} 호출
  - 성공 시 모달 닫고 목록/상세 페이지 새로고침
```

### 4.4 태스크 관리 컴포넌트

#### 4.4.1 TaskList 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/TaskList
- 표시 항목:
  - 태스크 목록 (카드 또는 테이블)
  - 태스크명, 할당자, 시작일, 종료일, 진행률, 상태
  - 정렬 기능
  - 필터 기능 (상태별)
- 동작:
  - 추가 버튼 (AddTaskModal 열기)
  - 수정 버튼 (EditTaskModal 열기)
  - 삭제 버튼 (삭제 확인 다이얼로그)
  - 상태 변경 드롭다운
- API 호출:
  - GET /api/v1/projects/{project_id}/tasks
  - POST /api/v1/projects/{project_id}/tasks
  - PATCH /api/v1/tasks/{task_id}
  - DELETE /api/v1/tasks/{task_id}
```

#### 4.4.2 AddTaskModal 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/Modals/AddTaskModal
- 입력 필드:
  - task_name: text, 필수, placeholder="태스크명"
  - task_start_date: date, 필수
  - task_end_date: date, 필수
  - predecessor_ids: multiple select, 선택 (태스크 목록에서 선택)
  - assigned_to: select, 선택 (사용자 목록)
  - status: select, 선택 (NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED)
- 동작:
  - 제출 시 POST /api/v1/projects/{project_id}/tasks 호출
  - 성공 시 모달 닫고 태스크 목록 새로고침
```

#### 4.4.3 EditTaskModal 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/Modals/EditTaskModal
- 동작:
  - 태스크 ID 로 데이터 가져오기 (pre-fill)
  - 제출 시 PATCH /api/v1/tasks/{task_id} 호출
  - 성공 시 모달 닫고 목록 새로고침
```

### 4.5 간트 차트 컴포넌트

#### 4.5.1 GanttChart 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/GanttChart
- 기능:
  - 프로젝트 일정 시각화 (차트)
  - 태스크 막대 표시 (시작일 ~ 종료일)
  - 진행률 색상 표현 (0-25%: 빨강, 26-50%: 주황, 51-75%: 노랑, 76-100%: 초록)
  - 태스크 간 연결선 (predecessor) 표시
  - 현재 날짜 라인 표시
  - 날짜 단위 전환 (일, 주, 월)
  - 태스크 클릭 시 상세 정보 표시
  - 태스크 드래그 앤 드롭으로 일정 조정
- 의존성:
  - react-gantt-timeline 또는 dhtmlx-gantt 라이브러리
- 데이터 구조:
  - 프로젝트 ID
  - 태스크 목록 (id, name, start_date, end_date, progress, status, predecessors, children)
- 상태 관리:
  - 현재 날짜 범위
  - 현재 날짜 라인 가시성
  - 태스크 선택 상태
- UI:
  - 사이드바 (태스크 목록)
  - 차트 영역 (시간軸 + 태스크 막대)
  - 컨트롤 바 (날짜 단위 전환, 필터)
```

### 4.6 공통 컴포넌트

#### 4.6.1 Layout 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/Layout
- 구조:
  - Header: 로고, 사용자 메뉴, 알림
  - Sidebar: 네비게이션 메뉴 (권한에 따라)
  - Main: 컨텐츠 영역
  - Footer: 저작권 정보
- 반응형:
  - 모바일에서 사이드바 햄버거 메뉴
- 상태:
  - 사이드바 열림/닫힘 상태
  - 사용자 메뉴 열림/닫힘 상태
```

#### 4.6.2 Navbar 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/Navbar
- 표시 항목:
  - 로고 (클릭 시 대시보드로 이동)
  - 검색 바 (프로젝트 검색)
  - 알림 아이콘 (알림 수)
  - 사용자 프로필 메뉴
- 기능:
  - 검색 바 입력 시 자동 완료
  - 알림 클릭 시 알림 목록 표시
  - 사용자 메뉴: 프로필, 설정, 로그아웃
```

#### 4.6.3 LoadingSpinner 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/LoadingSpinner
- 기능:
  - 로딩 중 표시
  - 크기 옵션 (small, medium, large)
  - 색상 옵션
  - 회색 원형 애니메이션
```

#### 4.6.4 ErrorDisplay 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/ErrorDisplay
- 기능:
  - 에러 메시지 표시
  - 에러 아이콘 표시
  - 재시도 버튼
  - 에러 종류별 다른 표시 (404, 500, 네트워크 에러 등)
```

#### 4.6.5 ConfirmDialog 컴포넌트
```python
# 구체적 명세
- 위치: /src/components/ConfirmDialog
- 기능:
  - 확인/취소 다이얼로그
  - 제목, 메시지, 확인 버튼 텍스트, 취소 버튼 텍스트
  - 에러 타입 (danger, warning, info)
  - 비동기적으로 true/false 반환
```

---

## 5. 테스트 개발 (TDD)

### 5.1 백엔드 테스트

#### 5.1.1 인증 시스템 테스트
```python
# 구체적 명세
- 테스트 파일: tests/test_auth.py
- 테스트 항목:
  - test_register_success: 정상 회원가입
  - test_register_duplicate_username: 중복 username 에러
  - test_register_duplicate_email: 중복 email 에러
  - test_register_invalid_email: 잘못된 이메일 형식
  - test_register_invalid_password: 약한 비밀번호
  - test_login_success: 정상 로그인
  - test_login_wrong_password: 잘못된 비밀번호
  - test_login_deleted_user: 삭제된 계정
  - test_token_refresh: 토큰 재발행
  - test_token_refresh_invalid: 유효하지 않은 refresh_token
  - test_logout: 로그아웃
```

#### 5.1.2 프로젝트 관리 테스트
```python
# 구체적 명세
- 테스트 파일: tests/test_project.py
- 테스트 항목:
  - test_create_project: 정상 프로젝트 생성
  - test_create_project_duplicate_code: 중복 프로젝트 코드
  - test_create_project_invalid_dates: 잘못된 일정
  - test_get_project_list: 프로젝트 목록 조회
  - test_get_project_list_with_filter: 필터링 조회
  - test_get_project_list_pagination: 페이지네이션
  - test_get_project_detail: 프로젝트 상세 조회
  - test_get_project_detail_no_permission: 권한 없음
  - test_update_project: 프로젝트 수정
  - test_update_project_no_permission: 권한 없음
  - test_delete_project: 프로젝트 삭제
  - test_delete_project_no_permission: 권한 없음
  - test_soft_delete: soft delete 여부 확인
```

#### 5.1.3 태스크 관리 테스트
```python
# 구체적 명세
- 테스트 파일: tests/test_task.py
- 테스트 항목:
  - test_create_task: 정상 태스크 생성
  - test_create_task_invalid_dates: 잘못된 일정
  - test_create_task_circular_reference: 순환 참조
  - test_get_task_list: 태스크 목록 조회
  - test_update_task: 태스크 수정
  - test_delete_task: 태스크 삭제
```

#### 5.1.4 간트 차트 데이터 테스트
```python
# 구체적 명세
- 테스트 파일: tests/test_gantt.py
- 테스트 항목:
  - test_get_gantt_data: 간트 차트 데이터 조회
  - test_get_gantt_data_with_children: 자식 태스크 포함
  - test_get_gantt_data_predecessors: 선행 태스크 관계
```

### 5.2 프론트엔드 테스트

#### 5.2.1 인증 페이지 테스트
```python
# 구체적 명세
- 테스트 파일: src/__tests__/pages/LoginPage.test.tsx
- 테스트 항목:
  - test_login_form_submit: 폼 제출
  - test_login_with_invalid_email: 잘못된 이메일
  - test_login_with_password: 비밀번호 입력
  - test_api_call_on_submit: API 호출
  - test_redirect_on_success: 성공 시 리다이렉션
  - test_error_display_on_failure: 에러 표시
```

#### 5.2.2 프로젝트 목록 컴포넌트 테스트
```python
# 구체적 명세
- 테스트 파일: src/__tests__/pages/ProjectListPage.test.tsx
- 테스트 항목:
  - test_load_projects: 프로젝트 로드
  - test_search_projects: 검색
  - test_filter_projects: 필터링
  - test_sort_projects: 정렬
  - test_pagination: 페이지네이션
  - test_add_project: 프로젝트 추가
```

#### 5.2.3 프로젝트 상세 컴포넌트 테스트
```python
# 구체적 명세
- 테스트 파일: src/__tests__/pages/ProjectDetailPage.test.tsx
- 테스트 항목:
  - test_load_project_detail: 프로젝트 상세 로드
  - test_display_project_info: 프로젝트 정보 표시
  - test_display_gantt_chart: 간트 차트 표시
  - test_display_tasks: 태스크 목록 표시
  - test_edit_project: 프로젝트 수정
  - test_delete_project: 프로젝트 삭제
```

#### 5.2.4 태스크 컴포넌트 테스트
```python
# 구체적 명세
- 테스트 파일: src/__tests__/components/TaskList.test.tsx
- 테스트 항목:
  - test_load_tasks: 태스크 로드
  - test_add_task: 태스크 추가
  - test_edit_task: 태스크 수정
  - test_delete_task: 태스크 삭제
  - test_filter_tasks: 태스크 필터링
```

#### 5.2.5 간트 차트 컴포넌트 테스트
```python
# 구체적 명세
- 테스트 파일: src/__tests__/components/GanttChart.test.tsx
- 테스트 항목:
  - test_render_gantt_chart: 간트 차트 렌더링
  - test_render_task_bars: 태스크 막대 표시
  - test_render_predecessor_lines: 선행 태스크 연결선
  - test_current_date_line: 현재 날짜 라인
  - test_click_task: 태스크 클릭
  - test_drag_drop_task: 태스크 드래그 앤 드롭
  - test_change_date_scale: 날짜 단위 전환
```

---

## 6. CI/CD 설정

### 6.1 GitHub Actions 워크플로우
```yaml
# 구체적 명세
- 파일: .github/workflows/ci.yml
- 단계:
  - lint: ESLint, Prettier
  - test: 백엔드, 프론트엔드 테스트
  - build: 백엔드, 프론트엔드 빌드
  - docker_build: Docker 이미지 빌드
  - deploy: 배포 (테스트 환경)
```

### 6.2 Docker 설정
```yaml
# 구체적 명세
- 파일: docker-compose.yml
- 서비스:
  - api: 백엔드 (FastAPI)
  - db: PostgreSQL
  - web: 프론트엔드 (Nginx)
  - worker: Celery worker
  - redis: Redis
```

---

## 7. 문서화

### 7.1 API 명세서
```python
# 구체적 명세
- 파일: docs/api.md
- 포함 내용:
  - 모든 API 엔드포인트 명세
  - 요청/응답 예시
  - 에러 코드 목록
  - 인증 방법 설명
```

### 7.2 배포 가이드
```python
# 구체적 명세
- 파일: docs/deployment.md
- 포함 내용:
  - 로컬 환경 설정
  - Docker 배포 가이드
  - AWS 배포 가이드
  - 환경 변수 설정
```

### 7.3 사용자 매뉴얼
```python
# 구체적 명세
- 파일: docs/user_manual.md
- 포함 내용:
  - 시스템 소개
  - 로그인 방법
  - 프로젝트 등록 방법
  - 태스크 관리 방법
  - 간트 차트 사용법
  - 자주 묻는 질문
```

---

## 8. 작업 우선순위

### Phase 1: 핵심 기능 (우선순위: P0)
1. 데이터베이스 설계 및 테이블 생성
2. 인증 시스템 (로그인, 회원가입)
3. 프로젝트 CRUD API 및 UI
4. 태스크 CRUD API 및 UI
5. 기본 간트 차트 구현

### Phase 2: 주요 기능 (우선순위: P1)
1. 프로젝트 검색/필터/정렬
2. 프로젝트 상태 관리
3. 사용자 관리 (관리자)
4. 알림 시스템
5. 보고서 기능

### Phase 3: 고급 기능 (우선순위: P2)
1. 태스크 선행 관계 개선
2. 드래그 앤 드롭 일정 조정
3. 모바일 최적화
4. 성능 최적화
5. 어둠/명 테마

---

## 9. 평가 기준

### 코드 품질
- 테스트 커버리지: 백엔드 80% 이상, 프론트엔드 70% 이상
- 코드 스타일: PEP 8 (백엔드), Airbnb (프론트엔드)
- 정적 분석: No critical issues

### 기능 품질
- 모든 요구사항 구현
- 에러 처리 완전
- 성능 요구사항 충족
- 보안 취약점 없음

### 사용자 경험
- 직관적인 UI/UX
- 반응형 디자인
- 접근성 준수
- 로딩 시간 최적화
