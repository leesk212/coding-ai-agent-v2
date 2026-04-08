# Coding AI Agent v2

DeepAgents v0.5 기반의 코딩 에이전트입니다.
메인 Supervisor는 `create_deep_agent()`로 구성되고, SubAgent는 **로컬 PC에서 타입별 독립 프로세스**로 실행됩니다.

핵심 목표:
- `create_deep_agent` 중심 아키텍처
- `AsyncSubAgent` 기반 백그라운드 작업
- SubAgent 프로세스 관리 + Task 상태 추적 + 결과 취합

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
                               │ Agent Protocol (HTTP)
             ┌─────────────────┼─────────────────┐
             │                 │                 │
┌────────────▼───────┐ ┌──────▼──────────┐ ┌────▼──────────────┐
│ researcher process │ │ code_writer proc │ │ reviewer/debugger │
│ FastAPI server     │ │ FastAPI server   │ │ FastAPI servers   │
│ create_deep_agent  │ │ create_deep_agent│ │ create_deep_agent │
└────────────────────┘ └──────────────────┘ └───────────────────┘
```

## 주요 기능

- `create_deep_agent` Supervisor 구성
- SubAgent 타입별 독립 프로세스 실행 (`researcher`, `code_writer`, `reviewer`, `debugger`)
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
- 로컬 Async SubAgent 프로세스 기동 및 health check
- Chat에서 `start_async_task`/`check_async_task`/`list_async_tasks` 등으로 Task 운용

### 2) CLI 실행

```bash
python -m coding_agent
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

## Async SubAgent 런타임 설정

`Settings` 페이지 또는 환경 변수로 조정:

| Variable | Description | Default |
|---|---|---|
| `ASYNC_SUBAGENT_HOST` | 로컬 subagent 서버 bind host | `127.0.0.1` |
| `ASYNC_SUBAGENT_BASE_PORT` | subagent 시작 포트(타입별 +1 증가) | `30240` |
| `MAX_SUBAGENTS` | 동시 SubAgent 제한(정책 레벨) | `3` |

예:
- `researcher` -> `30240`
- `code_writer` -> `30241`
- `reviewer` -> `30242`
- `debugger` -> `30243`

`~/.deepagents/config.toml`의 `[async_subagents]`로 타입별 설정 오버라이드도 가능합니다.

```toml
[async_subagents.researcher]
description = "Research specialist"
graph_id = "researcher"
system_prompt = "Research deeply and return structured findings."
model = "openai:gpt-4o-mini"
url = "http://127.0.0.1:30240"
```

- `url`이 있으면 host/port를 파싱해 해당 주소를 사용합니다.
- 같은 이름(`researcher`, `code_writer` 등)은 기본 설정 위에 merge 됩니다.
- 새 이름을 추가하면 새 async subagent 타입으로 등록됩니다.

## 메모리/모델 설정

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API 키 | `""` |
| `OPENAI_API_KEY` | OpenAI(ChatGPT) fallback API 키 | `""` |
| `OPENAI_FALLBACK_MODEL` | OpenAI fallback 모델 | `gpt-4o-mini` |
| `OLLAMA_BASE_URL` | Ollama URL | `http://localhost:11434` |
| `LOCAL_FALLBACK_MODEL` | 로컬 fallback 모델 | `qwen2.5-coder:7b` |
| `MEMORY_DIR` | ChromaDB 저장 경로 | `~/.coding_agent/memory` |

## 프로젝트 구조

```text
src/coding_agent/
├── agent.py                         # create_deep_agent supervisor assembly
├── async_subagent_manager.py        # 타입별 로컬 subagent 프로세스 매니저
├── async_subagent_server.py         # Agent Protocol FastAPI subagent 서버
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
        ├── subagents.py             # 프로세스/태스크 모니터 + snapshot/live diff
        ├── memory.py
        └── settings.py
```

## 현재 동작 요약

- Main Agent는 async task 도구를 통해 백그라운드 작업을 시작합니다.
- SubAgent 결과는 task ID 단위로 조회/업데이트/취소합니다.
- WebUI는 conversation 단위 `thread_id`를 유지하고, Mermaid에 task 흐름을 반영합니다.
- 각 assistant 결과는 `async_task_snapshot`을 함께 저장해 히스토리 시점 비교가 가능합니다.
- 기본 정책은 "동일 질의 내 결과 취합"입니다. 별도 요청이 없으면 launch 후 `check_async_task`로 결과를 모아 최종 답변을 만듭니다.

## Troubleshooting

- 초기화가 느린 경우:
  - SubAgent 프로세스 초기 기동/health check 시간(수 초~수십 초)이 포함됩니다.
- 포트 충돌:
  - `ASYNC_SUBAGENT_BASE_PORT`를 다른 값으로 변경
- OpenRouter 오류:
  - `OPENROUTER_API_KEY` 확인
  - OpenAI fallback을 쓰려면 `OPENAI_API_KEY` 설정
  - 둘 다 실패하면 Ollama fallback 준비

## Reference

- Deep Agents v0.5: https://blog.langchain.com/deep-agents-v0-5/
- Async SubAgents docs: https://docs.langchain.com/oss/python/deepagents/async-subagents
