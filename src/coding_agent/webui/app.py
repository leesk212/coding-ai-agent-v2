"""Danny's Coding AI Agent — Single-page WebUI.

Run with: python -m coding_agent --webui
"""

import logging
import time
import traceback

import streamlit as st

from coding_agent.agent import SYSTEM_PROMPT

WEBUI_SYSTEM_PROMPT = (
    SYSTEM_PROMPT
    + "\n\n## WebUI Flow Visualization\n"
    + "- If both `task` and `spawn_subagent` are available for delegation, prefer "
    + "`task(description, subagent_type)` because it is DeepAgents' native "
    + "subagent tool and is visualized in the WebUI flow chart.\n"
)

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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


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
            log("🔄", "Building model fallback chain...", 55)
            from coding_agent.middleware.model_fallback import ModelFallbackMiddleware
            fallback_mw = ModelFallbackMiddleware(models=models, timeout=settings.model_timeout)
            log("✅", f"Fallback chain ready — {time.time()-t0:.1f}s", 60)

            t0 = time.time()
            log("🤖", "Setting up SubAgent system...", 70)
            from coding_agent.middleware.subagent_lifecycle import SubAgentLifecycleMiddleware
            primary_model = fallback_mw.get_model_with_fallback()
            subagent_mw = SubAgentLifecycleMiddleware(model=primary_model, max_concurrent=settings.max_subagents)
            log("✅", f"SubAgents ready (max {settings.max_subagents}) — {time.time()-t0:.1f}s", 75)

            t0 = time.time()
            log("🏗️", "Creating agent...", 85)
            from coding_agent.agent import AgentLoopGuard
            loop_guard = AgentLoopGuard(max_iterations=settings.max_iterations)
            custom_tools = ltm_mw.get_tools() + subagent_mw.get_tools()
            log("🔧", f"Tools: {', '.join(t.name for t in custom_tools)}", 88)

            agent, backend = None, None
            _deepagents_error: str | None = None

            # ── Step 1: verify deepagents_cli can be imported ────────
            try:
                import inspect
                from deepagents_cli.agent import create_cli_agent  # noqa: PLC0415
                _deepagents_import_ok = True
            except ImportError as _ie:
                _deepagents_import_ok = False
                _deepagents_error = (
                    f"ImportError: {_ie}\n"
                    f"Python: {__import__('sys').version.split()[0]}  "
                    f"(deepagents-cli requires ≥ 3.11)"
                )
                log("⚠️", f"deepagents_cli import failed: {_ie}", 92)

            # ── Step 2: try to build the agent ────────────────────────
            if _deepagents_import_ok:
                try:
                    kwargs = {
                        "model": settings.primary_model_string,
                        "assistant_id": "coding-ai-agent",
                        "tools": custom_tools,
                        "system_prompt": WEBUI_SYSTEM_PROMPT,
                        "interactive": False,
                        "auto_approve": True,
                        "enable_memory": True,
                        "enable_skills": True,
                        "enable_shell": True,
                        "cwd": str(settings.memory_dir.parent),
                    }
                    try:
                        sig = inspect.signature(create_cli_agent)
                        supported = set(sig.parameters.keys())
                        if not any(
                            p.kind == inspect.Parameter.VAR_KEYWORD
                            for p in sig.parameters.values()
                        ):
                            kwargs = {k: v for k, v in kwargs.items() if k in supported}
                    except (ValueError, TypeError):
                        pass
                    agent, backend = create_cli_agent(**kwargs)
                    log("✅", f"DeepAgents CLI agent created — {time.time()-t0:.1f}s", 95)
                except Exception as _ce:
                    _deepagents_error = f"{type(_ce).__name__}: {_ce}"
                    log("⚠️", f"create_cli_agent failed: {_ce}", 92)

            # ── Step 3: LangGraph fallback if anything above failed ───
            if agent is None:
                _reason = _deepagents_error or "unknown error"
                log("🔄", f"LangGraph fallback (reason: {_reason[:80]})", 92)
                from langgraph.prebuilt import create_react_agent  # noqa: PLC0415
                agent = create_react_agent(
                    model=primary_model,
                    tools=custom_tools,
                    prompt="You are Danny's Coding AI Agent.",
                )
                log("✅", f"LangGraph agent created — {time.time()-t0:.1f}s", 95)

            total_elapsed = time.time() - t_init_start
            log("🚀", f"Ready! (total {total_elapsed:.1f}s)", 100)

            st.session_state.agent_components = {
                "agent": agent, "backend": backend,
                "fallback_middleware": fallback_mw, "memory_middleware": ltm_mw,
                "subagent_middleware": subagent_mw, "loop_guard": loop_guard,
            }
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
        # Chat 페이지 좌측 하단에 Settings 링크
        st.markdown(
            '<a href="?page=settings" target="_self" '
            'style="position:fixed;bottom:1rem;left:1.2rem;'
            'font-size:0.85rem;color:#64748b;text-decoration:none;z-index:9999;">'
            '⚙️ Settings</a>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
