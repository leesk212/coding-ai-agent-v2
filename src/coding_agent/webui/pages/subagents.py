"""SubAgent monitor - view active and historical sub-agents."""

import time
import streamlit as st


def render_subagents() -> None:
    st.title("🤖 SubAgent Monitor")

    components = st.session_state.get("agent_components")
    if not components:
        st.warning("Agent not initialized. Check Settings.")
        return

    sa_mw = components["subagent_middleware"]
    registry = sa_mw.registry

    # Active sub-agents
    st.subheader("Active Sub-Agents")
    active = {
        tid: task
        for tid, task in registry.tasks.items()
        if task.status.value in ("pending", "running")
    }

    if not active:
        st.info("No active sub-agents.")
    else:
        for tid, task in active.items():
            elapsed = time.time() - task.created_at
            status_icon = "⏳" if task.status.value == "pending" else "🔄"
            col1, col2, col3 = st.columns([1, 3, 1])
            col1.markdown(f"{status_icon} **{task.id}**")
            col2.markdown(f"{task.task_description[:100]}")
            col3.markdown(f"`{task.agent_type}` {elapsed:.0f}s")

    st.markdown("---")

    # Task history
    st.subheader("Task History")
    all_tasks = registry.get_all_tasks()

    if not all_tasks:
        st.info("No sub-agent tasks have been created yet.")
        st.markdown("""
        Sub-agents are created dynamically when the main agent encounters
        complex tasks. Available types:

        | Type | Description |
        |------|-------------|
        | `code_writer` | Writing new code or functions |
        | `researcher` | Investigating codebases, docs |
        | `reviewer` | Code review and quality analysis |
        | `debugger` | Root cause analysis, bug fixing |
        | `general` | Any other task |
        """)
        return

    # Summary metrics
    completed = sum(1 for t in all_tasks if t["status"] == "completed")
    failed = sum(1 for t in all_tasks if t["status"] == "failed")
    total = len(all_tasks)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tasks", total)
    col2.metric("Completed", completed)
    col3.metric("Failed", failed)

    # Task list
    for task in all_tasks:
        status = task["status"]
        icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
        }.get(status, "❓")

        duration = ""
        if task.get("completed_at") and task.get("created_at"):
            duration = f" ({task['completed_at'] - task['created_at']:.1f}s)"

        with st.expander(
            f"{icon} [{task['id']}] {task['agent_type']} - {task['task_description'][:60]}{duration}"
        ):
            st.markdown(f"**Task:** {task['task_description']}")
            st.markdown(f"**Type:** `{task['agent_type']}`")
            st.markdown(f"**Status:** {status}")

            if task.get("model_used"):
                st.markdown(f"**Model:** `{task['model_used']}`")

            if task.get("result"):
                st.markdown("**Result:**")
                st.code(task["result"][:2000], language="text")

            if task.get("error"):
                st.error(f"Error: {task['error']}")
