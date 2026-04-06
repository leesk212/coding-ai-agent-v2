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
