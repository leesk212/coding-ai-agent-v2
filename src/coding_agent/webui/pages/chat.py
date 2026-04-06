"""Chat page - interactive conversation with the Coding AI Agent."""

import asyncio
import streamlit as st
from langchain_core.messages import HumanMessage


def render_chat() -> None:
    st.title("💬 Chat")

    components = st.session_state.get("agent_components")
    if not components:
        st.warning("Agent not initialized. Check Settings.")
        return

    agent = components["agent"]
    fallback_mw = components["fallback_middleware"]
    loop_guard = components["loop_guard"]

    # Display chat history
    for msg in st.session_state.chat_messages:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role):
            st.markdown(content)
            if msg.get("model"):
                st.caption(f"Model: {msg['model']}")
            if msg.get("tools_used"):
                with st.expander("Tools used"):
                    for tool in msg["tools_used"]:
                        st.code(tool, language="text")

    # Chat input
    if prompt := st.chat_input("Ask me anything about coding..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            tools_used = []
            response_text = ""

            loop_guard.reset()

            try:
                config = {"configurable": {"thread_id": "webui-session"}}
                inputs = {"messages": [HumanMessage(content=prompt)]}

                with st.spinner("Thinking..."):
                    # Use invoke for simplicity (streaming with Streamlit is complex)
                    result = agent.invoke(inputs, config=config)

                    # Extract final response
                    messages = result.get("messages", [])
                    for msg in messages:
                        if hasattr(msg, "type"):
                            if msg.type == "ai" and msg.content:
                                response_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                            elif msg.type == "tool":
                                tools_used.append(f"{msg.name}: {str(msg.content)[:200]}")

                if not response_text:
                    response_text = "(No response generated)"

                response_placeholder.markdown(response_text)

                # Show model info
                model_name = fallback_mw.current_model or "unknown"
                st.caption(f"Model: {model_name}")

                if tools_used:
                    with st.expander(f"🔧 Tools used ({len(tools_used)})"):
                        for tool in tools_used:
                            st.code(tool, language="text")

            except Exception as e:
                response_text = f"Error: {e}"
                response_placeholder.error(response_text)

            # Save to history
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response_text,
                "model": fallback_mw.current_model,
                "tools_used": tools_used,
            })

    # Sidebar actions for chat
    with st.sidebar:
        st.markdown("### Chat Actions")
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            st.rerun()

        # Show current model status
        st.markdown("### Model Status")
        status = fallback_mw.get_status()
        for m in status["models"]:
            icon = "🟢" if m["circuit_state"] == "closed" else "🔴" if m["circuit_state"] == "open" else "🟡"
            st.text(f"{icon} {m['name'][:30]}")
