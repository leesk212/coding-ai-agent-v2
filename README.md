# Coding AI Agent v2

이 프로젝트는 단순 코드 생성 챗봇이 아니라, 실제 개발 작업을 지속적으로 수행할 수 있는 `DeepAgents` 기반 코딩 에이전트를 목표로 합니다.

핵심 축은 3개입니다.

1. 장기 메모리와 지식 저장 체계
2. 동적으로 생성되고 정리되는 SubAgent 수명주기 관리
3. Agentic loop의 복원력과 안전성

이 문서는 먼저 "어느 코드에서 어떻게 Agent가 설정되는지"를 빠르게 파악할 수 있게 정리하고, 그 다음 실행 구조와 현재 쟁점을 설명합니다.

## 한눈에 보는 구조

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

리뷰를 시작할 때 가장 먼저 볼 파일은 아래 5개입니다.

1. `src/coding_agent/runtime.py`
2. `src/coding_agent/agent.py`
3. `src/coding_agent/async_subagent_manager.py`
4. `src/coding_agent/async_subagent_server.py`
5. `src/coding_agent/webui/_pages/chat.py`

## Agent 설정은 어디서 하나

### 1. 런타임 진입점

메인 진입점은 `src/coding_agent/runtime.py`의 `create_runtime_components(...)`입니다.

여기서 하는 일:

1. `deployment_topology`를 읽습니다.
2. `single / split / hybrid` 중 어떤 모드로 띄울지 결정합니다.
3. `single`이면 LangGraph deployment 연결 가능 여부를 확인합니다.
4. deployment가 없으면 `split`으로 fallback 합니다.
5. 최종적으로 `create_coding_agent(...)` 또는 remote adapter를 반환합니다.

즉, "이 프로젝트가 로컬 DeepAgents supervisor를 띄울지, 외부 deployment에 붙을지"를 결정하는 첫 번째 분기점이 여기입니다.

### 2. Main Agent 조립

메인 Supervisor는 `src/coding_agent/agent.py`의 `create_coding_agent(...)`에서 조립됩니다.

조립 순서는 의도적으로 DeepAgents CLI 스타일을 따릅니다.

1. 모델 fallback middleware 생성
2. 장기 메모리 middleware 생성
3. async-only middleware 생성
4. lazy async subagent middleware 생성
5. subagent lifecycle middleware 생성
6. async task completion middleware 생성
7. `AsyncSubAgent` spec 목록 생성
8. runtime-aware system prompt 생성
9. `create_deep_agent(...)` 호출

핵심 함수:

- `build_system_prompt(...)`
- `create_coding_agent(...)`

중요 포인트:

- Main Agent도 `create_deep_agent(...)`로 생성됩니다.
- backend는 `LocalShellBackend(root_dir=...)`로 연결됩니다.
- 메모리 도구는 `LongTermMemoryMiddleware`에서 제공됩니다.
- async delegation은 DeepAgents 내장 async subagent tool 경로를 사용합니다.

### 3. AsyncSubAgent spec 로딩

SubAgent 정의는 `src/coding_agent/async_subagent_manager.py`에 있습니다.

핵심 함수는 2단계로 나뉩니다.

#### `load_async_subagent_specs(...)`

역할:

- `~/.deepagents/config.toml`에서 DeepAgents가 직접 이해하는 `AsyncSubAgent` spec만 읽습니다.
- CLI 스타일과 최대한 유사한 순수 spec 로더입니다.

지원 필드:

- `name`
- `description`
- `graph_id`
- `url`
- `headers`

#### `load_async_subagents(...)`

역할:

- 위 spec 위에 현재 프로젝트가 필요한 런타임 메타데이터를 확장합니다.

추가 필드:

- `transport`
- `host`
- `port`
- `model`
- `system_prompt`

즉 구조는 아래와 같습니다.

```text
config.toml
  -> load_async_subagent_specs()
    -> load_async_subagents()
      -> LocalAsyncSubagentManager.build_async_subagents()
        -> create_deep_agent(subagents=[...])
```

### 4. SubAgent를 실제로 누가 띄우나

`split` topology에서 SubAgent 프로세스를 실제로 관리하는 것은 `LocalAsyncSubagentManager`입니다.

핵심 메서드:

- `build_async_subagents()`
- `ensure_started(name)`
- `get_runtime_info(name)`

동작 방식:

1. 앱 시작 시 모든 SubAgent를 미리 띄우지 않습니다.
2. Main Agent가 `start_async_task`를 호출하려는 순간
3. `LazyAsyncSubagentsMiddleware`가 `ensure_started(name)`를 호출합니다.
4. 해당 role에 해당하는 로컬 SubAgent 프로세스만 spawn 됩니다.
5. health check가 통과되면 HTTP Agent Protocol로 task가 전달됩니다.

즉, 평소에는 Main Agent만 살아 있고, 필요한 SubAgent만 on-demand로 뜹니다.

### 5. SubAgent 프로세스 내부는 어떻게 구성되나

실제 SubAgent 프로세스는 `src/coding_agent/async_subagent_server.py`에서 실행됩니다.

핵심 함수:

- `_bootstrap_agent()`
- `_execute_run(...)`

여기서 중요한 점:

- 각 SubAgent도 내부적으로 `create_deep_agent(...)`를 사용합니다.
- 즉 SubAgent는 단순 함수가 아니라 독립적인 DeepAgents runtime 입니다.
- backend는 `LocalShellBackend(root_dir=...)`로 연결됩니다.
- system prompt에는 다음 런타임 정보가 포함됩니다.
  - 현재 working directory
  - 절대 경로 사용 규칙
  - 파일 read/write 가능
  - shell execution 가능
  - 사용 모델

이 부분이 현재 디렉터리 기준 파일 작업을 허용하는 핵심입니다.

## 한 개의 사용자 질의는 어떻게 처리되나

질의 단위 orchestration은 `src/coding_agent/webui/_pages/chat.py`에 있습니다.

핵심 함수:

- `_stream_response(...)`

처리 흐름:

1. query-scoped session/thread를 생성합니다.
2. Main Agent stream을 시작합니다.
3. Main Agent의 메시지, tool call, 상태 변화를 Event Feed와 Mermaid에 반영합니다.
4. `start_async_task`가 나오면 SubAgent를 `tracked_agents`에 등록합니다.
5. SubAgent server의 run 상태를 짧은 주기로 폴링합니다.
6. `partial_output`, `status`, `endpoint`, `pid`, `model`을 UI에 반영합니다.
7. 모든 SubAgent가 끝나면 결과를 취합합니다.
8. 이 한 질의를 하나의 history snapshot으로 저장합니다.

중요한 세션 정책:

- SubAgent를 호출하지 않은 질의
  - Main Agent 응답으로 종료
- SubAgent를 하나라도 호출한 질의
  - 같은 사용자 세션으로 유지
  - 중간에 새 질의로 넘어가지 않음
  - 모든 SubAgent 결과가 돌아온 뒤에만 최종 종료

즉 이 프로젝트에서 "질의 하나"는 Main Agent 답변 한 번이 아니라, 관련 SubAgent들이 모두 끝날 때까지의 전체 실행 단위입니다.

## WebUI에서 무엇을 보여주나

현재 WebUI는 아래를 동시에 보여주도록 설계되어 있습니다.

- Main Agent 답변
- `Agent 동작 분석` Mermaid
- Event Feed
- `SubAgent Streaming Output`
- SubAgent별 `127.0.0.1:port`
- `pid`
- `model`
- 완료 후 lifecycle snapshot

실시간성 관련 설계:

- Main Agent는 stream 이벤트 기반
- SubAgent는 `/threads/{thread_id}/runs/{run_id}` 고빈도 polling 기반
- `partial_output`은 SubAgent server가 상태 줄, tool 실행, tool 결과, 최종 본문을 계속 누적합니다.

즉 토큰 단위 SSE는 아니지만, 사용자 입장에서는 "지금 무엇을 하고 있는지"를 UI에서 따라갈 수 있게 구성되어 있습니다.

## 장기 메모리 설계

핵심 파일:

- `src/coding_agent/middleware/long_term_memory.py`
- `src/coding_agent/memory/store.py`
- `src/coding_agent/memory/categories.py`
- `src/coding_agent/state/store.py`

이 프로젝트는 세션 히스토리를 장기 메모리와 동일시하지 않습니다.

메모리 계층은 아래 3개로 나뉩니다.

1. `user/profile`
2. `project/context`
3. `domain/knowledge`

저장 구조:

- semantic retrieval: ChromaDB 계층
- durable source of truth: SQLite 계층

지원 도구:

- `memory_store`
- `memory_search`
- `memory_correct`

정정 정책:

- 기존 record는 `superseded`
- 새 record는 `active`

즉 메모리는 "저장만 하는 파일"이 아니라, 다음 질의에서 실제로 조회되고 다시 프롬프트/추론에 반영되는 구조를 목표로 합니다.

## SubAgent 수명주기 설계

핵심 파일:

- `src/coding_agent/async_subagent_manager.py`
- `src/coding_agent/middleware/subagent_lifecycle.py`
- `src/coding_agent/state/store.py`
- `src/coding_agent/state/models.py`

저장 메타데이터:

- `agent_id`
- `role`
- `task_summary`
- `parent_id`
- `state`
- `created_at`
- `updated_at`
- `task_id`
- `run_id`
- `endpoint`
- `pid`
- `model`

기본 상태 전이:

```text
created -> assigned -> running -> completed
created -> assigned -> running -> failed
created -> assigned -> running -> cancelled
completed/failed/cancelled -> destroyed
```

추가 상태:

- `blocked`

이 상태는 단순 UI 표시용이 아니라 durable store에 남겨서, 나중에 "실패했는지, 막혔는지, 정상 완료했는지"를 구분할 수 있게 합니다.

## Agentic loop 복원력

핵심 파일:

- `src/coding_agent/resilience.py`
- `src/coding_agent/middleware/model_fallback.py`
- `src/coding_agent/webui/_pages/chat.py`

현재 다루는 장애 유형:

- `model_timeout`
- `no_progress_loop`
- `tool_call_error`
- `subagent_failure`
- `external_api_error`
- `safe_stop`

현재 구현에 포함된 방어 전략:

- 모델 fallback
- max iteration guard
- 동일/무진전 루프 방지
- blocked 감지
- alternate subagent policy
- stop / refresh safe stop
- loop run durable status 저장

중요한 운영상 판단:

- "조용히 실행 중"과 "진짜 blocked"는 다릅니다.
- 그래서 blocked 판정은 단순 무출력 기준이 아니라, 프로세스 생존 여부와 최근 진행 신호를 함께 봅니다.

## deployment topology

### `split`

현재 기본값입니다.

- Main Agent: 로컬 WebUI 프로세스 내부
- SubAgent: 로컬 별도 프로세스
- transport: HTTP Agent Protocol

장점:

- 각 SubAgent를 on-demand로 띄울 수 있음
- 프로세스/포트/상태를 명확히 관찰 가능
- WebUI에서 SubAgent별 진행 상태를 보여주기 쉬움

### `single`

LangGraph deployment가 살아 있을 때만 사용합니다.

- supervisor와 subagent가 같은 deployment 안에 있음
- transport: ASGI

관련 파일:

- `src/coding_agent/runtime.py`
- `src/coding_agent/langgraph_remote.py`

## `~/.deepagents/config.toml` 예시

최소 spec:

```toml
[async_subagents.researcher]
description = "Research agent"
graph_id = "researcher"

[async_subagents.coder]
description = "Coding agent"
graph_id = "coder"
```

원격 endpoint 고정:

```toml
[async_subagents.reviewer]
description = "Review agent"
graph_id = "reviewer"
url = "http://127.0.0.1:30242"
headers = { Authorization = "Bearer demo-token" }
```

로컬 런타임 확장:

```toml
[async_subagents.debugger]
description = "Debugging agent"
graph_id = "debugger"
transport = "http"
host = "127.0.0.1"
port = 30243
model = "openrouter:qwen/qwen-2.5-coder-32b-instruct"
system_prompt = "You are a debugging specialist."
```

주의:

- `load_async_subagent_specs(...)`는 DeepAgents 표준 spec만 읽습니다.
- `load_async_subagents(...)`는 현재 프로젝트 운영에 필요한 추가 런타임 필드를 읽습니다.

## 현재 모델 정책

핵심 파일:

- `src/coding_agent/config.py`
- `src/coding_agent/middleware/model_fallback.py`

현재 방향:

- OpenRouter 경유 모델을 우선 사용
- 필요 시 OpenAI 또는 로컬 Ollama fallback
- 모델 제약은 system prompt와 로그에 노출

즉 특정 모델 하나에 과도하게 잠기지 않고, 실패 시 다른 모델 경로로 넘길 수 있게 설계되어 있습니다.

## 실행 방법

### WebUI 실행

```bash
cd /mnt/c/Users/SDS/Subject
source .venv/bin/activate
python -m coding_agent
```

브라우저:

- `http://localhost:8501`

### LangGraph deployment 사용

```bash
export DEEPAGENTS_DEPLOYMENT_TOPOLOGY=single
export LANGGRAPH_DEPLOYMENT_URL=http://127.0.0.1:2024
export LANGGRAPH_ASSISTANT_ID=supervisor
python -m coding_agent
```

### 로컬 `split` topology 명시

```bash
export DEEPAGENTS_DEPLOYMENT_TOPOLOGY=split
python -m coding_agent
```

### Docker Compose 실행

이 저장소에는 바로 실행 가능한 `Dockerfile`과 `docker-compose.yml`이 포함되어 있습니다.

기본 정책:

- 이미지 내부 애플리케이션 코드는 `/opt/app`
- 실제 작업 디렉터리와 SubAgent 파일 작업 경로는 `/workspace`
- 장기 메모리는 `/data/memory`
- durable state는 `/data/state`
- `.deepagents` 설정과 상태는 `/root/.deepagents`

처음 실행:

```bash
docker compose up --build
```

브라우저:

- `http://localhost:8501`

선택 사항:

- Ollama까지 같이 띄우려면:

```bash
docker compose --profile with-ollama up --build
```

다른 PC에서 실행할 때 필요한 것은 기본적으로 3개입니다.

1. Docker / Docker Compose
2. OpenRouter API key
3. 작업 결과를 받을 `./workspace` 디렉터리

`.env` 파일은 필수가 아닙니다.

- `docker compose`는 `.env` 없이도 실행됩니다.
- OpenRouter API key는 실행 후 WebUI 시작 화면에서 직접 입력할 수 있습니다.
- 필요하면 쉘 환경변수로 넘겨도 됩니다. 예: `OPENROUTER_API_KEY=... docker compose up`

중요:

- Docker 실행 시 Main Agent와 SubAgent의 현재 작업 디렉터리는 `/workspace`입니다.
- 따라서 에이전트가 생성/수정한 파일은 호스트의 `./workspace`에 나타납니다.

## 주요 환경 변수

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key | `""` |
| `OLLAMA_BASE_URL` | Ollama URL | `http://localhost:11434` |
| `LOCAL_FALLBACK_MODEL` | local fallback model | `qwen2.5-coder:7b` |
| `DEEPAGENTS_DEPLOYMENT_TOPOLOGY` | `single`, `split`, `hybrid` | `split` |
| `LANGGRAPH_DEPLOYMENT_URL` | remote deployment URL | `""` |
| `LANGGRAPH_ASSISTANT_ID` | remote supervisor assistant id | `supervisor` |
| `ASYNC_SUBAGENT_HOST` | local subagent host | `127.0.0.1` |
| `ASYNC_SUBAGENT_BASE_PORT` | base port for subagents | `30240` |
| `MEMORY_DIR` | semantic memory storage path | `~/.coding_agent/memory` |
| `STATE_DIR` | durable SQLite state path | `~/.coding_agent/state` |
| `CODING_AGENT_PORT` | compose-exposed Streamlit port | `8501` |
| `CODING_AGENT_IMAGE` | Docker image name used by compose | `leesk212/coding-ai-agent-v4:latest` |

## 테스트

전체:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

핵심:

```bash
python -m unittest tests.test_async_subagent_manager tests.test_async_subagent_server
```

## 현재 프로젝트 구조

```text
src/coding_agent/
├── agent.py
├── async_subagent_manager.py
├── async_subagent_server.py
├── async_task_tracker.py
├── config.py
├── graphs.py
├── langgraph_remote.py
├── runtime.py
├── memory/
│   ├── categories.py
│   └── store.py
├── middleware/
│   ├── async_only_subagents.py
│   ├── async_task_completion.py
│   ├── lazy_async_subagents.py
│   ├── long_term_memory.py
│   ├── model_fallback.py
│   └── subagent_lifecycle.py
├── resilience.py
├── state/
│   ├── models.py
│   └── store.py
└── webui/
    ├── app.py
    └── _pages/
        ├── chat.py
        ├── memory.py
        ├── settings.py
        └── subagents.py
```

## 현재 쟁점

리뷰할 때 특히 봐야 하는 쟁점은 아래입니다.

1. `start_async_task` 결과의 `task_id / run_id / thread_id` 바인딩이 일관적인가
2. Main Agent가 SubAgent를 호출한 질의는 세션을 끝까지 유지하는가
3. `partial_output`이 실제로 WebUI에 실시간에 가깝게 보이는가
4. "조용하지만 정상 실행 중"과 `blocked`를 구분하는가
5. 장기 메모리와 세션 히스토리를 혼동하지 않는가
6. on-demand spawn된 SubAgent가 현재 working directory 기준으로 파일 작업을 수행하는가

## 추천 리뷰 순서

가독성을 위해 아래 순서로 읽는 것을 권장합니다.

1. `src/coding_agent/runtime.py`
2. `src/coding_agent/agent.py`
3. `src/coding_agent/async_subagent_manager.py`
4. `src/coding_agent/async_subagent_server.py`
5. `src/coding_agent/webui/_pages/chat.py`
6. `src/coding_agent/middleware/long_term_memory.py`
7. `src/coding_agent/middleware/subagent_lifecycle.py`
8. `src/coding_agent/resilience.py`

이 순서대로 읽으면 "부팅 -> supervisor 조립 -> subagent runtime -> UI orchestration -> memory/lifecycle/resilience" 흐름으로 자연스럽게 따라갈 수 있습니다.
