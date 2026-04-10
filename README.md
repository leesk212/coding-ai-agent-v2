# Coding AI Agent v2

`DeepAgents` 개념을 기준선으로 삼아, 실제 개발 작업을 지속적으로 수행하는 코딩 에이전트를 구현한 프로젝트다.  
핵심 설계 축은 다음 3가지다.

1. 장기 메모리와 지식 저장 체계
2. 동적으로 생성되고 정리되는 SubAgent 수명주기 관리
3. Agentic loop의 복원력과 안전성

## 빠른 목차

- [실행 방법](#실행-방법)
- [데모 GIF](#데모-gif)
- [평가 기준 대응](#평가-기준-대응)
- [핵심 산출물 요약](#핵심-산출물-요약)
- [현재 구조](#현재-구조)
- [가장 먼저 볼 파일](#가장-먼저-볼-파일)
- [Agent 설정은 어디서 하나](#agent-설정은-어디서-하나)
- [현재 SubAgent 역할](#현재-subagent-역할)
- [SubAgent는 언제 실제로 뜨나](#subagent는-언제-실제로-뜨나)
- [SubAgent 프로세스 내부](#subagent-프로세스-내부)
- [사용자 질의 1개가 처리되는 방식](#사용자-질의-1개가-처리되는-방식)
- [장기 메모리 설계](#장기-메모리-설계)
- [Remember Agent + Human in the Loop](#remember-agent--human-in-the-loop)
- [동적 SubAgent 수명주기 관리](#동적-subagent-수명주기-관리)
- [Agentic Loop 복원력과 안전성](#agentic-loop-복원력과-안전성)
- [모델 정책](#모델-정책)
- [WebUI 핵심 기능](#webui-핵심-기능)
- [테스트 프롬프트와 시나리오](#테스트-프롬프트와-시나리오)
- [Docker 실행](#docker-실행)
- [검증 방법](#검증-방법)

## 실행 방법

### 로컬 실행

```bash
cd /mnt/c/Users/SDS/Subject
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m coding_agent
```

브라우저:

- `http://localhost:8501`

초기 진입 흐름:

1. WebUI 접속
2. `OpenRouter API Key` 입력
3. 필요하면 `Fallback` 설정
4. `Start Danny's Chat`
5. DeepAgents runtime initialize
6. Chat 진입

### Docker 실행

```bash
docker compose up --build
```

또는 이미 올린 이미지 사용:

```bash
docker run -p 8501:8501 --env-file .env leesk212/coding-ai-agent-v2:latest
```

## 데모 GIF

아래 3개 동작 화면을 이 섹션에 배치하면 된다.

### 1. Hello

```md
![Hello Demo](docs/gifs/hello.gif)
```

### 2. Code+Review

```md
![Code+Review Demo](docs/gifs/code-review.gif)
```

### 3. Scenario (PMS시스템구성)

```md
![Scenario Demo](docs/gifs/scenario-pms.gif)
```

## 평가 기준 대응

### 1. 요구사항 구현 (10점)

| 평가 항목 | 현재 상태 | 근거 |
| --- | --- | --- |
| DeepAgents(개념) 사용 여부 | 충족 | Main Agent와 SubAgent 모두 `create_deep_agent(...)` 기반으로 조립됨. AsyncSubAgent spec, middleware stack, local shell backend, checkpointer 구성을 사용 |
| PEP8 기준에 맞추어 파이썬 코드 구현 여부 | 충족 | 모듈 분리, 타입 힌트, snake_case, import 구조, 함수 길이 분리 기준을 유지하며, `compileall`과 `pytest tests`를 통과 |
| DocString Google Style 작성 여부 | 충족 | 핵심 모듈과 주요 함수 설명을 Google Style 기준으로 정리하고, 리뷰 가능한 수준으로 문서화를 유지 |

### 2. 메모리 시스템 활용 여부 (10점)

| 평가 항목 | 현재 상태 | 근거 |
| --- | --- | --- |
| 시스템 프롬프트 또는 스킬을 이용한 장기 메모리/도메인 지식 추출 메모리 시스템 탑재 여부 | 충족 | 현재는 `skills=[]`이므로 스킬 기반은 아니고, `Main Agent system prompt + LongTermMemoryMiddleware` 기반으로 추출/저장/재주입 경로를 명시적으로 구현 |

핵심 근거:
- `user/profile`, `project/context`, `domain/knowledge` 3계층 분리
- `memory_store`, `memory_search`, `memory_correct` 도구 제공
- system prompt에 “대화에서 durable memory를 추출하고 같은 turn에서 저장” 규칙 추가
- durable store(SQLite) + semantic store(ChromaDB) 병행 사용

### 3. 서브에이전트 시스템 동적 활용 여부 (10점)

| 평가 항목 | 현재 상태 | 근거 |
| --- | --- | --- |
| 작업을 Main Agent가 아닌 SubAgent로 할당하는지 | 충족 | `start_async_task` 기반 async delegation. planner, architect, frontend, backend, mobile, reviewer, remember 등 역할 분리 |
| SubAgent가 실행 시점에 동적으로 생성되는지 | 충족 | `split` topology에서 `LazyAsyncSubagentsMiddleware`가 실제 `start_async_task` 직전에만 subagent runtime을 on-demand spawn |

### 4. SLM 서빙 및 에이전트 내 활용 여부 (10점)

| 평가 항목 | 현재 상태 | 근거 |
| --- | --- | --- |
| SLM 사용 포함 여부 | 충족 | Ollama 기반 local fallback model 경로 존재 |
| Main/SubAgent 등 모든 Agent 로직 최적화 여부 | 충족 | Main Agent와 SubAgent 모두 동일한 모델 fallback 체계와 local SLM 경로를 공유하며, 필요 시 local SLM까지 포함해 일관되게 최적화 가능 |
| SLM을 전혀 사용하지 않는지 | 미해당 | 이 프로젝트는 SLM 경로를 실제로 포함하고 활용할 수 있도록 구성됨 |

정리:
- 현재 구조는 “OpenRouter 기반 오픈소스 모델 우선 + local SLM fallback 가능” 설계다.
- 즉, 요구사항 기준에서 SLM 서빙과 에이전트 내 활용 경로를 모두 포함한 상태다.

## 핵심 산출물 요약

이 프로젝트는 단순 CRUD 코드 생성 데모가 아니라, 아래 구조를 가진 실행형 코딩 에이전트다.

- Main Agent: `DeepAgents supervisor`
- SubAgent: `AsyncSubAgent` 기반 동적 런타임 생성
- 장기 메모리: `ChromaDB + SQLite durable memory`
- Human in the Loop: `remember` SubAgent 결과에 대한 중간 승인
- WebUI: Streamlit 기반 실시간 Mermaid/이벤트/SubAgent output 표시
- 실행 단위: 질의 1개 = Main Agent + 관련 SubAgent + HITL까지 포함한 하나의 세션

## 현재 구조

```text
Streamlit WebUI
  -> runtime bootstrap
    -> Main Supervisor (DeepAgents create_deep_agent)
      -> async task tools
        -> LocalAsyncSubagentManager
          -> AsyncSubAgent specs
          -> on-demand local subagent process
            -> async_subagent_server
              -> per-subagent create_deep_agent
```

## 가장 먼저 볼 파일

리뷰 시작 시 우선 보면 되는 파일은 아래 7개다.

1. [src/coding_agent/runtime.py](/mnt/c/Users/SDS/Subject/src/coding_agent/runtime.py)
2. [src/coding_agent/agent.py](/mnt/c/Users/SDS/Subject/src/coding_agent/agent.py)
3. [src/coding_agent/async_subagent_manager.py](/mnt/c/Users/SDS/Subject/src/coding_agent/async_subagent_manager.py)
4. [src/coding_agent/async_subagent_server.py](/mnt/c/Users/SDS/Subject/src/coding_agent/async_subagent_server.py)
5. [src/coding_agent/middleware/long_term_memory.py](/mnt/c/Users/SDS/Subject/src/coding_agent/middleware/long_term_memory.py)
6. [src/coding_agent/state/store.py](/mnt/c/Users/SDS/Subject/src/coding_agent/state/store.py)
7. [src/coding_agent/webui/_pages/chat.py](/mnt/c/Users/SDS/Subject/src/coding_agent/webui/_pages/chat.py)

## Agent 설정은 어디서 하나

### 1. 런타임 진입점

메인 진입점은 [src/coding_agent/runtime.py](/mnt/c/Users/SDS/Subject/src/coding_agent/runtime.py)의 `create_runtime_components(...)`다.

여기서 하는 일:

1. `deployment_topology` 결정
2. `split/single/hybrid` 분기
3. runtime prewarm 또는 direct init
4. 최종적으로 local DeepAgents supervisor 또는 remote adapter 반환

현재 기본 동작은 `split`이다.

이유:
- local Main Agent + local SubAgent on-demand spawn과 가장 잘 맞음
- WebUI에서 `pid`, `port`, `model`, `partial_output`을 추적하기 쉬움

### 2. Main Agent 조립

Main Supervisor는 [src/coding_agent/agent.py](/mnt/c/Users/SDS/Subject/src/coding_agent/agent.py)의 `create_coding_agent(...)` 계열 함수에서 조립된다.

조립 순서:

1. model fallback middleware 생성
2. long-term memory middleware 생성
3. async-only middleware 생성
4. lazy async subagent middleware 생성
5. subagent lifecycle middleware 생성
6. async task completion middleware 생성
7. `AsyncSubAgent` spec 생성
8. runtime-aware system prompt 생성
9. `create_deep_agent(...)` 호출

핵심 함수:
- `build_system_prompt(...)`
- `prewarm_coding_agent(...)`
- `finalize_coding_agent(...)`

### 3. AsyncSubAgent spec 로딩

SubAgent 정의는 [src/coding_agent/async_subagent_manager.py](/mnt/c/Users/SDS/Subject/src/coding_agent/async_subagent_manager.py)에 있다.

핵심 계층:

1. `load_async_subagent_specs(...)`
   - `~/.deepagents/config.toml` 기반 순수 `AsyncSubAgent` spec 로딩
2. `load_async_subagents(...)`
   - 위 spec에 `host`, `port`, `model`, `system_prompt`, `transport` 확장
3. `LocalAsyncSubagentManager.build_async_subagents()`
   - DeepAgents가 사용할 최종 spec 목록 생성

## 현재 SubAgent 역할

기본 등록 역할:

- `researcher`
- `coder`
- `reviewer`
- `debugger`
- `frontend`
- `backend`
- `planner`
- `architect`
- `mobile`
- `remember`

설계 의도:

- `planner`: PRD, atomic task breakdown, acceptance criteria
- `architect`: system design, 모듈 경계, API/data flow
- `frontend`: web UI/UX
- `mobile`: mobile UX/flow
- `backend`: DB/API/domain logic
- `reviewer`: 코드/산출물 검토
- `remember`: 장기 메모리 후보 파일 선별

## SubAgent는 언제 실제로 뜨나

`split` topology에서는 앱 시작 시 모든 SubAgent를 미리 띄우지 않는다.

실행 시점:

1. Main Agent가 `start_async_task`를 선택
2. [src/coding_agent/middleware/lazy_async_subagents.py](/mnt/c/Users/SDS/Subject/src/coding_agent/middleware/lazy_async_subagents.py)가 개입
3. `LocalAsyncSubagentManager.ensure_started(name)` 호출
4. 해당 역할의 SubAgent 프로세스만 spawn
5. health check 통과 후 task 실행

즉, 동적 생성이다. 고정 2-agent 선언이 아니다.

## SubAgent 프로세스 내부

실제 SubAgent 서버는 [src/coding_agent/async_subagent_server.py](/mnt/c/Users/SDS/Subject/src/coding_agent/async_subagent_server.py)에서 실행된다.

핵심:

- 각 SubAgent도 `create_deep_agent(...)` 기반
- `LocalShellBackend(root_dir=...)` 연결
- 작업 디렉터리/절대경로/파일 작업 가능 규칙을 system prompt에 주입
- `partial_output`을 계속 저장하여 WebUI가 polling 가능

## 사용자 질의 1개가 처리되는 방식

질의 단위 orchestration은 [src/coding_agent/webui/_pages/chat.py](/mnt/c/Users/SDS/Subject/src/coding_agent/webui/_pages/chat.py)의 `_stream_response(...)`와 `_resume_async_monitoring(...)`에서 수행된다.

흐름:

1. query-scoped `thread_id` 생성
2. 질의별 workdir 생성
3. Main Agent stream 시작
4. Main Agent의 tool call / 상태 / partial text를 UI에 반영
5. `start_async_task`가 나오면 local `tracked_agents` 등록
6. SubAgent output과 state를 고빈도 polling
7. remember SubAgent 필요 시 강제 launch
8. remember 결과가 나오면 Human in the Loop pause
9. 승인/거절 후 같은 세션에서 resume
10. 마지막에만 Main Agent가 최종 aggregation

중요:

- SubAgent가 없는 질의: Main Agent 응답으로 종료
- SubAgent가 있는 질의: 모든 SubAgent + HITL까지 끝나야 종료

즉, 질의 하나는 “Main Agent 답변 한 번”이 아니라 “전체 세션”이다.

## 장기 메모리 설계

핵심 파일:

- [src/coding_agent/middleware/long_term_memory.py](/mnt/c/Users/SDS/Subject/src/coding_agent/middleware/long_term_memory.py)
- [src/coding_agent/memory/store.py](/mnt/c/Users/SDS/Subject/src/coding_agent/memory/store.py)
- [src/coding_agent/memory/categories.py](/mnt/c/Users/SDS/Subject/src/coding_agent/memory/categories.py)
- [src/coding_agent/state/store.py](/mnt/c/Users/SDS/Subject/src/coding_agent/state/store.py)

메모리 계층:

1. `user/profile`
2. `project/context`
3. `domain/knowledge`

구조:

- semantic retrieval: `ChromaDB`
- durable source of truth: `SQLite`

도구:

- `memory_store`
- `memory_search`
- `memory_correct`

### 메모리 추출 방식

현재는 `skills` 기반이 아니라 `system prompt + LongTermMemoryMiddleware` 기반이다.

즉:

- Main Agent system prompt가 durable 정보를 추출하라고 지시
- `LongTermMemoryMiddleware`가 relevant memory를 system prompt에 주입
- agent는 `memory_store`로 같은 turn 안에서 durable memory를 저장
- 다음 질의에서는 `memory_search`와 자동 prompt injection으로 재활용

### 정정 정책

- 기존 record는 `superseded`
- 새 record는 `active`

이건 단순 thread history가 아니라, 실제 수정 가능한 durable memory다.

## Remember Agent + Human in the Loop

이번 업데이트에서 `remember` SubAgent와 중간 승인 흐름을 붙였다.

목적:

1. 산출물 중 장기 메모리화 가치가 높은 파일 후보 선별
2. 후보 최대 10개로 축소
3. 사람이 승인
4. 승인된 파일만 long-term memory 저장

동작:

1. turn에서 durable artifact 생성
2. `remember` SubAgent 실행
3. 후보 파일 목록 생성
4. Main Agent 최종 답변 전에 `Human in the Loop` pause
5. WebUI에서 파일별 다운로드 검토
6. `Approve and Continue` 또는 `Reject and Continue`
7. 같은 세션을 resume
8. 그 뒤에만 최종 Main Agent 답변 생성

핵심 파일:

- [src/coding_agent/agent.py](/mnt/c/Users/SDS/Subject/src/coding_agent/agent.py)
- [src/coding_agent/webui/_pages/chat.py](/mnt/c/Users/SDS/Subject/src/coding_agent/webui/_pages/chat.py)

## SubAgent 수명주기

핵심 파일:

- [src/coding_agent/async_subagent_manager.py](/mnt/c/Users/SDS/Subject/src/coding_agent/async_subagent_manager.py)
- [src/coding_agent/middleware/subagent_lifecycle.py](/mnt/c/Users/SDS/Subject/src/coding_agent/middleware/subagent_lifecycle.py)
- [src/coding_agent/state/store.py](/mnt/c/Users/SDS/Subject/src/coding_agent/state/store.py)

수명주기 상태:

- `created`
- `assigned`
- `running`
- `blocked`
- `completed`
- `failed`
- `cancelled`
- `destroyed`

메타데이터:

- `agent_id`
- `role`
- `task_summary`
- `parent_id`
- `state`
- `created_at`
- `updated_at`

현재 UI에 보이는 것:

- role + ordinal
  - 예: `architect agent #1`
- `task_id`
- `run_id`
- `endpoint`
- `pid`
- `model`
- lifecycle event summary

## Agentic Loop 복원력

핵심 파일:

- [src/coding_agent/resilience.py](/mnt/c/Users/SDS/Subject/src/coding_agent/resilience.py)
- [src/coding_agent/agent.py](/mnt/c/Users/SDS/Subject/src/coding_agent/agent.py)
- [src/coding_agent/webui/_pages/chat.py](/mnt/c/Users/SDS/Subject/src/coding_agent/webui/_pages/chat.py)

현재 반영된 방어 전략:

- model timeout / fallback
- no-progress loop guard
- bad tool-call 대응
- subagent failure / blocked 대응
- safe stop

현재 loop 관련 설정:

- `max_iterations = 10000`
- `max_subagents = 100`

## WebUI에서 보이는 것

현재 Chat UI는 다음을 보여준다.

- Main Agent answer
- `Agent 동작 분석`
  - Mermaid
  - event timeline
  - HITL 상태
  - SubAgent Streaming Output
- workspace 다운로드
- remember review
- 개별 파일 다운로드
- Memory / Settings / Chat 페이지 전환

추가된 UX:

- `Focused Analysis View`
- `Human In The Loop` 강조 카드
- HITL 시 자동 스크롤
- SubAgent 최신 활동 기준 정렬

## 질의별 작업 디렉터리

각 사용자 질의는 별도 workdir에서 실행된다.

형식:

```text
query_sessions/YYYYMMDD_HHMMSS
```

의미:

- Main Agent와 SubAgent는 같은 질의 단위 workdir을 공유
- 산출물, PRD, 코드, spec, 문서가 질의 단위로 분리됨
- 완료 후 해당 workdir을 zip으로 다운로드 가능

## Settings와 Prompt Override

Settings에서 다음을 직접 조정할 수 있다.

- Main Agent default system prompt 확인
- Main Agent prompt override
- 각 SubAgent prompt override
- 모델/fallback 설정
- topology 설정
- memory record correction

prompt override 저장 위치:

```text
state/prompt_overrides.json
```

## Test Prompt / Scenario

기능 검증용 prompt가 WebUI에 들어 있다.

### Input Test Prompt (Module Function Test)

- `User/Profile`
- `Project/Context`
- `Domain Knowledge`
- `Memory Correction`
- `Memory Extraction`
- `SubAgent Lifecycle`
- `Code+Review Test`
- `Blocked/Failed`
- `Loop Safety`
- `Model Policy`
- `Remember Agent`

### Input Test Scenario

- `Scenario_1 : PMS시스템 구성`

이 시나리오는 planner / architect / frontend / mobile / backend / reviewer / remember 분할과, 실행 가능한 코드 산출 흐름을 같이 검증하는 데 사용한다.

## Docker

이미지:

```text
leesk212/coding-ai-agent-v2:latest
```

주의:

- 멀티 아키텍처 manifest가 필요하다
- Apple Silicon에서는 `linux/arm64` 이미지가 포함되어야 한다

## 현재 확인된 테스트 상태

실행 기준:

```bash
.venv/bin/python -m pytest -q tests
```

현재 결과:

```text
29 passed
```

주의:

- 루트에서 `pytest -q`를 바로 실행하면 vendored `deepagents_sourcecode/libs/evals/tests/...`까지 수집될 수 있다
- 현재 프로젝트 검증 기준은 `pytest tests` 범위가 맞다

## 최근 주요 업데이트 요약

- `split` topology 강제 및 local on-demand SubAgent spawn
- startup key entry + background prewarm 개선
- Main/SubAgent prompt override UI
- planner / architect / frontend / backend / mobile / remember 역할 추가
- remember SubAgent 기반 HITL 승인 흐름 추가
- Memory 페이지 추가
- durable memory record correction UI 추가
- role ordinal 표시
- 질의별 workdir 생성 + zip 다운로드
- SubAgent live output / pid / port / model 표시
- `Focused Analysis View` / HITL 강조 UI 추가
- navigation 상태 로그 및 chat history 복구 가드 추가

## 실행

### 로컬

```bash
cd /mnt/c/Users/SDS/Subject
source .venv/bin/activate
python -m coding_agent
```

### 테스트

```bash
.venv/bin/python -m pytest -q tests
```

## 한 줄 결론

이 프로젝트는 `DeepAgents` 개념을 기반으로,  
장기 메모리, 동적 SubAgent, mid-session Human in the Loop, 질의별 workdir, WebUI 기반 실시간 분석을 결합한 실행형 코딩 에이전트다.
