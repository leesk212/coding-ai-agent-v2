# Coding AI Agent

DeepAgents Framework 기반 Coding AI Agent. 장기 메모리, 동적 SubAgent, 모델 Fallback, WebUI를 지원합니다.

## Architecture

```
┌─────────────── WebUI (Streamlit) ────────────────┐
│  Chat │ Memory Dashboard │ SubAgent │ Settings    │
└───────────────────┬──────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────┐
│              Middleware Stack                      │
│  ModelFallbackMiddleware   (OpenRouter → Ollama)  │
│  LongTermMemoryMiddleware  (ChromaDB vector)      │
│  SubAgentLifecycleMiddleware (동적 생성/소멸)       │
│  + DeepAgents 기본 미들웨어                        │
└──────────────────────────────────────────────────┘
```

## Features

| 기능 | 설명 |
|------|------|
| **장기 메모리** | ChromaDB 벡터 스토어, 4개 카테고리 (domain_knowledge, user_preferences, code_patterns, project_context) |
| **동적 SubAgent** | 런타임 생성/실행/소멸, Registry 상태 관리, 5가지 타입 (code_writer, researcher, reviewer, debugger, general) |
| **모델 Fallback** | OpenRouter 오픈소스 모델 → Ollama 로컬 LLM, Circuit Breaker 패턴 |
| **Agentic Loop 방어** | Max iterations, empty response guard, stuck detection |
| **WebUI** | Streamlit 4페이지: Chat, Memory 대시보드, SubAgent 모니터, Settings |

## Quick Start

### Docker (권장)

```bash
# 1. .env 파일 생성
cp .env.example .env
# OPENROUTER_API_KEY 를 설정하세요

# 2. 실행
docker compose up --build

# 3. 브라우저에서 접속
# http://localhost:8501

# Ollama 로컬 LLM도 함께 실행하려면:
docker compose --profile with-ollama up --build
```

### 로컬 실행

```bash
# 1. 의존성 설치
pip install -e .

# 2. .env 파일 생성
cp .env.example .env

# 3. WebUI 모드
python -m coding_agent --webui

# 4. CLI 모드
python -m coding_agent
```

## Model Priority

기본 모델 우선순위 (OpenRouter):

1. `deepseek/deepseek-chat-v3-0324`
2. `qwen/qwen-2.5-coder-32b-instruct`
3. `meta-llama/llama-3.3-70b-instruct`
4. `mistralai/mistral-small-3.1-24b-instruct`
5. **Fallback**: Ollama `qwen2.5-coder:7b` (로컬)

모델 실패 시 자동으로 다음 모델로 전환됩니다. Circuit Breaker: 3회 연속 실패 시 5분간 해당 모델 스킵.

## Testing

### WebUI 테스트 (사이드바 Test Prompts)

WebUI Chat 페이지의 사이드바에 내장된 테스트 프롬프트를 사용할 수 있습니다.

| 테스트 | 프롬프트 | 확인 사항 |
|--------|----------|-----------|
| **SubAgent** | `Analyze the following task by spawning sub-agents: 1) A researcher to investigate best practices for Python error handling, 2) A code_writer to write an example implementation` | 화면 자동 분할, 2개 SubAgent 생성/실행/소멸, Event Timeline |
| **Memory** | `Remember that I prefer Python type hints and Google-style docstrings. Then search memory to confirm it was saved.` | `memory_store` → `memory_search` 호출, Memory 대시보드에서 확인 |
| **Multi-Agent** | `I need you to: spawn a code_writer to create a fibonacci function, then spawn a reviewer to review the code quality` | 순차 SubAgent 생성, reviewer가 code_writer 결과를 참조 |
| **Fallback** | `Write a simple hello world in Python` | 정상 응답, 사용된 모델명 표시 |

### CLI 테스트

```bash
python -m coding_agent

# 1. SubAgent 테스트
You> Create a fibonacci function using a code_writer subagent, then have a reviewer check it

# 2. Memory 테스트
You> Remember that my project uses FastAPI and PostgreSQL
You> What do you know about my project setup?

# 3. Fallback 테스트 (API 키 없이 실행 → Ollama로 자동 전환)
You> Write hello world

# 4. 상태 확인 명령어
You> /status     # 모델별 Circuit Breaker 상태
You> /memory     # 메모리 카테고리별 통계
You> /subagents  # SubAgent 실행 이력
```

### 기능별 검증 체크리스트

- [ ] **장기 메모리**: 대화 후 Memory 대시보드에서 저장 확인 → 새 세션에서 recall 가능
- [ ] **모델 Fallback**: OpenRouter API 키 제거 시 → Ollama로 자동 전환 확인
- [ ] **SubAgent 라이프사이클**: Chat 화면 자동 분할 → 각 Agent 카드 상태 전환 (⏳→🔄→✅)
- [ ] **Agentic Loop 방어**: 25회 이상 반복 시 자동 종료 확인
- [ ] **WebUI**: Chat, Memory, SubAgent, Settings 4개 페이지 정상 렌더링

## Project Structure

```
src/coding_agent/
├── __main__.py              # CLI 엔트리포인트
├── agent.py                 # Agent 조립 + AgentLoopGuard
├── config.py                # 설정 관리
├── middleware/
│   ├── model_fallback.py    # OpenRouter→Ollama + CircuitBreaker
│   ├── long_term_memory.py  # ChromaDB 벡터 메모리 미들웨어
│   └── subagent_lifecycle.py # 동적 SubAgent 관리
├── memory/
│   ├── store.py             # ChromaDB 벡터 스토어
│   └── categories.py        # 메모리 카테고리
└── webui/
    ├── app.py               # Streamlit 메인 앱
    └── pages/               # Chat, Memory, SubAgents, Settings
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API 키 | (required) |
| `OLLAMA_BASE_URL` | Ollama 서버 URL | `http://localhost:11434` |
| `LOCAL_FALLBACK_MODEL` | 로컬 fallback 모델 | `qwen2.5-coder:7b` |
| `MEMORY_DIR` | 메모리 저장 경로 | `~/.coding_agent/memory` |
| `MAX_SUBAGENTS` | 최대 동시 SubAgent 수 | `3` |
