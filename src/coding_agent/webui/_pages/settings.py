"""Settings page - configure API keys, models, and preferences."""

import os
import streamlit as st

from coding_agent.async_subagent_manager import get_default_subagent_system_prompts
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

    openai_key = st.text_input(
        "OpenAI API Key",
        value=settings.openai_api_key or "",
        type="password",
        help="Optional. Used only when fallback mode is set to OpenAI.",
    )
    if openai_key != settings.openai_api_key:
        settings.openai_api_key = openai_key
        os.environ["OPENAI_API_KEY"] = openai_key
        st.success("OpenAI API key updated!")

    st.markdown("---")

    # Model Configuration
    st.subheader("🧪 Model Priority (Open-Source Models)")
    st.markdown(
        "오픈소스 모델을 우선순위 순서로 시도합니다. "
        "실패 시 다음 모델로 자동 전환됩니다."
    )

    for i, model in enumerate(settings.model_priority):
        col1, col2 = st.columns([4, 1])
        col1.text(f"{i+1}. {model.name}")
        col2.text(model.provider)

    fallback_mode = st.selectbox(
        "Fallback Mode",
        options=["none", "local", "openai"],
        index=["none", "local", "openai"].index(
            settings.fallback_mode if settings.fallback_mode in {"none", "local", "openai"} else "local"
        ),
        help="Choose the last-resort model path used when OpenRouter models fail.",
    )
    if fallback_mode != settings.fallback_mode:
        settings.fallback_mode = fallback_mode
        os.environ["FALLBACK_MODE"] = fallback_mode

    selected_fallback = settings.selected_fallback_model
    if selected_fallback is None:
        st.markdown("**Fallback:** disabled")
    else:
        label = "Ollama local" if selected_fallback.provider == "ollama" else "OpenAI"
        st.markdown(f"**Fallback:** {selected_fallback.name} ({label})")

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
            provider="ollama",
            priority=99,
        )

    openai_model = st.text_input(
        "OpenAI Fallback Model",
        value=settings.openai_fallback_model.name,
        help="OpenAI model name used when fallback mode is OpenAI.",
    )
    if openai_model != settings.openai_fallback_model.name:
        settings.openai_fallback_model = ModelSpec(
            name=openai_model,
            provider="openai",
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
                if model_names:
                    st.success(f"Connected! Available models: {', '.join(model_names[:5])}")
                else:
                    st.warning("Connected, but no models found. Run: ollama pull qwen2.5-coder:7b")
            else:
                st.error(f"Connection failed: HTTP {resp.status_code}")
        except Exception as e:
            st.error(f"Cannot connect to Ollama: {e}")

    st.markdown("---")
    st.subheader("🧩 Agent System Prompts")
    st.caption("Main Agent and each SubAgent system prompt can be overridden here. Changes apply after reinitialization.")

    prompt_defaults = get_default_subagent_system_prompts()
    current_main_override = st.text_area(
        "Main Agent Prompt Override",
        value=settings.main_system_prompt_override,
        height=220,
        help="Appended to the default Main Agent system prompt.",
    )

    prompt_inputs: dict[str, str] = {}
    for name, default_prompt in prompt_defaults.items():
        with st.expander(f"{name} prompt", expanded=False):
            st.caption("Default prompt shown below. Add an override only when you need to change behavior.")
            st.code(default_prompt, language="text")
            prompt_inputs[name] = st.text_area(
                f"{name} override",
                value=settings.subagent_system_prompt_overrides.get(name, ""),
                height=180,
                key=f"subagent_prompt_override_{name}",
                help=f"Override for the {name} subagent system prompt.",
            )

    col_prompt_save, col_prompt_reset = st.columns(2)
    with col_prompt_save:
        save_prompts = st.button("Save Prompt Overrides", use_container_width=True)
    with col_prompt_reset:
        reset_prompts = st.button("Reset Prompt Overrides", use_container_width=True)

    if save_prompts:
        settings.main_system_prompt_override = current_main_override.strip()
        settings.subagent_system_prompt_overrides = {
            name: value.strip()
            for name, value in prompt_inputs.items()
            if value.strip()
        }
        settings.save_prompt_overrides()
        st.session_state.agent_components = None
        st.session_state.initialized = False
        st.success("Prompt overrides saved. The agent will rebuild with the new prompts.")

    if reset_prompts:
        settings.main_system_prompt_override = ""
        settings.subagent_system_prompt_overrides = {}
        settings.save_prompt_overrides()
        st.session_state.agent_components = None
        st.session_state.initialized = False
        st.success("Prompt overrides cleared. The default prompts will be used after reinitialization.")
        st.rerun()

    st.markdown("---")

    # Memory Settings
    st.subheader("🧠 Memory")

    st.text_input(
        "Memory Directory",
        value=str(settings.memory_dir),
        help="Directory for ChromaDB persistent storage",
        disabled=True,
    )

    st.markdown("---")

    # Agent Settings
    st.subheader("🧭 Deployment")

    topology = st.selectbox(
        "Deployment Topology",
        options=["single", "split", "hybrid"],
        index=["single", "split", "hybrid"].index(
            settings.deployment_topology if settings.deployment_topology in {"single", "split", "hybrid"} else "split"
        ),
        help="single=langgraph co-deploy(ASGI), split=HTTP runtimes, hybrid=mixed",
    )
    if topology != settings.deployment_topology:
        settings.deployment_topology = topology
        os.environ["DEEPAGENTS_DEPLOYMENT_TOPOLOGY"] = topology

    deployment_url = st.text_input(
        "LangGraph Deployment URL",
        value=settings.langgraph_deployment_url,
        help="Required for single topology when the WebUI should talk to a running langgraph deployment.",
    )
    if deployment_url != settings.langgraph_deployment_url:
        settings.langgraph_deployment_url = deployment_url
        os.environ["LANGGRAPH_DEPLOYMENT_URL"] = deployment_url

    assistant_id = st.text_input(
        "LangGraph Assistant ID",
        value=settings.langgraph_assistant_id,
        help="Usually `supervisor` for this project.",
    )
    if assistant_id != settings.langgraph_assistant_id:
        settings.langgraph_assistant_id = assistant_id
        os.environ["LANGGRAPH_ASSISTANT_ID"] = assistant_id

    st.markdown("---")

    # Agent Settings
    st.subheader("🔄 Agent Loop Defense")

    col1, col2 = st.columns(2)
    with col1:
        max_iter = st.number_input(
            "Max Iterations",
            min_value=5,
            max_value=100000,
            value=settings.max_iterations,
            help="Maximum agent loop iterations before stopping",
        )
        settings.max_iterations = max_iter

    with col2:
        max_sa = st.number_input(
            "Max Concurrent SubAgents",
            min_value=1,
            max_value=100,
            value=settings.max_subagents,
            help="Maximum number of sub-agents running at once",
        )
        settings.max_subagents = max_sa

    st.markdown("---")
    st.subheader("🛰️ Async SubAgent Runtime")

    host = st.text_input(
        "Async SubAgent Host",
        value=settings.async_subagent_host,
        help="Host interface used by local async subagent Agent Protocol servers.",
    )
    if host != settings.async_subagent_host:
        settings.async_subagent_host = host

    base_port = st.number_input(
        "Async SubAgent Base Port",
        min_value=1024,
        max_value=65000,
        value=settings.async_subagent_base_port,
        help="The first port used for local async subagent processes. Each agent type increments from here.",
    )
    settings.async_subagent_base_port = int(base_port)

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
            help="Consecutive failures before skipping a model",
        )
        settings.circuit_breaker_threshold = cb_threshold

    st.markdown("---")

    # Re-initialize agent
    col_reinit, col_refresh = st.columns(2)
    with col_reinit:
        reinit_clicked = st.button("Reinitialize Agent", type="primary", use_container_width=True)
    with col_refresh:
        refresh_clicked = st.button("Refresh Chat", use_container_width=True)

    if reinit_clicked:
        st.session_state.agent_components = None
        st.session_state.initialized = False
        st.success("Agent will be reinitialized on next page load.")
        st.rerun()
    if refresh_clicked:
        st.query_params.clear()
        st.query_params["page"] = "chat"
        st.query_params["refresh"] = "1"
        st.rerun()

    # Current status
    if st.session_state.get("initialized"):
        components = st.session_state.agent_components
        if components:
            st.markdown("---")
            st.subheader("📊 Current Status")

            fallback = components["fallback_middleware"]
            status = fallback.get_status()
            st.caption(f"Topology: `{components.get('deployment_topology', settings.deployment_topology)}`")
            st.caption(f"Fallback mode: `{settings.fallback_mode}`")

            for m in status["models"]:
                icon = (
                    "🟢"
                    if m["circuit_state"] == "closed"
                    else "🔴"
                    if m["circuit_state"] == "open"
                    else "🟡"
                )
                st.markdown(
                    f"{icon} **{m['name']}** ({m['provider']}) - "
                    f"Circuit: {m['circuit_state']}, Failures: {m['failure_count']}"
                )
