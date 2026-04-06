"""Memory dashboard - view, search, and manage long-term memories."""

import streamlit as st
from coding_agent.memory.categories import MemoryCategory


def render_memory() -> None:
    st.title("🧠 Long-Term Memory")

    components = st.session_state.get("agent_components")
    if not components:
        st.warning("Agent not initialized. Check Settings.")
        return

    memory_mw = components["memory_middleware"]
    store = memory_mw.store

    # Stats overview
    stats = store.get_stats()
    total = sum(stats.values())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total", total)
    col2.metric("Domain", stats.get("domain_knowledge", 0))
    col3.metric("Preferences", stats.get("user_preferences", 0))
    col4.metric("Patterns", stats.get("code_patterns", 0))
    col5.metric("Project", stats.get("project_context", 0))

    st.markdown("---")

    # Tabs for different operations
    tab_browse, tab_search, tab_add = st.tabs(["📋 Browse", "🔍 Search", "➕ Add"])

    # Browse tab
    with tab_browse:
        category = st.selectbox(
            "Category",
            [c.value for c in MemoryCategory],
            key="browse_category",
        )

        entries = store.get_all(MemoryCategory(category))

        if not entries:
            st.info(f"No memories in '{category}' yet.")
        else:
            for entry in entries:
                with st.expander(f"📝 {entry['content'][:80]}...", expanded=False):
                    st.markdown(entry["content"])
                    st.caption(f"ID: {entry['id']}")
                    if entry.get("metadata"):
                        st.json(entry["metadata"])
                    if st.button("🗑️ Delete", key=f"del_{entry['id']}"):
                        store.delete(entry["id"], MemoryCategory(category))
                        st.success("Deleted!")
                        st.rerun()

    # Search tab
    with tab_search:
        query = st.text_input("Search query", placeholder="e.g., Python coding style preferences")
        search_category = st.selectbox(
            "Filter by category (optional)",
            ["All"] + [c.value for c in MemoryCategory],
            key="search_category",
        )
        n_results = st.slider("Max results", 1, 20, 5)

        if st.button("🔍 Search") and query:
            cat = MemoryCategory(search_category) if search_category != "All" else None
            results = store.search(query, cat, n_results)

            if not results:
                st.info("No matching memories found.")
            else:
                for r in results:
                    similarity = 1 - r["distance"]
                    color = "green" if similarity > 0.7 else "orange" if similarity > 0.4 else "red"
                    st.markdown(
                        f"**[{r['category']}]** Similarity: :{color}[{similarity:.2f}]"
                    )
                    st.markdown(r["content"])
                    st.markdown("---")

    # Add tab
    with tab_add:
        st.markdown("Manually add a memory entry.")
        add_content = st.text_area("Content", placeholder="Enter the knowledge to store...")
        add_category = st.selectbox(
            "Category",
            [c.value for c in MemoryCategory],
            key="add_category",
        )
        add_tags = st.text_input("Tags (comma-separated)", placeholder="python, testing, best-practice")

        if st.button("💾 Store") and add_content:
            metadata = {}
            if add_tags:
                metadata["tags"] = add_tags
            metadata["source"] = "manual"

            doc_id = store.store(add_content, MemoryCategory(add_category), metadata)
            st.success(f"Stored with ID: {doc_id}")
            st.rerun()
