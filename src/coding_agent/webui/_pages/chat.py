"""Chat page — Mermaid flowchart + Event Feed + Scrollable Result.

Back-end generates Mermaid syntax → front-end renders it dynamically via CDN.

Layout (top → bottom):
┌──────────────────────────────────────────────────────────┐
│  📝 질의 입력창 (text_area)  │ 🚀 Send / 🔄 Refresh    │
├──────────────────────────────────────────────────────────┤
│  🔍 Agent 동작 분석                                       │
│  ├─ 📊 Mermaid FlowChart  (graph LR)                     │
│  └─ 📡 Event Feed                                        │
├──────────────────────────────────────────────────────────┤
│  💬 Result  (고정 높이 400px, 내부 스크롤)                 │
├──────────────────────────────────────────────────────────┤
│  📌 Prompt  (프리셋 프롬프트 버튼들)                       │
└──────────────────────────────────────────────────────────┘
"""

import io
import json
import logging
import re
import threading
import time
import traceback
import uuid
import zipfile
from pathlib import Path

import httpx
import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import HumanMessage
from coding_agent.memory.categories import MemoryCategory

from coding_agent.config import settings
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
from coding_agent.resilience import get_policy
from coding_agent.runtime import create_runtime_components

logger = logging.getLogger(__name__)

AGENT_ICONS = {
    "coder": "✍️", "code_writer": "✍️", "researcher": "🔍", "reviewer": "📋",
    "debugger": "🐛", "frontend": "🖥️", "backend": "🗄️", "planner": "🗂️",
    "architect": "🏗️", "mobile": "📱", "general": "🤖",
    "remember": "🧠",
}

TEST_PROMPTS = {
    "User/Profile": (
        "장기 메모리 테스트다. 다음 사용자 선호를 user/profile 계층에 저장하고, "
        "바로 다시 조회해서 이후 응답 형식에 어떻게 반영할지 설명해라. "
        "규칙: 출력은 항상 한국어 설명 + 영어 코드, Python 스타일을 선호한다."
    ),
    "Project/Context": (
        "장기 메모리 테스트다. 다음 프로젝트 규칙을 project/context 계층에 저장하고 다시 조회해라. "
        "규칙: 모든 공개 Python 함수에는 타입 힌트가 필요하고, pytest를 사용하며, "
        "pydantic은 금지한다. 이후 이 규칙이 코드 생성에 어떻게 반영되는지 설명해라."
    ),
    "Domain Knowledge": (
        "장기 메모리 테스트다. 다음 도메인 지식을 domain/knowledge 계층에 저장하고, "
        "같은 응답에서 다시 검색해라. 규칙: 고객 등급 Silver는 환불 수수료 0%, "
        "Gold는 0%, Bronze는 10%다. 그리고 이 규칙을 결제/환불 로직 생성 시 어떻게 재사용할지 설명해라."
    ),
    "Memory Correction": (
        "메모리 정정 테스트다. domain/knowledge 에서 Silver 환불 규칙을 찾아서 "
        "이제 Silver는 환불 수수료 5%로 바뀌었다고 정정하고, 정정 전/후 차이를 요약해라."
    ),
    "Memory Extraction": (
        "검증 테스트다. 이 시스템에 시스템 프롬프트 또는 스킬 기반으로 장기 메모리와 도메인 지식을 "
        "추출/저장/재주입하는 메모리 시스템이 실제로 탑재되어 있는지 점검해라. "
        "다음 문장을 근거 데이터로 사용하라: 우리 팀은 모든 공개 Python 함수에 타입 힌트를 강제하고, "
        "고객 등급 Silver는 환불 수수료 0%다. 이 정보를 어떤 메모리 계층(user/profile, project/context, "
        "domain/knowledge)으로 추출할지 설명하고, 추출 시점, 저장 위치, 다음 작업에서의 재사용 경로를 구체적으로 답해라. "
        "가능하면 memory_search 또는 memory_store 같은 실제 메모리 도구 사용 여부도 함께 보고해라."
    ),
    "SubAgent Lifecycle": (
        "동적 SubAgent 수명주기 테스트다. 이 요청은 반드시 async subagent를 사용해야 한다. "
        "하나의 사용자 질의 안에서 researcher subagent와 coder subagent를 `start_async_task`로 "
        "동적으로 생성해서 실행하고, 완료될 때까지 기다린 뒤, 각 subagent의 상태 전이 "
        "created -> assigned -> running -> completed/destroyed 를 요약해라."
    ),
    "Code+Review Test": (
        "Handle this in one user turn. You must use async subagents via `start_async_task`. "
        "First launch a coder subagent to implement a fibonacci function "
        "with type hints and save it to a concrete Python file in the current query workspace. "
        "After the coder completes and the file path is known, launch a reviewer subagent to review "
        "that exact file for correctness, edge cases, and missing tests. Wait for both to finish, "
        "collect the completed results in the same response, and synthesize one final answer."
    ),
    "Blocked/Failed": (
        "SubAgent 예외 처리 테스트다. 이 요청은 반드시 async subagent를 사용해야 한다. 일부러 모호한 작업을 coder subagent에 맡기고, "
        "blocked 또는 failed 상태가 감지되면 대체 경로를 사용해라. "
        "최종적으로 어떤 상태 전이가 있었는지와 어떤 대체 역할을 사용했는지 요약해라."
    ),
    "Loop Safety": (
        "Agentic loop 복원력 테스트다. 다음 4가지를 짧게 점검해라: "
        "모델 timeout, 반복 무진전, tool call 오류, safe stop. "
        "각 항목마다 감지 신호, 재시도 여부, fallback 여부, stop 조건을 설명해라."
    ),
    "Model Policy": (
        "모델 정책 증빙 테스트다. 현재 사용 중인 모델 식별자를 말하고, "
        "OpenRouter 우선 사용 여부, fallback 모델, tool calling/긴 문맥/모델 전환 제약을 요약해라."
    ),
    "Remember Agent": (
        "Remember agent 동작 확인 테스트다. 간단한 산출물을 하나 이상 만든 뒤, "
        "turn 마지막에 remember subagent를 호출해서 현재 query workspace에서 장기 메모리화할 가치가 높은 "
        "파일 후보를 최대 10개까지 추려라. 각 후보에 대해 왜 기억할 가치가 있는지 짧게 설명하고, "
        "최종적으로 Human in the Loop 승인이 필요하다는 점을 명시해라."
    ),
}

SCENARIO_PROMPTS = {
    "Scenario_1 : PMS시스템 구성": (
        "## Task\n\n"
        "PMS (project manage system) 시스템을 구성하는 프로젝트.\n\n"
        "## Process\n\n"
        "1. PRD 파일을 만들고\n"
        "2. PRD 파일을 기반으로 작업을 원자 단위 작업으로 분해할 것.\n"
        "3. 작업에 대한 명세는 구체적이어야하며, 추상적인 문구를 배제하고 확실히 개발 방향을 명시할 것.\n"
        "4. 개발 명세서를 Spec Driven Development 기반으로 도출할 것.\n"
        "5. 위 내용으로 도출된 개발 명세서를 기반으로 개발 작업을 수행할 것.\n"
        "(단, Test Driven Development 방식으로 개발하는 것을 필히 준수해야함)\n\n"
        "## 세부 요구사항\n"
        "1. 사용자 : it 회사의 프로젝트을 수행하는 PM\n"
        "2. 관리자 : it 회사의 임원 및 PMO 조직\n"
        "3. 웹, 모바일에서 접속 가능\n"
        "4. 사용자는 프로젝트 정보를 입력한다. (프로젝트명, 프로젝트코드, 고객사, 설계자, 개발자, 프로젝트 일정)\n"
        "5. 관리자는 등록된 프로젝트와 일자를 관리한다.\n"
        "6. 사용자가 사용하기 편하게 해야 한다.\n"
        "7. 기본적으로 간트 차트 기능이 구현되어야 한다.\n\n"
        "이 요청은 PRD, atomic task breakdown, spec-driven development, TDD, web/mobile, "
        "frontend/backend 분리를 포함하므로 planner, architect, frontend, mobile, backend, reviewer "
        "같은 async subagent를 적절히 사용해서 진행하고, 최종적으로는 실행 가능한 코드 산출물까지 포함해라."
    ),
}

TEST_PROMPT_DETAILS = {
    "User/Profile": "장기 메모리 `user/profile` 저장, 조회, 재주입 경로를 검증합니다.",
    "Project/Context": "장기 메모리 `project/context` 저장과 이후 코드 생성 규칙 반영을 검증합니다.",
    "Domain Knowledge": "장기 메모리 `domain/knowledge` 누적 저장과 이후 재사용 경로를 검증합니다.",
    "Memory Correction": "잘못된 장기 메모리를 정정하고 최신 근거로 교체하는 정책을 검증합니다.",
    "Memory Extraction": "시스템 프롬프트 또는 스킬을 통해 장기 메모리와 도메인 지식을 추출·저장·재주입하는 구조가 실제로 있는지 검증합니다.",
    "SubAgent Lifecycle": "동적 SubAgent 생성, 상태 전이, 종료 정리까지의 lifecycle 기록을 검증합니다.",
    "Code+Review Test": "동시 async subagent 실행 후 한 응답 안에서 결과를 취합하는지 검증합니다.",
    "Blocked/Failed": "blocked 또는 failed 상태 감지와 alternate path 정책을 검증합니다.",
    "Loop Safety": "timeout, 무진전, tool 오류, safe stop 같은 복원력 정책을 검증합니다.",
    "Model Policy": "현재 모델, fallback, 제약사항이 설명 가능한지 검증합니다.",
    "Remember Agent": "remember subagent가 장기 메모리 후보 파일을 고르고 Human in the Loop 검토 대상으로 넘기는지 검증합니다.",
}

SCENARIO_PROMPT_DETAILS = {
    "Scenario_1 : PMS시스템 구성": "PMS 프로젝트형 요청을 입력해 planner, architect, frontend, mobile, backend, reviewer 분할과 실행 가능한 코드 산출까지 유도하는 시나리오 테스트입니다.",
}

BLOCKED_AFTER_SECONDS = 45.0
SUBAGENT_POLL_INTERVAL_SECONDS = 0.25
SUBAGENT_RUN_POLL_TIMEOUT_SECONDS = 0.2
ALTERNATE_ROLE_POLICY = {
    "coder": "debugger",
    "frontend": "reviewer",
    "backend": "reviewer",
    "planner": "architect",
    "architect": "reviewer",
    "mobile": "reviewer",
    "debugger": "reviewer",
    "researcher": "reviewer",
    "reviewer": "coder",
    "remember": "reviewer",
    "general": "reviewer",
}


def _create_query_workdir(root: Path | None = None) -> Path:
    """Create a per-query working directory rooted under the current project root."""
    base_root = (root or Path.cwd()).resolve()
    sessions_root = base_root / "query_sessions"
    sessions_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    candidate = sessions_root / stamp
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = sessions_root / f"{stamp}_{suffix:02d}"
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def _shutdown_runtime_components(components_obj) -> None:
    if not components_obj:
        return
    runtime = components_obj.get("subagent_runtime")
    if runtime is not None and hasattr(runtime, "shutdown_all"):
        try:
            runtime.shutdown_all()
        except Exception:
            logger.exception("Failed to shutdown previous subagent runtime")


def _agent_display_name(row: dict) -> str:
    agent_type = str(row.get("type", "subagent") or "subagent")
    ordinal = row.get("ordinal")
    if ordinal:
        return f"{agent_type} agent #{ordinal}"
    return f"{agent_type} agent"


def _prepare_query_runtime(workdir: Path):
    """Rebuild runtime components so one user query executes inside one workdir."""
    previous = st.session_state.get("agent_components")
    prev_workdir = str((previous or {}).get("working_dir", "") or "")
    workdir_str = str(workdir.resolve())
    if previous and prev_workdir == workdir_str:
        return previous

    _shutdown_runtime_components(previous)
    components_obj = create_runtime_components(
        custom_settings=settings,
        cwd=workdir,
    )
    st.session_state.agent_components = components_obj
    st.session_state["_active_query_workdir"] = workdir_str
    return components_obj


def _build_workdir_zip_bytes(workdir: str | Path | None) -> bytes | None:
    if not workdir:
        return None
    root = Path(workdir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            try:
                arcname = str(path.relative_to(root))
                zf.write(path, arcname=arcname)
            except Exception:
                logger.exception("Failed to add file to workdir zip: %s", path)
    buf.seek(0)
    return buf.getvalue()


def _read_workspace_file_bytes(workdir: str | Path | None, rel_path: str) -> bytes | None:
    if not workdir or not rel_path:
        return None
    root = Path(workdir).expanduser().resolve()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except Exception:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    try:
        return candidate.read_bytes()
    except Exception:
        logger.exception("Failed to read workspace file for download: %s", candidate)
        return None


def _get_cached_workdir_zip_bytes(workdir: str | Path | None) -> bytes | None:
    if not workdir:
        return None
    cache = st.session_state.setdefault("_workdir_zip_cache", {})
    key = str(Path(workdir).expanduser().resolve())
    if key not in cache:
        cache[key] = _build_workdir_zip_bytes(key)
    return cache.get(key)


def _workspace_has_artifacts(workdir: str | Path | None) -> bool:
    if not workdir:
        return False
    root = Path(workdir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return False
    return any(path.is_file() for path in root.rglob("*"))


def _remember_candidate_score(path: Path, root: Path) -> tuple[int, str]:
    rel = str(path.relative_to(root)).lower()
    name = path.name.lower()
    suffix = path.suffix.lower()
    score = 0
    reasons: list[str] = []
    if any(token in rel for token in ("prd", "spec", "architecture", "design", "requirements")):
        score += 120
        reasons.append("spec artifact")
    if any(token in rel for token in ("readme", "api", "contract", "schema", "gantt")):
        score += 90
        reasons.append("durable project context")
    if "/tests/" in rel or name.startswith("test_") or suffix in {".spec.ts", ".test.ts"}:
        score += 80
        reasons.append("behavior-encoding test")
    if suffix in {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml"}:
        score += 40
    if "/node_modules/" in rel or "/.git/" in rel or "__pycache__" in rel:
        score -= 500
    if path.stat().st_size > 200_000:
        score -= 50
    return score, ", ".join(reasons) or "important artifact"


def _select_remember_candidates(workdir: str | Path | None, limit: int = 10) -> list[dict]:
    if not workdir:
        return []
    root = Path(workdir).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []
    scored: list[tuple[int, dict]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            score, reason = _remember_candidate_score(path, root)
        except Exception:
            continue
        if score <= 0:
            continue
        rel = str(path.relative_to(root))
        scored.append((score, {"path": rel, "reason": reason, "bytes": path.stat().st_size}))
    scored.sort(key=lambda item: (-item[0], item[1]["path"]))
    return [item[1] for item in scored[:limit]]


def _parse_remember_candidates_from_history(subagent_history: list[dict], workdir: str | Path | None, limit: int = 10) -> list[dict]:
    if not subagent_history:
        return []
    root = Path(workdir).expanduser().resolve() if workdir else None
    remember_rows = [
        row for row in subagent_history
        if str(row.get("type", "")).lower() == "remember"
        and str(row.get("status", "") or row.get("durable_state", "")).lower() == "completed"
    ]
    if not remember_rows:
        return []
    text = str(remember_rows[-1].get("result_summary", "") or remember_rows[-1].get("live_output", "") or "")
    candidates: list[dict] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("-*0123456789. ").strip()
        if not line:
            continue
        path_match = re.search(r"([A-Za-z0-9_./-]+\.(?:md|txt|py|ts|tsx|js|jsx|json|ya?ml))", line)
        if not path_match:
            continue
        rel = path_match.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        reason = line.replace(rel, "").strip(" :-") or "remember agent recommended this artifact"
        size = 0
        if root is not None:
            path = root / rel
            if path.exists() and path.is_file():
                try:
                    size = path.stat().st_size
                except Exception:
                    size = 0
        candidates.append({"path": rel, "reason": reason, "bytes": size, "source": "remember_subagent"})
        if len(candidates) >= limit:
            break
    return candidates


def _render_live_remember_review() -> None:
    review = st.session_state.get("_pending_human_review")
    if not review or str(review.get("status", "")) != "pending":
        return
    candidates = review.get("candidates") or []
    workdir = str(review.get("workdir", "") or "")
    st.markdown("<div id='hitl-remember-review-anchor'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hitl-review-card'>"
        "<div class='hitl-review-title'>Action Required · Human In The Loop</div>"
        "<div class='hitl-review-text'>The remember subagent paused this turn for approval. "
        "Review the nominated files, approve the ones that should become long-term memory, then continue the same session. "
        "The final Main Agent answer is intentionally being held until this decision is completed.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.session_state.pop("_hitl_scroll_pending", False):
        components.html(
            """
            <script>
            const scrollToAnchor = () => {
              const anchor = window.parent.document.getElementById('hitl-remember-review-anchor');
              if (anchor) {
                anchor.scrollIntoView({behavior: 'smooth', block: 'center'});
              }
            };
            setTimeout(scrollToAnchor, 50);
            setTimeout(scrollToAnchor, 250);
            </script>
            """,
            height=0,
            scrolling=False,
        )
    if workdir:
        st.caption(f"Workspace: {workdir}")
    if not candidates:
        st.warning("No remember candidates were produced.")
        return
    for idx, row in enumerate(candidates):
        file_cols = st.columns([6, 2])
        with file_cols[0]:
            st.markdown(
                f"**{_escape_html(str(row.get('path', '')))}**  \n"
                f"<span style='color:#64748b;font-size:.86em'>{_escape_html(str(row.get('reason', '')))}</span>",
                unsafe_allow_html=True,
            )
        with file_cols[1]:
            file_bytes = _read_workspace_file_bytes(workdir, str(row.get("path", "") or ""))
            if file_bytes:
                st.download_button(
                    "Download",
                    data=file_bytes,
                    file_name=Path(str(row.get("path", "artifact"))).name,
                    mime="application/octet-stream",
                    key=f"live_remember_download_{idx}_{row.get('path', '')}",
                    use_container_width=True,
                )
    default_selection = [row["path"] for row in candidates[: min(5, len(candidates))]]
    with st.form("live_remember_review_form"):
        selected_paths = st.multiselect(
            "Approve files for long-term memory",
            options=[row["path"] for row in candidates],
            default=review.get("selected_paths", default_selection),
            format_func=lambda p: next(
                (
                    f"{row['path']} · {row['reason']}"
                    for row in candidates if row["path"] == p
                ),
                p,
            ),
        )
        target_layer = st.selectbox(
            "Memory Layer",
            options=["project/context", "domain/knowledge", "user/profile"],
            index=["project/context", "domain/knowledge", "user/profile"].index(
                str(review.get("target_layer", "project/context"))
            ),
        )
        approve_col, reject_col = st.columns(2)
        with approve_col:
            approve = st.form_submit_button("Approve and Continue", use_container_width=True)
        with reject_col:
            reject = st.form_submit_button("Reject and Continue", use_container_width=True)
    if approve:
        stored_ids = _store_approved_memory_files(workdir, selected_paths, target_layer)
        st.session_state["_human_review_resolution"] = {
            "approved": True,
            "selected_paths": list(selected_paths),
            "target_layer": target_layer,
            "stored_ids": stored_ids,
        }
        st.session_state.pop("_pending_human_review", None)
        st.rerun()
    if reject:
        st.session_state["_human_review_resolution"] = {
            "approved": False,
            "selected_paths": [],
            "target_layer": target_layer,
            "stored_ids": [],
        }
        st.session_state.pop("_pending_human_review", None)
        st.rerun()


def _remember_layer_to_category(layer: str) -> MemoryCategory:
    mapping = {
        "project/context": MemoryCategory.PROJECT_CONTEXT,
        "domain/knowledge": MemoryCategory.DOMAIN_KNOWLEDGE,
        "user/profile": MemoryCategory.USER_PREFERENCES,
    }
    return mapping[layer]


def _store_approved_memory_files(workdir: str, selected_paths: list[str], layer: str) -> list[str]:
    root = Path(workdir).expanduser().resolve()
    ltm = LongTermMemoryMiddleware(memory_dir=str(settings.memory_dir))
    category = _remember_layer_to_category(layer)
    stored_ids: list[str] = []
    for rel_path in selected_paths[:10]:
        path = root / rel_path
        if not path.exists() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        trimmed = content[:15000]
        durable_payload = f"[remember_agent]\nfile: {rel_path}\nlayer: {layer}\n\n{trimmed}"
        record_id = ltm._state_store.store_memory(
            layer=layer,
            content=durable_payload,
            scope_key=root.name,
            source="remember_agent_human_approved",
            tags=["remember_agent", rel_path],
        )
        ltm.store.store(trimmed, category, {"source": "remember_agent_human_approved", "path": rel_path})
        stored_ids.append(record_id)
    return stored_ids


# ─────────────────────────────────────────────────────────
#  Mermaid helpers
# ─────────────────────────────────────────────────────────

def _clean_label_text(text: str) -> str:
    """Sanitise *text* before it is placed inside a Mermaid label."""
    import re
    t = (
        text
        .replace("\\", "")
        .replace('"', "'")
        .replace("\n", " ")
        .replace("\r", "")
        .replace("#", " ")
        .replace(";", ",")
        .replace("|", " ")
        .replace("<", " ")
        .replace(">", " ")
        .replace("{", " ")
        .replace("}", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("[", " ")
        .replace("]", " ")
        .replace("`", "'")
        .replace("$", " ")
        .replace("&", "+")
        .replace("~", " ")
        .replace("=", " ")
        .replace("--", " ")  # Mermaid edge syntax
        .replace("->", " ")  # Mermaid edge syntax
        .replace("=>", " ")  # Mermaid edge syntax
        .replace(":", " ")   # Mermaid node description separator
    )
    return re.sub(r"\s+", " ", t).strip()


def _ascii_label(text: str) -> str:
    """Encode non-ASCII chars as HTML entities while keeping source ASCII-only."""
    return "".join(ch if ord(ch) < 128 else f"&#{ord(ch)};" for ch in text)


def _esc(text: str) -> str:
    """Sanitise *text* so it can be safely placed inside a Mermaid label
    (both ``"node label"`` and ``|"edge label"|``).

    Mermaid source is kept ASCII-only to avoid browser btoa() failures, but
    non-ASCII preview text is preserved through HTML numeric entities.
    """
    t = _clean_label_text(text)
    # Mermaid may call window.btoa() internally, which fails on non-Latin1 text.
    # Keep the diagram source ASCII-only; browsers render entities as text.
    return _ascii_label(t)


def _escape_html(text: str) -> str:
    """Escape HTML special chars (for Event Feed entries)."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\n", " ")
        .replace("\r", "")
    )


def _escape_bubble_html(text: str) -> str:
    """Escape assistant/user message HTML while preserving line breaks."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\r", "")
        .replace("\n", "<br>")
    )


def _bubble_width_style(text: str, role: str) -> str:
    """Return a width style that loosely tracks message length."""
    width = _bubble_width_percent(text)
    if role == "user":
        margin = "margin:0 0 8px auto;"
    else:
        margin = "margin:0 auto 8px 0;"
    return f"display:inline-block;width:fit-content;max-width:{width}%;{margin}"


def _bubble_width_percent(text: str) -> int:
    """Return a rough width percentage for chat/analysis alignment."""
    plain = re.sub(r"\s+", " ", (text or "").replace("<br>", "\n")).strip()
    lines = max(1, plain.count("\n") + 1)
    length = len(plain)
    if length <= 24:
        width = 30
    elif length <= 60:
        width = 42
    elif length <= 120:
        width = 56
    elif length <= 220:
        width = 70
    else:
        width = 86
    if lines >= 4:
        width = min(90, width + 8)
    return width


def _bubble_wrap_open(role: str) -> str:
    if role == "user":
        return "<div style='width:100%;text-align:right'>"
    return "<div style='width:100%;text-align:left'>"


def _analysis_column_weights(text: str) -> list[float]:
    width = _bubble_width_percent(text)
    return [float(width), float(max(8, 100 - width))]


def _edge_label(text: str, fallback: str, limit: int = 28) -> str:
    """Return a short Mermaid-safe edge label."""
    safe_text = _clean_label_text(text or "")
    if not safe_text:
        return fallback
    if len(safe_text) > limit:
        safe_text = safe_text[:limit].rstrip() + "..."
    safe = _ascii_label(safe_text)
    if not safe:
        return fallback
    return safe


def _add_tooltip(tooltips: dict[str, str], label: str, full_text: str) -> None:
    """Register tooltip by both raw entity label and rendered text label."""
    import html as _html
    tooltips[label] = full_text
    tooltips[_html.unescape(label)] = full_text


def _build_mermaid(
    agents: list[dict],
    is_working: bool,
    prompt_text: str = "",
    result_text: str = "",
    model_name: str = "",
) -> tuple[str, dict[str, str]]:
    """Return a (mermaid_definition, tooltips) tuple.

    Edge labels show short sanitised prompt/result previews.
    Full prompt/result text is exposed through browser tooltips.

    Nodes:
      U  = User  (stadium shape)
      M  = Main Agent  (rectangle)
      S0 … Sn = SubAgents  (rectangle, coloured by status)
    """
    has_result = bool(result_text)
    lines = ["graph LR"]

    # ── User ──────────────────────────────────────────────
    lines.append('    U(["User"])')

    # ── Main Agent ────────────────────────────────────────
    if has_result:
        m_detail = "Done"
        if model_name:
            safe_model = _esc(model_name[:20])
            m_detail += f" {safe_model}"
    elif is_working:
        m_detail = "Processing"
    else:
        m_detail = "Idle"
    lines.append(f'    M["Main Agent<br/><small>{m_detail}</small>"]')

    # ── User → Main edge (prompt은 짧은 요약만) ──────────
    if prompt_text:
        safe_p = _edge_label(prompt_text, "user prompt", limit=24)
        lines.append(f'    U -->|"{safe_p}"| M')
    else:
        lines.append("    U --> M")

    # ── SubAgents ─────────────────────────────────────────
    for i, a in enumerate(agents):
        display_name = str(a.get("display_name") or f"{a['type']} agent")
        detail = a["status"]
        if a.get("last_action"):
            detail += f" · {a['last_action']}"
        if a.get("task_id"):
            detail += f" {a['task_id'][:8]}"
        if a.get("elapsed"):
            detail += f" {a['elapsed']}s"
        endpoint = _clean_label_text(str(a.get("endpoint", "") or ""))
        pid = str(a.get("pid", "") or "").strip()
        model = _clean_label_text(str(a.get("model", "") or ""))

        nid = f"S{i}"
        label = f"{_esc(display_name)}<br/><small>{detail}</small>"
        if endpoint:
            label += f"<br/><small>{_esc(endpoint)}</small>"
        if pid:
            label += f"<br/><small>pid {_esc(pid)}</small>"
        if model:
            label += f"<br/><small>{_esc(model[:28])}</small>"
        lines.append(f'    {nid}["{label}"]')

        prompt_label = _edge_label(a.get("query", ""), f"{a['type']} task")
        result_label = _edge_label(a.get("result_summary", ""), "result")

        # Main → SubAgent edge: prompt preview
        lines.append(f'    M -->|"{prompt_label}"| {nid}')

        # SubAgent → Main feedback: result/error preview
        if a["status"] == "completed":
            lines.append(f'    {nid} -.->|"{result_label}"| M')
        elif a["status"] == "failed":
            error_label = _edge_label(a.get("result_summary", ""), "failed")
            lines.append(f'    {nid} -.->|"{error_label}"| M')

    # ── Main Agent → User (완료 시) ──────────────────────
    if has_result:
        response_label = _edge_label(result_text, "response", limit=32)
        lines.append(f'    M ==>|"{response_label}"| U')

    # ── Styles ────────────────────────────────────────────
    lines.append(
        "    style U fill:#eff6ff,stroke:#3b82f6,"
        "stroke-width:2px,color:#1e40af"
    )
    if has_result:
        lines.append(
            "    style M fill:#f0fdf4,stroke:#22c55e,"
            "stroke-width:2px,color:#166534"
        )
    elif is_working:
        lines.append(
            "    style M fill:#dcfce7,stroke:#16a34a,"
            "stroke-width:3px,color:#166534"
        )
    else:
        lines.append(
            "    style M fill:#f0fdf4,stroke:#22c55e,"
            "stroke-width:2px,color:#166534"
        )

    _STATUS_STYLE = {
        "pending":   "fill:#fffbeb,stroke:#f59e0b,stroke-width:2px,color:#92400e",
        "running":   "fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#166534",
        "completed": "fill:#f8fafc,stroke:#94a3b8,stroke-width:2px,color:#475569",
        "cancelled": "fill:#fff7ed,stroke:#f97316,stroke-width:2px,color:#9a3412",
        "failed":    "fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#991b1b",
    }
    for i, a in enumerate(agents):
        s = _STATUS_STYLE.get(a["status"], _STATUS_STYLE["pending"])
        lines.append(f"    style S{i} {s}")

    # Only the currently active nodes should pulse. Completed nodes stay static.
    lines.append("    classDef activeNode stroke-width:3px")
    active_nodes: list[str] = []
    if is_working and not has_result:
        active_nodes.append("M")
    active_nodes.extend(f"S{i}" for i, a in enumerate(agents) if a["status"] == "running")
    if active_nodes:
        lines.append(f"    class {','.join(active_nodes)} activeNode")

    # Build tooltip map: truncated edge-label text → full text
    # JS looks up edge labels by their displayed text, not node IDs
    tooltips: dict[str, str] = {}
    if prompt_text:
        safe_p = _edge_label(prompt_text, "user prompt", limit=24)
        _add_tooltip(tooltips, safe_p, prompt_text)
    if result_text:
        response_label = _edge_label(result_text, "response", limit=32)
        _add_tooltip(tooltips, response_label, result_text)
    for i, a in enumerate(agents):
        prompt_label = _edge_label(a.get("query", ""), f"{a['type']} task")
        if a.get("query"):
            _add_tooltip(tooltips, prompt_label, a["query"])

        if a.get("result_summary"):
            result_label = _edge_label(a.get("result_summary", ""), "result")
            _add_tooltip(tooltips, result_label, a["result_summary"])

        if a.get("task_id"):
            task_meta = f"task_id: {a['task_id']}"
            if a.get("run_id"):
                task_meta += f"\nrun_id: {a['run_id']}"
            if a.get("endpoint"):
                task_meta += f"\nendpoint: {a['endpoint']}"
            if a.get("pid"):
                task_meta += f"\npid: {a['pid']}"
            if a.get("model"):
                task_meta += f"\nmodel: {a['model']}"
            _add_tooltip(tooltips, _edge_label(a.get("query", ""), f"{a['type']} task"), (a.get("query", "") + "\n\n" + task_meta).strip())

    return "\n".join(lines), tooltips


def _build_page_html(
    mermaid_def: str,
    events: list[dict],
    is_working: bool,
    tooltips: dict[str, str] | None = None,
    render_id: int = 0,
) -> str:
    """Build a self-contained HTML page with Mermaid chart + Event Feed.

    This HTML is rendered inside an iframe via Streamlit's st.iframe() API.
    Mermaid JS is loaded from jsDelivr CDN and renders entirely client-side.
    """
    # Build event feed HTML
    evt_parts: list[str] = []
    for e in events:
        css = e.get("css_class", "")
        ts = e.get("time", "")
        evt_parts.append(
            f'<div class="ev {css}">'
            f'<span class="ts">{ts}</span> '
            f'{e["icon"]} {e["text"]}'
            f"</div>"
        )
    events_html = "\n".join(evt_parts)

    # Build JSON map for edge-label tooltips.
    # Sanitise values: they end up as HTML title attributes AND live inside
    # a <script> block, so we must neutralise </script> injection and
    # control characters.  json.dumps with ensure_ascii=True is safest.
    import json as _json
    _safe_tips: dict[str, str] = {}
    for _k, _v in (tooltips or {}).items():
        _sv = _v.replace("\r", "").replace("\x00", "")
        # Prevent </script> injection
        _sv = _sv.replace("</", "<\\/")
        _safe_tips[_k] = _sv
    tooltip_json = _json.dumps(_safe_tips, ensure_ascii=True)
    mermaid_json = _json.dumps(
        mermaid_def.replace("\r", "").replace("\x00", "").replace("</", "<\\/"),
        ensure_ascii=True,
    )

    # Optional CSS pulse for currently active nodes only.
    pulse_css = """
    @keyframes active-node-pulse {
        0%,100% { filter: drop-shadow(0 0 2px rgba(22,163,74,.20)); }
        50%     { filter: drop-shadow(0 0 16px rgba(22,163,74,.75)); }
    }
    .mermaid .activeNode rect,
    .mermaid .activeNode path,
    .mermaid .activeNode polygon {
        animation: active-node-pulse 1.35s ease-in-out infinite;
    }
    """ if is_working else ""

    return f"""<!DOCTYPE html>
<html data-render-id="{render_id}"><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#fff;color:#1e293b;padding:16px 12px 8px}}

/* Mermaid chart */
.mermaid{{text-align:center;min-height:100px;margin-bottom:8px}}
.mermaid svg{{max-width:100%}}
{pulse_css}

/* Event Feed */
.evts{{padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;
  border-radius:10px;max-height:175px;overflow-y:auto;scroll-behavior:smooth}}
.evts-t{{font-size:10.5px;font-weight:700;color:#475569;
  margin-bottom:5px;letter-spacing:.3px}}
.ev{{font-size:10.5px;padding:2px 0 2px 8px;color:#334155;
  border-left:2px solid #e2e8f0;margin-bottom:2px;line-height:1.45}}
.ev.subagent{{border-left-color:#a78bfa}}
.ev.tool{{border-left-color:#60a5fa}}
.ev.memory{{border-left-color:#34d399}}
.ev.done{{border-left-color:#22c55e}}
.ev.error{{border-left-color:#ef4444}}
.ev .ts{{color:#94a3b8;font-family:monospace;font-size:9px;margin-right:4px}}
.mermaid-error{{display:none;margin:8px 0 10px;padding:10px 12px;
  border:1px solid #fecaca;border-radius:10px;background:#fef2f2;color:#991b1b;
  font-size:11px;line-height:1.45;text-align:left;white-space:pre-wrap}}
.mermaid-error-title{{font-weight:700;margin-bottom:6px}}
.mermaid-error pre{{margin-top:6px;max-height:180px;overflow:auto;
  color:#7f1d1d;background:#fff1f2;border:1px solid #fecdd3;border-radius:6px;
  padding:8px;font-size:10px;white-space:pre-wrap}}
.edge-tooltip{{position:fixed;display:none;z-index:9999;max-width:min(760px,92vw);
  max-height:260px;min-width:min(340px,72vw);padding:0;border:1px solid #cbd5e1;
  border-radius:10px;background:#0f172a;color:#f8fafc;box-shadow:0 12px 32px rgba(15,23,42,.22);
  font-size:11px;line-height:1.45;text-align:left;pointer-events:auto;overflow:hidden}}
.edge-tooltip-content{{max-height:228px;overflow-y:auto;padding:10px 12px 8px;
  white-space:pre-wrap}}
.edge-tooltip-hint{{display:none;padding:6px 12px;border-top:1px solid rgba(203,213,225,.18);
  background:linear-gradient(180deg, rgba(15,23,42,.88), rgba(15,23,42,1));
  color:#cbd5e1;font-size:10px;letter-spacing:.2px}}
.edge-tooltip.scrollable .edge-tooltip-hint{{display:block}}
.edge-tooltip-content::-webkit-scrollbar{{width:10px}}
.edge-tooltip-content::-webkit-scrollbar-track{{background:rgba(148,163,184,.12);border-radius:999px}}
.edge-tooltip-content::-webkit-scrollbar-thumb{{background:rgba(148,163,184,.55);border-radius:999px}}
.edge-tooltip-content{{scrollbar-width:thin;scrollbar-color:rgba(148,163,184,.55) rgba(148,163,184,.12)}}
</style>
</head>
<body>

<pre class="mermaid">
{mermaid_def}
</pre>
<div id="mermaid-error" class="mermaid-error"></div>
<div id="edge-tooltip" class="edge-tooltip">
  <div id="edge-tooltip-content" class="edge-tooltip-content"></div>
  <div id="edge-tooltip-hint" class="edge-tooltip-hint">Scroll for more</div>
</div>

<div class="evts" id="ev">
  {events_html}
</div>

<script>
mermaid.initialize({{
  startOnLoad:false,
  theme:'base',
  themeVariables:{{
    fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
    fontSize:'13px',
    lineColor:'#94a3b8',
    edgeLabelBackground:'#ffffff'
  }},
  flowchart:{{
    useMaxWidth:true,
    htmlLabels:true,
    curve:'basis',
    nodeSpacing:50,
    rankSpacing:80
  }}
}});
document.getElementById('ev').scrollTop=
  document.getElementById('ev').scrollHeight;

// ── Tooltip injection: hover on truncated edge labels to see full text ──
var _tooltips = {tooltip_json};
var _mermaidSource = {mermaid_json};
function _showMermaidError(err) {{
  var detail = err && (err.stack || err.message || String(err)) || "Unknown Mermaid error";
  console.error("[CodingAgent Mermaid] render failed", err);
  console.error("[CodingAgent Mermaid] source:\\n" + _mermaidSource);
  var box = document.getElementById("mermaid-error");
  if(box) {{
    box.style.display = "block";
    box.innerHTML =
      '<div class="mermaid-error-title">Mermaid rendering failed. Open browser console for full logs.</div>' +
      '<div><b>Error</b></div><pre></pre>' +
      '<div><b>Mermaid source</b></div><pre></pre>';
    var pres = box.querySelectorAll("pre");
    pres[0].textContent = detail;
    pres[1].textContent = _mermaidSource;
  }}
}}
window.addEventListener("error", function(event) {{
  if(String(event.message || "").toLowerCase().includes("mermaid")) {{
    _showMermaidError(event.error || event.message);
  }}
}});
mermaid.run().then(function(){{
  var tipBox = document.getElementById('edge-tooltip');
  var tipContent = document.getElementById('edge-tooltip-content');
  var hideTimer = null;
  var tooltipPinned = false;
  function cancelHide() {{
    if(hideTimer) {{
      clearTimeout(hideTimer);
      hideTimer = null;
    }}
  }}
  function scheduleHide() {{
    cancelHide();
    hideTimer = setTimeout(function() {{
      if(tipBox) {{
        tipBox.style.display = 'none';
        tipBox.classList.remove('scrollable');
      }}
      tooltipPinned = false;
    }}, 120);
  }}
  function updateScrollableHint() {{
    if(!tipBox || !tipContent) return;
    var scrollable = tipContent.scrollHeight > tipContent.clientHeight + 4;
    tipBox.classList.toggle('scrollable', scrollable);
  }}
  function moveTip(event) {{
    if(!tipBox) return;
    var x = Math.min(event.clientX + 14, window.innerWidth - tipBox.offsetWidth - 12);
    var y = Math.min(event.clientY + 14, window.innerHeight - tipBox.offsetHeight - 12);
    tipBox.style.left = Math.max(12, x) + 'px';
    tipBox.style.top = Math.max(12, y) + 'px';
  }}
  if(tipBox) {{
    tipBox.addEventListener('mouseenter', function() {{
      tooltipPinned = true;
      cancelHide();
    }});
    tipBox.addEventListener('mouseleave', function() {{
      tooltipPinned = false;
      scheduleHide();
    }});
  }}
  document.querySelectorAll('.edgeLabel span, .edgeLabel p, .edgeLabel div, .edgeLabel foreignObject span').forEach(function(el){{
    var txt = (el.textContent||'').trim();
    if(_tooltips[txt]){{
      el.dataset.fullTooltip = _tooltips[txt];
      el.style.cursor = 'help';
      el.addEventListener('mouseenter', function(event) {{
        if(!tipBox) return;
        cancelHide();
        if(tipContent) {{
          tipContent.textContent = el.dataset.fullTooltip || '';
          tipContent.scrollTop = 0;
        }}
        tipBox.style.display = 'block';
        moveTip(event);
        updateScrollableHint();
      }});
      el.addEventListener('mousemove', function(event) {{
        if(!tooltipPinned) moveTip(event);
      }});
      el.addEventListener('mouseleave', function() {{
        scheduleHide();
      }});
    }}
  }});
}}).catch(_showMermaidError);
</script>
</body></html>"""


def _build_prewarm_html() -> str:
    return _build_page_html("graph LR\nA[Warmup]-->B[Ready]", [], False, {}, render_id=0)


def _render_mermaid(
    placeholder,
    mermaid_def: str,
    events: list[dict],
    is_working: bool,
    num_agents: int = 0,
    tooltips: dict[str, str] | None = None,
) -> None:
    """Render Mermaid flowchart + event feed inside an iframe."""
    h = max(520, 320 + num_agents * 90 + min(len(events), 24) * 12)
    st.session_state["_mermaid_render_seq"] = (
        st.session_state.get("_mermaid_render_seq", 0) + 1
    )
    render_id = st.session_state["_mermaid_render_seq"]
    html = _build_page_html(
        mermaid_def,
        events,
        is_working,
        tooltips=tooltips,
        render_id=render_id,
    )
    print(
        "[CodingAgent Mermaid] render",
        render_id,
        "working=",
        is_working,
        "agents=",
        num_agents,
        "events=",
        len(events),
        flush=True,
    )
    placeholder.empty()
    with placeholder.container():
        components.html(html, height=h, scrolling=True)


def _synthesize_subagent_results(agents: list[dict]) -> str:
    """Fallback synthesis when the supervisor cannot do one more aggregation turn."""
    completed = []
    failed = []
    blocked = []
    for row in agents:
        status = str(row.get("status", "") or row.get("durable_state", "")).lower()
        item = {
            "type": str(row.get("type", "subagent")),
            "summary": str(row.get("result_summary", "") or row.get("live_output", "") or "").strip(),
            "endpoint": str(row.get("endpoint", "") or ""),
            "pid": row.get("pid"),
        }
        if status == "completed":
            completed.append(item)
        elif status == "failed":
            failed.append(item)
        elif status == "blocked":
            blocked.append(item)

    lines = []
    if completed:
        lines.append("SubAgent completed results:")
        for item in completed:
            meta = item["endpoint"]
            if item["pid"]:
                meta = f"{meta}, pid {item['pid']}" if meta else f"pid {item['pid']}"
            summary = item["summary"] or "(no result content)"
            lines.append(f"- {item['type']} [{meta or 'local'}]: {summary}")
    if failed:
        lines.append("")
        lines.append("Failed subagents:")
        for item in failed:
            lines.append(f"- {item['type']}: {item['summary'] or '(no error detail)'}")
    if blocked:
        lines.append("")
        lines.append("Blocked subagents:")
        for item in blocked:
            lines.append(f"- {item['type']}: {item['summary'] or '(no blocked detail)'}")
    if not lines:
        return "No completed SubAgent result was available to synthesize."
    return "\n".join(lines)


def _build_completed_subagent_report(agents: list[dict]) -> str:
    lines = []
    for row in agents:
        status = str(row.get("status", "") or row.get("durable_state", "")).lower()
        if status != "completed":
            continue
        agent_type = str(row.get("type", "subagent"))
        endpoint = str(row.get("endpoint", "") or "")
        pid = row.get("pid")
        model = str(row.get("model", "") or "")
        result = str(row.get("result_summary", "") or row.get("live_output", "") or "").strip()
        if not result:
            result = "(no final result captured)"
        meta = []
        if endpoint:
            meta.append(endpoint)
        if pid:
            meta.append(f"pid {pid}")
        if model:
            meta.append(f"model {model}")
        meta_text = ", ".join(meta) if meta else "local runtime"
        display_name = _agent_display_name(row)
        lines.append(f"- {display_name} [{meta_text}]\n  {result}")
    return "\n".join(lines) if lines else "No completed SubAgent results were captured."


def _capture_subagent_history_snapshot(
    tracked_agents: list[dict],
    state_store,
) -> list[dict]:
    """Persist a query-local SubAgent history snapshot for later UI rendering.

    The live UI uses `tracked_agents`, which is ephemeral to a single Streamlit
    execution. To avoid losing history after cleanup/rerun, store a merged view
    with any durable lifecycle rows/events that can be resolved by task_id.
    """
    rows: list[dict] = []
    for tracked in tracked_agents:
        snapshot = dict(tracked)
        snapshot.setdefault("result_summary", "")
        snapshot.setdefault("live_output", "")
        snapshot.setdefault("task_id", "")
        snapshot.setdefault("run_id", "")
        snapshot.setdefault("endpoint", "")
        snapshot.setdefault("pid", None)
        snapshot["lifecycle_events"] = []
        snapshot["durable_state"] = snapshot.get("status", "")
        task_id = str(snapshot.get("task_id", "") or "").strip()
        if state_store is not None and task_id:
            try:
                durable = state_store.find_subagent_by_task_id(task_id)
                if durable:
                    agent_id = str(durable.get("agent_id", "") or "")
                    snapshot["agent_id"] = agent_id
                    snapshot["durable_state"] = str(durable.get("state", "") or snapshot["durable_state"])
                    snapshot["task_summary"] = str(durable.get("task_summary", "") or snapshot.get("query", ""))
                    snapshot["endpoint"] = str(durable.get("endpoint", "") or snapshot.get("endpoint", ""))
                    snapshot["pid"] = durable.get("pid") or snapshot.get("pid")
                    snapshot["model"] = str(durable.get("model", "") or snapshot.get("model", ""))
                    snapshot["error"] = str(durable.get("error", "") or "")
                    if agent_id:
                        snapshot["lifecycle_events"] = state_store.list_subagent_events(agent_id)
            except Exception:
                logger.exception("Failed to capture durable SubAgent history for task %s", task_id)
        rows.append(snapshot)
    return rows


def _resume_async_monitoring(
    graph_ph,
    result_ph,
    subagent_ph=None,
) -> bool:
    """Resume a turn after the main answer is visible and only async tasks remain.

    This decouples "main answer completed" from "all async subagents completed".
    The UI reruns immediately once the main answer is available, then this
    monitor path keeps polling subagent health/output until final aggregation.
    """
    comp = st.session_state.agent_components
    live_turn = st.session_state.get("_live_turn_state") or {}
    if not comp or not live_turn or not st.session_state.get("_monitor_async_after_answer"):
        return False

    agent = comp["agent"]
    fallback_mw = comp["fallback_middleware"]
    loop_guard = comp["loop_guard"]
    subagent_runtime = comp.get("subagent_runtime")
    state_store = comp.get("state_store")
    prompt = str(live_turn.get("prompt", "") or "")
    final_text = str(live_turn.get("result_text", "") or "")
    current_model = str(live_turn.get("model", "") or fallback_mw.current_model or "unknown")
    events = list(live_turn.get("events") or [])
    tracked_agents = list(live_turn.get("agents") or [])
    _sa_role_counters: dict[str, int] = {}
    for row in tracked_agents:
        agent_type = str(row.get("type", "general") or "general")
        try:
            ordinal = int(row.get("ordinal") or 0)
        except Exception:
            ordinal = 0
        _sa_role_counters[agent_type] = max(_sa_role_counters.get(agent_type, 0), ordinal)
    thread_id = str(st.session_state.get("_last_query_thread_id", "") or "")
    working_dir = str(st.session_state.get("_active_query_workdir", "") or Path.cwd())
    config = {"configurable": {"thread_id": thread_id}} if thread_id else {}

    def _capture_async_tasks() -> list[dict]:
        tracker = comp.get("async_task_tracker")
        if not tracker or not thread_id:
            return []
        try:
            rows = tracker.get_tasks(thread_id)
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    def _sync_live(working: bool) -> None:
        st.session_state["_live_turn_state"] = {
            "prompt": prompt,
            "result_text": final_text,
            "model": current_model,
            "events": list(events),
            "agents": _capture_subagent_history_snapshot(tracked_agents, state_store),
            "working": working,
            "hold_final_answer": bool(tracked_agents) or bool(st.session_state.get("_pending_human_review")),
        }

    def _evt(icon: str, text: str, css: str = "") -> None:
        ts = time.strftime("%H:%M:%S")
        events.append({"icon": icon, "text": text, "css_class": css, "time": ts})
        _sync_live(True)

    def _refresh(working: bool) -> None:
        agents = list(tracked_agents)
        _sync_live(working)
        mermaid_def, tips = _build_mermaid(
            agents,
            working,
            prompt,
            result_text=final_text,
            model_name=current_model,
        )
        _render_mermaid(graph_ph, mermaid_def, events, working, num_agents=len(agents), tooltips=tips)

        model_html = (
            f"<div class='agent-bubble-model'>🧠 {_escape_html(current_model)}</div>"
            if current_model else ""
        )
        result_ph.markdown(
            f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{_bubble_width_style(final_text, 'agent')}'>"
            f"{_escape_bubble_html(final_text)}{model_html}</div></div>",
            unsafe_allow_html=True,
        )

        if subagent_ph is not None:
            rows = [
                a for a in tracked_agents
                if a.get("task_id")
                or a.get("live_output")
                or a.get("result_summary")
                or a.get("endpoint")
                or a.get("status") in {"running", "blocked", "failed", "completed", "cancelled"}
            ]
            if not rows:
                subagent_ph.empty()
            else:
                parts = [
                    "<div style='margin:8px 0 14px'>"
                    "<div style='font-size:.78em;font-weight:700;color:#64748b;letter-spacing:.35px;margin-bottom:6px'>"
                    "SubAgent Streaming Output</div>"
                ]
                for row in rows:
                    endpoint = row.get("endpoint") or ""
                    pid = row.get("pid")
                    model = row.get("model") or ""
                    status = row.get("status", "running")
                    content = row.get("live_output") or row.get("result_summary") or "waiting for output..."
                    parts.append(
                        "<div style='background:#fff;border:1px solid #bbf7d0;border-radius:14px;"
                        "padding:10px 12px;margin-bottom:8px;box-shadow:0 4px 14px rgba(22,163,74,.05)'>"
                        f"<div style='font-size:.8em;font-weight:700;color:#166534;margin-bottom:4px'>{_escape_html(_agent_display_name(row))}</div>"
                        f"<div style='font-size:.72em;color:#64748b;margin-bottom:6px'>{_escape_html(str(endpoint))}"
                        f"{f'<br>pid {pid}' if pid else ''}"
                        f"{f'<br>model { _escape_html(str(model)) }' if model else ''} · {_escape_html(str(status))}</div>"
                        f"<div style='font-size:.88em;color:#14532d;white-space:pre-wrap;max-height:180px;overflow-y:auto'>{_escape_bubble_html(str(content))}</div>"
                        "</div>"
                    )
                parts.append("</div>")
                subagent_ph.markdown("".join(parts), unsafe_allow_html=True)

    def _find_tracked_by_task_id(task_id: str) -> int | None:
        if not task_id:
            return None
        for idx, agent_row in enumerate(tracked_agents):
            if str(agent_row.get("task_id", "")) == task_id:
                return idx
        return None

    def _drain_runtime_events() -> None:
        if subagent_runtime is None or not hasattr(subagent_runtime, "drain_events"):
            return
        for event in subagent_runtime.drain_events():
            host = _escape_html(str(event.get("host") or "127.0.0.1"))
            port = _escape_html(str(event.get("port") or ""))
            pid = event.get("pid")
            name = _escape_html(str(event.get("name") or "subagent"))
            etype = str(event.get("type") or "")
            endpoint = f"{host}:{port}" if port else host
            pid_line = f"<br>pid {pid}" if pid else ""
            if etype == "spawned":
                _evt("🚀", f"Spawned <b>{name}</b> on <b>{endpoint}</b>{pid_line}", "subagent")
            elif etype == "healthy":
                _evt("✅", f"<b>{name}</b> healthy on <b>{endpoint}</b>{pid_line}", "subagent")
            elif etype == "attached":
                _evt("🔌", f"Attached to <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent")
            elif etype == "reused":
                _evt("♻️", f"Reusing <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent")
            elif etype == "stopping":
                _evt("🧹", f"Stopping <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent")
            elif etype == "stopped":
                _evt("🧹", f"Stopped <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent")

    def _sync_async_tasks_from_tracker() -> list[dict]:
        rows = _capture_async_tasks()
        for row in rows:
            task_id = str(row.get("task_id", "") or "")
            idx = _find_tracked_by_task_id(task_id)
            if idx is None:
                agent_type = str(row.get("agent_type", "general") or "general")
                ordinal = _sa_role_counters.get(agent_type, 0) + 1
                _sa_role_counters[agent_type] = ordinal
                tracked_agents.append(
                    {
                        "id": f"tracker_{task_id[:12] or len(tracked_agents)}",
                        "type": agent_type,
                        "ordinal": ordinal,
                        "display_name": f"{agent_type} agent #{ordinal}",
                        "status": "running",
                        "last_action": "tracker",
                        "elapsed": "",
                        "query": "",
                        "task_id": task_id,
                        "run_id": str(row.get("run_id", "") or ""),
                        "model": "",
                        "started_at": time.time(),
                        "endpoint": "",
                        "pid": None,
                        "live_output": "",
                        "result_summary": "",
                        "last_progress_at": time.time(),
                        "alternate_attempted": False,
                    }
                )
                idx = len(tracked_agents) - 1
                _evt("🛰️", f"Tracker discovered async task for <b>{_escape_html(str(row.get('agent_type', 'general')))}</b>", "subagent")
            if idx is None:
                continue
            local_status = str(tracked_agents[idx].get("status", "")).lower()
            tracked_agents[idx]["run_id"] = str(row.get("run_id", "") or tracked_agents[idx].get("run_id", ""))
            status = str(row.get("status", "")).lower()
            if local_status in {"blocked", "completed", "failed", "cancelled"} and status == "running":
                continue
            if status in {"success", "completed"}:
                tracked_agents[idx]["status"] = "completed"
            elif status in {"error", "failed"}:
                tracked_agents[idx]["status"] = "failed"
            elif status == "cancelled":
                tracked_agents[idx]["status"] = "cancelled"
            else:
                tracked_agents[idx]["status"] = "running"
        return rows

    def _poll_subagent_outputs() -> None:
        if subagent_runtime is None:
            return
        _sync_async_tasks_from_tracker()
        for row in tracked_agents:
            task_id = str(row.get("task_id", "") or "")
            run_id = str(row.get("run_id", "") or "")
            agent_type = str(row.get("type", "general"))
            if not task_id:
                continue
            try:
                runtime_info = subagent_runtime.get_runtime_info(agent_type)
            except Exception:
                continue
            url = runtime_info.get("url")
            runtime_status = str(runtime_info.get("status", "") or "").lower()
            if not url:
                continue
            row["endpoint"] = f"{runtime_info.get('host', '127.0.0.1')}:{runtime_info.get('port', '')}"
            row["pid"] = runtime_info.get("pid")
            if row.get("status") == "running" and runtime_status in {"running", "inprocess"}:
                # A silent but healthy local process is not blocked.
                row["last_progress_at"] = time.time()
            try:
                if run_id:
                    run_resp = httpx.get(
                        f"{url}/threads/{task_id}/runs/{run_id}",
                        timeout=SUBAGENT_RUN_POLL_TIMEOUT_SECONDS,
                    )
                    if run_resp.status_code == 200:
                        data = run_resp.json()
                        partial = str(data.get("partial_output", "") or "")
                        if partial:
                            row["live_output"] = partial
                            row["last_progress_at"] = time.time()
                        status = str(data.get("status", "")).lower()
                        if status in {"success", "completed"}:
                            row["status"] = "completed"
                        elif status in {"error", "failed"}:
                            row["status"] = "failed"
                            if hasattr(subagent_runtime, "update_task_state"):
                                subagent_runtime.update_task_state(task_id=task_id, state="failed", detail=str(data.get("error", "") or "run failed"), run_id=run_id)
                        elif status == "cancelled":
                            row["status"] = "cancelled"
                        elif status:
                            row["status"] = "running"
                if row.get("status") == "completed":
                    thread_resp = httpx.get(
                        f"{url}/threads/{task_id}",
                        timeout=SUBAGENT_RUN_POLL_TIMEOUT_SECONDS,
                    )
                    if thread_resp.status_code == 200:
                        messages = (thread_resp.json().get("messages") or [])
                        assistants = [m for m in messages if isinstance(m, dict) and m.get("role") == "assistant"]
                        if assistants:
                            final_output = str(assistants[-1].get("content", "") or "")
                            if final_output:
                                row["result_summary"] = final_output
                                row["live_output"] = final_output
            except Exception:
                continue
            if row.get("status") == "running" and runtime_status not in {"running", "inprocess"}:
                row["status"] = "failed"
                row["result_summary"] = row.get("result_summary") or f"SubAgent runtime is no longer healthy ({runtime_status or 'unknown'})."
                row["last_progress_at"] = time.time()
                _evt("❌", f"SubAgent <b>{_escape_html(agent_type)}</b> runtime stopped unexpectedly", "error")
            elif row.get("status") == "running":
                last_progress_at = float(row.get("last_progress_at") or row.get("started_at") or time.time())
                if time.time() - last_progress_at >= BLOCKED_AFTER_SECONDS:
                    row["status"] = "blocked"
                    row["result_summary"] = row.get("result_summary") or "No observable progress within the blocked threshold."
                    row["last_progress_at"] = time.time()
                    if hasattr(subagent_runtime, "update_task_state"):
                        subagent_runtime.update_task_state(task_id=task_id, state="blocked", detail="No output or status progress detected within threshold", run_id=run_id or None)
                    _evt("⛔", f"SubAgent <b>{_escape_html(agent_type)}</b> appears blocked", "error")

    def _unfinished_async_tasks() -> list[dict]:
        _sync_async_tasks_from_tracker()
        unfinished: list[dict] = []
        for row in tracked_agents:
            local_status = str(row.get("status", "")).lower()
            if local_status in {"completed", "failed", "cancelled"}:
                continue
            unfinished.append(row)
        return unfinished

    def _pause_for_human_review_if_needed() -> bool:
        if st.session_state.get("_pending_human_review"):
            return True
        if st.session_state.get("_human_review_resolution") is not None:
            return False
        candidates = _parse_remember_candidates_from_history(tracked_agents, working_dir)
        if not candidates:
            return False
        st.session_state["_pending_human_review"] = {
            "status": "pending",
            "workdir": working_dir,
            "candidates": candidates,
        }
        st.session_state["_hitl_scroll_pending"] = True
        _sync_live(True)
        st.rerun()
        return True

    def _maybe_schedule_alternate_subagent() -> None:
        for row in tracked_agents:
            if row.get("status") not in {"blocked", "failed"} or row.get("alternate_attempted"):
                continue
            source_role = str(row.get("type", "general"))
            alternate_role = ALTERNATE_ROLE_POLICY.get(source_role)
            row["alternate_attempted"] = True
            if not alternate_role:
                continue
            task_summary = str(row.get("query", "") or row.get("result_summary", "") or "recover prior subagent failure")
            _evt("🧭", f"Alternate path policy: launching <b>{alternate_role}</b> for {source_role} recovery", "subagent")
            row["result_summary"] = row.get("result_summary") or f"{source_role} handed off to alternate role {alternate_role}."
            row["status"] = "failed"
            try:
                agent.invoke(
                    {
                        "messages": [
                            HumanMessage(
                                content=(
                                    f"A subagent of role `{source_role}` became `{row.get('status')}` while handling: {task_summary}. "
                                    f"Launch one async `{alternate_role}` subagent to recover or validate the work, "
                                    "then continue the same user turn."
                                )
                            )
                        ]
                    },
                    config=config,
                )
            except Exception as exc:  # noqa: BLE001
                _evt("⚠️", f"Alternate path launch failed: {_escape_html(str(exc))}", "error")

    def _persist_history_snapshot(content: str, model: str) -> None:
        final_agents = list(tracked_agents)
        subagent_history_snapshot = _capture_subagent_history_snapshot(final_agents, state_store)
        active_workdir = str(st.session_state.get("_active_query_workdir", "") or Path.cwd())
        final_mdef, final_tips = _build_mermaid(
            final_agents,
            False,
            prompt,
            result_text=content,
            model_name=model,
        )
        prompt_label = st.session_state.get("_active_test_prompt_label")
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": content,
            "model": model,
            "tools_used": [],
            "activity_log": [(e["icon"], e["text"]) for e in events],
            "mermaid_def": final_mdef,
            "mermaid_html": None,
            "mermaid_tooltips": final_tips,
            "mermaid_events": list(events),
            "num_agents": len(final_agents),
            "async_task_snapshot": _capture_async_tasks(),
            "subagent_history_snapshot": subagent_history_snapshot,
            "working_dir": active_workdir,
            "test_prompt_label": prompt_label,
        })

    def _cleanup_turn_subagents_async() -> None:
        if subagent_runtime is None or not hasattr(subagent_runtime, "shutdown_turn_subagents"):
            return
        def _worker() -> None:
            try:
                subagent_runtime.shutdown_turn_subagents()
            except Exception:
                logger.exception("Background subagent cleanup failed")
        threading.Thread(target=_worker, daemon=True).start()

    if st.session_state.get("_refresh_requested"):
        _cleanup_turn_subagents_async()
        return False
    if st.session_state.get("_stop_requested"):
        _cleanup_turn_subagents_async()
        st.session_state["_is_running"] = False
        st.session_state["_has_result"] = True
        st.session_state.pop("_monitor_async_after_answer", None)
        st.session_state.pop("_live_turn_state", None)
        st.rerun()

    _drain_runtime_events()
    _poll_subagent_outputs()
    _maybe_schedule_alternate_subagent()
    unfinished = _unfinished_async_tasks()
    last_wait_count = st.session_state.get("_monitor_last_wait_count", -1)
    if unfinished:
        if len(unfinished) != last_wait_count:
            _evt("⏳", f"Waiting for {len(unfinished)} async task(s) to finish before closing this user session", "subagent")
            st.session_state["_monitor_last_wait_count"] = len(unfinished)
        _refresh(True)
        time.sleep(0.05)
        st.rerun()

    if _pause_for_human_review_if_needed():
        return False

    _evt("🧩", "All async subagents finished. Collecting results into one final answer", "subagent")
    try:
        loop_guard.reset()
        completed_report = _build_completed_subagent_report(tracked_agents)
        human_review = st.session_state.pop("_human_review_resolution", None)
        human_review_note = ""
        if human_review:
            human_review_note = (
                "\n\nHuman review resolution:\n"
                f"- approved={human_review.get('approved')}\n"
                f"- layer={human_review.get('target_layer', '')}\n"
                f"- selected_paths={human_review.get('selected_paths', [])}\n"
                f"- stored_ids={human_review.get('stored_ids', [])}\n"
            )
        _evt("📦", "Completed SubAgent results prepared for Main Agent aggregation", "subagent")
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            "All async subagent tasks from this user turn should now be finished. "
                            "Below is the completed SubAgent result ledger gathered by the WebUI runtime. "
                            "Use it as the primary aggregation source, and use live async task tools only if you need to verify details.\n\n"
                            f"{completed_report}{human_review_note}\n\n"
                            "then produce one final synthesized answer for the user. "
                            "Do not launch new async tasks unless absolutely required."
                        )
                    )
                ]
            },
            config=config,
        )
        for msg in reversed(result.get("messages", [])):
            if getattr(msg, "type", None) == "ai" and getattr(msg, "content", None):
                content = getattr(msg, "content")
                final_text = content if isinstance(content, str) else str(content)
                break
    except Exception as exc:  # noqa: BLE001
        logger.exception("Final async aggregation failed during monitor mode")
        _evt("⚠️", f"Final async aggregation failed: {_escape_html(str(exc))}", "error")
        final_text = _synthesize_subagent_results(tracked_agents)

    _poll_subagent_outputs()
    current_model = fallback_mw.current_model or current_model or "unknown"
    _refresh(False)
    _persist_history_snapshot(final_text or "*(No response generated)*", current_model)
    _cleanup_turn_subagents_async()
    st.session_state["_is_running"] = False
    st.session_state["_has_result"] = True
    st.session_state.pop("_monitor_async_after_answer", None)
    st.session_state.pop("_monitor_last_wait_count", None)
    st.session_state.pop("_live_turn_state", None)
    st.rerun()


# ─────────────────────────────────────────────────────────
#  Streaming logic
# ─────────────────────────────────────────────────────────

def _stream_response(
    prompt: str,
    graph_ph,
    result_ph,
    subagent_ph=None,
) -> bool:
    """Stream agent response — update flowchart, event feed, and result."""
    comp = st.session_state.agent_components
    if not comp:
        return False

    agent = comp["agent"]
    working_dir = str(comp.get("working_dir", "") or st.session_state.get("_active_query_workdir", "") or Path.cwd())
    fallback_mw = comp["fallback_middleware"]
    loop_guard = comp["loop_guard"]
    subagent_runtime = comp.get("subagent_runtime")
    state_store = comp.get("state_store")

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    loop_guard.reset()

    # ── Query-scoped thread ID ───────────────────────────────
    thread_id = f"webui-query-{uuid.uuid4().hex}"
    loop_run_id = f"loop_{uuid.uuid4().hex[:12]}"
    st.session_state["_last_query_thread_id"] = thread_id
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=prompt)]}

    final_text = ""
    streamed_text = ""
    current_model = ""
    tools_used: list[dict] = []
    events: list[dict] = []  # 질의별 독립 이벤트 리스트
    step_count = 0
    t_start = time.time()
    history_snapshot_saved = False
    stream_cutoff_for_async = False
    last_subagent_poll_at = 0.0
    launched_async = False

    # Local SubAgent tracking — 질의별 독립
    tracked_agents: list[dict] = []
    _sa_counter = [0]  # mutable counter for unique IDs
    _sa_role_counters: dict[str, int] = {}
    tool_call_agents: dict[str, int] = {}
    tool_call_actions: dict[str, str] = {}
    logged_status_keys: set[tuple[str, str]] = set()

    # ── helpers ───────────────────────────────────────────

    def _is_refresh_requested() -> bool:
        return bool(st.session_state.get("_refresh_requested"))

    def _is_stop_requested() -> bool:
        return bool(st.session_state.get("_stop_requested"))

    def _capture_async_tasks() -> list[dict]:
        tracker = comp.get("async_task_tracker")
        if not tracker:
            return []
        try:
            rows = tracker.get_tasks(thread_id)
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    def _sync_live_turn_state(*, working: bool) -> None:
        st.session_state["_live_turn_state"] = {
            "prompt": prompt,
            "result_text": final_text or streamed_text,
            "model": current_model,
            "events": list(events),
            "agents": _capture_subagent_history_snapshot(_agents_state(), state_store),
            "working": working,
            "hold_final_answer": bool(tracked_agents) or bool(st.session_state.get("_pending_human_review")),
        }

    def _clear_live_turn_state() -> None:
        st.session_state.pop("_live_turn_state", None)

    def _mark_ui_ready_for_next_turn() -> None:
        st.session_state["_is_running"] = False
        st.session_state["_has_result"] = True

    def _finalize_and_rerun() -> None:
        _mark_ui_ready_for_next_turn()
        _clear_live_turn_state()
        st.rerun()

    def _record_loop(
        status: str,
        current_step: str,
        *,
        failure_reason: str | None = None,
        next_action: str | None = None,
        retries: int = 0,
        policy_type: str | None = None,
    ) -> None:
        if state_store is None:
            return
        try:
            metadata = {"prompt_preview": prompt[:200]}
            if policy_type:
                policy = get_policy(policy_type)
                metadata["policy"] = {
                    "type": policy.failure_type,
                    "detect_signal": policy.detect_signal,
                    "max_retries": policy.max_retries,
                    "fallback": policy.fallback,
                    "user_status": policy.user_status,
                    "safe_stop_condition": policy.safe_stop_condition,
                }
            state_store.upsert_loop_run(
                run_id=loop_run_id,
                thread_id=thread_id,
                status=status,
                current_step=current_step,
                retries=retries,
                failure_reason=failure_reason,
                next_action=next_action,
                model=fallback_mw.current_model or None,
                metadata=metadata,
            )
        except Exception:
            logger.exception("Failed to persist loop run state")

    def _persist_history_snapshot(content: str, model: str, events_working: bool = False) -> None:
        nonlocal history_snapshot_saved
        if history_snapshot_saved:
            return
        final_agents = _agents_state()
        subagent_history_snapshot = _capture_subagent_history_snapshot(final_agents, state_store)
        completed_report = _build_completed_subagent_report(final_agents)
        active_workdir = str(st.session_state.get("_active_query_workdir", "") or Path.cwd())
        final_mdef, final_tips = _build_mermaid(
            final_agents,
            events_working,
            prompt,
            result_text=content,
            model_name=model,
        )
        prompt_label = st.session_state.get("_active_test_prompt_label")
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": content,
            "model": model,
            "tools_used": list(tools_used),
            "activity_log": [(e["icon"], e["text"]) for e in events],
            "mermaid_def": final_mdef,
            "mermaid_html": None,
            "mermaid_tooltips": final_tips,
            "mermaid_events": list(events),
            "num_agents": len(final_agents),
            "async_task_snapshot": _capture_async_tasks(),
            "subagent_history_snapshot": subagent_history_snapshot,
            "aggregated_subagent_report": completed_report,
            "working_dir": active_workdir,
            "test_prompt_label": prompt_label,
        })
        history_snapshot_saved = True
        _clear_live_turn_state()

    def _render_subagent_outputs() -> None:
        if subagent_ph is None:
            return
        rows = [
            a for a in tracked_agents
            if a.get("task_id")
            or a.get("live_output")
            or a.get("result_summary")
            or a.get("endpoint")
            or a.get("status") in {"running", "blocked", "failed", "completed", "cancelled"}
        ]
        if not rows:
            subagent_ph.empty()
            return
        parts = [
            "<div style='margin:8px 0 14px'>"
            "<div style='font-size:.78em;font-weight:700;color:#64748b;letter-spacing:.35px;margin-bottom:6px'>"
            "SubAgent Streaming Output</div>"
        ]
        for row in rows:
            endpoint = row.get("endpoint") or ""
            pid = row.get("pid")
            model = row.get("model") or ""
            status = row.get("status", "running")
            content = row.get("live_output") or row.get("result_summary") or "waiting for output..."
            parts.append(
                "<div style='background:#fff;border:1px solid #bbf7d0;border-radius:14px;"
                "padding:10px 12px;margin-bottom:8px;box-shadow:0 4px 14px rgba(22,163,74,.05)'>"
                f"<div style='font-size:.8em;font-weight:700;color:#166534;margin-bottom:4px'>{_escape_html(_agent_display_name(row))}</div>"
                f"<div style='font-size:.72em;color:#64748b;margin-bottom:6px'>{_escape_html(endpoint)}"
                f"{f'<br>pid {pid}' if pid else ''}"
                f"{f'<br>model { _escape_html(str(model)) }' if model else ''} · {_escape_html(status)}</div>"
                f"<div style='font-size:.88em;color:#14532d;white-space:pre-wrap;max-height:180px;overflow-y:auto'>{_escape_bubble_html(str(content))}</div>"
                "</div>"
            )
        parts.append("</div>")
        subagent_ph.markdown("".join(parts), unsafe_allow_html=True)

    def _drain_runtime_events(*, refresh: bool = True) -> None:
        if subagent_runtime is None or not hasattr(subagent_runtime, "drain_events"):
            return
        runtime_events = subagent_runtime.drain_events()
        if not runtime_events:
            return

        changed = False
        for event in runtime_events:
            host = _escape_html(str(event.get("host") or "127.0.0.1"))
            port = _escape_html(str(event.get("port") or ""))
            pid = event.get("pid")
            name = _escape_html(str(event.get("name") or "subagent"))
            etype = str(event.get("type") or "")
            endpoint = f"{host}:{port}" if port else host
            pid_line = f"<br>pid {pid}" if pid else ""
            if etype == "spawned":
                _evt("🚀", f"Spawned <b>{name}</b> on <b>{endpoint}</b>{pid_line}", "subagent", refresh=False)
                changed = True
            elif etype == "healthy":
                _evt("✅", f"<b>{name}</b> healthy on <b>{endpoint}</b>{pid_line}", "subagent", refresh=False)
                changed = True
            elif etype == "attached":
                _evt("🔌", f"Attached to <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent", refresh=False)
                changed = True
            elif etype == "reused":
                _evt("♻️", f"Reusing <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent", refresh=False)
                changed = True
            elif etype == "stopping":
                _evt("🧹", f"Stopping <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent", refresh=False)
                changed = True
            elif etype == "stopped":
                _evt("🧹", f"Stopped <b>{name}</b> at <b>{endpoint}</b>{pid_line}", "subagent", refresh=False)
                changed = True

        if changed and refresh:
            _refresh(True, result=final_text, model=current_model)

    def _cleanup_turn_subagents() -> None:
        if subagent_runtime is None or not hasattr(subagent_runtime, "shutdown_turn_subagents"):
            return
        try:
            subagent_runtime.shutdown_turn_subagents()
            _drain_runtime_events(refresh=True)
        except Exception as exc:  # noqa: BLE001
            _evt("⚠️", f"Subagent cleanup warning: {_escape_html(str(exc))}", "error", refresh=False)

    def _cleanup_turn_subagents_async() -> None:
        if subagent_runtime is None or not hasattr(subagent_runtime, "shutdown_turn_subagents"):
            return

        def _worker() -> None:
            try:
                subagent_runtime.shutdown_turn_subagents()
            except Exception:
                logger.exception("Background subagent cleanup failed")

        threading.Thread(target=_worker, daemon=True).start()

    def _render_agent_status(text: str) -> None:
        """Show progress in the Agent bubble until actual model content arrives."""
        if final_text:
            return
        bubble_style = _bubble_width_style(text, "agent")
        result_ph.markdown(
            f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{bubble_style}'>"
            f"{text}<div class='agent-bubble-model'>Working...</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )

    def _render_agent_answer(text: str, model: str = "") -> None:
        model_html = ""
        if model:
            model_html = f"<div class='agent-bubble-model'>🧠 {_escape_html(model)}</div>"
        bubble_style = _bubble_width_style(text, "agent")
        result_ph.markdown(
            f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{bubble_style}'>{_escape_bubble_html(text)}{model_html}</div></div>",
            unsafe_allow_html=True,
        )

    def _message_text_delta(message, metadata) -> str:
        """Extract user-visible streamed text from a LangGraph messages chunk."""
        if metadata and metadata.get("lc_source") == "summarization":
            return ""

        if isinstance(message, dict):
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(str(block.get("text", "")))
                        elif "text" in block:
                            text_parts.append(str(block.get("text", "")))
                return "".join(text_parts)
            return str(content) if content else ""

        blocks = getattr(message, "content_blocks", None)
        if blocks:
            text_parts: list[str] = []
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)

        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)
        return ""

    def _tool_call_value(tool_call, key: str, default=None):
        if isinstance(tool_call, dict):
            return tool_call.get(key, default)
        return getattr(tool_call, key, default)

    def _msg_value(msg, key: str, default=None):
        if isinstance(msg, dict):
            return msg.get(key, default)
        return getattr(msg, key, default)

    def _msg_type(msg) -> str | None:
        return _msg_value(msg, "type")

    def _msg_content(msg):
        return _msg_value(msg, "content", "")

    def _msg_tool_calls(msg):
        return _msg_value(msg, "tool_calls", []) or []

    def _msg_name(msg) -> str:
        return str(_msg_value(msg, "name", "unknown"))

    def _is_subagent_spawn_tool(tool_name: str) -> bool:
        return tool_name == "start_async_task"

    def _is_subagent_tool(tool_name: str) -> bool:
        return tool_name in (
            "start_async_task",
            "check_async_task",
            "update_async_task",
            "cancel_async_task",
            "list_async_tasks",
        )

    def _subagent_args(tool_name: str, args) -> tuple[str, str]:
        """Normalize async subagent tool arguments."""
        if not isinstance(args, dict):
            return "general", str(args)
        return (
            args.get("subagent_type", "general"),
            args.get("description", "") or str(args),
        )

    def _evt(icon: str, text: str, css: str = "", refresh: bool = True) -> None:
        ts = time.strftime("%H:%M:%S")
        events.append({"icon": icon, "text": text, "css_class": css, "time": ts})
        _sync_live_turn_state(working=True)
        _render_agent_status(f"{icon} {text}")
        _render_subagent_outputs()
        if refresh:
            _refresh(True)

    def _log_subagent_status_once(row: dict, status: str, detail: str = "", *, icon: str = "📍", css: str = "subagent") -> None:
        task_key = str(row.get("task_id", "") or row.get("id", "") or row.get("type", "subagent"))
        key = (task_key, status)
        if key in logged_status_keys:
            return
        logged_status_keys.add(key)
        role = _escape_html(_agent_display_name(row))
        endpoint = _escape_html(str(row.get("endpoint", "") or ""))
        pid = row.get("pid")
        meta_parts = []
        if endpoint:
            meta_parts.append(endpoint)
        if pid:
            meta_parts.append(f"pid {pid}")
        meta = f" ({', '.join(meta_parts)})" if meta_parts else ""
        suffix = f" — {_escape_html(detail)}" if detail else ""
        _evt(icon, f"{role} -> <b>{status}</b>{meta}{suffix}", css, refresh=False)

    def _track_spawn(agent_type: str, description: str) -> int:
        """Record a SubAgent spawn locally. Returns the index."""
        endpoint = ""
        pid = None
        if subagent_runtime is not None:
            try:
                info = subagent_runtime.get_runtime_info(agent_type)
                endpoint = f"{info.get('host', '127.0.0.1')}:{info.get('port', '')}"
                pid = info.get("pid")
                model = str(info.get("model", "") or "")
            except Exception:
                endpoint = ""
                model = ""
        else:
            model = ""
        idx = _sa_counter[0]
        _sa_counter[0] += 1
        ordinal = _sa_role_counters.get(agent_type, 0) + 1
        _sa_role_counters[agent_type] = ordinal
        tracked_agents.append({
            "id": f"local_{idx}",
            "type": agent_type,
            "ordinal": ordinal,
            "display_name": f"{agent_type} agent #{ordinal}",
            "status": "running",
            "last_action": "launch",
            "elapsed": "",
            "query": description,
            "task_id": "",
            "run_id": "",
            "model": model,
            "started_at": time.time(),
            "endpoint": endpoint,
            "pid": pid,
            "live_output": "",
            "last_progress_at": time.time(),
            "alternate_attempted": False,
        })
        print(
            "[CodingAgent Mermaid] spawn_async_subagent",
            idx,
            f"{agent_type}#{ordinal}",
            description[:120],
            flush=True,
        )
        _log_subagent_status_once(tracked_agents[idx], "created", description[:120], icon="🆕")
        return idx

    def _set_task_identity(idx: int | None, task_id: str = "", run_id: str = "") -> None:
        if idx is None or idx < 0 or idx >= len(tracked_agents):
            return
        if task_id:
            tracked_agents[idx]["task_id"] = task_id
        if run_id:
            tracked_agents[idx]["run_id"] = run_id
        if task_id or run_id:
            ident = []
            if task_id:
                ident.append(f"task_id {task_id[:12]}...")
            if run_id:
                ident.append(f"run_id {run_id[:12]}...")
            _evt("🪪", f"{_escape_html(_agent_display_name(tracked_agents[idx]))} identity bound: {' / '.join(ident)}", "subagent", refresh=False)

    def _set_task_action(idx: int | None, action: str, query: str | None = None) -> None:
        if idx is None or idx < 0 or idx >= len(tracked_agents):
            return
        tracked_agents[idx]["last_action"] = action
        if query:
            tracked_agents[idx]["query"] = query
        _evt("📝", f"{_escape_html(_agent_display_name(tracked_agents[idx]))} action -> <b>{_escape_html(action)}</b>", "subagent", refresh=False)

    def _find_tracked_by_task_id(task_id: str) -> int | None:
        if not task_id:
            return None
        for idx, agent_row in enumerate(tracked_agents):
            if agent_row.get("task_id") == task_id:
                return idx
        return None

    def _sync_async_tasks_from_tracker() -> list[dict]:
        rows = _capture_async_tasks()
        for row in rows:
            task_id = str(row.get("task_id", "") or "")
            idx = _find_tracked_by_task_id(task_id)
            if idx is None:
                discovered_role = str(row.get("agent_type", "general") or "general")
                idx = _track_spawn(discovered_role, f"tracker discovered async task {task_id[:12]}...")
                tracked_agents[idx]["task_id"] = task_id
                tracked_agents[idx]["run_id"] = str(row.get("run_id", "") or "")
                tracked_agents[idx]["last_action"] = "tracker"
                _evt("🛰️", f"Tracker discovered async task for <b>{_escape_html(discovered_role)}</b>", "subagent", refresh=False)
            local_status = str(tracked_agents[idx].get("status", "")).lower()
            tracked_agents[idx]["run_id"] = str(row.get("run_id", "") or tracked_agents[idx].get("run_id", ""))
            status = str(row.get("status", "")).lower()
            if local_status in {"blocked", "completed", "failed", "cancelled"} and status == "running":
                continue
            if status in {"success", "completed"}:
                tracked_agents[idx]["status"] = "completed"
                _log_subagent_status_once(tracked_agents[idx], "completed", "tracker reported completion", icon="✅")
            elif status in {"error", "failed"}:
                tracked_agents[idx]["status"] = "failed"
                _log_subagent_status_once(tracked_agents[idx], "failed", str(row.get("error", "") or "tracker reported failure"), icon="❌", css="error")
            elif status == "cancelled":
                tracked_agents[idx]["status"] = "cancelled"
                _log_subagent_status_once(tracked_agents[idx], "cancelled", "tracker reported cancellation", icon="🛑", css="error")
            else:
                tracked_agents[idx]["status"] = "running"
                _log_subagent_status_once(tracked_agents[idx], "running", "tracker confirms task is running", icon="🏃")
        return rows

    def _poll_subagent_outputs() -> None:
        if subagent_runtime is None:
            return
        _sync_async_tasks_from_tracker()
        changed = False
        for row in tracked_agents:
            task_id = str(row.get("task_id", "") or "")
            run_id = str(row.get("run_id", "") or "")
            agent_type = str(row.get("type", "general"))
            if not task_id:
                continue
            try:
                runtime_info = subagent_runtime.get_runtime_info(agent_type)
            except Exception:
                continue
            url = runtime_info.get("url")
            runtime_status = str(runtime_info.get("status", "") or "").lower()
            if not url:
                continue
            row["endpoint"] = f"{runtime_info.get('host', '127.0.0.1')}:{runtime_info.get('port', '')}"
            row["pid"] = runtime_info.get("pid")
            row["model"] = str(runtime_info.get("model", "") or row.get("model", ""))
            if row.get("status") == "running" and runtime_status in {"running", "inprocess"}:
                row["last_progress_at"] = time.time()
            try:
                if run_id:
                    run_resp = httpx.get(
                        f"{url}/threads/{task_id}/runs/{run_id}",
                        timeout=SUBAGENT_RUN_POLL_TIMEOUT_SECONDS,
                    )
                    if run_resp.status_code == 200:
                        data = run_resp.json()
                        partial = str(data.get("partial_output", "") or "")
                        if partial and partial != row.get("live_output", ""):
                            row["live_output"] = partial
                            row["last_progress_at"] = time.time()
                            changed = True
                        status = str(data.get("status", "")).lower()
                        if status in {"success", "completed"}:
                            row["status"] = "completed"
                            row["last_progress_at"] = time.time()
                            _log_subagent_status_once(row, "completed", "run endpoint returned success", icon="✅")
                        elif status in {"error", "failed"}:
                            row["status"] = "failed"
                            row["last_progress_at"] = time.time()
                            subagent_runtime.update_task_state(task_id=task_id, state="failed", detail=str(data.get("error", "") or "run failed"), run_id=run_id)
                            _log_subagent_status_once(row, "failed", str(data.get("error", "") or "run endpoint returned failure"), icon="❌", css="error")
                        elif status == "cancelled":
                            row["status"] = "cancelled"
                            row["last_progress_at"] = time.time()
                            subagent_runtime.update_task_state(task_id=task_id, state="cancelled", detail="run cancelled", run_id=run_id)
                            _log_subagent_status_once(row, "cancelled", "run endpoint returned cancellation", icon="🛑", css="error")
                        elif status:
                            row["status"] = "running"
                            _log_subagent_status_once(row, "running", "run endpoint is active", icon="🏃")
                if row.get("status") == "completed":
                    thread_resp = httpx.get(
                        f"{url}/threads/{task_id}",
                        timeout=SUBAGENT_RUN_POLL_TIMEOUT_SECONDS,
                    )
                    if thread_resp.status_code == 200:
                        messages = (thread_resp.json().get("messages") or [])
                        assistants = [m for m in messages if isinstance(m, dict) and m.get("role") == "assistant"]
                        if assistants:
                            final_output = str(assistants[-1].get("content", "") or "")
                            if final_output and final_output != row.get("result_summary", ""):
                                row["result_summary"] = final_output
                                row["live_output"] = final_output
                                row["last_progress_at"] = time.time()
                                changed = True
                                _evt("📬", f"{_escape_html(agent_type)} final result captured ({len(final_output):,} chars)", "subagent", refresh=False)
            except Exception:
                continue
            if row.get("status") == "running" and runtime_status not in {"running", "inprocess"}:
                row["status"] = "failed"
                row["result_summary"] = row.get("result_summary") or f"SubAgent runtime is no longer healthy ({runtime_status or 'unknown'})."
                row["last_progress_at"] = time.time()
                _evt("❌", f"SubAgent <b>{_escape_html(agent_type)}</b> runtime stopped unexpectedly", "error", refresh=False)
                changed = True
            elif row.get("status") == "running":
                last_progress_at = float(row.get("last_progress_at") or row.get("started_at") or time.time())
                if time.time() - last_progress_at >= BLOCKED_AFTER_SECONDS:
                    row["status"] = "blocked"
                    row["result_summary"] = row.get("result_summary") or "No observable progress within the blocked threshold."
                    row["last_progress_at"] = time.time()
                    subagent_runtime.update_task_state(task_id=task_id, state="blocked", detail="No output or status progress detected within threshold", run_id=run_id or None)
                    _evt("⛔", f"SubAgent <b>{_escape_html(agent_type)}</b> appears blocked", "error", refresh=False)
                    changed = True
        if changed:
            _render_subagent_outputs()
            _refresh(True, result=final_text, model=current_model)

    def _unfinished_async_tasks() -> list[dict]:
        _sync_async_tasks_from_tracker()
        unfinished: list[dict] = []
        for row in tracked_agents:
            local_status = str(row.get("status", "")).lower()
            if local_status in {"completed", "failed", "cancelled"}:
                continue
            unfinished.append(row)
        return unfinished

    def _maybe_schedule_alternate_subagent() -> bool:
        triggered = False
        for row in tracked_agents:
            if row.get("status") not in {"blocked", "failed"}:
                continue
            if row.get("alternate_attempted"):
                continue
            source_role = str(row.get("type", "general"))
            alternate_role = ALTERNATE_ROLE_POLICY.get(source_role)
            if not alternate_role:
                row["alternate_attempted"] = True
                continue
            row["alternate_attempted"] = True
            task_summary = str(row.get("query", "") or row.get("result_summary", "") or "recover prior subagent failure")
            _evt(
                "🧭",
                f"Alternate path policy: launching <b>{alternate_role}</b> for {source_role} recovery",
                "subagent",
                refresh=False,
            )
            _record_loop(
                "running",
                "alternate_path",
                failure_reason=f"{source_role} entered {row.get('status')}",
                next_action=f"launch_alternate:{alternate_role}",
                policy_type="subagent_failure",
            )
            try:
                result = agent.invoke(
                    {
                        "messages": [
                            HumanMessage(
                                content=(
                                    f"A subagent of role `{source_role}` became `{row.get('status')}` while handling: {task_summary}. "
                                    f"Launch one async `{alternate_role}` subagent to recover or validate the work, "
                                    "then continue the same user turn."
                                )
                            )
                        ]
                    },
                    config=config,
                )
                for msg in result.get("messages", []):
                    if _msg_type(msg) == "tool":
                        tools_used.append({
                            "name": _msg_name(msg),
                            "result": str(_msg_content(msg) or "")[:200],
                            "is_subagent": _is_subagent_tool(_msg_name(msg)),
                        })
                triggered = True
            except Exception as exc:  # noqa: BLE001
                _evt("⚠️", f"Alternate path launch failed: {_escape_html(str(exc))}", "error", refresh=False)
                _record_loop(
                    "degraded",
                    "alternate_path_failed",
                    failure_reason=str(exc),
                    next_action="return_current_failure",
                    policy_type="subagent_failure",
                )
        if triggered:
            _drain_runtime_events(refresh=True)
            _poll_subagent_outputs()
            _refresh(True, result=final_text, model=current_model)
        return triggered

    def _track_complete(
        agent_type: str,
        success: bool = True,
        model: str = "",
        result_summary: str = "",
    ) -> None:
        """Mark the most recent running SubAgent of the given type as done."""
        for a in reversed(tracked_agents):
            if a["type"] == agent_type and a["status"] == "running":
                a["status"] = "completed" if success else "failed"
                a["elapsed"] = f"{time.time() - a['started_at']:.1f}"
                if model:
                    a["model"] = model
                if result_summary:
                    a["result_summary"] = result_summary
                break

    def _track_complete_by_index(
        idx: int | None,
        success: bool = True,
        model: str = "",
        result_summary: str = "",
        status: str | None = None,
    ) -> bool:
        if idx is None or idx < 0 or idx >= len(tracked_agents):
            return False

        agent = tracked_agents[idx]
        agent["status"] = status or ("completed" if success else "failed")
        agent["elapsed"] = f"{time.time() - agent['started_at']:.1f}"
        agent["last_progress_at"] = time.time()
        if model:
            agent["model"] = model
        if result_summary:
            agent["result_summary"] = result_summary
        print(
            "[CodingAgent Mermaid] complete_subagent",
            idx,
            agent["type"],
            agent["status"],
            result_summary[:120],
            flush=True,
        )
        return True

    def _parse_task_id(text: str) -> str:
        payload = _parse_check_payload(text)
        for key in ("task_id", "thread_id"):
            value = str(payload.get(key, "") or "").strip()
            if value:
                return value
        match = re.search(r"task_id:\s*([a-f0-9-]{8,})", text, flags=re.IGNORECASE)
        return match.group(1) if match else ""

    def _parse_check_payload(text: str) -> dict[str, str]:
        payload = text.strip()
        if not payload.startswith("{"):
            return {}
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        parsed = {
            "task_id": str(data.get("task_id", "")),
            "status": str(data.get("status", "")),
            "thread_id": str(data.get("thread_id", "")),
            "run_id": str(data.get("run_id", "")),
            "result": str(data.get("result", "")),
            "error": str(data.get("error", "")),
        }
        return parsed

    def _apply_list_async_tasks(text: str) -> None:
        for line in text.splitlines():
            if "task_id:" not in line:
                continue
            task_id_match = re.search(r"task_id:\s*([a-f0-9-]{8,})", line, flags=re.IGNORECASE)
            status_match = re.search(r"status:\s*([a-z_]+)", line, flags=re.IGNORECASE)
            if not task_id_match:
                continue
            idx = _find_tracked_by_task_id(task_id_match.group(1))
            if idx is None:
                continue
            if status_match:
                status = status_match.group(1).lower()
                if status == "success":
                    tracked_agents[idx]["status"] = "completed"
                elif status == "cancelled":
                    tracked_agents[idx]["status"] = "cancelled"
                elif status == "error":
                    tracked_agents[idx]["status"] = "failed"
                else:
                    tracked_agents[idx]["status"] = "running"

    def _agents_state() -> list[dict]:
        """Return locally tracked SubAgents for THIS query only.

        Avoids mixing prior-query async task state into this Mermaid graph.
        """
        return list(tracked_agents)

    def _pause_for_human_review_if_needed() -> bool:
        if st.session_state.get("_pending_human_review"):
            return True
        if st.session_state.get("_human_review_resolution") is not None:
            return False
        candidates = _parse_remember_candidates_from_history(tracked_agents, working_dir)
        if not candidates:
            return False
        st.session_state["_pending_human_review"] = {
            "status": "pending",
            "workdir": working_dir,
            "candidates": candidates,
        }
        st.session_state["_hitl_scroll_pending"] = True
        st.session_state["_monitor_async_after_answer"] = True
        _sync_live_turn_state(working=True)
        st.rerun()
        return True

    def _maybe_force_remember_subagent() -> bool:
        if not _workspace_has_artifacts(working_dir):
            return False
        existing = [
            row for row in tracked_agents
            if str(row.get("type", "")).lower() == "remember"
            and str(row.get("status", "")).lower() not in {"failed", "cancelled"}
        ]
        if existing:
            return False
        _evt(
            "🧠",
            "Artifacts detected. Forcing a remember subagent to nominate memory candidates before finalizing this turn",
            "subagent",
            refresh=False,
        )
        try:
            agent.invoke(
                {
                    "messages": [
                        HumanMessage(
                            content=(
                                "The current user turn produced durable workspace artifacts. "
                                "You must now launch exactly one async `remember` subagent with `start_async_task`. "
                                "Its job is to inspect the current query workspace, nominate up to 10 files worth long-term memory, "
                                "and explain briefly why each one matters. Do not finalize the user turn yet."
                            )
                        )
                    ]
                },
                config=config,
            )
            _drain_runtime_events(refresh=True)
            _poll_subagent_outputs()
            return True
        except Exception as exc:  # noqa: BLE001
            _evt("⚠️", f"Failed to launch remember subagent: {_escape_html(str(exc))}", "error", refresh=False)
            return False

    def _refresh(working: bool, result: str = "", model: str = "") -> None:
        agents = _agents_state()
        _sync_live_turn_state(working=working)
        mdef, tips = _build_mermaid(
            agents, working, prompt,
            result_text=result, model_name=model,
        )
        if agents:
            print("[CodingAgent Mermaid] source\n" + mdef, flush=True)
        _render_mermaid(graph_ph, mdef, events, working, num_agents=len(agents), tooltips=tips)

    # ── Non-streaming fallback ────────────────────────────

    try:
        _record_loop("running", "start")
        _sync_live_turn_state(working=True)
        _evt("🚀", f"Prompt received ({len(prompt)} chars)", "tool")
        _evt("📁", f"Query workspace: <b>{_escape_html(working_dir)}</b>", "tool", refresh=False)

        if not hasattr(agent, "stream"):
            _evt("⚠️", "Agent lacks .stream() — using non-streaming invoke", "tool")
            result = agent.invoke(inputs, config=config)
            for msg in result.get("messages", []):
                if _msg_type(msg) == "ai" and _msg_content(msg):
                    content = _msg_content(msg)
                    final_text = (
                        content if isinstance(content, str)
                        else str(content)
                    )
                elif _msg_type(msg) == "tool":
                    tname = _msg_name(msg)
                    content = _msg_content(msg)
                    tools_used.append({
                        "name": tname,
                        "result": str(content)[:200] if content else "",
                        "is_subagent": _is_subagent_tool(tname),
                    })
                    _evt("🔧", f"Tool <b>{tname}</b> executed", "tool")

            with result_ph:
                _model_tag = ""
                _cm = fallback_mw.current_model or "?"
                if _cm:
                    _model_tag = f"<div class='agent-bubble-model'>🧠 {_escape_html(_cm)}</div>"
                safe_final_text = _escape_bubble_html(final_text or "*(No response)*")
                bubble_style = _bubble_width_style(final_text or "*(No response)*", "agent")
                st.markdown(
                    f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{bubble_style}'>{safe_final_text}{_model_tag}</div></div>",
                    unsafe_allow_html=True,
                )

            current_model = fallback_mw.current_model or "?"
            elapsed_s = f"{time.time() - t_start:.1f}"
            _evt("🏁", f"Done — <b>{current_model}</b> · {elapsed_s}s · {len(final_text):,} chars", "done")
            # 최종 Mermaid: Main Agent → User edge 포함
            _refresh(False, result=final_text, model=current_model)

            inv_agents = _agents_state()
            inv_mdef, inv_tips = _build_mermaid(
                inv_agents, False, prompt,
                result_text=final_text, model_name=current_model,
            )
            inv_html = _build_page_html(
                inv_mdef,
                list(events),
                False,
                tooltips=inv_tips,
            )
            prompt_label = st.session_state.get("_active_test_prompt_label")
            subagent_history_snapshot = _capture_subagent_history_snapshot(inv_agents, state_store)
            active_workdir = str(st.session_state.get("_active_query_workdir", "") or Path.cwd())
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": final_text or "*(No response)*",
                "model": current_model,
                "tools_used": tools_used,
                "activity_log": [(e["icon"], e["text"]) for e in events],
                "mermaid_def": inv_mdef,
                "mermaid_html": inv_html,
                "mermaid_tooltips": inv_tips,
                "mermaid_events": list(events),
                "num_agents": len(inv_agents),
                "async_task_snapshot": _capture_async_tasks(),
                "subagent_history_snapshot": subagent_history_snapshot,
                "aggregated_subagent_report": _build_completed_subagent_report(inv_agents),
                "working_dir": active_workdir,
                "test_prompt_label": prompt_label,
            })
            _finalize_and_rerun()
            return True

        # ── Streaming mode ────────────────────────────────

        current_model = fallback_mw.current_model or ""
        _evt("🔄", f"Streaming started (model: <b>{_escape_html(current_model or 'selecting…')}</b>)", "tool")

        try:
            stream = agent.stream(
                inputs,
                config=config,
                stream_mode=["messages", "updates"],
                subgraphs=True,
            )
        except TypeError:
            stream = agent.stream(
                inputs,
                config=config,
                stream_mode=["messages", "updates"],
            )

        for raw_chunk in stream:
            _drain_runtime_events(refresh=True)
            now = time.time()
            if now - last_subagent_poll_at >= SUBAGENT_POLL_INTERVAL_SECONDS:
                _poll_subagent_outputs()
                last_subagent_poll_at = now
            if _is_refresh_requested():
                _record_loop("stopped", "refresh_requested", next_action="user_refresh", policy_type="safe_stop")
                _evt("🛑", "Refresh requested — stopping current run", "error", refresh=False)
                _cleanup_turn_subagents_async()
                return False
            if _is_stop_requested():
                _record_loop("stopped", "stop_requested", next_action="user_stop", policy_type="safe_stop")
                _evt("🛑", "Stop requested — halting current run", "error", refresh=False)
                if final_text:
                    current_model = fallback_mw.current_model or current_model or "unknown"
                    _refresh(False, result=final_text, model=current_model)
                    _render_agent_answer(final_text, current_model)
                    _persist_history_snapshot(final_text, current_model)
                    _cleanup_turn_subagents_async()
                    _finalize_and_rerun()
                    return True
                _cleanup_turn_subagents_async()
                _refresh(False)
                return False

            if isinstance(raw_chunk, tuple) and len(raw_chunk) == 3:
                namespace, current_stream_mode, chunk_data = raw_chunk
                is_main_agent = not namespace
            elif isinstance(raw_chunk, tuple) and len(raw_chunk) == 2:
                namespace = ()
                current_stream_mode, chunk_data = raw_chunk
                is_main_agent = True
            else:
                namespace = ()
                current_stream_mode = "updates"
                chunk_data = raw_chunk
                is_main_agent = True

            if current_stream_mode == "messages":
                if not is_main_agent:
                    continue
                if not isinstance(chunk_data, tuple) or len(chunk_data) != 2:
                    continue
                message, metadata = chunk_data
                msg_type = _msg_type(message)
                if msg_type == "AIMessageChunk" or "AIMessageChunk" in type(message).__name__ or msg_type == "ai":
                    text_delta = _message_text_delta(message, metadata)
                    if text_delta:
                        streamed_text += text_delta
                        final_text = streamed_text
                        current_model = fallback_mw.current_model or current_model or "unknown"
                        _render_agent_answer(streamed_text)
                        if not tracked_agents:
                            _refresh(False, result=streamed_text, model=current_model)
                continue

            if not is_main_agent:
                continue

            chunk = chunk_data
            if not isinstance(chunk, dict):
                continue

            step_count += 1
            if (loop_warning := loop_guard.check_iteration()) is not None:
                if tracked_agents:
                    stream_cutoff_for_async = True
                    _evt(
                        "🧭",
                        "Main loop iteration cap reached after launching async work; switching to async wait/collect mode",
                        "subagent",
                        refresh=False,
                    )
                    _record_loop(
                        "degraded",
                        "iteration_cutoff_async_collect",
                        failure_reason=loop_warning,
                        next_action="wait_for_async_tasks",
                        policy_type="no_progress_loop",
                    )
                    break
                _evt("🛑", _escape_html(loop_warning), "error", refresh=False)
                _record_loop(
                    "stopped",
                    "no_progress_guard",
                    failure_reason=loop_warning,
                    next_action="safe_stop",
                    policy_type="no_progress_loop",
                )
                _cleanup_turn_subagents_async()
                _refresh(False, result=final_text, model=current_model)
                return bool(final_text)
            for _node, node_output in chunk.items():
                if _is_refresh_requested():
                    _record_loop("stopped", "refresh_requested", next_action="user_refresh", policy_type="safe_stop")
                    _evt("🛑", "Refresh requested — stopping current run", "error", refresh=False)
                    _cleanup_turn_subagents_async()
                    return False
                if _is_stop_requested():
                    _record_loop("stopped", "stop_requested", next_action="user_stop", policy_type="safe_stop")
                    _evt("🛑", "Stop requested — halting current run", "error", refresh=False)
                    if final_text:
                        current_model = fallback_mw.current_model or current_model or "unknown"
                        _refresh(False, result=final_text, model=current_model)
                        _render_agent_answer(final_text, current_model)
                        _persist_history_snapshot(final_text, current_model)
                        _cleanup_turn_subagents_async()
                        _finalize_and_rerun()
                        return True
                    _cleanup_turn_subagents_async()
                    _refresh(False)
                    return False

                # Unwrap LangGraph Overwrite wrapper if present
                if not isinstance(node_output, dict):
                    node_output = getattr(node_output, "value", None) or {}
                if not isinstance(node_output, dict):
                    continue

                # messages may also be wrapped in Overwrite
                raw_msgs = node_output.get("messages", [])
                if not isinstance(raw_msgs, list):
                    raw_msgs = getattr(raw_msgs, "value", None) or []
                if not isinstance(raw_msgs, list):
                    raw_msgs = [raw_msgs] if raw_msgs else []

                for msg in raw_msgs:
                    msg_type = _msg_type(msg)

                    if msg_type == "ai":
                        tool_calls = _msg_tool_calls(msg)
                        if tool_calls:
                            for tc in tool_calls:
                                name = _tool_call_value(tc, "name", "unknown")
                                args = _tool_call_value(tc, "args", {}) or {}
                                if _is_subagent_spawn_tool(name):
                                    launched_async = True
                                    atype, full_desc = _subagent_args(name, args)
                                    desc = _escape_html(full_desc[:60])
                                    # Track locally so Mermaid shows it immediately
                                    tracked_idx = _track_spawn(atype, full_desc)
                                    tool_call_id = _tool_call_value(tc, "id")
                                    if tool_call_id:
                                        tool_call_agents[str(tool_call_id)] = tracked_idx
                                        tool_call_actions[str(tool_call_id)] = "launch"
                                    _evt(
                                        AGENT_ICONS.get(atype, "🤖"),
                                        f"Launching <b>{atype}</b> async task: {desc}",
                                        "subagent",
                                    )
                                    _drain_runtime_events(refresh=True)
                                elif name == "list_async_tasks":
                                    _evt("📋", "Listing async task status", "subagent")
                                elif name == "check_async_task":
                                    task_id = _escape_html(str(args.get("task_id", ""))[:24])
                                    raw_task_id = str(args.get("task_id", ""))
                                    tool_call_id = _tool_call_value(tc, "id")
                                    if tool_call_id:
                                        idx = _find_tracked_by_task_id(raw_task_id)
                                        if idx is not None:
                                            tool_call_agents[str(tool_call_id)] = idx
                                        tool_call_actions[str(tool_call_id)] = "check"
                                    _evt("📡", f"Checking async task <b>{task_id}</b>", "subagent")
                                elif name == "update_async_task":
                                    task_id = _escape_html(str(args.get("task_id", ""))[:24])
                                    raw_task_id = str(args.get("task_id", ""))
                                    raw_message = str(args.get("message", "") or "")
                                    tool_call_id = _tool_call_value(tc, "id")
                                    if tool_call_id:
                                        idx = _find_tracked_by_task_id(raw_task_id)
                                        if idx is not None:
                                            tool_call_agents[str(tool_call_id)] = idx
                                            _set_task_action(idx, "update", query=raw_message[:300])
                                        tool_call_actions[str(tool_call_id)] = "update"
                                    _evt("✏️", f"Updating async task <b>{task_id}</b>", "subagent")
                                elif name == "cancel_async_task":
                                    task_id = _escape_html(str(args.get("task_id", ""))[:24])
                                    raw_task_id = str(args.get("task_id", ""))
                                    tool_call_id = _tool_call_value(tc, "id")
                                    if tool_call_id:
                                        idx = _find_tracked_by_task_id(raw_task_id)
                                        if idx is not None:
                                            tool_call_agents[str(tool_call_id)] = idx
                                        tool_call_actions[str(tool_call_id)] = "cancel"
                                    _evt("🛑", f"Cancelling async task <b>{task_id}</b>", "subagent")
                                elif "memory_store" in name:
                                    cat = args.get("category", "?")
                                    _evt("🧠", f"Storing memory → <b>{cat}</b>", "memory")
                                elif "memory_search" in name:
                                    q = _escape_html(args.get("query", "")[:40])
                                    _evt("🧠", f"Searching memory: {q}", "memory")
                                else:
                                    arg_summary = ", ".join(
                                        f"{k}={str(v)[:20]}" for k, v in list(args.items())[:3]
                                    )
                                    _evt("🔧", f"Calling <b>{name}</b>({_escape_html(arg_summary)})", "tool")

                        content = (
                            _msg_content(msg)
                            if isinstance(_msg_content(msg), str)
                            else str(_msg_content(msg)) if _msg_content(msg)
                            else ""
                        )
                        if content and not tool_calls:
                            final_text = content
                            streamed_text = content
                            current_model = fallback_mw.current_model or current_model or "unknown"
                            _evt(
                                "💬",
                                f"AI response received ({len(content):,} chars)",
                                "done",
                                refresh=False,
                            )
                            if tracked_agents or launched_async:
                                _render_agent_status("SubAgent results are still running. Final answer will be released after the remember review.")
                            else:
                                _render_agent_answer(final_text, current_model)
                            _refresh(True if tracked_agents else False, result=final_text, model=current_model)

                    elif msg_type == "tool":
                        tool_name = _msg_name(msg)
                        tool_call_id = _msg_value(msg, "tool_call_id", None)
                        tracked_idx = tool_call_agents.get(str(tool_call_id)) if tool_call_id else None
                        action = tool_call_actions.get(str(tool_call_id), "")
                        msg_content = _msg_content(msg)
                        tool_content_full = str(msg_content) if msg_content else ""
                        tool_content = tool_content_full[:300]
                        is_sa = _is_subagent_tool(tool_name)
                        tools_used.append({
                            "name": tool_name,
                            "result": tool_content,
                            "is_subagent": is_sa,
                        })

                        if _is_subagent_spawn_tool(tool_name):
                            launched_async = True
                            if tracked_idx is None:
                                tracked_idx = _track_spawn("general", f"{tool_name} result")
                            sa_type = (
                                tracked_agents[tracked_idx]["type"]
                                if tracked_idx is not None and tracked_idx < len(tracked_agents)
                                else "general"
                            )
                            sa_model_short = ""

                            # Extract raw result from tool output (no truncation)
                            _result_raw = ""
                            task_id = _parse_task_id(tool_content_full)
                            start_payload = _parse_check_payload(tool_content_full)
                            run_id = start_payload.get("run_id", "")
                            if task_id:
                                _set_task_identity(tracked_idx, task_id=task_id, run_id=run_id)
                            if tool_content_full.strip():
                                _result_raw = tool_content_full.strip()

                            if tool_name == "start_async_task" and task_id:
                                _evt(
                                    AGENT_ICONS.get(sa_type, "🤖"),
                                    f"Async SubAgent <b>{sa_type}</b> launched with task_id <b>{task_id[:12]}...</b>",
                                    "subagent",
                                )
                                _set_task_action(tracked_idx, "launch")
                            elif "failed" in tool_content_full.lower():
                                if not _track_complete_by_index(
                                    tracked_idx,
                                    success=False,
                                    model=sa_model_short,
                                    result_summary=_result_raw,
                                ):
                                    _track_complete(sa_type, success=False, model=sa_model_short, result_summary=_result_raw)
                                err_preview = _escape_html(tool_content[:80])
                                _evt("❌", f"SubAgent failed: {err_preview}", "error")
                            else:
                                _evt("🔄", f"SubAgent returned: {_escape_html(tool_content[:60])}", "subagent")
                            # SubAgent 상태 변경 → Mermaid 즉시 갱신
                            _refresh(True)

                        elif tool_name == "check_async_task":
                            payload = _parse_check_payload(tool_content_full)
                            idx = _find_tracked_by_task_id(payload.get("thread_id", ""))
                            if idx is None and tracked_idx is not None:
                                idx = tracked_idx
                            status = payload.get("status", "").lower()
                            if status == "success":
                                summary = payload.get("result", "")
                                _track_complete_by_index(idx, success=True, result_summary=summary, status="completed")
                                _set_task_action(idx, "check")
                                _evt("✅", f"Async task completed: {_escape_html(summary[:80])}", "done")
                            elif status == "cancelled":
                                summary = payload.get("error", "") or status
                                _track_complete_by_index(idx, success=False, result_summary=summary, status="cancelled")
                                _set_task_action(idx, "cancel")
                                _evt("🛑", f"Async task cancelled: {_escape_html(summary[:80])}", "error")
                            elif status == "error":
                                summary = payload.get("error", "") or status
                                _track_complete_by_index(idx, success=False, result_summary=summary, status="failed")
                                _set_task_action(idx, "check")
                                _evt("❌", f"Async task {status}: {_escape_html(summary[:80])}", "error")
                            else:
                                _set_task_action(idx, "check")
                                _evt("📡", f"Async task still {status or 'running'}", "subagent")
                            _refresh(True)

                        elif tool_name == "update_async_task":
                            task_id = _parse_task_id(tool_content_full)
                            idx = _find_tracked_by_task_id(task_id)
                            if idx is None and tracked_idx is not None:
                                idx = tracked_idx
                            if idx is not None:
                                tracked_agents[idx]["status"] = "running"
                                _set_task_action(idx, "update")
                            _evt("✏️", f"Async task updated: {_escape_html((task_id or tool_content)[:80])}", "subagent")
                            _refresh(True)

                        elif tool_name == "cancel_async_task":
                            task_id = _parse_task_id(tool_content_full)
                            idx = _find_tracked_by_task_id(task_id)
                            if idx is None and tracked_idx is not None:
                                idx = tracked_idx
                            _track_complete_by_index(idx, success=False, result_summary="cancelled", status="cancelled")
                            _set_task_action(idx, "cancel")
                            _evt("🛑", f"Async task cancelled: {_escape_html((task_id or tool_content)[:80])}", "error")
                            _refresh(True)

                        elif tool_name == "list_async_tasks":
                            _apply_list_async_tasks(tool_content_full)
                            count = tool_content_full.count("task_id:")
                            if tracked_idx is not None:
                                _set_task_action(tracked_idx, action or "list")
                            _evt("📋", f"Async task list returned ({count} entries)", "subagent")
                            _refresh(True)

                        elif "memory_store" in tool_name:
                            _evt("✅", f"Memory stored: {_escape_html(tool_content[:60])}", "done")

                        elif "memory_search" in tool_name:
                            n_results = tool_content.count("---") + (1 if tool_content.strip() and "No relevant" not in tool_content else 0)
                            _evt("✅", f"Memory search returned {n_results} results", "done")

                        else:
                            preview = _escape_html(tool_content[:60])
                            _evt("✅", f"<b>{tool_name}</b> → {preview}", "done")

                # 매 chunk마다 모델명 갱신 시도
                if fallback_mw.current_model:
                    current_model = fallback_mw.current_model
                _drain_runtime_events(refresh=True)

        had_async_subagents = bool(tracked_agents) or bool(_capture_async_tasks())
        if stream_cutoff_for_async:
            _evt(
                "⏳",
                f"Proceeding with {len(tracked_agents)} launched async task(s) despite main loop cutoff",
                "subagent",
                refresh=False,
            )
        unfinished = _unfinished_async_tasks()
        if launched_async and not unfinished:
            grace_deadline = time.time() + 2.0
            while time.time() < grace_deadline and not unfinished:
                _poll_subagent_outputs()
                time.sleep(0.1)
                unfinished = _unfinished_async_tasks()
        last_wait_count = -1
        while unfinished:
            if _is_refresh_requested():
                _record_loop("stopped", "refresh_requested", next_action="user_refresh", policy_type="safe_stop")
                _evt("🛑", "Refresh requested — stopping current run", "error", refresh=False)
                _cleanup_turn_subagents_async()
                return False
            if _is_stop_requested():
                _record_loop("stopped", "stop_requested", next_action="user_stop", policy_type="safe_stop")
                _evt("🛑", "Stop requested — halting current run", "error", refresh=False)
                _cleanup_turn_subagents_async()
                _refresh(False, result=final_text, model=current_model)
                return bool(final_text)
            if len(unfinished) != last_wait_count:
                _evt(
                    "⏳",
                    f"Waiting for {len(unfinished)} async task(s) to finish before closing this user session",
                    "subagent",
                    refresh=False,
                )
                for row in unfinished:
                    task_fragment = ""
                    if row.get("task_id"):
                        task_fragment = f", task_id={_escape_html(str(row.get('task_id', ''))[:12])}..."
                    _evt(
                        "🔎",
                        f"Pending {_escape_html(_agent_display_name(row))}: "
                        f"status={_escape_html(str(row.get('status', 'running')))}{task_fragment}",
                        "subagent",
                        refresh=False,
                    )
                last_wait_count = len(unfinished)
            _poll_subagent_outputs()
            _maybe_schedule_alternate_subagent()
            _render_agent_status("Waiting for async subagents to finish...")
            time.sleep(SUBAGENT_POLL_INTERVAL_SECONDS)
            unfinished = _unfinished_async_tasks()

        if not unfinished and _maybe_force_remember_subagent():
            had_async_subagents = True
            unfinished = _unfinished_async_tasks()
            while unfinished:
                if len(unfinished) != last_wait_count:
                    _evt(
                        "⏳",
                        f"Waiting for {len(unfinished)} async task(s) to finish before closing this user session",
                        "subagent",
                        refresh=False,
                    )
                    last_wait_count = len(unfinished)
                _poll_subagent_outputs()
                time.sleep(SUBAGENT_POLL_INTERVAL_SECONDS)
                unfinished = _unfinished_async_tasks()

        if _pause_for_human_review_if_needed():
            return False

        if had_async_subagents and not unfinished:
            _evt("🧩", "All async subagents finished. Collecting results into one final answer", "subagent", refresh=False)
            _render_agent_status("Collecting completed async task results...")
            completed_report = _build_completed_subagent_report(tracked_agents)
            human_review = st.session_state.pop("_human_review_resolution", None)
            human_review_note = ""
            if human_review:
                human_review_note = (
                    "\n\nHuman review resolution:\n"
                    f"- approved={human_review.get('approved')}\n"
                    f"- layer={human_review.get('target_layer', '')}\n"
                    f"- selected_paths={human_review.get('selected_paths', [])}\n"
                    f"- stored_ids={human_review.get('stored_ids', [])}\n"
                )
            _evt("📦", "Completed SubAgent results prepared for Main Agent aggregation", "subagent", refresh=False)
            _evt("🧾", f"Aggregation ledger size: {len(completed_report):,} chars", "subagent", refresh=False)
            followup = (
                "All async subagent tasks from this user turn should now be finished. "
                "Below is the completed SubAgent result ledger gathered by the WebUI runtime. "
                "Use it as the primary aggregation source, and use live async task tools only if you need to verify details.\n\n"
                f"{completed_report}{human_review_note}\n\n"
                "then produce one final synthesized answer for the user. "
                "Do not launch new async tasks unless absolutely required."
            )
            try:
                loop_guard.reset()
                result = agent.invoke(
                    {"messages": [HumanMessage(content=followup)]},
                    config=config,
                )
                for msg in reversed(result.get("messages", [])):
                    if _msg_type(msg) == "ai" and _msg_content(msg):
                        content = _msg_content(msg)
                        final_text = content if isinstance(content, str) else str(content)
                        break
            except Exception as exc:  # noqa: BLE001
                _evt("⚠️", f"Final async aggregation failed: {_escape_html(str(exc))}", "error", refresh=False)
                final_text = _synthesize_subagent_results(tracked_agents)
                _record_loop(
                    "degraded",
                    "aggregation_fallback",
                    failure_reason=str(exc),
                    next_action="return_subagent_summary",
                    policy_type="no_progress_loop",
                )
            _poll_subagent_outputs()

        # ── Extract final text if not captured ────────────

        if not final_text:
            try:
                state = agent.get_state(config)
                for msg in reversed(state.values.get("messages", [])):
                    if _msg_type(msg) == "ai" and _msg_content(msg):
                        content = _msg_content(msg)
                        final_text = (
                            content
                            if isinstance(content, str)
                            else str(content)
                        )
                        if not streamed_text:
                            streamed_text = final_text
                        break
            except Exception:
                pass

        if not final_text:
            final_text = "*(No response generated)*"
            _record_loop(
                "degraded",
                "empty_response",
                failure_reason="No final response generated",
                next_action="return_placeholder",
                policy_type="no_progress_loop",
            )

        current_model = fallback_mw.current_model or current_model or "unknown"
        _model_tag = f"<div class='agent-bubble-model'>🧠 {_escape_html(current_model)}</div>"
        elapsed_s = f"{time.time() - t_start:.1f}"
        _evt(
            "🏁",
            f"Completed — <b>{current_model}</b> · {step_count} steps · {elapsed_s}s · {len(final_text):,} chars",
            "done",
            refresh=False,
        )
        _record_loop("completed", "finalized")
        # 최종 Mermaid를 먼저 갱신한 뒤 답변 bubble을 채워서 둘이 같이 나타나는 느낌을 준다.
        _refresh(False, result=final_text, model=current_model)
        with result_ph:
            safe_final_text = _escape_bubble_html(final_text)
            bubble_style = _bubble_width_style(final_text, "agent")
            st.markdown(
                f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{bubble_style}'>{safe_final_text}{_model_tag}</div></div>",
                unsafe_allow_html=True,
            )

        _persist_history_snapshot(final_text, current_model)
        _cleanup_turn_subagents_async()
        _finalize_and_rerun()
        return True

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Agent error: %s\n%s", e, tb)
        elapsed_s = f"{time.time() - t_start:.1f}"
        policy_type = "external_api_error" if isinstance(e, httpx.HTTPError) else "tool_call_error"
        _record_loop("failed", "exception", failure_reason=str(e), next_action="safe_stop", policy_type=policy_type)
        _evt("❌", f"Error after {elapsed_s}s: {_escape_html(str(e))}", "error")
        with result_ph:
            st.error(f"Error: {e}")
            with st.expander("Traceback"):
                st.code(tb, language="python")
        _refresh(False)
        err_agents = _agents_state()
        err_mdef, err_tips = _build_mermaid(err_agents, False, prompt)
        err_html = _build_page_html(
            err_mdef,
            list(events),
            False,
            tooltips=err_tips,
        )
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": f"Error: {e}",
            "model": None,
            "tools_used": [],
            "mermaid_def": err_mdef,
            "mermaid_html": err_html,
            "mermaid_tooltips": err_tips,
            "mermaid_events": list(events),
            "num_agents": len(err_agents),
            "async_task_snapshot": _capture_async_tasks(),
            "subagent_history_snapshot": _capture_subagent_history_snapshot(err_agents, state_store),
            "aggregated_subagent_report": _build_completed_subagent_report(err_agents),
            "working_dir": str(st.session_state.get("_active_query_workdir", "") or Path.cwd()),
            "test_prompt_label": st.session_state.get("_active_test_prompt_label"),
        })
        st.session_state["_is_running"] = False
        st.session_state["_has_result"] = True
        _cleanup_turn_subagents_async()
        _clear_live_turn_state()
        return True


# ─────────────────────────────────────────────────────────
#  Page renderer
# ─────────────────────────────────────────────────────────

def render_chat() -> None:
    """Render the Chat page.

    Layout:
      ┌──────────────────────────────────────────────────────┐
      │  (idle) Danny's Coding AI Agent  (중앙 타이틀)       │
      │  (active) 🤖 Agent answer                             │
      │           🔍 Agent 동작 분석                          │
      │           👤 User prompt                              │
      ├──────────────────────────────────────────────────────┤
      │  📌 PROMPT 프리셋 버튼                                │
      │  ┌──────────── Chat Input Card ───────────────┐      │
      │  │  📝 입력창      ⏹ Stop      🚀 Send        │      │
      │  └────────────────────────────────────────────┘      │
      └──────────────────────────────────────────────────────┘
    """
    comp = st.session_state.get("agent_components")
    if not comp:
        st.warning("Agent not initialized.")
        return

    if not st.session_state.get("_mermaid_prewarmed", False):
        st.session_state["_mermaid_prewarmed"] = True
        components.html(_build_prewarm_html(), height=1, scrolling=False)

    # ── Session state defaults ────────────────────────────
    for k, v in [
        ("_is_running", False),
        ("_has_result", False),
        ("_stop_requested", False),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    # Pending prompt: set by Send button, consumed this render cycle
    pending = st.session_state.pop("_pending_prompt", None)
    if pending:
        st.session_state["_is_running"] = True
    is_running = st.session_state["_is_running"]

    # 전송 후 입력창 비우기 — 위젯 렌더링 전에 처리해야 함
    if st.session_state.pop("_clear_prompt", False):
        st.session_state["_prompt_area"] = ""
    preset_prompt = st.session_state.pop("_preset_prompt", None)
    if preset_prompt is not None:
        st.session_state["_prompt_area"] = preset_prompt
    live_turn = st.session_state.get("_live_turn_state") or {}

    # ── Page-level CSS ────────────────────────────────────
    st.markdown("""
    <style>
    section[data-testid="stMain"] .block-container {
        padding-top: 1.2rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100%;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
    }
    /* Chat bubble styles — User (right, blue) */
    .user-bubble {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 16px 16px 4px 16px;
        padding: 14px 18px;
        font-size: 0.95em;
        color: #1e40af;
        line-height: 1.55;
        word-break: break-word;
        box-shadow: 0 4px 14px rgba(59, 130, 246, .08);
    }
    .user-bubble-label {
        font-size: .75em;
        font-weight: 700;
        color: #3b82f6;
        margin-bottom: 4px;
        letter-spacing: .3px;
        text-align: right;
        padding-right: .25rem;
    }
    /* Chat bubble styles — Agent (left, green) */
    .agent-bubble {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 16px 16px 16px 4px;
        padding: 14px 18px;
        font-size: 0.95em;
        color: #166534;
        line-height: 1.55;
        word-break: break-word;
        overflow: visible;
        box-shadow: 0 4px 14px rgba(22, 163, 74, .08);
    }
    .agent-bubble-label {
        font-size: .75em;
        font-weight: 700;
        color: #16a34a;
        margin-bottom: 4px;
        margin-top: 22px;
        letter-spacing: .3px;
        padding-left: .25rem;
    }
    .agent-bubble-model {
        font-size: .7em;
        color: #6b7280;
        margin-top: 8px;
    }
    .hitl-review-card {
        background: linear-gradient(135deg, rgba(127,29,29,.08), rgba(249,115,22,.12));
        border: 2px solid rgba(220,38,38,.45);
        border-radius: 16px;
        padding: 14px 16px;
        margin: 12px 0;
        box-shadow: 0 8px 24px rgba(220,38,38,.12);
    }
    .hitl-review-title {
        font-size: .92em;
        font-weight: 800;
        color: #991b1b;
        letter-spacing: .35px;
        margin-bottom: 6px;
        text-transform: uppercase;
    }
    .hitl-review-text {
        font-size: .84em;
        color: #7f1d1d;
        line-height: 1.55;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #bbf7d0;
        border-radius: 16px;
        background: #f0fdf4;
        box-shadow: 0 4px 14px rgba(22, 163, 74, .08);
    }
    div[data-testid="stExpander"] summary {
        color: #166534;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Determine conversation state ─────────────────────
    has_conversation = bool(st.session_state.chat_messages) or pending or is_running or bool(live_turn)

    # ── 1. Main content area ─────────────────────────────
    graph_ph = st.empty()
    result_ph_ref = {"ph": None}
    subagent_ph_ref = {"ph": None}

    if not has_conversation:
        # ── Idle state: centered title (no heavy Mermaid render) ──
        st.markdown(
            "<div style='text-align:center;padding:100px 20px 60px'>"
            "<h1 style='color:#1e293b;font-size:2em;margin-bottom:8px'>"
            "Danny's Coding AI Agent</h1>"
            "<p style='color:#94a3b8;font-size:1.05em'>"
            "메시지를 입력하거나 프롬프트를 클릭하세요</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Lightweight hidden placeholders (no iframe rendering)
        result_ph_ref["ph"] = st.empty()
        subagent_ph_ref["ph"] = st.empty()

    else:
        # ── Active conversation: chat-style layout ────────

        # Show previous conversation pairs (history within session)
        # Layout: Agent answer → Mermaid analysis → User prompt.
        _last_user_content = ""
        _assistant_total = sum(
            1 for msg in st.session_state.chat_messages
            if msg["role"] == "assistant"
        )
        _assistant_idx = 0
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                _last_user_content = msg["content"]

            elif msg["role"] == "assistant":
                _assistant_idx += 1
                _is_latest_assistant = _assistant_idx == _assistant_total

                model_html = ""
                if msg.get("model"):
                    model_html = f"<div class='agent-bubble-model'>🧠 {_escape_html(msg['model'])}</div>"
                safe_content = _escape_bubble_html(msg["content"])
                agent_style = _bubble_width_style(msg["content"], "agent")
                st.markdown(
                    f"<div class='agent-bubble-label'>🤖 Agent</div>"
                    f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{agent_style}'>{safe_content}{model_html}</div></div>",
                    unsafe_allow_html=True,
                )
                msg_workdir = str(msg.get("working_dir", "") or "")
                if msg_workdir and st.toggle(
                    "Download Workspace",
                    key=f"_show_workspace_hist_{_assistant_idx}",
                    value=False,
                ):
                    st.caption(msg_workdir)
                    workdir_zip = _get_cached_workdir_zip_bytes(msg_workdir)
                    if workdir_zip:
                        zip_name = f"{Path(msg_workdir).name or 'query_workspace'}.zip"
                        st.download_button(
                            "Download Workspace (.zip)",
                            data=workdir_zip,
                            file_name=zip_name,
                            mime="application/zip",
                            key=f"download_workdir_{_assistant_idx}",
                        )
                    else:
                        st.caption("Workspace is empty or unavailable.")

                if msg_workdir and st.toggle(
                    "Remember Review",
                    key=f"_show_remember_review_hist_{_assistant_idx}",
                    value=False,
                ):
                    if "remember_candidates" not in msg:
                        remember_candidates = _parse_remember_candidates_from_history(
                            msg.get("subagent_history_snapshot") or [],
                            msg_workdir,
                        )
                        if not remember_candidates:
                            remember_candidates = _select_remember_candidates(msg_workdir)
                        msg["remember_candidates"] = remember_candidates
                    msg.setdefault("remember_review_status", "pending")
                    candidates = msg.get("remember_candidates") or []
                    if not candidates:
                        st.caption("remember agent did not find any strong memory candidates in this workspace.")
                    else:
                        source = "remember subagent" if any(row.get("source") == "remember_subagent" for row in candidates) else "workspace heuristic fallback"
                        st.caption(f"Candidate source: {source}. Only this review path uses Human in the Loop.")
                        for row in candidates:
                            hist_cols = st.columns([6, 2])
                            with hist_cols[0]:
                                st.markdown(
                                    f"**{_escape_html(str(row.get('path', '')))}**  \n"
                                    f"<span style='color:#64748b;font-size:.86em'>{_escape_html(str(row.get('reason', '')))}</span>",
                                    unsafe_allow_html=True,
                                )
                            with hist_cols[1]:
                                file_bytes = _read_workspace_file_bytes(msg_workdir, str(row.get("path", "") or ""))
                                if file_bytes:
                                    st.download_button(
                                        "Download",
                                        data=file_bytes,
                                        file_name=Path(str(row.get('path', 'artifact'))).name,
                                        mime="application/octet-stream",
                                        key=f"hist_remember_download_{_assistant_idx}_{row.get('path', '')}",
                                        use_container_width=True,
                                    )
                        default_selection = [row["path"] for row in candidates[: min(5, len(candidates))]]
                        with st.form(f"remember_review_form_{_assistant_idx}"):
                            selected_paths = st.multiselect(
                                "Approve files for long-term memory",
                                options=[row["path"] for row in candidates],
                                default=msg.get("remember_selected_paths", default_selection),
                                format_func=lambda p: next(
                                    (
                                        f"{row['path']} · {row['reason']}"
                                        for row in candidates if row["path"] == p
                                    ),
                                    p,
                                ),
                            )
                            target_layer = st.selectbox(
                                "Memory Layer",
                                options=["project/context", "domain/knowledge", "user/profile"],
                                index=["project/context", "domain/knowledge", "user/profile"].index(
                                    str(msg.get("remember_target_layer", "project/context"))
                                ),
                            )
                            approve = st.form_submit_button("Approve Selected for Memory", use_container_width=True)
                        if approve:
                            stored_ids = _store_approved_memory_files(msg_workdir, selected_paths, target_layer)
                            msg["remember_selected_paths"] = list(selected_paths)
                            msg["remember_target_layer"] = target_layer
                            msg["remember_review_status"] = "approved"
                            msg["remember_record_ids"] = stored_ids
                            if stored_ids:
                                st.success(f"Stored {len(stored_ids)} approved file(s) into long-term memory.")
                            else:
                                st.warning("No files were stored. Check whether the selected files still exist.")
                        elif msg.get("remember_review_status") == "approved":
                            st.success(
                                f"Approved files stored: {len(msg.get('remember_record_ids', []) or [])} · "
                                f"layer={msg.get('remember_target_layer', 'project/context')}"
                            )

                if msg.get("mermaid_def"):
                    _hist_html = msg.get("mermaid_html") or _build_page_html(
                        msg["mermaid_def"],
                        msg.get("mermaid_events", []),
                        False,
                        tooltips=msg.get("mermaid_tooltips", {}),
                    )
                    _h = max(560, 340 + msg.get("num_agents", 0) * 90 + min(len(msg.get("mermaid_events", [])), 24) * 12)
                    if st.toggle(
                        "Agent 동작 분석",
                        key=f"_show_analysis_hist_{_assistant_idx}",
                        value=_is_latest_assistant,
                    ):
                        components.html(_hist_html, height=_h, scrolling=True)
                        _history = msg.get("subagent_history_snapshot") or []
                        aggregated_report = str(msg.get("aggregated_subagent_report", "") or "").strip()
                        if aggregated_report and aggregated_report != "No completed SubAgent results were captured.":
                            st.markdown(
                                "<div style='background:#fff;border:1px solid #cbd5e1;border-radius:12px;padding:10px 12px;margin:8px 0'>"
                                "<div style='font-size:.78em;font-weight:700;color:#334155;margin-bottom:6px'>Main Agent Aggregation Input</div>"
                                f"<div style='font-size:.82em;color:#475569;white-space:pre-wrap'>{_escape_bubble_html(aggregated_report)}</div>"
                                "</div>",
                                unsafe_allow_html=True,
                            )
                        if _history:
                            st.caption(f"Tracked subagents at completion: {len(_history)}")
                            for _row in _history[:6]:
                                endpoint = str(_row.get("endpoint", "") or "")
                                pid = _row.get("pid")
                                state = str(_row.get("durable_state", "") or _row.get("status", "unknown"))
                                lifecycle = " → ".join(
                                    str(ev.get("state", "") or "")
                                    for ev in (_row.get("lifecycle_events") or [])
                                    if ev.get("state")
                                )
                                meta = endpoint
                                if pid:
                                    meta = f"{meta}<br>pid {pid}" if meta else f"pid {pid}"
                                st.markdown(
                                    "<div style='background:#fff;border:1px solid #d1d5db;border-radius:12px;"
                                    "padding:8px 10px;margin:6px 0'>"
                                    f"<div style='font-size:.84em;font-weight:700;color:#166534'>{_escape_html(_agent_display_name(_row))} "
                                    f"[{_escape_html(state)}]</div>"
                                    f"<div style='font-size:.72em;color:#64748b'>{meta}</div>"
                                    f"<div style='font-size:.78em;color:#334155;margin-top:4px'>{_escape_html(str(_row.get('task_summary', '') or _row.get('query', '') or ''))}</div>"
                                    f"{f'<div style=\"font-size:.72em;color:#64748b;margin-top:4px\">{_escape_html(lifecycle)}</div>' if lifecycle else ''}"
                                    "</div>",
                                    unsafe_allow_html=True,
                                )

                st.markdown(
                    f"<div class='user-bubble-label'>👤 User</div>"
                    f"{_bubble_wrap_open('user')}<div class='user-bubble' style='{_bubble_width_style(_last_user_content, 'user')}'>{_escape_bubble_html(_last_user_content)}</div></div>",
                    unsafe_allow_html=True,
                )

                st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:12px 0'>",
                            unsafe_allow_html=True)

        # ── Live interaction area (current pending/running) ──
        # Layout: Agent progress/answer → Mermaid analysis → User prompt.
        if pending or is_running or live_turn:
            st.markdown(
                "<div class='agent-bubble-label'>🤖 Agent</div>",
                unsafe_allow_html=True,
            )
            result_ph_ref["ph"] = st.empty()
            live_result = str(live_turn.get("result_text", "") or "")
            live_model = str(live_turn.get("model", "") or "")
            hold_final_answer = bool(live_turn.get("hold_final_answer", False))
            live_model_html = (
                f"<div class='agent-bubble-model'>🧠 {_escape_html(live_model)}</div>"
                if live_model else ""
            )
            if hold_final_answer:
                hold_text = "SubAgent execution and Remember review are still in progress. Final answer will appear after approval."
                result_ph_ref["ph"].markdown(
                    f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{_bubble_width_style(hold_text, 'agent')}'>"
                    f"{_escape_bubble_html(hold_text)}"
                    "<div class='agent-bubble-model'>Waiting for Human In the Loop</div>"
                    "</div></div>",
                    unsafe_allow_html=True,
                )
            elif live_result:
                result_ph_ref["ph"].markdown(
                    f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{_bubble_width_style(live_result, 'agent')}'>"
                    f"{_escape_bubble_html(live_result)}"
                    f"{live_model_html}"
                    "</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                result_ph_ref["ph"].markdown(
                    f"{_bubble_wrap_open('agent')}<div class='agent-bubble' style='{_bubble_width_style('Thinking...', 'agent')}'>"
                    "Thinking...<div class='agent-bubble-model'>Waiting for model output</div>"
                    "</div></div>",
                    unsafe_allow_html=True,
                )

            if st.toggle("Agent 동작 분석", key="_show_analysis_live", value=True):
                graph_ph = st.empty()
                live_agents = live_turn.get("agents") or []
                live_events = live_turn.get("events") or []
                live_prompt = str(live_turn.get("prompt", "") or pending or "")
                live_working = bool(live_turn.get("working", True))
                idle_def, tips = _build_mermaid(
                    live_agents,
                    live_working,
                    live_prompt,
                    result_text=live_result if not live_working else "",
                    model_name=live_model,
                )
                _render_mermaid(
                    graph_ph,
                    idle_def,
                    live_events,
                    live_working,
                    num_agents=len(live_agents),
                    tooltips=tips,
                )

                subagent_ph_ref["ph"] = st.empty()
                if live_agents:
                    parts = [
                        "<div style='margin:8px 0 14px'>"
                        "<div style='font-size:.78em;font-weight:700;color:#64748b;letter-spacing:.35px;margin-bottom:6px'>"
                        "SubAgent Streaming Output</div>"
                    ]
                    for row in live_agents:
                        endpoint = row.get("endpoint") or ""
                        pid = row.get("pid")
                        model = row.get("model") or ""
                        status = row.get("durable_state") or row.get("status", "running")
                        content = row.get("live_output") or row.get("result_summary") or "waiting for output..."
                        parts.append(
                            "<div style='background:#fff;border:1px solid #bbf7d0;border-radius:14px;"
                            "padding:10px 12px;margin-bottom:8px;box-shadow:0 4px 14px rgba(22,163,74,.05)'>"
                            f"<div style='font-size:.8em;font-weight:700;color:#166534;margin-bottom:4px'>{_escape_html(_agent_display_name(row))}</div>"
                            f"<div style='font-size:.72em;color:#64748b;margin-bottom:6px'>{_escape_html(str(endpoint))}"
                            f"{f'<br>pid {pid}' if pid else ''}"
                            f"{f'<br>model { _escape_html(str(model)) }' if model else ''} · {_escape_html(str(status))}</div>"
                            f"<div style='font-size:.88em;color:#14532d;white-space:pre-wrap;max-height:180px;overflow-y:auto'>{_escape_bubble_html(str(content))}</div>"
                            "</div>"
                        )
                    parts.append("</div>")
                    subagent_ph_ref["ph"].markdown("".join(parts), unsafe_allow_html=True)
                else:
                    subagent_ph_ref["ph"] = st.empty()

                _render_live_remember_review()

            prompt_display = live_prompt or pending or "(processing…)"
            st.markdown(
                f"<div class='user-bubble-label'>👤 User</div>"
                f"{_bubble_wrap_open('user')}<div class='user-bubble' style='{_bubble_width_style(prompt_display, 'user')}'>{_escape_bubble_html(prompt_display)}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            result_ph_ref["ph"] = st.empty()

    # ── Bottom section: Prompt presets + Input ────────────
    bottom_controls = st.empty()

    def _queue_current_prompt() -> None:
        raw = str(st.session_state.get("_prompt_area", "") or "").strip()
        if not raw or st.session_state.get("_is_running"):
            return
        matched_label = next(
            (
                label
                for label, prompt_text in {**TEST_PROMPTS, **SCENARIO_PROMPTS}.items()
                if prompt_text == raw
            ),
            None,
        )
        st.session_state["_active_test_prompt_label"] = matched_label
        st.session_state["_pending_prompt"] = raw
        st.session_state["_clear_prompt"] = True

    with bottom_controls.container():
        st.markdown(
            "<hr style='border:none;border-top:1px solid #e2e8f0;margin:16px 0 8px'>",
            unsafe_allow_html=True,
        )

        show_test_prompts = st.toggle(
            "Input Test Prompt (Module Function Test)",
            key="_show_test_prompts",
            value=False,
        )
        if show_test_prompts:
            st.markdown(
                "<div style='background:#fff;padding:4px 0 2px'>",
                unsafe_allow_html=True,
            )
            labels = list(TEST_PROMPTS.keys())
            pills_value = None
            if hasattr(st, "pills"):
                pills_value = st.pills(
                    "Test Prompt",
                    options=labels,
                    selection_mode="single",
                    label_visibility="collapsed",
                    disabled=is_running,
                    key="_test_prompt_pills",
                )
            else:
                pills_value = st.radio(
                    "Test Prompt",
                    options=labels,
                    horizontal=True,
                    label_visibility="collapsed",
                    disabled=is_running,
                    key="_test_prompt_radio",
                )

            if pills_value:
                st.caption(TEST_PROMPT_DETAILS.get(pills_value, ""))
                apply_col, _ = st.columns([1, 8])
                with apply_col:
                    use_clicked = st.button(
                        "Use",
                        key=f"use_test_prompt_{pills_value}",
                        disabled=is_running,
                        use_container_width=True,
                    )
                if use_clicked:
                    st.session_state["_preset_prompt"] = TEST_PROMPTS[pills_value]
                    st.session_state["_active_test_prompt_label"] = pills_value
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        show_test_scenarios = st.toggle(
            "Input Test Scenario",
            key="_show_test_scenarios",
            value=False,
        )
        if show_test_scenarios:
            st.markdown(
                "<div style='background:#fff;padding:4px 0 2px'>",
                unsafe_allow_html=True,
            )
            scenario_labels = list(SCENARIO_PROMPTS.keys())
            scenario_value = None
            if hasattr(st, "pills"):
                scenario_value = st.pills(
                    "Input Test Scenario",
                    options=scenario_labels,
                    selection_mode="single",
                    label_visibility="collapsed",
                    disabled=is_running,
                    key="_test_scenario_pills",
                )
            else:
                scenario_value = st.radio(
                    "Input Test Scenario",
                    options=scenario_labels,
                    horizontal=True,
                    label_visibility="collapsed",
                    disabled=is_running,
                    key="_test_scenario_radio",
                )

            if scenario_value:
                st.caption(SCENARIO_PROMPT_DETAILS.get(scenario_value, ""))
                apply_col, _ = st.columns([1, 8])
                with apply_col:
                    use_scenario_clicked = st.button(
                        "Use",
                        key=f"use_test_scenario_{scenario_value}",
                        disabled=is_running,
                        use_container_width=True,
                    )
                if use_scenario_clicked:
                    st.session_state["_preset_prompt"] = SCENARIO_PROMPTS[scenario_value]
                    st.session_state["_active_test_prompt_label"] = scenario_value
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        input_col, stop_col, send_col = st.columns([12, 1, 1])
        with input_col:
            st.text_input(
                "prompt",
                key="_prompt_area",
                disabled=is_running,
                label_visibility="collapsed",
                placeholder="Ask me anything about coding…",
                on_change=_queue_current_prompt,
            )
        with stop_col:
            stop_clicked = st.button(
                "■",
                key="stop_icon_button",
                use_container_width=True,
                disabled=not is_running,
                type="secondary",
            )
        with send_col:
            send_clicked = st.button(
                "↑",
                key="send_icon_button",
                use_container_width=True,
                disabled=is_running,
                type="primary",
            )

    if send_clicked:
        _queue_current_prompt()
        if st.session_state.get("_pending_prompt"):
            st.rerun()
        st.info("메시지를 입력한 뒤 전송하세요.")
    if stop_clicked:
        st.session_state["_stop_requested"] = True
        st.rerun()

    # ── Pending prompt 실행 / Async monitor resume ───────────────────────────────
    if pending:
        bottom_controls.empty()
        st.session_state["_refresh_requested"] = False
        st.session_state["_stop_requested"] = False
        st.session_state["_is_running"] = True
        query_workdir = _create_query_workdir(Path.cwd())
        st.session_state["_active_query_workdir"] = str(query_workdir)
        st.session_state["_active_query_started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.agent_components = _prepare_query_runtime(query_workdir)
        completed = False
        try:
            completed = _stream_response(pending, graph_ph, result_ph_ref["ph"], subagent_ph_ref["ph"])
        finally:
            if not st.session_state.get("_monitor_async_after_answer"):
                st.session_state["_is_running"] = False
                st.session_state["_has_result"] = completed
            st.session_state["_stop_requested"] = False
            if not st.session_state.get("_monitor_async_after_answer"):
                # 실행 완료 후 rerun → 입력창 활성화
                st.rerun()
    elif st.session_state.get("_pending_human_review"):
        st.session_state["_is_running"] = True
    elif st.session_state.get("_monitor_async_after_answer"):
        st.session_state["_is_running"] = True
        _resume_async_monitoring(graph_ph, result_ph_ref["ph"], subagent_ph_ref["ph"])
