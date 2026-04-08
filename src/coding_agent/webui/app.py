"""Danny's Coding AI Agent — Single-page WebUI."""

import logging
import time
import traceback
import uuid
from pathlib import Path

import streamlit as st

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
    st.session_state.pop("_pending_prompt", None)


def _init_agent():
    if st.session_state.agent_components is not None:
        return

    init_area = st.empty()
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
            log("⚙️", "Loading configuration...", 10)
            from coding_agent.config import settings
            key_ok = "✓" if settings.openrouter_api_key else "✗ NOT SET"
            log("🔑", f"API Key: {key_ok}", 15)
            models = settings.get_all_models()
            log("🧪", f"Models: {len(models)} configured", 20)

            t0 = time.time()
            log("🧠", "Initializing ChromaDB memory...", 35)
            from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
            ltm_mw = LongTermMemoryMiddleware(memory_dir=str(settings.memory_dir))
            total = sum(ltm_mw.store.get_stats().values())
            st.session_state.mem_count = total
            log("✅", f"Memory ready ({total} entries) — {time.time()-t0:.1f}s", 40)

            t0 = time.time()
            log("🏗️", "Creating DeepAgents supervisor...", 55)
            from coding_agent.agent import create_coding_agent
            components = create_coding_agent(cwd=Path.cwd())
            log("✅", f"DeepAgents supervisor ready — {time.time()-t0:.1f}s", 90)

            t0 = time.time()
            log("🤖", "Starting local async subagent processes...", 92)
            manager = components["subagent_manager"]
            specs = manager.ensure_all_started()
            log("✅", f"Async subagents healthy ({len(specs)}) — {time.time()-t0:.1f}s", 97)

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
            '💬 Back to Chat</a>',
            unsafe_allow_html=True,
        )
    else:
        _init_agent()

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
            '⚙️ Settings</a>'
            '<a href="?page=chat&refresh=1" target="_self" '
            'style="font-size:0.85rem;color:#64748b;text-decoration:none;">'
            '🔄 Refresh</a>'
            '</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
