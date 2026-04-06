"""Settings page - configure API keys, models, and preferences."""

import os
import streamlit as st

from coding_agent.config import ModelSpec, settings


def render_settings() -> None:
    st.title("⚙️ Settings")

    # API Keys
    st.subheader("🔑 API Keys")

    openrouter_key = st.text_input(
        "OpenRouter API Key",
        value=settings.openrouter_api_key or "",
        type="password",
        help="Get your key at https://openrouter.ai/keys",
    )
    if openrouter_key != settings.openrouter_api_key:
        settings.openrouter_api_key = openrouter_key
        os.environ["OPENROUTER_API_KEY"] = openrouter_key
        st.success("OpenRouter API key updated!")

    st.markdown("---")

    # Model Configuration
    st.subheader("🧪 Model Priority")
    st.markdown("Models are tried in order. First success wins. Local model is last resort.")

    for i, model in enumerate(settings.model_priority):
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.text(f"{i+1}. {model.name}")
        col2.text(model.provider)
        col3.text(f"ctx: {model.context_window:,}")

    st.markdown(f"**Fallback:** {settings.local_fallback_model.name} (Ollama)")

    st.markdown("---")

    # Ollama Settings
    st.subheader("🏠 Local LLM (Ollama)")

    ollama_url = st.text_input(
        "Ollama Base URL",
        value=settings.ollama_base_url,
        help="Default: http://localhost:11434",
    )
    if ollama_url != settings.ollama_base_url:
        settings.ollama_base_url = ollama_url

    local_model = st.text_input(
        "Local Model Name",
        value=settings.local_fallback_model.name,
        help="Ollama model name (e.g., qwen2.5-coder:7b)",
    )
    if local_model != settings.local_fallback_model.name:
        settings.local_fallback_model = ModelSpec(
            name=local_model,
            context_window=32768,
            provider="ollama",
            priority=99,
        )

    # Test Ollama connection
    if st.button("🔌 Test Ollama Connection"):
        try:
            import httpx
            resp = httpx.get(f"{ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m["name"] for m in models]
                st.success(f"Connected! Available models: {', '.join(model_names[:5])}")
            else:
                st.error(f"Connection failed: HTTP {resp.status_code}")
        except Exception as e:
            st.error(f"Cannot connect to Ollama: {e}")

    st.markdown("---")

    # Memory Settings
    st.subheader("🧠 Memory")

    memory_dir = st.text_input(
        "Memory Directory",
        value=str(settings.memory_dir),
        help="Directory for ChromaDB persistent storage",
    )

    st.markdown("---")

    # Agent Settings
    st.subheader("🔄 Agent Loop")

    col1, col2 = st.columns(2)
    with col1:
        max_iter = st.number_input(
            "Max Iterations",
            min_value=5,
            max_value=100,
            value=settings.max_iterations,
            help="Maximum agent loop iterations before stopping",
        )
        settings.max_iterations = max_iter

    with col2:
        max_sa = st.number_input(
            "Max Concurrent SubAgents",
            min_value=1,
            max_value=10,
            value=settings.max_subagents,
            help="Maximum number of sub-agents running at once",
        )
        settings.max_subagents = max_sa

    col1, col2 = st.columns(2)
    with col1:
        timeout = st.number_input(
            "Model Timeout (seconds)",
            min_value=10.0,
            max_value=300.0,
            value=settings.model_timeout,
            step=10.0,
            help="Timeout before trying the next model",
        )
        settings.model_timeout = timeout

    with col2:
        cb_threshold = st.number_input(
            "Circuit Breaker Threshold",
            min_value=1,
            max_value=10,
            value=settings.circuit_breaker_threshold,
            help="Failures before skipping a model",
        )
        settings.circuit_breaker_threshold = cb_threshold

    st.markdown("---")

    # Re-initialize agent
    if st.button("🔄 Reinitialize Agent", type="primary"):
        st.session_state.agent_components = None
        st.session_state.initialized = False
        st.success("Agent will be reinitialized on next page load.")
        st.rerun()

    # Current status
    if st.session_state.get("initialized"):
        components = st.session_state.agent_components
        if components:
            st.markdown("---")
            st.subheader("📊 Current Status")

            fallback = components["fallback_middleware"]
            status = fallback.get_status()

            for m in status["models"]:
                icon = "🟢" if m["circuit_state"] == "closed" else "🔴" if m["circuit_state"] == "open" else "🟡"
                st.markdown(
                    f"{icon} **{m['name']}** ({m['provider']}) - "
                    f"Circuit: {m['circuit_state']}, Failures: {m['failure_count']}"
                )
