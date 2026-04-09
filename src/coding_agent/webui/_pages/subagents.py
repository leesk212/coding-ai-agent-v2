"""DeepAgents AsyncSubAgent runtime monitor."""

import time
import streamlit as st


def render_subagents() -> None:
    st.title("🤖 SubAgent Monitor")

    components = st.session_state.get("agent_components")
    if not components:
        st.warning("Agent not initialized. Check Settings.")
        return

    sa_mw = components["subagent_runtime"]
    tracker = components.get("async_task_tracker")
    all_tasks = sa_mw.get_all_tasks()
    thread_id = st.session_state.get("_conversation_thread_id", "")
    tracked_tasks = tracker.get_tasks(thread_id) if tracker and thread_id else []

    st.subheader("AsyncSubAgent Runtimes")
    active = [task for task in all_tasks if task["status"] == "running"]

    if not active:
        st.info("No active subagent processes.")
    else:
        for task in active:
            elapsed = time.time() - task["started_at"] if task.get("started_at") else 0
            col1, col2, col3 = st.columns([2, 4, 2])
            col1.markdown(f"🔄 **{task['id']}**")
            col2.markdown(f"{task['task_description']}  \n`{task['url']}`")
            col3.markdown(f"PID `{task.get('pid') or '-'} `  \n{elapsed:.0f}s")

    st.markdown("---")

    st.subheader("Process Inventory")

    if not all_tasks:
        st.info("No subagent processes are configured.")
        st.markdown("""
        AsyncSubAgents run as DeepAgents specs backed by either local Agent Protocol
        servers (`url=...`) or in-process ASGI transport (`url` omitted). Available types:

        | Type | Description |
        |------|-------------|
        | `coder` | Writing new code or functions |
        | `researcher` | Investigating codebases, docs |
        | `reviewer` | Code review and quality analysis |
        | `debugger` | Root cause analysis, bug fixing |
        """)
        return

    # Summary metrics
    completed = sum(1 for t in all_tasks if t["status"] == "running")
    failed = sum(1 for t in all_tasks if t["status"] == "exited")
    total = len(all_tasks)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tasks", total)
    col2.metric("Running", completed)
    col3.metric("Exited", failed)

    # Task list
    for task in all_tasks:
        status = task["status"]
        icon = {"running": "🔄", "stopped": "⏹️", "exited": "❌"}.get(status, "❓")

        duration = ""
        if task.get("started_at"):
            duration = f" ({time.time() - task['started_at']:.1f}s)"

        with st.expander(
            f"{icon} [{task['id']}] {task['agent_type']} - {task['task_description'][:60]}{duration}"
        ):
            st.markdown(f"**Description:** {task['task_description']}")
            st.markdown(f"**Type:** `{task['agent_type']}`")
            st.markdown(f"**Status:** {status}")
            st.markdown(f"**URL:** `{task['url']}`")
            if task.get("pid"):
                st.markdown(f"**PID:** `{task['pid']}`")

            if task.get("error"):
                st.error(f"Error: {task['error']}")

    st.markdown("---")
    st.subheader("Tracked Async Tasks")
    if thread_id:
        st.caption(f"Conversation thread: `{thread_id}`")

    if not tracked_tasks:
        st.info("No async tasks have been tracked in the current conversation yet.")
        return

    running = sum(1 for t in tracked_tasks if t["status"] == "running")
    success = sum(1 for t in tracked_tasks if t["status"] == "success")
    failed = sum(1 for t in tracked_tasks if t["status"] in ("error", "cancelled"))
    c1, c2, c3 = st.columns(3)
    c1.metric("Running Tasks", running)
    c2.metric("Completed Tasks", success)
    c3.metric("Failed/Cancelled", failed)

    for task in tracked_tasks:
        icon = {
            "running": "🔄",
            "success": "✅",
            "error": "❌",
            "cancelled": "🛑",
        }.get(task["status"], "❓")
        with st.expander(
            f"{icon} [{task['task_id'][:12]}...] {task['agent_type']} - {task['status']}"
        ):
            st.markdown(f"**Task ID:** `{task['task_id']}`")
            st.markdown(f"**Agent Type:** `{task['agent_type']}`")
            st.markdown(f"**Status:** `{task['status']}`")
            st.markdown(f"**Run ID:** `{task['run_id']}`")
            st.markdown(f"**Created:** `{task['created_at']}`")
            st.markdown(f"**Last Checked:** `{task['last_checked_at']}`")
            st.markdown(f"**Last Updated:** `{task['last_updated_at']}`")

    st.markdown("---")
    st.subheader("Snapshot vs Live")
    latest_snapshot = []
    for msg in reversed(st.session_state.get("chat_messages", [])):
        if msg.get("role") == "assistant" and msg.get("async_task_snapshot"):
            latest_snapshot = msg.get("async_task_snapshot") or []
            break

    if not latest_snapshot:
        st.info("No stored async task snapshot from assistant history yet.")
        return

    live_by_id = {task["task_id"]: task for task in tracked_tasks}
    snap_by_id = {task["task_id"]: task for task in latest_snapshot if isinstance(task, dict) and task.get("task_id")}

    changed = []
    for task_id, snap in snap_by_id.items():
        live = live_by_id.get(task_id)
        if not live:
            changed.append((task_id, snap.get("status", "unknown"), "missing"))
            continue
        s_status = str(snap.get("status", "unknown"))
        l_status = str(live.get("status", "unknown"))
        if s_status != l_status:
            changed.append((task_id, s_status, l_status))

    new_live = [task_id for task_id in live_by_id if task_id not in snap_by_id]

    col1, col2, col3 = st.columns(3)
    col1.metric("Snapshot Tasks", len(snap_by_id))
    col2.metric("Status Changes", len(changed))
    col3.metric("New Live Tasks", len(new_live))

    for task_id, old_status, new_status in changed[:8]:
        st.caption(f"- `{task_id[:12]}...` `{old_status}` -> `{new_status}`")
    for task_id in new_live[:8]:
        st.caption(f"- `{task_id[:12]}...` exists live only")
