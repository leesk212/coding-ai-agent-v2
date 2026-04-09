"""Danny's Coding AI Agent — Single-page WebUI."""

import logging
import os
import threading
import time
import traceback
import uuid
from pathlib import Path

import streamlit as st

from coding_agent.config import ModelSpec, settings

st.set_page_config(
    page_title="Danny's Coding AI Agent",
    page_icon="data:,",
    layout="wide",
    initial_sidebar_state="collapsed",  # sidebar hidden via CSS
)

logging.getLogger("coding_agent").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stStatusWidget"] {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDeployButton"] {display: none !important;}
    .stDeployButton {display: none !important;}
    /* Sidebar completely hidden */
    [data-testid="stSidebar"] {display:none !important;}
</style>
""", unsafe_allow_html=True)


def _init_state():
    defaults = {
        "agent_components": None,
        "chat_messages": [],
        "initialized": False,
        "init_error": None,
        "page": "chat",
        "mem_count": 0,
        "prewarm_bundle": None,
        "prewarm_complete": False,
        "prewarm_error": None,
        "prewarm_started": False,
        "prewarm_progress": 0,
        "prewarm_logs": [],
        "prewarm_status": None,
        "startup_setup_complete": False,
        "_conversation_thread_id": f"webui-{uuid.uuid4().hex}",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_chat_state() -> None:
    st.session_state["_refresh_requested"] = True
    st.session_state["_stop_requested"] = False
    st.session_state["_is_running"] = False
    st.session_state["_has_result"] = False
    st.session_state["chat_messages"] = []
    st.session_state["_prompt_area"] = ""
    st.session_state["_clear_prompt"] = True
    st.session_state["_conversation_thread_id"] = f"webui-{uuid.uuid4().hex}"
    st.session_state.pop("_active_query_workdir", None)
    st.session_state.pop("_pending_prompt", None)
    st.session_state.pop("_live_turn_state", None)
    st.session_state.pop("_mermaid_render_seq", None)


def _persist_runtime_settings(
    *,
    openrouter_key: str,
    fallback_mode: str,
    ollama_url: str,
    local_model: str,
    openai_key: str,
    openai_model: str,
) -> None:
    settings.openrouter_api_key = openrouter_key.strip()
    settings.fallback_mode = fallback_mode.strip().lower()
    settings.ollama_base_url = ollama_url.strip() or settings.ollama_base_url
    settings.local_fallback_model = ModelSpec(
        name=(local_model.strip() or settings.local_fallback_model.name),
        provider="ollama",
        priority=99,
    )
    settings.openai_api_key = openai_key.strip()
    settings.openai_fallback_model = ModelSpec(
        name=(openai_model.strip() or settings.openai_fallback_model.name),
        provider="openai",
        priority=99,
    )

    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key
    os.environ["FALLBACK_MODE"] = settings.fallback_mode
    os.environ["OLLAMA_BASE_URL"] = settings.ollama_base_url
    os.environ["LOCAL_FALLBACK_MODEL"] = settings.local_fallback_model.name
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    os.environ["OPENAI_FALLBACK_MODEL"] = settings.openai_fallback_model.name


def _render_startup_setup(area=None) -> None:
    host = area or st
    with host.container():
        st.markdown(
            "<h2 style='text-align:center'>Danny's Coding AI Agent</h2>"
            "<p style='text-align:center; color:#666'>"
            "Enter your model credentials while DeepAgents initializes in the background."
            "</p>",
            unsafe_allow_html=True,
        )
        with st.form("startup_setup_form", clear_on_submit=False):
            st.subheader("Model Access")
            openrouter_key = st.text_input(
                "OpenRouter API Key",
                value=settings.openrouter_api_key or "",
                type="password",
                help="Required. Danny's Chat will not initialize before this is set.",
            )
            fallback_mode = st.selectbox(
                "Fallback",
                options=["none", "local", "openai"],
                index=["none", "local", "openai"].index(
                    settings.fallback_mode if settings.fallback_mode in {"none", "local", "openai"} else "local"
                ),
                help="Use no fallback, a local Ollama model, or an OpenAI model when the primary model fails.",
            )

            if fallback_mode == "local":
                ollama_url = st.text_input(
                    "Local LLM URL",
                    value=settings.ollama_base_url,
                    help="Default: http://localhost:11434",
                )
                local_model = st.text_input(
                    "Local LLM Model",
                    value=settings.local_fallback_model.name,
                    help="Example: qwen2.5-coder:7b",
                )
                openai_key = settings.openai_api_key or ""
                openai_model = settings.openai_fallback_model.name
            elif fallback_mode == "openai":
                openai_key = st.text_input(
                    "OpenAI API Key",
                    value=settings.openai_api_key or "",
                    type="password",
                    help="Required when fallback is OpenAI.",
                )
                openai_model = st.text_input(
                    "OpenAI Fallback Model",
                    value=settings.openai_fallback_model.name,
                    help="Example: gpt-4o-mini",
                )
                ollama_url = settings.ollama_base_url
                local_model = settings.local_fallback_model.name
            else:
                ollama_url = settings.ollama_base_url
                local_model = settings.local_fallback_model.name
                openai_key = settings.openai_api_key or ""
                openai_model = settings.openai_fallback_model.name

            submitted = st.form_submit_button("Start Danny's Chat", type="primary", use_container_width=True)

        if not submitted:
            if st.session_state.get("prewarm_started"):
                _render_prewarm_status()
            else:
                st.caption("Starting DeepAgents background initialization…")
                _start_prewarm_if_needed()
            st.info("OpenRouter API key is required. DeepAgents prewarm is running in parallel.")
            st.stop()

        if not openrouter_key.strip():
            st.error("OpenRouter API key is required.")
            st.stop()
        if fallback_mode == "openai" and not openai_key.strip():
            st.error("OpenAI API key is required when OpenAI fallback is selected.")
            st.stop()

        _persist_runtime_settings(
            openrouter_key=openrouter_key,
            fallback_mode=fallback_mode,
            ollama_url=ollama_url,
            local_model=local_model,
            openai_key=openai_key,
            openai_model=openai_model,
        )
        st.session_state.startup_setup_complete = True
        st.session_state.agent_components = None
        st.session_state.initialized = False
        st.session_state.init_error = None
    if area is not None:
        area.empty()


def _start_prewarm_if_needed() -> None:
    if st.session_state.prewarm_started or st.session_state.prewarm_complete:
        return

    st.session_state.prewarm_started = True
    st.session_state.prewarm_progress = 1
    st.session_state.prewarm_logs = []
    st.session_state.prewarm_error = None
    st.session_state.prewarm_status = {
        "progress": 1,
        "complete": False,
        "error": None,
        "bundle": None,
    }

    logs = st.session_state.prewarm_logs
    status = st.session_state.prewarm_status

    def worker() -> None:
        t_init_start = time.time()

        def log(icon: str, msg: str, pct: int) -> None:
            ts = time.strftime("%H:%M:%S")
            elapsed = f"{time.time() - t_init_start:.1f}s"
            logs.append(f"[{ts}] (+{elapsed}) {icon} {msg}")
            status["progress"] = pct

        try:
            log("⚙️", "Loading configuration...", 10)
            log("🏗️", "Prewarming DeepAgents runtime...", 30)
            from coding_agent.runtime import prewarm_runtime_components

            bundle = prewarm_runtime_components(
                custom_settings=settings,
                cwd=Path.cwd(),
                progress_cb=lambda msg: log("   ", msg, 70),
            )
            status["bundle"] = bundle
            status["complete"] = True
            status["error"] = None
            log("✅", "DeepAgents runtime prewarm complete", 100)
        except Exception:
            status["error"] = traceback.format_exc()
            logs.append("[error] DeepAgents prewarm failed")

    thread = threading.Thread(target=worker, daemon=True, name="coding-agent-prewarm")
    thread.start()


def _render_prewarm_status() -> None:
    status = st.session_state.get("prewarm_status") or {}
    if status:
        st.session_state.prewarm_progress = int(status.get("progress", 0) or 0)
        st.session_state.prewarm_complete = bool(status.get("complete"))
        st.session_state.prewarm_error = status.get("error")
        if status.get("bundle") is not None:
            st.session_state.prewarm_bundle = status["bundle"]

    progress_val = int(st.session_state.get("prewarm_progress", 0) or 0)
    st.progress(max(0, min(progress_val, 100)))
    logs = st.session_state.get("prewarm_logs", []) or []
    if logs:
        st.code("\n".join(logs[-12:]), language="text")
    if st.session_state.get("prewarm_error"):
        st.error("DeepAgents prewarm failed.")
        st.code(st.session_state.prewarm_error, language="python")
        st.stop()


def _init_agent(area=None):
    if st.session_state.agent_components is not None:
        return

    init_area = area or st.empty()
    with init_area.container():
        st.markdown(
            "<h2 style='text-align:center'>Danny's Coding AI Agent</h2>"
            "<p style='text-align:center; color:#888'>Loading...</p>",
            unsafe_allow_html=True,
        )
        progress = st.progress(0)
        log_area = st.empty()
        logs = []

        t_init_start = time.time()

        def log(icon, msg, pct):
            ts = time.strftime("%H:%M:%S")
            elapsed = f"{time.time() - t_init_start:.1f}s"
            logs.append(f"[{ts}] (+{elapsed}) {icon} {msg}")
            progress.progress(pct)
            log_area.code("\n".join(logs), language="text")

        try:
            _render_prewarm_status()
            log("⚙️", "Loading configuration...", 10)
            from coding_agent.config import settings
            key_ok = "✓" if settings.openrouter_api_key else "✗ NOT SET"
            log("🔑", f"API Key: {key_ok}", 15)
            models = settings.get_all_models()
            log("🧪", f"Models: {len(models)} configured", 20)
            log("🪂", f"Fallback mode: {settings.fallback_mode}", 21)
            log("📂", f"Working directory: {Path.cwd()}", 22)
            log("🗃️", f"Memory directory: {settings.memory_dir}", 24)
            log("🗄️", f"State store path: {settings.state_dir / 'agent_state.db'}", 26)
            primary_model = getattr(settings, "primary_model_string", "") or "unknown"
            log("🤖", f"Primary model: {primary_model}", 28)

            t0 = time.time()
            log("🧠", "Initializing ChromaDB memory...", 35)
            from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
            ltm_mw = LongTermMemoryMiddleware(memory_dir=str(settings.memory_dir))
            total = sum(ltm_mw.store.get_stats().values())
            st.session_state.mem_count = total
            log("✅", f"Memory ready ({total} entries) — {time.time()-t0:.1f}s", 40)

            t0 = time.time()
            log("🏗️", "Creating DeepAgents supervisor...", 55)
            from coding_agent.runtime import create_runtime_components, finalize_runtime_components
            prewarm_bundle = st.session_state.get("prewarm_bundle")
            if prewarm_bundle is not None:
                log("🧩", "Using prewarmed DeepAgents runtime bundle", 58)
                components = finalize_runtime_components(
                    prewarm_bundle,
                    custom_settings=settings,
                    cwd=Path.cwd(),
                    progress_cb=lambda msg: log("   ", msg, 70),
                )
            else:
                components = create_runtime_components(
                    cwd=Path.cwd(),
                    progress_cb=lambda msg: log("   ", msg, 70),
                )
            log("✅", f"DeepAgents supervisor ready — {time.time()-t0:.1f}s", 90)
            topo = components.get("deployment_topology", "unknown")
            log("🧭", f"Topology: {topo}", 91)
            async_specs = components.get("async_subagents") or []
            spec_names = ", ".join(str(spec.get("name", "?")) for spec in async_specs) or "none"
            log("🧩", f"AsyncSubAgent specs: {spec_names}", 92)

            t0 = time.time()
            manager = components["subagent_runtime"]
            summary = manager.topology_summary()
            log("🤖", "Configuring AsyncSubAgent runtime policy...", 93)
            if summary["topology"] == "split":
                log(
                    "⏳",
                    (
                        "Split topology enabled: subagent processes will launch "
                        "on demand when MainAgent calls start_async_task"
                    ),
                    94,
                )
                for name in sorted(spec["name"] for spec in async_specs):
                    try:
                        info = manager.get_runtime_info(name)
                        log(
                            "   ",
                            f"{name}: prepared at {info.get('host', '127.0.0.1')}:{info.get('port', '')} (spawn on demand)",
                            95,
                        )
                    except Exception:
                        log("   ", f"{name}: runtime metadata unavailable yet", 95)
            else:
                log(
                    "🧩",
                    (
                        f"{summary['topology']} topology enabled: subagents are "
                        "resolved inside the current deployment/runtime"
                    ),
                    95,
                )
            log(
                "✅",
                (
                    "Async subagent policy ready "
                    f"({summary['num_subagents']} specs, {summary['http_subagents']} HTTP, "
                    f"{summary['asgi_subagents']} ASGI) — {time.time()-t0:.1f}s"
                ),
                97,
            )

            total_elapsed = time.time() - t_init_start
            log("🚀", f"Ready! (total {total_elapsed:.1f}s)", 100)

            st.session_state.agent_components = components
            st.session_state.initialized = True

        except Exception as e:
            st.session_state.init_error = traceback.format_exc()
            st.session_state.initialized = False
            st.error(f"Failed: {e}")
            st.code(st.session_state.init_error, language="python")
            return

    init_area.empty()
    # Init 완료 → 즉시 rerun하여 clean render (Init UI 잔재 없이 chat 진입)
    if st.session_state.initialized:
        st.rerun()


def main():
    _init_state()

    # ── query_params 로 페이지 전환 감지 ─────────────────────────────
    qp = st.query_params
    if qp.get("page") == "settings" and st.session_state.page != "settings":
        st.session_state.page = "settings"
    elif qp.get("page") == "chat" and st.session_state.page != "chat":
        st.session_state.page = "chat"
    if qp.get("refresh") == "1":
        _reset_chat_state()
        st.session_state.page = "chat"
        st.query_params.clear()
        st.query_params["page"] = "chat"
        st.rerun()

    # ── Page routing ─────────────────────────────────────────────────
    page = st.session_state.page
    if page == "settings":
        from coding_agent.webui._pages.settings import render_settings
        render_settings()
        # Settings 페이지 하단에 Chat 복귀 링크
        st.markdown(
            '<a href="?page=chat" target="_self" '
            'style="position:fixed;bottom:1rem;left:1.2rem;'
            'font-size:0.85rem;color:#64748b;text-decoration:none;z-index:9999;">'
            'Back to Chat</a>',
            unsafe_allow_html=True,
        )
    else:
        startup_area = st.empty()
        if not st.session_state.startup_setup_complete:
            _render_startup_setup(startup_area)

        _init_agent(startup_area)

        if not st.session_state.initialized:
            st.stop()

        from coding_agent.webui._pages.chat import render_chat
        render_chat()
        # Chat 페이지 좌측 하단에 Settings/Refresh 링크
        st.markdown(
            '<div style="position:fixed;bottom:1rem;left:1.2rem;'
            'display:flex;gap:.9rem;align-items:center;z-index:9999;">'
            '<a href="?page=settings" target="_self" '
            'style="font-size:0.85rem;color:#64748b;text-decoration:none;">'
            'Settings</a>'
            '</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
