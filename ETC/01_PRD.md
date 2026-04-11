# PMS (Project Management System) - PRD

## 1. 개요
### 1.1 문서 정보
- **문서명**: PMS 제품 요구사항 정의서
- **버전**: 1.0
- **작성일**: 2025
- **작성자**: AI Agent

### 1.2 프로젝트 목적
IT 회사의 프로젝트 효율적 관리를 위한 웹/모바일 기반 프로젝트 관리 시스템 구축

### 1.3 목표 사용자
- **일반 사용자 (PM)**: 프로젝트 정보 입력 및 관리
- **관리자 (임원/PMO)**: 전사 프로젝트 모니터링 및 일정이중 관리

---

## 2. 기능 요구사항

### 2.1 사용자 역할 정의

#### 2.1.1 일반 사용자 (PM)
- 프로젝트 정보 입력/수정/삭제
- 프로젝트 일정 관리
- 간트 차트 조회
- 프로젝트 상태 모니터링

#### 2.1.2 관리자 (임원/PMO)
- 전체 프로젝트 목록 조회
- 프로젝트 일정 중복 확인
- 프로젝트 현황 대시보드
- 사용자 권한 관리

### 2.2 핵심 기능

#### 2.2.1 프로젝트 관리 (CRUD)
- **프로젝트 등록**
  - 프로젝트명 (필수, 50 자 이내)
  - 프로젝트코드 (필수, 고유값, 20 자 이내)
  - 고객사 (필수, 100 자 이내)
  - 설계자 (필수, 50 자 이내)
  - 개발자 (선택, 200 자 이내, 다중입력)
  - 프로젝트 시작일 (필수)
  - 프로젝트 종료일 (필수, 시작일 이후)
  - 프로젝트 상태 ( planning, in_progress, completed, on_hold)

- **프로젝트 조회**
  - 전체 목록 조회 (페이징 지원)
  - 검색 기능 (프로젝트명, 코드, 고객사)
  - 필터링 기능 (상태, 기간, 고객사)
  - 상세 정보 조회

- **프로젝트 수정**
  - 모든 필드 수정 가능
  - 일정 변경 시 간트 차트 자동 업데이트

- **프로젝트 삭제**
  - 논리적 삭제 (deleted_at 필드)
  - 물리적 삭제 (관리자만 가능)

#### 2.2.2 일정 관리
- 프로젝트 시작일/종료일 관리
- 하위 미션/태스크 일정 관리 (옵션)
- 일정 중복 체크
- 일정 알람 기능

#### 2.2.3 간트 차트
- 시각적 프로젝트 일정 표현
- 프로젝트별 진행률 표시
- 마일스톤 표시
- 기간 드래그 앤 드롭 지원
- 월/주/일 뷰 전환
- 모바일 대응 레스폰시브 디자인

#### 2.2.4 대시보드
- 전체 프로젝트 현황 (통계)
- 진행률 차트
- 고객사별 프로젝트 분포
- 월간 프로젝트 생성/완료 통계

### 2.3 비기능 요구사항

#### 2.3.1 플랫폼 지원
- **웹**: Chrome, Firefox, Safari, Edge (최신 2 버전)
- **모바일**: iOS 14+, Android 10+ (PWA 지원)

#### 2.3.2 성능 요구사항
- 페이지 로딩 시간: 3 초 이내
- 동시 사용자: 100 명 지원
- API 응답 시간: 200ms 이내 (95% 일지)

#### 2.3.3 보안 요구사항
- JWT 기반 인증
- 역할 기반 접근 제어 (RBAC)
- SQL 인젝션 방지
- XSS 대응
- HTTPS 필수

#### 2.3.4 데이터 요구사항
- PostgreSQL 데이터베이스
- 자동 백업 (일일)
- 데이터 무결성约束

---

## 3. 기술 스택

### 3.1 백엔드
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+
- **Migration**: Alembic
- **Authentication**: PyJWT, Passlib

### 3.2 프론트엔드
- **Framework**: React 18+
- **State Management**: Redux Toolkit
- **UI Library**: Material-UI
- **Gantt Chart**: dhtmlxGantt 또는 Viser
- **HTTP Client**: Axios
- **Testing**: Jest, React Testing Library

### 3.3 인프라
- **Container**: Docker
- **Orchestration**: Docker Compose (dev), Kubernetes (prod)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana

---

## 4. 데이터 모델

### 4.1 주요 엔티티

#### User
- id: UUID
- email: String (unique)
- password_hash: String
- name: String
- role: Enum (PM, ADMIN)
- created_at: DateTime
- updated_at: DateTime

#### Project
- id: UUID
- project_code: String (unique)
- project_name: String
- client: String
- designer: String
- developers: String (comma-separated)
- start_date: Date
- end_date: Date
- status: Enum
- created_by: UUID (FK -> User)
- created_at: DateTime
- updated_at: DateTime
- deleted_at: DateTime (nullable)

#### Mission (옵션 - 하위 태스크)
- id: UUID
- project_id: UUID (FK -> Project)
- title: String
- start_date: Date
- end_date: Date
- progress: Int (0-100)
- assigned_to: UUID (FK -> User)
- created_at: DateTime

---

## 5. API 설계 개요

### 5.1 Authentication
- POST /api/v1/auth/login
- POST /api/v1/auth/register
- POST /api/v1/auth/logout
- GET /api/v1/auth/me

### 5.2 Projects
- GET /api/v1/projects (목록 조회, 필터링)
- POST /api/v1/projects (등록)
- GET /api/v1/projects/{id} (상세 조회)
- PUT /api/v1/projects/{id} (수정)
- DELETE /api/v1/projects/{id} (삭제)
- GET /api/v1/projects/stats (통계)

### 5.3 Missions
- GET /api/v1/projects/{project_id}/missions
- POST /api/v1/projects/{project_id}/missions
- PUT /api/v1/missions/{id}
- DELETE /api/v1/missions/{id}

---

## 6. UI/UX 요구사항

### 6.1 페이지 구성
1. **로그인/등록 페이지**
2. **대시보드** (통계, 차트)
3. **프로젝트 목록 페이지** (테이블, 필터)
4. **프로젝트 상세 페이지** (정보, 간트 차트, 태스크)
5. **프로젝트 등록/수정 페이지**
6. **관리자 페이지** (사용자 관리, 전체 일정)

### 6.2 디자인 원칙
- 모던하고 직관적인 UI
- 일관된 컬러 스키마
- 접근성 (WCAG 2.1 AA)
- 모바일 퍼스트 응답 디자인

---

## 7. 개발 방법론

### 7.1 프로세스
1. **SDD (Specification Driven Development)**: 명세서 기반 개발
2. **TDD (Test Driven Development)**: 테스트 우선 개발
   - Red: 테스트 작성
   - Green: 최소 코드 구현
   - Refactor: 코드 리팩토링

### 7.2 품질 기준
- 코드 커버리지: 80% 이상
- 정적 분석: Pass (flake8, mypy)
-linting: Black, isort 적용

---

## 8. 일정 계획 (추정)

| 단계 | 작업 내용 | 예상 기간 |
|------|----------|----------|
| 1 | PRD 작성 및 검토 | 1 일 |
| 2 | 상세 명세서 작성 | 2 일 |
| 3 | DB 설계 및 마이그레이션 | 1 일 |
| 4 | 백엔드 API 개발 (TDD) | 5 일 |
| 5 | 프론트엔드 UI 개발 | 5 일 |
| 6 | 간트 차트 구현 | 2 일 |
| 7 | 통합 테스트 | 2 일 |
| 8 | 배포 및 문서화 | 1 일 |
| **총계** | | **19 일** |

---

## 9. 위험 요소 및 대응

| 위험 | 영향 | 대응 방안 |
|------|------|----------|
| 일정 지연 | 프로젝트 지연 | weekly 체크, 우선순위 관리 |
| 기술적 어려움 | 품질 저하 | POC, 기술 검토 세션 |
| 요구사항 변경 | 재작업 | 변경 관리 프로세스 |
| 보안전락 | 데이터 유출 | 보안 검토, 정기 감사 |

---

## 10. 성공 지표 (KPI)

- 사용자 만족도: 4.0/5.0 이상
- 시스템 가용성: 99.5% 이상
- 평균 응답 시간: 200ms 이내
- 버그 밀도: 0.5/천 줄 이하

---

## 부록

### A. 참고 문서
- FastAPI 공식 문서
- SQLAlchemy ORM 가이드
- Material-UI 컴포넌트

### B. 용어 사전
- **PM**: 프로젝트 매니저
- **PMO**: 프로젝트 관리办公室
- **Gantt**: 프로젝트 일정을 막대차트로 표현
- **Milestone**: 주요 달성 목표 지점
