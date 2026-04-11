# 07. 기능 격차 분석: Claude Code vs Codex CLI vs DeepAgents CLI

> **분석 대상**: langchain-ai/deepagents@26647a346cd3c71ca223ad2dc17db812f7203b0f
> **비교 대상**: Claude Code v2.1.x (Anthropic) | Codex CLI v0.119.x (OpenAI, [GitHub](https://github.com/openai/codex))
> **분석일**: 2026-04-04
> **관련 문서**: [06-아키텍처-종합](./06-아키텍처-종합-패턴-레퍼런스.md)

---

## 1. 개요

이 문서는 **DeepAgents CLI**를 발전시킬 때의 개발 방향을 설정하기 위해, 현재 시장을 선도하는 두 AI 코딩 에이전트 CLI — **Claude Code**(Anthropic)와 **Codex CLI**(OpenAI) — 가 보유한 기능 중 DeepAgents CLI에 없는 기능을 식별하고 분석합니다.

### 비교 도구 프로필

| 항목 | Claude Code | Codex CLI | DeepAgents CLI |
|------|-------------|-----------|----------------|
| **개발사** | Anthropic | OpenAI | LangChain AI |
| **언어** | TypeScript | Rust | Python |
| **라이선스** | 독점 (CLI 무료) | Apache-2.0 | MIT |
| **LLM** | Claude (Opus/Sonnet/Haiku) | GPT-4.1/o3/o4-mini | 모든 LangChain 프로바이더 (21개) |
| **프레임워크** | 자체 구현 | 자체 구현 | LangGraph + LangChain |
| **TUI** | Ink (React 터미널) | 자체 Rust TUI | Textual (Python) |
| **출시** | 2024 | 2025 | 2025 |
| **GitHub Stars** | 비공개 소스 | 73,000+ | ~5,000 |

---

## 2. 전체 기능 비교 매트릭스

### 범례
- ✅ 완전 지원 | ⚡ 부분/기본 지원 | ❌ 미지원 | 🔧 외부 도구로 가능

| 카테고리 | 기능 | Claude Code | Codex CLI | DeepAgents CLI |
|----------|------|-------------|-----------|----------------|
| **코어 에이전트** | 코드 생성/수정 | ✅ | ✅ | ✅ |
| | 멀티파일 편집 | ✅ | ✅ | ✅ |
| | 버그 수정 | ✅ | ✅ | ✅ |
| | 코드 설명 | ✅ | ✅ | ✅ |
| | **구조화된 계획 모드** | ✅ Plan Mode | ❌ | ❌ |
| | **확장된 사고** (Extended Thinking) | ✅ | ✅ (o3/o4) | ❌ |
| **도구 시스템** | 파일 읽기/쓰기 | ✅ | ✅ | ✅ |
| | 셸 명령 실행 | ✅ | ✅ | ✅ |
| | **전문 파일 검색 (Glob)** | ✅ 전용 도구 | ✅ ripgrep 통합 | ❌ (셸 명령으로 대체) |
| | **전문 코드 검색 (Grep)** | ✅ 전용 도구 | ✅ ripgrep 내장 | ❌ (셸 명령으로 대체) |
| | **정밀 편집 (Diff 기반)** | ✅ Edit 도구 | ✅ 패치 적용 | ⚡ (전체 파일 쓰기 위주) |
| | 웹 검색 | ✅ WebSearch | ❌ | ✅ Tavily |
| | **웹 페이지 가져오기** | ✅ WebFetch | ❌ | ⚡ (fetch_url) |
| | **Notebook 편집** | ✅ NotebookEdit | ❌ | ❌ |
| | **LSP 통합** | ✅ hover, goto, references | ❌ | ❌ |
| | **JavaScript REPL** | ❌ | ✅ | ❌ |
| | **Python REPL** | ❌ (Bash로 가능) | ❌ | ❌ (Bash로 가능) |
| **컨텍스트 관리** | **프로젝트 메모리 파일** | ✅ CLAUDE.md (계층적) | ✅ AGENTS.md | ❌ |
| | **자동 컨텍스트 압축** | ✅ /compact, 자동 | ❌ | ⚡ (SummarizationMiddleware) |
| | **컨텍스트 윈도우 관리** | ✅ 1M 토큰 + 자동 압축 | ⚡ | ⚡ (토큰 추적만) |
| | **로컬 프로젝트 탐지** | ⚡ (Git root) | ✅ (자동 폴더 전환) | ✅ (git root + 환경 스캔) |
| **안전성** | HITL 승인 시스템 | ✅ 도구별 허용/거부 | ✅ 3단계 정책 | ✅ interrupt() 기반 |
| | **OS 레벨 샌드박스** | ✅ Seatbelt(macOS)/bubblewrap(Linux) | ✅ Seatbelt(macOS)/Docker(Linux) | ❌ (외부 샌드박스만) |
| | **네트워크 격리** | ✅ 도메인 기반 접근 제어 | ✅ Full Auto시 기본 차단 | ❌ |
| | **세분화된 권한 모드** | ✅ 6단계 (plan→bypassPermissions) | ✅ 3단계 (suggest→full-auto) | ⚡ (2단계: 승인/자동) |
| | 셸 허용 목록 | ⚡ (설정) | ⚡ (정책) | ✅ ShellAllowListMiddleware |
| | 유니코드 보안 | ❌ | ❌ | ✅ BiDi/퓨니코드 검출 |
| **UI/UX** | 리치 터미널 UI | ✅ Ink 기반 | ✅ Rust TUI | ✅ Textual TUI |
| | **스트리밍 Markdown 렌더링** | ✅ | ✅ | ✅ MarkdownStream |
| | **키보드 단축키 커스터마이징** | ✅ keybindings.json | ⚡ | ❌ |
| | 테마 시스템 | ✅ (light/dark + 커스텀) | ⚡ | ✅ (CSS 변수 기반) |
| | **Diff 미리보기** | ✅ (인라인 diff) | ✅ (패치 프리뷰) | ✅ (unified diff) |
| | **진행률 표시** | ✅ (상태바, 스피너) | ✅ | ✅ (스피너, 상태바) |
| | **이미지 표시** | ✅ (터미널 이미지) | ❌ | ⚡ (이미지 입력 지원) |
| **통합** | **IDE 확장 (VS Code)** | ✅ | ✅ | ❌ |
| | **IDE 확장 (JetBrains)** | ✅ | ❌ | ❌ |
| | MCP 서버 통합 | ✅ | ✅ | ✅ |
| | **Git 네이티브 작업** | ✅ (커밋, PR, diff) | ✅ (GitHub 통합) | ❌ (셸 명령으로 가능) |
| | **데스크톱 앱** | ✅ (Mac/Windows) | ✅ (`codex app`) | ❌ |
| | **웹 앱** | ✅ (claude.ai/code) | ✅ (chatgpt.com/codex) | ❌ |
| | **CI/CD 통합** | ✅ (GitHub Actions) | ✅ (GitHub 봇) | ⚡ (비대화형 모드) |
| **에이전트 오케스트레이션** | **서브에이전트 생성** | ✅ 전문 에이전트 유형 | ❌ | ✅ SubAgent/AsyncSubAgent |
| | **병렬 에이전트 실행** | ✅ (백그라운드 에이전트) | ✅ (병렬 작업) | ⚡ (오프로드) |
| | **에이전트 팀 협업** | ✅ TeamCreate/SendMessage | ❌ | ❌ |
| | **작업 관리 (TODO)** | ✅ TaskCreate/TaskUpdate | ❌ | ✅ TodoListMiddleware |
| **세션 관리** | 대화 영속성 | ✅ (자동) | ✅ (아카이브) | ✅ (SQLite 체크포인트) |
| | **대화 이력 브라우징** | ✅ /history | ✅ | ✅ (스레드 선택기) |
| | **대화 분기** | ❌ | ⚡ | ❌ |
| | **크로스 세션 메모리** | ✅ (프로젝트 메모리) | ⚡ | ✅ MemoryMiddleware |
| **확장성** | 슬래시 커맨드 | ✅ (/help, /compact 등) | ✅ | ✅ (20개 커맨드) |
| | **커스텀 슬래시 커맨드** | ✅ (.claude/commands/) | ⚡ | ✅ (스킬 시스템) |
| | **훅 시스템** | ✅ (pre/post 도구 사용) | ❌ | ✅ (hooks.json) |
| | **스킬/플러그인** | ✅ (Skills via .claude/) | ❌ | ✅ (built_in_skills/) |
| **고급 기능** | 비대화형/헤드리스 모드 | ✅ | ✅ | ✅ |
| | **원격 에이전트 (트리거)** | ✅ (스케줄링) | ✅ (GitHub 봇) | ❌ |
| | **에이전트 SDK** | ✅ (Claude Agent SDK) | ✅ (Agents SDK) | ✅ (deepagents 패키지) |
| | **다중 모델 라우팅** | ✅ (Opus/Sonnet/Haiku) | ✅ (o3/o4-mini/gpt-4.1) | ✅ (21개 프로바이더) |
| | **모델 핫스왑** | ✅ (/model) | ⚡ | ✅ ConfigurableModelMiddleware |
| | **Worktree 격리** | ✅ (Git worktree) | ❌ | ❌ |
| **추가 기능** | **플러그인 마켓플레이스** | ✅ (설치/배포/검색) | ❌ | ❌ |
| | **원격 제어 (Teleport)** | ✅ (웹↔CLI 세션 이관) | ❌ | ❌ |
| | **체크포인팅/되감기** | ✅ (Esc+Esc, /branch) | ❌ | ❌ |
| | **음성 입력** | ✅ (push-to-talk) | ❌ | ❌ |
| | **Chrome 디버깅** | ✅ (--chrome 플래그) | ❌ | ❌ |
| | **예약 작업 (Cron)** | ✅ (클라우드/로컬) | ❌ | ❌ |
| | **대규모 배치 처리** | ✅ (/batch 스킬) | ❌ | ❌ |
| | **Slack 통합** | ✅ (@Claude 멘션) | ❌ | ❌ |
| | **Side Question** | ✅ (/btw 오버레이) | ❌ | ❌ |

---

## 3. DeepAgents CLI에 없는 핵심 기능 상세 분석

### 3.1 🔴 Critical Gap: 전문 파일/코드 검색 도구

**Claude Code**: `Glob`(파일 패턴 검색)과 `Grep`(코드 내용 검색) 전용 도구 보유. ripgrep 기반으로 대형 코드베이스에서도 빠른 검색 가능.

**Codex CLI**: ripgrep(rg)이 시스템 의존성으로 포함. 코드 검색에 최적화.

**DeepAgents CLI**: 전용 검색 도구 없음. 셸 명령(`find`, `grep`)으로 대체해야 하며, 에이전트가 매번 적절한 셸 명령을 구성해야 함.

**영향**: 코딩 에이전트의 가장 빈번한 작업인 "코드 찾기"가 비효율적. 에이전트가 검색 명령을 잘못 구성할 위험.

**권장 구현**:
```python
# 새로운 도구 추가
@tool
def glob_search(pattern: str, path: str = ".") -> list[str]:
    """Glob 패턴으로 파일 검색"""

@tool
def grep_search(pattern: str, path: str = ".", file_type: str = None) -> str:
    """ripgrep 기반 코드 내용 검색"""
```

---

### 3.2 🔴 Critical Gap: 정밀 편집 도구 (Diff 기반)

**Claude Code**: `Edit` 도구로 파일의 특정 문자열을 정확히 교체. 전체 파일을 다시 쓰지 않고 변경 부분만 전송.

**Codex CLI**: 패치 형식으로 정밀 편집 지원.

**DeepAgents CLI**: 파일 쓰기 도구는 있지만, 전체 파일을 다시 쓰는 방식. 대형 파일에서 비효율적이고 실수 위험.

**영향**: 큰 파일 편집 시 토큰 낭비 + 의도치 않은 변경 위험.

**권장 구현**:
```python
@tool
def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """파일에서 old_string을 new_string으로 정확히 교체"""
```

---

### 3.3 🔴 Critical Gap: 프로젝트 메모리 파일 (CLAUDE.md / AGENTS.md)

**Claude Code**: `CLAUDE.md` 파일로 프로젝트별 지시사항, 코딩 컨벤션, 아키텍처 결정을 영속적으로 저장. 계층적 구조 (루트 → 하위 디렉토리) 지원.

**Codex CLI**: `AGENTS.md` 파일로 유사한 기능 제공. 디렉토리별 에이전트 지시사항 저장.

**DeepAgents CLI**: 이에 상응하는 메커니즘 없음. `MemoryMiddleware`가 크로스 세션 메모리를 제공하지만, 프로젝트 루트에 체크인 가능한 지시사항 파일 없음.

**영향**: 팀 전체가 공유하는 에이전트 지시사항을 Git에 커밋할 수 없음. 매 세션마다 프로젝트 컨텍스트를 수동으로 제공해야 함.

**권장 구현**:
- `DEEPAGENTS.md` 또는 `.deepagents/instructions.md` 파일 지원
- 디렉토리 계층 탐색으로 상위 지시사항 자동 상속
- 시스템 프롬프트에 자동 주입하는 미들웨어 추가

---

### 3.4 🟡 Important Gap: 구조화된 계획 모드

**Claude Code**: 전용 Plan Mode로 코드 수정 없이 계획 수립 → 사용자 승인 → 실행의 3단계 워크플로우. 계획 파일을 별도로 관리.

**Codex CLI**: 명시적 Plan Mode 없음 (suggest 모드가 유사).

**DeepAgents CLI**: Plan Mode 없음. 에이전트가 바로 코드 수정에 돌입할 수 있음.

**영향**: 복잡한 태스크에서 에이전트가 계획 없이 코드 수정을 시작하여 방향이 어긋날 위험.

**권장 구현**:
- 새 미들웨어 `PlanModeMiddleware`로 도구 사용을 읽기 전용으로 제한
- 계획 파일 작성 → 사용자 승인 → 도구 잠금 해제 흐름

---

### 3.5 🟡 Important Gap: OS 레벨 로컬 샌드박스

**Claude Code**: **OS 레벨 샌드박싱 지원**:
- **macOS**: Apple Seatbelt 기반 파일시스템 격리 + 도메인 기반 네트워크 접근 제어
- **Linux/WSL2**: bubblewrap 기반 격리
- `sandbox.failIfUnavailable: true`로 샌드박스 필수 강제 가능
- 오픈소스 런타임: `@anthropic-ai/sandbox-runtime` npm 패키지

**Codex CLI** ([github.com/openai/codex](https://github.com/openai/codex)): **Defense-in-Depth 샌드박싱**:
- **macOS 12+**: Apple Seatbelt — 읽기 전용 jail + 네트워크 비활성화
- **Linux**: Docker 컨테이너 + Firewall 기반 격리
- **Full Auto 모드**: 네트워크 차단(기본) + 작업 디렉토리 제한 + 임시 파일만 허용

**DeepAgents CLI**: 외부 샌드박스 프로바이더(LangSmith, Daytona, Modal 등)에 의존. **로컬 OS 레벨 샌드박스 없음**.

**영향**: 자율 실행 시 에이전트가 시스템에 직접 영향. HITL 승인 없이는 위험.

**권장 구현**:
- macOS: Apple Seatbelt 프로파일 (Claude Code/Codex 방식 참고)
- Linux: bubblewrap 또는 Docker 기반 격리
- 새 백엔드 `LocalSandboxBackend` 추가
- Defense-in-Depth: 네트워크 차단 + 디렉토리 격리 + 임시 파일 제한의 3중 보호

---

### 3.6 🟡 Important Gap: IDE 확장

**Claude Code**: VS Code + JetBrains 확장 프로그램 제공. IDE 내에서 직접 에이전트와 대화.

**Codex CLI**: VS Code, Cursor, Windsurf 통합.

**DeepAgents CLI**: IDE 확장 없음. 터미널에서만 사용 가능.

**영향**: 개발자 워크플로우의 중심인 IDE에서 직접 사용 불가. 컨텍스트 전환 비용.

**권장 구현**:
- VS Code 확장: 터미널 패널 + 사이드바 통합
- Language Server Protocol 활용으로 IDE 독립적 통합

---

### 3.7 🟡 Important Gap: 자동 컨텍스트 압축

**Claude Code**: 컨텍스트 윈도우가 가득 차면 자동으로 대화를 압축. `/compact` 명령으로 수동 압축도 가능. 1M 토큰 윈도우를 효율적으로 관리.

**Codex CLI**: 명시적 압축 메커니즘 없음 (짧은 세션 설계).

**DeepAgents CLI**: `SummarizationMiddleware`가 존재하지만, Claude Code의 자동 압축만큼 정교하지 않음. 토큰 추적(`TokenStateMiddleware`)은 있으나 자동 압축 트리거 없음.

**영향**: 긴 대화에서 컨텍스트 윈도우 초과 → 중요 맥락 손실.

**권장 구현**:
- `SummarizationMiddleware` 강화: 토큰 임계값 도달 시 자동 요약 트리거
- 중요 메시지 핀닝 (요약 시 제외)
- `/compact` 슬래시 커맨드 추가

---

### 3.8 🟡 Important Gap: 확장된 사고 (Extended Thinking)

**Claude Code**: Claude의 Extended Thinking 기능으로 복잡한 문제에 대해 단계별 추론 과정을 공개.

**Codex CLI**: o3/o4-mini 모델의 추론 토큰으로 유사 기능.

**DeepAgents CLI**: Extended Thinking / Chain-of-Thought 추론을 활용하는 메커니즘 없음.

**영향**: 복잡한 아키텍처 결정이나 디버깅에서 추론 품질 저하.

**권장 구현**:
- Anthropic Extended Thinking API 활용 미들웨어
- 추론 과정을 UI에 표시하는 위젯 추가

---

### 3.9 🟡 Important Gap: 클라우드 위임 (Cloud Offloading)

**Claude Code**: 원격 에이전트(트리거)로 스케줄링 가능. GitHub Actions 통합.

**Codex CLI**: **클라우드 위임** 기능 내장 — 로컬 리소스가 부족하거나 대형 작업을 처리할 때 자동으로 클라우드(chatgpt.com/codex)로 오프로드. `@codex` 태그로 GitHub에서 직접 작업 위임 가능.

**DeepAgents CLI**: `offload.py`로 작업 오프로드 메커니즘이 있지만, 클라우드 위임은 아님. LangGraph Cloud 배포는 별도 설정 필요.

**영향**: 대형 리팩토링이나 멀티 레포 작업에서 로컬 제약.

**권장 구현**:
- LangGraph Cloud 연동으로 원격 에이전트 실행 지원
- GitHub 봇/앱으로 PR 코멘트에서 직접 에이전트 호출

---

### 3.10 🟡 Important Gap: 멀티모달 입력 (스크린샷/다이어그램)

**Claude Code**: 터미널에서 이미지 파일을 직접 읽고 분석 가능.

**Codex CLI**: 스크린샷, 다이어그램 등 멀티모달 입력을 네이티브로 지원. UI 목업을 보고 코드 생성 가능.

**DeepAgents CLI**: `media_utils.py`와 `Pillow` 의존성으로 이미지 처리 기반은 있지만, 멀티모달 입력 워크플로우가 제한적.

**영향**: UI/UX 작업에서 시각 자료 기반 코드 생성 불가.

**권장 구현**:
- 채팅 입력에서 이미지 파일 드래그앤드롭 또는 경로 첨부 지원
- 멀티모달 LLM API(Claude Vision, GPT-4o) 활용 미들웨어

---

### 3.11 🟢 Nice-to-Have Gap: 데스크톱 / 웹 앱

**Claude Code**: Mac/Windows 데스크톱 앱 + claude.ai/code 웹 앱.

**Codex CLI**: `codex app` 데스크톱 앱 + chatgpt.com/codex 웹 앱.

**DeepAgents CLI**: 터미널 전용.

**권장**: Textual 기반 TUI가 충분히 리치하므로 우선순위 낮음. 필요 시 Electron 래퍼 또는 웹 버전 (Textual-web) 고려.

---

### 3.12 🟢 Nice-to-Have Gap: Git Worktree 격리

**Claude Code**: Git worktree를 활용하여 서브에이전트가 독립된 작업 공간에서 코드 수정. 메인 브랜치에 영향 없음.

**DeepAgents CLI**: Worktree 격리 없음.

**권장**: 서브에이전트 사용 시 worktree 격리 옵션 추가.

---

### 3.13 🟢 Nice-to-Have Gap: LSP 통합

**Claude Code**: Language Server Protocol 통합으로 `hover`, `goto_definition`, `find_references`, `rename` 등 IDE 수준의 코드 인텔리전스 제공.

**DeepAgents CLI**: LSP 통합 없음.

**권장**: 에이전트가 타입 정보, 참조 관계를 활용하면 코드 수정 정확도가 크게 향상됨.

---

### 3.14 🟢 Nice-to-Have Gap: Notebook 편집

**Claude Code**: Jupyter Notebook 셀 직접 편집/실행 도구.

**DeepAgents CLI**: Notebook 지원 없음.

**권장**: 데이터 사이언스 워크플로우 지원 시 필요.

### 3.15 🟡 Important Gap: 플러그인 마켓플레이스

**Claude Code**: 완전한 플러그인 생태계 — 스킬 + 훅 + 서브에이전트 + 출력 스타일 + MCP 서버를 묶은 플러그인 패키지. `claude plugin install`로 설치, 마켓플레이스 탐색/배포 지원. 관리 정책으로 차단/허용 제어.

**Codex CLI / DeepAgents CLI**: 플러그인 마켓플레이스 없음.

**권장**: `built_in_skills/` 구조를 확장하여 커뮤니티 스킬 레지스트리 구축.

---

### 3.16 🟡 Important Gap: 체크포인팅 / 되감기 / 대화 분기

**Claude Code**: `Esc+Esc`로 이전 시점 되감기, `/branch`로 대화 분기(fork), `/rewind`로 특정 시점 복원. 실험적 경로를 안전하게 시도 가능.

**Codex CLI / DeepAgents CLI**: 체크포인팅/분기 없음.

**권장**: LangGraph 체크포인트 시스템이 이미 상태 스냅샷을 저장하므로, 특정 체크포인트로 되감기하는 UI 명령만 추가하면 구현 가능.

---

### 3.17 🟢 Nice-to-Have Gap: 원격 제어 / Teleport

**Claude Code**: 로컬 CLI 세션을 웹/모바일에서 원격 제어 (`--remote-control`). `--teleport`으로 웹 세션을 로컬로 가져오기. Telegram/Discord/Slack 채널 알림.

**Codex CLI / DeepAgents CLI**: 없음.

**권장**: DeepAgents의 클라이언트-서버 아키텍처(HTTP+SSE)가 이미 원격 제어의 기반을 갖추고 있음. 웹 클라이언트만 추가하면 구현 가능.

---

### 3.18 🟢 Nice-to-Have Gap: 고급 훅 시스템 (24+ 이벤트)

**Claude Code**: 24개 이상의 훅 이벤트 (SessionStart/End, PreToolUse, PostToolUse, SubagentStart/Stop, TaskCreated/Completed, FileChanged, PreCompact, WorktreeCreate 등). 4가지 훅 타입(command, http, prompt, agent). 비동기 훅, Defer 메커니즘.

**DeepAgents CLI**: `hooks.json` 기반 단순 훅 디스패치 (fire-and-forget). 이벤트 종류와 제어 수준이 제한적.

**권장**: 훅 이벤트 종류를 확대하고, 훅에서 도구 실행을 차단/수정할 수 있는 제어 메커니즘 추가.

---

## 4. DeepAgents CLI의 고유 강점 (경쟁 우위)

역으로, DeepAgents CLI만이 가진 강점도 있습니다:

| 강점 | 설명 | Claude Code | Codex CLI |
|------|------|-------------|-----------|
| **21개 모델 프로바이더** | Anthropic, OpenAI, Google, Ollama 등 모두 지원 | Claude 전용 | OpenAI 전용 |
| **미들웨어 체인 아키텍처** | 13개 미들웨어로 유연한 확장 | 내부 구현 (비공개) | 내부 구현 |
| **유니코드 보안** | BiDi 공격, 퓨니코드 도메인 검출 | ❌ | ❌ |
| **7+ 샌드박스 백엔드** | LangSmith, Daytona, Modal, Runloop 등 | ❌ | 로컬 샌드박스만 |
| **오픈소스 (MIT)** | 완전한 소스코드 접근 + 수정 가능 | 비공개 소스 | Apache-2.0 |
| **LangGraph 생태계** | LangSmith 모니터링, LangGraph Cloud 배포 | ❌ | ❌ |
| **클라이언트-서버 분리** | UI ↔ 에이전트 프로세스 분리, 원격 지원 | 단일 프로세스 | 단일 프로세스 |

---

## 5. 개발 우선순위 로드맵 제안

격차의 심각도와 구현 난이도를 기반으로 한 우선순위:

### Tier 1: 즉시 구현 (높은 가치, 낮은 난이도)

| # | 기능 | 예상 난이도 | 예상 영향 |
|---|------|------------|-----------|
| 1 | **전문 검색 도구** (Glob + Grep) | 낮음 (새 도구 2개) | 🔴 매우 높음 |
| 2 | **정밀 편집 도구** (Diff 기반 Edit) | 낮음 (새 도구 1개) | 🔴 매우 높음 |
| 3 | **프로젝트 메모리 파일** (DEEPAGENTS.md) | 중간 (미들웨어 1개) | 🔴 높음 |

### Tier 2: 단기 구현 (높은 가치, 중간 난이도)

| # | 기능 | 예상 난이도 | 예상 영향 |
|---|------|------------|-----------|
| 4 | **Plan Mode** | 중간 (미들웨어 + UI) | 🟡 높음 |
| 5 | **자동 컨텍스트 압축 강화** | 중간 (기존 MW 확장) | 🟡 높음 |
| 6 | **Extended Thinking 지원** | 낮음 (API 파라미터) | 🟡 중간 |
| 7 | **세분화된 권한 모드** (3~5단계) | 중간 (설정 + MW) | 🟡 중간 |

### Tier 3: 중기 구현 (중간 가치, 높은 난이도)

| # | 기능 | 예상 난이도 | 예상 영향 |
|---|------|------------|-----------|
| 8 | **로컬 샌드박스** | 높음 (OS별 구현) | 🟡 중간 |
| 9 | **VS Code 확장** | 높음 (새 프로젝트) | 🟡 중간 |
| 10 | **LSP 통합** | 높음 (프로토콜 구현) | 🟢 중간 |

### Tier 4: 장기 고려 (낮은 가치 또는 매우 높은 난이도)

| # | 기능 | 비고 |
|---|------|------|
| 11 | 데스크톱 앱 | Textual-web으로 우회 가능 |
| 12 | 웹 앱 | LangGraph Cloud로 대체 가능 |
| 13 | Notebook 편집 | 특정 사용 사례에만 필요 |
| 14 | Git Worktree 격리 | 서브에이전트 고급 기능 |

---

## 6. 구현 전략 제안

### 6.1 DeepAgents의 미들웨어 아키텍처를 활용한 빠른 확장

DeepAgents CLI의 가장 큰 아키텍처적 강점은 **미들웨어 체인**입니다. 대부분의 새 기능은 미들웨어로 구현할 수 있어, 핵심 코드 수정 없이 확장 가능:

```
기능 → 구현 방식
──────────────────────────────────
프로젝트 메모리 파일     → ProjectMemoryMiddleware (새 미들웨어)
Plan Mode              → PlanModeMiddleware (새 미들웨어)
Extended Thinking      → ExtendedThinkingMiddleware (새 미들웨어)
세분화된 권한           → PermissionMiddleware (ShellAllowList 확장)
자동 컨텍스트 압축      → SummarizationMiddleware 확장
```

### 6.2 새 도구는 Backend으로 구현

검색/편집 도구는 기존 Backend 추상화를 활용:

```
도구 → 구현 방식
──────────────────────────────────
Glob 검색              → FilesystemBackend에 glob 메서드 추가
Grep 검색              → 새 SearchBackend 또는 FilesystemBackend 확장
정밀 편집               → FilesystemBackend의 write를 diff 기반으로 확장
```

### 6.3 LangChain/LangGraph 생태계 활용

DeepAgents가 Claude Code/Codex 대비 유일하게 가진 강점은 **LangGraph 생태계**입니다:

- **LangSmith**: 에이전트 실행 추적, 디버깅, 모니터링
- **LangGraph Cloud**: 서버리스 에이전트 배포
- **LangGraph Studio**: 그래프 시각화 및 디버깅
- **LangChain Hub**: 프롬프트 공유 및 버전 관리

이 생태계 통합을 강화하면 Claude Code/Codex가 제공할 수 없는 차별화 포인트가 됩니다.

---

## 7. 결론

### 핵심 격차 요약

DeepAgents CLI에는 **3개의 Critical 격차**가 존재합니다:
1. **전문 검색 도구 부재** — 코딩 에이전트의 가장 기본적인 기능
2. **정밀 편집 도구 부재** — 대형 파일 편집 시 비효율
3. **프로젝트 메모리 파일 부재** — 팀 공유 가능한 에이전트 지시사항

이 3개는 즉시 구현해야 하며, 미들웨어 아키텍처 덕분에 핵심 코드 변경 없이 추가 가능합니다.

### 전략적 방향

DeepAgents CLI가 Claude Code/Codex와 차별화할 수 있는 방향:

1. **모델 독립성** — 21개 프로바이더 지원은 유일한 강점. 더 강화
2. **미들웨어 확장성** — 커뮤니티가 미들웨어를 만들어 공유하는 생태계
3. **LangGraph 생태계** — 모니터링, 배포, 시각화 통합은 경쟁자 없음
4. **오픈소스** — 완전한 소스 공개와 MIT 라이선스로 기업 채택 촉진

---

*관련 문서: [06-아키텍처-종합-패턴-레퍼런스](./06-아키텍처-종합-패턴-레퍼런스.md) — DeepAgents CLI의 현재 아키텍처 패턴 상세 분석*
