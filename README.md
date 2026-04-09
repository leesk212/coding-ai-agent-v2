# Coding AI Agent v2

DeepAgents v0.5 기반의 코딩 에이전트입니다.
이 프로젝트는 이제 공식 `AsyncSubAgent` 패턴을 기준으로 재구성되어,

- `deepagents.AsyncSubAgent(...)`
- `deepagents.create_deep_agent(...)`
- `langgraph.json` graph registry

를 중심으로 동작합니다.

핵심 목표:
- 공식 DeepAgents async-subagent 패턴 사용
- `single / split / hybrid` deployment topology 지원
- Supervisor + specialist graph 분리
- WebUI/CLI와 LangGraph deployment 실행 경로를 모두 지원

## Architecture

```text
┌────────────────────────── WebUI / CLI ──────────────────────────┐
│   Chat + Mermaid + SubAgent Monitor + Settings                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│         Main Supervisor (DeepAgents create_deep_agent)          │
│  - ModelFallbackMiddleware (OpenRouter -> Ollama)               │
│  - LongTermMemoryMiddleware (ChromaDB)                          │
│  - AsyncOnlySubagentsMiddleware (sync task tool 차단)           │
│  - Async task tools: start/check/update/cancel/list             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
      single topology                    split / hybrid topology
      (ASGI co-deploy)                   (HTTP Agent Protocol)
              │                                 │
   ┌──────────┼──────────┐             ┌────────┼────────┐
   │          │          │             │        │        │
 researcher  coder    reviewer      researcher coder  reviewer/debugger
 debugger    graphs    graphs        local servers or remote deployments
```

## 주요 기능

- `create_deep_agent` Supervisor 구성
- `AsyncSubAgent` spec 기반 subagent 구성 (`researcher`, `coder`, `reviewer`, `debugger`)
- `langgraph.json` graph registry 제공
- 공식 single deployment(ASGI) 경로 제공
- standalone WebUI/CLI용 split deployment(HTTP) 경로 제공
- Async Task 도구 기반 상태 관리
- `async_tasks` state 추적기 제공 (`AsyncTaskTracker`)
- ChromaDB 장기 메모리 (`memory_store`, `memory_search`)
- 모델 폴백 + Circuit Breaker
- WebUI Mermaid로 Async Task 흐름 시각화

## 설치

요구사항:
- Python 3.11+
- OpenRouter API Key 또는 Ollama 로컬 모델

```bash
# 1) 가상환경(선택)
python -m venv .venv
source .venv/bin/activate

# 2) 의존성 설치
pip install -e .

# 3) 환경 파일
cp .env.example .env
# OPENROUTER_API_KEY=... 설정
```

주의:
- `deepagents-cli`가 별도 설치되어 있으면 `deepagents==0.4.x` 충돌 경고가 날 수 있습니다.
- 본 프로젝트는 `deepagents>=0.5` 경로를 사용하며 `deepagents-cli` 런타임에 의존하지 않습니다.

## 실행 방법

### 1) WebUI 실행

```bash
python -m coding_agent --webui
```

브라우저: `http://localhost:8501`

동작:
- 초기화 시 Main Supervisor 생성
- `DEEPAGENTS_DEPLOYMENT_TOPOLOGY=single` 이고 `LANGGRAPH_DEPLOYMENT_URL` 이 설정되어 있으면,
  WebUI는 running `langgraph` deployment의 `supervisor` graph에 직접 연결됩니다.
- 그렇지 않으면 standalone split topology로 로컬 AsyncSubAgent runtime을 기동합니다.
- Chat에서 `start_async_task`/`check_async_task`/`list_async_tasks` 등으로 Task 운용

### 2) CLI 실행

```bash
python -m coding_agent
```

single topology 예시:

```bash
export DEEPAGENTS_DEPLOYMENT_TOPOLOGY=single
export LANGGRAPH_DEPLOYMENT_URL=http://127.0.0.1:2024
export LANGGRAPH_ASSISTANT_ID=supervisor
python -m coding_agent --webui
```

CLI 명령:
- `/status` 모델 상태
- `/memory` 메모리 통계
- `/subagents` 프로세스 + tracked async tasks
- `/quit` 종료

### 3) 디버그 실행

```bash
python -m coding_agent --debug
```

## 테스트 실행

```bash
# 전체 테스트
python -m unittest discover -s tests -p "test_*.py"

# 코드 작성 + 리뷰 워크플로우 테스트만 실행
python -m unittest tests.test_code_review_workflow
```

## LangGraph Deployment 실행

공식 문서 권장 경로는 single deployment 입니다. 이 프로젝트는 이를 위해
루트에 [`langgraph.json`](/mnt/c/Users/SDS/Subject/langgraph.json) 을 제공합니다.

등록 graph:
- `supervisor`
- `researcher`
- `coder`
- `reviewer`
- `debugger`

예시:

```bash
langgraph dev --n-jobs-per-worker 10
```

이 경우 supervisor는 co-deployed subagent들을 `url` 없이 ASGI transport로 호출합니다.

## Async SubAgent 런타임 설정

`Settings` 페이지 또는 환경 변수로 조정:

| Variable | Description | Default |
|---|---|---|
| `DEEPAGENTS_DEPLOYMENT_TOPOLOGY` | `single`, `split`, `hybrid` | `single` |
| `ASYNC_SUBAGENT_HOST` | 로컬 subagent 서버 bind host | `127.0.0.1` |
| `ASYNC_SUBAGENT_BASE_PORT` | subagent 시작 포트(타입별 +1 증가) | `30240` |
| `MAX_SUBAGENTS` | 동시 SubAgent 제한(정책 레벨) | `3` |

예:
- `researcher` -> `30240`
- `coder` -> `30241`
- `reviewer` -> `30242`
- `debugger` -> `30243`

## 메모리/모델 설정

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API 키 | `""` |
| `OLLAMA_BASE_URL` | Ollama URL | `http://localhost:11434` |
| `LOCAL_FALLBACK_MODEL` | 로컬 fallback 모델 | `qwen2.5-coder:7b` |
| `MEMORY_DIR` | ChromaDB 저장 경로 | `~/.coding_agent/memory` |

## 프로젝트 구조

```text
src/coding_agent/
├── agent.py                         # create_deep_agent supervisor assembly
├── graphs.py                        # langgraph.json용 supervisor/subagent graph exports
├── async_subagent_manager.py        # AsyncSubAgent spec + topology/runtime manager
├── async_subagent_server.py         # split topology용 Agent Protocol subagent 서버
├── async_task_tracker.py            # async_tasks state 조회
├── config.py                        # 모델/런타임 설정
├── middleware/
│   ├── async_only_subagents.py      # sync subagent tool 차단
│   ├── long_term_memory.py          # ChromaDB memory middleware + tools
│   └── model_fallback.py            # 모델 폴백 + circuit breaker
├── memory/
│   ├── categories.py
│   └── store.py
└── webui/
    ├── app.py
    └── _pages/
        ├── chat.py                  # Mermaid + streaming chat + task snapshot
        ├── subagents.py             # runtime/태스크 모니터 + snapshot/live diff
        ├── memory.py
        └── settings.py
```

## 현재 동작 요약

- Main Agent는 async task 도구를 통해 백그라운드 작업을 시작합니다.
- 공식 DeepAgents `AsyncSubAgent` toolchain (`start/check/update/cancel/list`)을 사용합니다.
- single topology에서는 co-deployed ASGI transport를, standalone WebUI/CLI에서는 split HTTP transport를 사용합니다.
- WebUI는 conversation 단위 `thread_id`를 유지하고, Mermaid에 task 흐름을 반영합니다.
- 각 assistant 결과는 `async_task_snapshot`을 함께 저장해 히스토리 시점 비교가 가능합니다.
- 기본 정책은 "동일 질의 내 결과 취합"입니다. 별도 요청이 없으면 launch 후 `check_async_task`로 결과를 모아 최종 답변을 만듭니다.

## Troubleshooting

- 초기화가 느린 경우:
  - SubAgent 프로세스 초기 기동/health check 시간(수 초~수십 초)이 포함됩니다.
- 포트 충돌:
  - `ASYNC_SUBAGENT_BASE_PORT`를 다른 값으로 변경
- OpenRouter 오류:
  - API 키 확인 또는 Ollama fallback 준비

## Reference

- Deep Agents v0.5: https://blog.langchain.com/deep-agents-v0-5/
- Async SubAgents docs: https://docs.langchain.com/oss/python/deepagents/async-subagents
