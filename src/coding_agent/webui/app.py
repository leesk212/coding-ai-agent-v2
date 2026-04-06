"""Main Streamlit application - multi-page WebUI for Coding AI Agent.

Run with: streamlit run src/coding_agent/webui/app.py
Or: python -m coding_agent --webui
"""

import streamlit as st

st.set_page_config(
    page_title="Coding AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """Initialize shared session state."""
    if "agent_components" not in st.session_state:
        st.session_state.agent_components = None
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "initialized" not in st.session_state:
        st.session_state.initialized = False


def init_agent() -> None:
    """Initialize the agent components (cached in session state)."""
    if st.session_state.agent_components is not None:
        return

    with st.spinner("Initializing agent..."):
        try:
            from coding_agent.agent import create_coding_agent
            st.session_state.agent_components = create_coding_agent()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            st.session_state.initialized = False


def main() -> None:
    init_session_state()

    # Sidebar navigation
    st.sidebar.title("Coding AI Agent")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["💬 Chat", "🧠 Memory", "🤖 SubAgents", "⚙️ Settings"],
        index=0,
    )

    # Show connection status in sidebar
    if st.session_state.initialized:
        components = st.session_state.agent_components
        if components:
            fallback = components["fallback_middleware"]
            model = fallback.current_model or "not yet used"
            st.sidebar.success(f"Connected: {model}")

            memory = components["memory_middleware"]
            stats = memory.store.get_stats()
            total = sum(stats.values())
            st.sidebar.info(f"Memory: {total} entries")
    else:
        st.sidebar.warning("Agent not initialized")

    # Route to pages
    if page == "💬 Chat":
        from coding_agent.webui.pages.chat import render_chat
        init_agent()
        render_chat()
    elif page == "🧠 Memory":
        from coding_agent.webui.pages.memory import render_memory
        init_agent()
        render_memory()
    elif page == "🤖 SubAgents":
        from coding_agent.webui.pages.subagents import render_subagents
        init_agent()
        render_subagents()
    elif page == "⚙️ Settings":
        from coding_agent.webui.pages.settings import render_settings
        render_settings()


if __name__ == "__main__":
    main()
