# deepagents_cli 주석 보강 가이드

## 목적
이 문서는 `deepagents_cli` 하위 Python 소스에 적용한 주석 보강 작업의 기준과 결과를 한국어로 정리한 보조 문서입니다.
코드 내부 주석과 docstring 은 저장소 규칙에 맞춰 영어로 유지했고, 이 문서는 학습용 해설과 인벤토리 역할을 합니다.

## 적용 기준
- 모듈 docstring: 파일의 역할, 주요 협력 객체, 생명주기 제약을 설명
- public API docstring: 기존 Google-style docstring 유지 또는 보강
- private helper docstring: 파싱, 캐시, 상태 전이, 프로토콜 변환처럼 비직관적인 경우만 유지/보강
- inline / section comment: 큰 파일에서 흐름 경계를 찾기 어려운 구간에만 추가
- 비목표: 동작 변경, 리팩터링, 이름 변경, 기계적인 줄 단위 설명

## 이번 작업에서 실제로 강화한 파일

### 1. 오케스트레이션 / 실행 흐름
- `deepagents_cli/app.py`
  - Textual 앱의 책임 범위를 더 명확히 설명하도록 모듈 docstring 확장
  - 터미널 워크어라운드, 테마/파싱 헬퍼, 세션 상태, 종료 결과 영역에 section comment 추가
- `deepagents_cli/main.py`
  - CLI 진입점 전체 책임을 설명하도록 모듈 docstring 확장
  - 의존성 검사, 인자 파싱, 대체 엔트리포인트 구간에 section comment 추가
- `deepagents_cli/textual_adapter.py`
  - LangGraph 스트림 이벤트와 Textual UI 사이의 브리지 역할을 드러내도록 모듈 docstring 확장
  - schema helper, bridge object, stream execution 영역에 section comment 추가
- `deepagents_cli/sessions.py`
  - SQLite 체크포인터 기반 스레드 조회/캐시/표시 데이터 변환 역할을 설명하도록 모듈 docstring 확장
  - SQLite 호환 패치, formatting helper, checkpoint inspection, public helper 구간에 section comment 추가
- `deepagents_cli/agent.py`
  - 모델, 미들웨어, 툴, 백엔드를 조립하는 역할을 드러내도록 모듈 docstring 확장
- `deepagents_cli/ask_user.py`
  - `ask_user` tool 과 CLI interrupt 사이의 변환 레이어라는 점을 명확히 설명

### 2. 설정 / 유틸리티 / 통합 계층
- `deepagents_cli/config.py`
- `deepagents_cli/clipboard.py`
- `deepagents_cli/editor.py`
- `deepagents_cli/file_ops.py`
- `deepagents_cli/media_utils.py`
- `deepagents_cli/project_utils.py`
- `deepagents_cli/tools.py`
- `deepagents_cli/integrations/__init__.py`
- `deepagents_cli/integrations/sandbox_factory.py`
- `deepagents_cli/integrations/sandbox_provider.py`
- `deepagents_cli/__init__.py`
- `deepagents_cli/__main__.py`
- `deepagents_cli/_testing_models.py`
- `deepagents_cli/_version.py`

위 파일들은 대부분 모듈 최상단 설명이 너무 짧아서, "이 파일이 시스템 안에서 왜 존재하는가"를 빠르게 파악할 수 있도록 설명형 docstring 으로 바꿨습니다.

### 3. 대형 Textual 위젯
- `deepagents_cli/widgets/messages.py`
  - transcript helper / user-skill widget / assistant-tool widget / auxiliary widget 구간을 나눠 탐색성을 높임
- `deepagents_cli/widgets/chat_input.py`
  - completion popup, text-entry heuristics, adapter/container 영역을 분리
- `deepagents_cli/widgets/thread_selector.py`
  - column formatting helper 와 interactive modal 영역을 나눔
- `deepagents_cli/widgets/_links.py`
- `deepagents_cli/widgets/approval.py`
- `deepagents_cli/widgets/ask_user.py`
- `deepagents_cli/widgets/diff.py`
- `deepagents_cli/widgets/history.py`
- `deepagents_cli/widgets/loading.py`
- `deepagents_cli/widgets/mcp_viewer.py`
- `deepagents_cli/widgets/model_selector.py`
- `deepagents_cli/widgets/status.py`
- `deepagents_cli/widgets/theme_selector.py`
- `deepagents_cli/widgets/tool_renderers.py`
- `deepagents_cli/widgets/tool_widgets.py`
- `deepagents_cli/widgets/welcome.py`

위 파일들은 위젯 책임이 한 줄 제목만으로는 충분히 전달되지 않는 경우가 많아, 모듈 docstring 을 확장해 "무엇을 렌더링하고 어떤 상호작용을 담당하는지"를 더 분명히 적었습니다.

## 이미 상대적으로 충분해서 이번에 최소 수정 또는 무수정으로 둔 파일군

### 설정 / 모델 / 서버
- `deepagents_cli/model_config.py`
- `deepagents_cli/non_interactive.py`
- `deepagents_cli/server.py`
- `deepagents_cli/server_manager.py`
- `deepagents_cli/remote_client.py`
- `deepagents_cli/server_graph.py`
- `deepagents_cli/mcp_tools.py`
- `deepagents_cli/mcp_trust.py`
- `deepagents_cli/local_context.py`
- `deepagents_cli/hooks.py`
- `deepagents_cli/configurable_model.py`
- `deepagents_cli/update_check.py`
- `deepagents_cli/unicode_security.py`
- `deepagents_cli/output.py`
- `deepagents_cli/token_state.py`
- `deepagents_cli/_session_stats.py`
- `deepagents_cli/_server_config.py`
- `deepagents_cli/_env_vars.py`
- `deepagents_cli/_debug.py`
- `deepagents_cli/_cli_context.py`
- `deepagents_cli/_ask_user_types.py`

### 위젯 / 지원 모듈
- `deepagents_cli/widgets/autocomplete.py`
- `deepagents_cli/widgets/message_store.py`

### 기타
- `deepagents_cli/built_in_skills/__init__.py`
- `deepagents_cli/built_in_skills/skill-creator/scripts/init_skill.py`
- `deepagents_cli/built_in_skills/skill-creator/scripts/quick_validate.py`
- `deepagents_cli/skills/__init__.py`
- `deepagents_cli/skills/commands.py`
- `deepagents_cli/skills/load.py`
- `deepagents_cli/subagents.py`
- `deepagents_cli/ui.py`
- `deepagents_cli/input.py`

이 파일들은 이미 다중 문단 docstring, 세부 함수 설명, 또는 충분한 inline comment 를 가지고 있어서 이번 작업에서는 기준선만 확인하고 지나갔습니다.

## 읽는 순서 추천
1. `app.py` 와 `main.py` 로 전체 CLI 진입 흐름 파악
2. `textual_adapter.py` 와 `sessions.py` 로 실행/스레드 데이터 흐름 이해
3. `widgets/chat_input.py`, `widgets/messages.py`, `widgets/thread_selector.py` 로 UI 상호작용 이해
4. `config.py`, `agent.py`, `tools.py`, `integrations/*` 로 설정과 의존성 연결 방식 확인

## 해석 팁
- section comment 는 “여기부터 책임이 바뀐다”는 경계 표시로 읽으면 됩니다.
- module docstring 은 “왜 이 파일이 따로 존재하는가”를 설명하는 요약으로 읽으면 됩니다.
- 기존 함수 docstring 이 이미 좋았던 곳은 일부러 과도하게 늘리지 않았습니다. 이 작업의 목표는 문서량 증가가 아니라 탐색성과 이해도 향상입니다.
