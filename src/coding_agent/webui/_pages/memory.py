"""Memory dashboard - browse and correct durable long-term memory records."""

import streamlit as st

from coding_agent.config import settings
from coding_agent.state.store import DurableStateStore


def render_memory() -> None:
    st.title("🧠 Memory Records")
    st.caption("Browse approved long-term memory artifacts and correct records when needed.")

    store = DurableStateStore(settings.state_dir / "agent_state.db")

    col1, col2 = st.columns(2)
    with col1:
        layer_filter = st.selectbox(
            "Layer",
            options=["all", "project/context", "domain/knowledge", "user/profile"],
            index=0,
        )
    with col2:
        status_filter = st.selectbox(
            "Status",
            options=["active", "superseded", "all"],
            index=0,
        )

    search_query = st.text_input(
        "Search",
        value="",
        help="Search durable memory content and tags.",
    )

    if search_query.strip():
        records = store.search_memory(
            search_query.strip(),
            layer=None if layer_filter == "all" else layer_filter,
            limit=50,
        )
        if status_filter != "all":
            records = [row for row in records if str(row.get("status", "")) == status_filter]
    else:
        records = store.list_memory_records(
            layer=None if layer_filter == "all" else layer_filter,
            status=None if status_filter == "all" else status_filter,
            limit=50,
        )

    st.caption(f"Loaded records: {len(records)}")

    for idx, row in enumerate(records):
        record_id = str(row.get("record_id", ""))
        layer = str(row.get("layer", "unknown"))
        status = str(row.get("status", "unknown"))
        with st.expander(f"{record_id} · {layer} · {status}", expanded=False):
            st.caption(
                f"source={row.get('source', '')} · scope={row.get('scope_key', '')} · "
                f"updated={row.get('updated_at', '')}"
            )
            st.code(str(row.get("content", "")), language="text")
            corrected_content = st.text_area(
                "Corrected Content",
                value=str(row.get("content", "")),
                height=220,
                key=f"memory_page_correct_content_{idx}",
            )
            correction_reason = st.text_input(
                "Correction Reason",
                value="",
                key=f"memory_page_correct_reason_{idx}",
            )
            if st.button("Save Correction", key=f"memory_page_correct_btn_{idx}", use_container_width=True):
                new_id = store.store_memory(
                    layer=layer,
                    content=corrected_content.strip(),
                    scope_key=str(row.get("scope_key", "global")),
                    source="memory_page_correction",
                    tags=[correction_reason.strip()] if correction_reason.strip() else [],
                    correction_of=record_id,
                )
                st.success(f"Stored correction as {new_id}")
                st.rerun()
