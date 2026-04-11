# PMS (Project Management System) - 제품 요구사항 명세서 (PRD)

## 1. 문서 정보
- **문서명**: PMS 제품 요구사항 명세서
- **버전**: 1.0
- **작성일**: 2024
- **작성자**: AI Assistant
- **대상**: PM, PMO, 개발자

## 2. 개요

### 2.1 프로젝트 배경
IT 회사에서 다수의 프로젝트를 효율적으로 관리하기 위한 통합 프로젝트 관리 시스템 필요

### 2.2 목표
- 프로젝트 정보의 체계적인 관리
- 직관적인 일정이행 시각화 (간트 차트)
- 웹 및 모바일 접근성 확보
- 역할 기반 접근 제어 (PM, PMO, 임원)

### 2.3 범위
- 프로젝트 등록, 조회, 수정, 삭제 기능
- 일정 관리 및 간트 차트 시각화
- 사용자 권한 관리
- 웹 및 모바일 웹 인터페이스

## 3. 사용자 역할

### 3.1 일반 사용자 (PM)
- 프로젝트 정보 입력 및 관리
- 자신의 프로젝트 일정 확인
- 간트 차트 조회

### 3.2 관리자 (임원, PMO)
- 모든 프로젝트 조회 및 관리
- 프로젝트 등록 승인/거절
- 전체 일정 모니터링
- 사용자 권한 관리

## 4. 기능 요구사항

### 4.1 프로젝트 관리 기능

#### 4.1.1 프로젝트 등록
- **입력 항목**:
  - 프로젝트명 (필수, 최대 100 자)
  - 프로젝트코드 (필수, 영대문자/숫자, 최대 20 자)
  - 고객사 (필수, 최대 50 자)
  - 설계자 (필수, 최대 50 자)
  - 개발자 (복수 입력 가능, 최대 50 자)
  - 시작일 (필수)
  - 종료일 (필수, 시작일 이후)
- **유효성 검사**:
  - 중복 프로젝트코드 체크
  - 종료일은 시작일보다 늦어야 함
  - 필수 항목 입력 확인

#### 4.1.2 프로젝트 조회
- 전체 프로젝트 목록 조회
- 검색 기능 (프로젝트명, 프로젝트코드, 고객사)
- 필터링 기능 (상태, 기간)
- 페이지네이션 (페이지당 10 개 항목)

#### 4.1.3 프로젝트 수정
- 기존 프로젝트 정보 수정
- 수정 이력 기록
- 권한 체크 (자신의 프로젝트만 수정 가능, 관리자는 모든 프로젝트 수정 가능)

#### 4.1.4 프로젝트 삭제
- 소프트 삭제 (삭제 플래그 설정)
- 삭제 불가 조건 (진행 중인 프로젝트는 삭제 제한)

### 4.2 일정 관리 기능

#### 4.2.1 간트 차트
- 프로젝트 일정을 시각적으로 표현
- Gantt.js 또는 유사 라이브러리 활용
- 시작일, 종료일, 진행률 표시
- 마일스톤 표시 기능
- 모바일 반응형 지원

#### 4.2.2 일정 변경
- 드래그 앤 드롭으로 일정 조정
- 실시간 진행률 업데이트
- 변경 사항 자동 저장

### 4.3 사용자 관리 기능

#### 4.3.1 인증/권한
- 로그인/로그아웃
- 역할 기반 접근 제어 (RBAC)
- 토큰 기반 인증 (JWT)

#### 4.3.2 권한 정의
- `USER`: 프로젝트 등록, 자신의 프로젝트 관리
- `ADMIN`: 모든 프로젝트 관리, 사용자 관리
- `EXECUTIVE`: 전체 프로젝트 조회, 대시보드 접근

### 4.4 대시보드 기능 (관리자)
- 전체 프로젝트 현황
- 진행 중 프로젝트 수
- 마감 임박 프로젝트 알림
- 프로젝트별 진행률 현황

## 5. 비기능 요구사항

### 5.1 성능
- 페이지 로딩 시간 3 초 이내
- 동시 사용자 100 명 지원
- API 응답 시간 500ms 이내

### 5.2 보안
- HTTPS 통신
- 비밀번호 암호화 (BCrypt)
- JWT 토큰 만료 시간 24 시간
- SQL 인젝션 방지

### 5.3 호환성
- 웹: Chrome, Firefox, Safari, Edge 최신 2 개 버전
- 모바일: iOS Safari, Android Chrome

### 5.4 유지보수
- 코드 주석 및 docstring 필수
-单元测试覆盖率 80% 이상
- CI/CD 파이프라인 구축

## 6. 기술 스택

### 6.1 백엔드
- **언어**: Python 3.9+
- **프레임워크**: FastAPI
- **데이터베이스**: PostgreSQL 14+
- **ORM**: SQLAlchemy
- **인증**: JWT

### 6.2 프론트엔드
- **웹**: React 18+, TypeScript
- **모바일**: React Native
- **차트**: Gantt.js
- **스타일**: Tailwind CSS

### 6.3 인프라
- **서버**: Nginx
- **컨테이너**: Docker, Docker Compose
- **배포**: AWS 또는 온프레미스

## 7. 데이터베이스 스키마 (초안)

### 7.1 사용자 테이블 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL, -- USER, ADMIN, EXECUTIVE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.2 프로젝트 테이블 (projects)
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name VARCHAR(100) NOT NULL,
    project_code VARCHAR(20) UNIQUE NOT NULL,
    client_name VARCHAR(50) NOT NULL,
    designer VARCHAR(50) NOT NULL,
    developers TEXT, -- JSON 배열
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'PLANNING', -- PLANNING, IN_PROGRESS, COMPLETED, CANCELLED
    progress INTEGER DEFAULT 0, -- 0-100
    is_deleted BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 8. API 명세 (초안)

### 8.1 인증
- `POST /api/auth/login`: 로그인
- `POST /api/auth/logout`: 로그아웃
- `GET /api/auth/me`: 현재 사용자 정보

### 8.2 프로젝트
- `POST /api/projects`: 프로젝트 등록
- `GET /api/projects`: 프로젝트 목록 조회
- `GET /api/projects/{id}`: 프로젝트 상세 조회
- `PUT /api/projects/{id}`: 프로젝트 수정
- `DELETE /api/projects/{id}`: 프로젝트 삭제

### 8.3 간트 차트
- `GET /api/gantt`: 간트 차트 데이터 조회

## 9. UI/UX 요구사항

### 9.1 디자인 원칙
- 간결하고 직관적인 인터페이스
- 모달, 툴팁 활용
- 반응형 디자인
- 일관된 색상 시스템

### 9.2 주요 화면
- 로그인 화면
- 대시보드
- 프로젝트 목록
- 프로젝트 등록/수정
- 간트 차트 뷰

## 10. 일정 계획

| 단계 | 기간 | 주요 작업 |
|------|------|----------|
| 1 단계 | 1 주 | PRD 최종화, DB 스키마 설계 |
| 2 단계 | 2 주 | 백엔드 API 개발 (TDD) |
| 3 단계 | 2 주 | 프론트엔드 개발 |
| 4 단계 | 1 주 | 통합 테스트, 버그 수정 |
| 5 단계 | 1 주 | 배포 및 문서화 |

## 11. 리스크 관리

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| 일정 지연 | 높음 | 우선순위 기반 개발, MVP 먼저 |
| 기술적 난이도 | 중간 | Proof of Concept 먼저 수행 |
| 보안 문제 | 높음 | 보안 검토, 정기적인 취약점 검사 |

## 12. 승인

| 역할 | 이름 | 날짜 | 서명 |
|------|------|------|------|
| 작성자 | AI Assistant | - | - |
| 검토자 | - | - | - |
| 승인자 | - | - | - |
