"""Chat page — Mermaid flowchart + Event Feed + Scrollable Result.

Back-end generates Mermaid syntax → front-end renders it dynamically via CDN.

Layout (top → bottom):
┌──────────────────────────────────────────────────────────┐
│  📝 질의 입력창 (text_area)  │ 🚀 Send / 🔄 Refresh    │
├──────────────────────────────────────────────────────────┤
│  🔍 Agent 동작 분석                                       │
│  ├─ 📊 Mermaid FlowChart  (graph LR)                     │
│  └─ 📡 Event Feed                                        │
├──────────────────────────────────────────────────────────┤
│  💬 Result  (고정 높이 400px, 내부 스크롤)                 │
├──────────────────────────────────────────────────────────┤
│  📌 Prompt  (프리셋 프롬프트 버튼들)                       │
└──────────────────────────────────────────────────────────┘
"""

import logging
import time
import traceback

import streamlit as st
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

AGENT_ICONS = {
    "code_writer": "✍️", "researcher": "🔍", "reviewer": "📋",
    "debugger": "🐛", "general": "🤖",
}

TEST_PROMPTS = {
    "SubAgent Test": (
        "Analyze the following task by spawning sub-agents: "
        "1) A researcher to investigate best practices for Python error handling, "
        "2) A code_writer to write an example implementation"
    ),
    "Memory Test": (
        "Remember that I prefer Python type hints and Google-style docstrings. "
        "Then search memory to confirm it was saved."
    ),
    "Multi-Agent Review": (
        "I need you to: spawn a code_writer to create a fibonacci function, "
        "then spawn a reviewer to review the code quality"
    ),
    "Fallback Test": "Write a simple hello world in Python",
}


# ─────────────────────────────────────────────────────────
#  Mermaid helpers
# ─────────────────────────────────────────────────────────

def _clean_label_text(text: str) -> str:
    """Sanitise *text* before it is placed inside a Mermaid label."""
    import re
    t = (
        text
        .replace("\\", "")
        .replace('"', "'")
        .replace("\n", " ")
        .replace("\r", "")
        .replace("#", " ")
        .replace(";", ",")
        .replace("|", " ")
        .replace("<", " ")
        .replace(">", " ")
        .replace("{", " ")
        .replace("}", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace("[", " ")
        .replace("]", " ")
        .replace("`", "'")
        .replace("$", " ")
        .replace("&", "+")
        .replace("~", " ")
        .replace("=", " ")
        .replace("--", " ")  # Mermaid edge syntax
        .replace("->", " ")  # Mermaid edge syntax
        .replace("=>", " ")  # Mermaid edge syntax
        .replace(":", " ")   # Mermaid node description separator
    )
    return re.sub(r"\s+", " ", t).strip()


def _ascii_label(text: str) -> str:
    """Encode non-ASCII chars as HTML entities while keeping source ASCII-only."""
    return "".join(ch if ord(ch) < 128 else f"&#{ord(ch)};" for ch in text)


def _esc(text: str) -> str:
    """Sanitise *text* so it can be safely placed inside a Mermaid label
    (both ``"node label"`` and ``|"edge label"|``).

    Mermaid source is kept ASCII-only to avoid browser btoa() failures, but
    non-ASCII preview text is preserved through HTML numeric entities.
    """
    t = _clean_label_text(text)
    # Mermaid may call window.btoa() internally, which fails on non-Latin1 text.
    # Keep the diagram source ASCII-only; browsers render entities as text.
    return _ascii_label(t)


def _escape_html(text: str) -> str:
    """Escape HTML special chars (for Event Feed entries)."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\n", " ")
        .replace("\r", "")
    )


def _escape_bubble_html(text: str) -> str:
    """Escape assistant/user message HTML while preserving line breaks."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\r", "")
        .replace("\n", "<br>")
    )


def _edge_label(text: str, fallback: str, limit: int = 28) -> str:
    """Return a short Mermaid-safe edge label."""
    safe_text = _clean_label_text(text or "")
    if not safe_text:
        return fallback
    if len(safe_text) > limit:
        safe_text = safe_text[:limit].rstrip() + "..."
    safe = _ascii_label(safe_text)
    if not safe:
        return fallback
    return safe


def _add_tooltip(tooltips: dict[str, str], label: str, full_text: str) -> None:
    """Register tooltip by both raw entity label and rendered text label."""
    import html as _html
    tooltips[label] = full_text
    tooltips[_html.unescape(label)] = full_text


def _build_mermaid(
    agents: list[dict],
    is_working: bool,
    prompt_text: str = "",
    result_text: str = "",
    model_name: str = "",
) -> tuple[str, dict[str, str]]:
    """Return a (mermaid_definition, tooltips) tuple.

    Edge labels show short sanitised prompt/result previews.
    Full prompt/result text is exposed through browser tooltips.

    Nodes:
      U  = User  (stadium shape)
      M  = Main Agent  (rectangle)
      S0 … Sn = SubAgents  (rectangle, coloured by status)
    """
    has_result = bool(result_text)
    lines = ["graph LR"]

    # ── User ──────────────────────────────────────────────
    lines.append('    U(["User"])')

    # ── Main Agent ────────────────────────────────────────
    if has_result:
        m_detail = "Done"
        if model_name:
            safe_model = _esc(model_name[:20])
            m_detail += f" {safe_model}"
    elif is_working:
        m_detail = "Processing"
    else:
        m_detail = "Idle"
    lines.append(f'    M["Main Agent<br/><small>{m_detail}</small>"]')

    # ── User → Main edge (prompt은 짧은 요약만) ──────────
    if prompt_text:
        safe_p = _edge_label(prompt_text, "user prompt", limit=24)
        lines.append(f'    U -->|"{safe_p}"| M')
    else:
        lines.append("    U --> M")

    # ── SubAgents ─────────────────────────────────────────
    for i, a in enumerate(agents):
        detail = a["status"]
        if a.get("elapsed"):
            detail += f" {a['elapsed']}s"

        nid = f"S{i}"
        label = f"{_esc(a['type'])} Agent<br/><small>{detail}</small>"
        lines.append(f'    {nid}["{label}"]')

        prompt_label = _edge_label(a.get("query", ""), f"{a['type']} task")
        result_label = _edge_label(a.get("result_summary", ""), "result")

        # Main → SubAgent edge: prompt preview
        lines.append(f'    M -->|"{prompt_label}"| {nid}')

        # SubAgent → Main feedback: result/error preview
        if a["status"] == "completed":
            lines.append(f'    {nid} -.->|"{result_label}"| M')
        elif a["status"] == "failed":
            error_label = _edge_label(a.get("result_summary", ""), "failed")
            lines.append(f'    {nid} -.->|"{error_label}"| M')

    # ── Main Agent → User (완료 시) ──────────────────────
    if has_result:
        response_label = _edge_label(result_text, "response", limit=32)
        lines.append(f'    M ==>|"{response_label}"| U')

    # ── Styles ────────────────────────────────────────────
    lines.append(
        "    style U fill:#eff6ff,stroke:#3b82f6,"
        "stroke-width:2px,color:#1e40af"
    )
    if has_result:
        lines.append(
            "    style M fill:#f0fdf4,stroke:#22c55e,"
            "stroke-width:2px,color:#166534"
        )
    elif is_working:
        lines.append(
            "    style M fill:#dcfce7,stroke:#16a34a,"
            "stroke-width:3px,color:#166534"
        )
    else:
        lines.append(
            "    style M fill:#f0fdf4,stroke:#22c55e,"
            "stroke-width:2px,color:#166534"
        )

    _STATUS_STYLE = {
        "pending":   "fill:#fffbeb,stroke:#f59e0b,stroke-width:2px,color:#92400e",
        "running":   "fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#166534",
        "completed": "fill:#f8fafc,stroke:#94a3b8,stroke-width:2px,color:#475569",
        "failed":    "fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#991b1b",
    }
    for i, a in enumerate(agents):
        s = _STATUS_STYLE.get(a["status"], _STATUS_STYLE["pending"])
        lines.append(f"    style S{i} {s}")

    # Only the currently active nodes should pulse. Completed nodes stay static.
    lines.append("    classDef activeNode stroke-width:3px")
    active_nodes: list[str] = []
    if is_working and not has_result:
        active_nodes.append("M")
    active_nodes.extend(f"S{i}" for i, a in enumerate(agents) if a["status"] == "running")
    if active_nodes:
        lines.append(f"    class {','.join(active_nodes)} activeNode")

    # Build tooltip map: truncated edge-label text → full text
    # JS looks up edge labels by their displayed text, not node IDs
    tooltips: dict[str, str] = {}
    if prompt_text:
        safe_p = _edge_label(prompt_text, "user prompt", limit=24)
        _add_tooltip(tooltips, safe_p, prompt_text)
    if result_text:
        response_label = _edge_label(result_text, "response", limit=32)
        _add_tooltip(tooltips, response_label, result_text)
    for i, a in enumerate(agents):
        prompt_label = _edge_label(a.get("query", ""), f"{a['type']} task")
        if a.get("query"):
            _add_tooltip(tooltips, prompt_label, a["query"])

        if a.get("result_summary"):
            result_label = _edge_label(a.get("result_summary", ""), "result")
            _add_tooltip(tooltips, result_label, a["result_summary"])

    return "\n".join(lines), tooltips


def _build_page_html(
    mermaid_def: str,
    events: list[dict],
    is_working: bool,
    tooltips: dict[str, str] | None = None,
    render_id: int = 0,
) -> str:
    """Build a self-contained HTML page with Mermaid chart + Event Feed.

    This HTML is rendered inside an iframe via Streamlit's st.iframe() API.
    Mermaid JS is loaded from jsDelivr CDN and renders entirely client-side.
    """
    # Build event feed HTML
    evt_parts: list[str] = []
    for e in events:
        css = e.get("css_class", "")
        ts = e.get("time", "")
        evt_parts.append(
            f'<div class="ev {css}">'
            f'<span class="ts">{ts}</span> '
            f'{e["icon"]} {e["text"]}'
            f"</div>"
        )
    events_html = "\n".join(evt_parts)

    # Build JSON map for edge-label tooltips.
    # Sanitise values: they end up as HTML title attributes AND live inside
    # a <script> block, so we must neutralise </script> injection and
    # control characters.  json.dumps with ensure_ascii=True is safest.
    import json as _json
    _safe_tips: dict[str, str] = {}
    for _k, _v in (tooltips or {}).items():
        _sv = _v.replace("\r", "").replace("\x00", "")
        # Prevent </script> injection
        _sv = _sv.replace("</", "<\\/")
        _safe_tips[_k] = _sv
    tooltip_json = _json.dumps(_safe_tips, ensure_ascii=True)
    mermaid_json = _json.dumps(
        mermaid_def.replace("\r", "").replace("\x00", "").replace("</", "<\\/"),
        ensure_ascii=True,
    )

    # Optional CSS pulse for currently active nodes only.
    pulse_css = """
    @keyframes active-node-pulse {
        0%,100% { filter: drop-shadow(0 0 2px rgba(22,163,74,.20)); }
        50%     { filter: drop-shadow(0 0 16px rgba(22,163,74,.75)); }
    }
    .mermaid .activeNode rect,
    .mermaid .activeNode path,
    .mermaid .activeNode polygon {
        animation: active-node-pulse 1.35s ease-in-out infinite;
    }
    """ if is_working else ""

    return f"""<!DOCTYPE html>
<html data-render-id="{render_id}"><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#fff;color:#1e293b;padding:16px 12px 8px}}

/* Mermaid chart */
.mermaid{{text-align:center;min-height:100px;margin-bottom:8px}}
.mermaid svg{{max-width:100%}}
{pulse_css}

/* Event Feed */
.evts{{padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;
  border-radius:10px;max-height:175px;overflow-y:auto;scroll-behavior:smooth}}
.evts-t{{font-size:10.5px;font-weight:700;color:#475569;
  margin-bottom:5px;letter-spacing:.3px}}
.ev{{font-size:10.5px;padding:2px 0 2px 8px;color:#334155;
  border-left:2px solid #e2e8f0;margin-bottom:2px;line-height:1.45}}
.ev.subagent{{border-left-color:#a78bfa}}
.ev.tool{{border-left-color:#60a5fa}}
.ev.memory{{border-left-color:#34d399}}
.ev.done{{border-left-color:#22c55e}}
.ev.error{{border-left-color:#ef4444}}
.ev .ts{{color:#94a3b8;font-family:monospace;font-size:9px;margin-right:4px}}
.mermaid-error{{display:none;margin:8px 0 10px;padding:10px 12px;
  border:1px solid #fecaca;border-radius:10px;background:#fef2f2;color:#991b1b;
  font-size:11px;line-height:1.45;text-align:left;white-space:pre-wrap}}
.mermaid-error-title{{font-weight:700;margin-bottom:6px}}
.mermaid-error pre{{margin-top:6px;max-height:180px;overflow:auto;
  color:#7f1d1d;background:#fff1f2;border:1px solid #fecdd3;border-radius:6px;
  padding:8px;font-size:10px;white-space:pre-wrap}}
.edge-tooltip{{position:fixed;display:none;z-index:9999;max-width:min(760px,92vw);
  max-height:260px;overflow:auto;padding:10px 12px;border:1px solid #cbd5e1;
  border-radius:10px;background:#0f172a;color:#f8fafc;box-shadow:0 12px 32px rgba(15,23,42,.22);
  font-size:11px;line-height:1.45;text-align:left;white-space:pre-wrap;pointer-events:none}}
</style>
</head>
<body>

<pre class="mermaid">
{mermaid_def}
</pre>
<div id="mermaid-error" class="mermaid-error"></div>
<div id="edge-tooltip" class="edge-tooltip"></div>

<div class="evts" id="ev">
  {events_html}
</div>

<script>
mermaid.initialize({{
  startOnLoad:false,
  theme:'base',
  themeVariables:{{
    fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
    fontSize:'13px',
    lineColor:'#94a3b8',
    edgeLabelBackground:'#ffffff'
  }},
  flowchart:{{
    useMaxWidth:true,
    htmlLabels:true,
    curve:'basis',
    nodeSpacing:50,
    rankSpacing:80
  }}
}});
document.getElementById('ev').scrollTop=
  document.getElementById('ev').scrollHeight;

// ── Tooltip injection: hover on truncated edge labels to see full text ──
var _tooltips = {tooltip_json};
var _mermaidSource = {mermaid_json};
function _showMermaidError(err) {{
  var detail = err && (err.stack || err.message || String(err)) || "Unknown Mermaid error";
  console.error("[CodingAgent Mermaid] render failed", err);
  console.error("[CodingAgent Mermaid] source:\\n" + _mermaidSource);
  var box = document.getElementById("mermaid-error");
  if(box) {{
    box.style.display = "block";
    box.innerHTML =
      '<div class="mermaid-error-title">Mermaid rendering failed. Open browser console for full logs.</div>' +
      '<div><b>Error</b></div><pre></pre>' +
      '<div><b>Mermaid source</b></div><pre></pre>';
    var pres = box.querySelectorAll("pre");
    pres[0].textContent = detail;
    pres[1].textContent = _mermaidSource;
  }}
}}
window.addEventListener("error", function(event) {{
  if(String(event.message || "").toLowerCase().includes("mermaid")) {{
    _showMermaidError(event.error || event.message);
  }}
}});
mermaid.run().then(function(){{
  var tipBox = document.getElementById('edge-tooltip');
  function moveTip(event) {{
    if(!tipBox) return;
    var x = Math.min(event.clientX + 14, window.innerWidth - tipBox.offsetWidth - 12);
    var y = Math.min(event.clientY + 14, window.innerHeight - tipBox.offsetHeight - 12);
    tipBox.style.left = Math.max(12, x) + 'px';
    tipBox.style.top = Math.max(12, y) + 'px';
  }}
  document.querySelectorAll('.edgeLabel span, .edgeLabel p, .edgeLabel div, .edgeLabel foreignObject span').forEach(function(el){{
    var txt = (el.textContent||'').trim();
    if(_tooltips[txt]){{
      el.dataset.fullTooltip = _tooltips[txt];
      el.style.cursor = 'help';
      el.addEventListener('mouseenter', function(event) {{
        if(!tipBox) return;
        tipBox.textContent = el.dataset.fullTooltip || '';
        tipBox.style.display = 'block';
        moveTip(event);
      }});
      el.addEventListener('mousemove', moveTip);
      el.addEventListener('mouseleave', function() {{
        if(tipBox) tipBox.style.display = 'none';
      }});
    }}
  }});
}}).catch(_showMermaidError);
</script>
</body></html>"""


def _render_mermaid(
    placeholder,
    mermaid_def: str,
    events: list[dict],
    is_working: bool,
    num_agents: int = 0,
    tooltips: dict[str, str] | None = None,
) -> None:
    """Render Mermaid flowchart + event feed inside an iframe."""
    h = max(420, 260 + num_agents * 70)
    st.session_state["_mermaid_render_seq"] = (
        st.session_state.get("_mermaid_render_seq", 0) + 1
    )
    render_id = st.session_state["_mermaid_render_seq"]
    html = _build_page_html(
        mermaid_def,
        events,
        is_working,
        tooltips=tooltips,
        render_id=render_id,
    )
    print(
        "[CodingAgent Mermaid] render",
        render_id,
        "working=",
        is_working,
        "agents=",
        num_agents,
        "events=",
        len(events),
        flush=True,
    )
    placeholder.empty()
    placeholder.iframe(html, height=h)


# ─────────────────────────────────────────────────────────
#  Streaming logic
# ─────────────────────────────────────────────────────────

def _stream_response(
    prompt: str,
    graph_ph,
    result_ph,
    sa_mw,
) -> bool:
    """Stream agent response — update flowchart, event feed, and result."""
    comp = st.session_state.agent_components
    if not comp:
        return False

    agent = comp["agent"]
    fallback_mw = comp["fallback_middleware"]
    loop_guard = comp["loop_guard"]

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    loop_guard.reset()

    # ── Per-query unique thread ID (각 질의는 독립적 대화 컨텍스트) ──
    import uuid as _uuid
    query_id = _uuid.uuid4().hex[:8]
    config = {"configurable": {"thread_id": f"webui-{query_id}"}}
    inputs = {"messages": [HumanMessage(content=prompt)]}

    final_text = ""
    streamed_text = ""
    current_model = ""
    tools_used: list[dict] = []
    events: list[dict] = []  # 질의별 독립 이벤트 리스트
    step_count = 0
    t_start = time.time()

    # Local SubAgent tracking — 질의별 독립 (registry는 세션 공유이므로 사용하지 않음)
    tracked_agents: list[dict] = []
    _sa_counter = [0]  # mutable counter for unique IDs
    tool_call_agents: dict[str, int] = {}

    # ── helpers ───────────────────────────────────────────

    def _is_cancelled() -> bool:
        return bool(st.session_state.get("_refresh_requested"))

    def _render_agent_status(text: str) -> None:
        """Show progress in the Agent bubble until actual model content arrives."""
        if final_text:
            return
        result_ph.markdown(
            "<div class='agent-bubble'>"
            f"{text}<div class='agent-bubble-model'>Working...</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    def _render_agent_answer(text: str, model: str = "") -> None:
        model_html = ""
        if model:
            model_html = f"<div class='agent-bubble-model'>🧠 {_escape_html(model)}</div>"
        result_ph.markdown(
            f"<div class='agent-bubble'>{_escape_bubble_html(text)}{model_html}</div>",
            unsafe_allow_html=True,
        )

    def _message_text_delta(message, metadata) -> str:
        """Extract user-visible streamed text from a LangGraph messages chunk."""
        if metadata and metadata.get("lc_source") == "summarization":
            return ""

        blocks = getattr(message, "content_blocks", None)
        if blocks:
            text_parts: list[str] = []
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)

        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)
        return ""

    def _tool_call_value(tool_call, key: str, default=None):
        if isinstance(tool_call, dict):
            return tool_call.get(key, default)
        return getattr(tool_call, key, default)

    def _is_subagent_tool(tool_name: str) -> bool:
        return tool_name in ("spawn_subagent", "task")

    def _subagent_args(tool_name: str, args) -> tuple[str, str]:
        """Normalize custom and DeepAgents native subagent tool arguments."""
        if not isinstance(args, dict):
            return "general", str(args)
        if tool_name == "task":
            return (
                args.get("subagent_type", "general"),
                args.get("description", "") or str(args),
            )
        return (
            args.get("agent_type", "general"),
            args.get("task_description", "") or str(args),
        )

    def _evt(icon: str, text: str, css: str = "", refresh: bool = True) -> None:
        ts = time.strftime("%H:%M:%S")
        events.append({"icon": icon, "text": text, "css_class": css, "time": ts})
        _render_agent_status(f"{icon} {text}")
        if refresh:
            _refresh(True)

    def _track_spawn(agent_type: str, description: str) -> int:
        """Record a SubAgent spawn locally. Returns the index."""
        idx = _sa_counter[0]
        _sa_counter[0] += 1
        tracked_agents.append({
            "id": f"local_{idx}",
            "type": agent_type,
            "status": "running",
            "elapsed": "",
            "query": description,
            "model": "",
            "started_at": time.time(),
        })
        print(
            "[CodingAgent Mermaid] spawn_subagent",
            idx,
            agent_type,
            description[:120],
            flush=True,
        )
        return idx

    def _track_complete(
        agent_type: str,
        success: bool = True,
        model: str = "",
        result_summary: str = "",
    ) -> None:
        """Mark the most recent running SubAgent of the given type as done."""
        for a in reversed(tracked_agents):
            if a["type"] == agent_type and a["status"] == "running":
                a["status"] = "completed" if success else "failed"
                a["elapsed"] = f"{time.time() - a['started_at']:.1f}"
                if model:
                    a["model"] = model
                if result_summary:
                    a["result_summary"] = result_summary
                break

    def _track_complete_by_index(
        idx: int | None,
        success: bool = True,
        model: str = "",
        result_summary: str = "",
    ) -> bool:
        if idx is None or idx < 0 or idx >= len(tracked_agents):
            return False

        agent = tracked_agents[idx]
        agent["status"] = "completed" if success else "failed"
        agent["elapsed"] = f"{time.time() - agent['started_at']:.1f}"
        if model:
            agent["model"] = model
        if result_summary:
            agent["result_summary"] = result_summary
        print(
            "[CodingAgent Mermaid] complete_subagent",
            idx,
            agent["type"],
            agent["status"],
            result_summary[:120],
            flush=True,
        )
        return True

    def _agents_state() -> list[dict]:
        """Return locally tracked SubAgents for THIS query only.

        Does NOT fall back to registry (which is session-global) to avoid
        mixing SubAgent history from previous queries into this Mermaid graph.
        """
        return list(tracked_agents)

    def _refresh(working: bool, result: str = "", model: str = "") -> None:
        agents = _agents_state()
        mdef, tips = _build_mermaid(
            agents, working, prompt,
            result_text=result, model_name=model,
        )
        if agents:
            print("[CodingAgent Mermaid] source\n" + mdef, flush=True)
        _render_mermaid(graph_ph, mdef, events, working, num_agents=len(agents), tooltips=tips)

    # ── Non-streaming fallback ────────────────────────────

    try:
        _evt("🚀", f"Prompt received ({len(prompt)} chars)", "tool")

        if not hasattr(agent, "stream"):
            _evt("⚠️", "Agent lacks .stream() — using non-streaming invoke", "tool")
            result = agent.invoke(inputs, config=config)
            for msg in result.get("messages", []):
                if getattr(msg, "type", None) == "ai" and msg.content:
                    final_text = (
                        msg.content if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                elif getattr(msg, "type", None) == "tool":
                    tname = getattr(msg, "name", "?")
                    tools_used.append({
                        "name": tname,
                        "result": str(msg.content)[:200] if msg.content else "",
                        "is_subagent": _is_subagent_tool(tname) or tname == "list_subagents",
                    })
                    _evt("🔧", f"Tool <b>{tname}</b> executed", "tool")

            with result_ph:
                _model_tag = ""
                _cm = fallback_mw.current_model or "?"
                if _cm:
                    _model_tag = f"<div class='agent-bubble-model'>🧠 {_escape_html(_cm)}</div>"
                safe_final_text = _escape_bubble_html(final_text or "*(No response)*")
                st.markdown(
                    f"<div class='agent-bubble'>{safe_final_text}{_model_tag}</div>",
                    unsafe_allow_html=True,
                )

            current_model = fallback_mw.current_model or "?"
            elapsed_s = f"{time.time() - t_start:.1f}"
            _evt("🏁", f"Done — <b>{current_model}</b> · {elapsed_s}s · {len(final_text):,} chars", "done")
            # 최종 Mermaid: Main Agent → User edge 포함
            _refresh(False, result=final_text, model=current_model)

            inv_agents = _agents_state()
            inv_mdef, inv_tips = _build_mermaid(
                inv_agents, False, prompt,
                result_text=final_text, model_name=current_model,
            )
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": final_text or "*(No response)*",
                "model": current_model,
                "tools_used": tools_used,
                "activity_log": [(e["icon"], e["text"]) for e in events],
                "mermaid_def": inv_mdef,
                "mermaid_tooltips": inv_tips,
                "mermaid_events": list(events),
                "num_agents": len(inv_agents),
            })
            return True

        # ── Streaming mode ────────────────────────────────

        current_model = fallback_mw.current_model or ""
        _evt("🔄", f"Streaming started (model: <b>{_escape_html(current_model or 'selecting…')}</b>)", "tool")

        try:
            stream = agent.stream(
                inputs,
                config=config,
                stream_mode=["messages", "updates"],
                subgraphs=True,
            )
        except TypeError:
            stream = agent.stream(
                inputs,
                config=config,
                stream_mode=["messages", "updates"],
            )

        for raw_chunk in stream:
            if _is_cancelled():
                _evt("🛑", "Refresh requested — stopping current run", "error", refresh=False)
                return False

            if isinstance(raw_chunk, tuple) and len(raw_chunk) == 3:
                namespace, current_stream_mode, chunk_data = raw_chunk
                is_main_agent = not namespace
            elif isinstance(raw_chunk, tuple) and len(raw_chunk) == 2:
                namespace = ()
                current_stream_mode, chunk_data = raw_chunk
                is_main_agent = True
            else:
                namespace = ()
                current_stream_mode = "updates"
                chunk_data = raw_chunk
                is_main_agent = True

            if current_stream_mode == "messages":
                if not is_main_agent:
                    continue
                if not isinstance(chunk_data, tuple) or len(chunk_data) != 2:
                    continue
                message, metadata = chunk_data
                msg_type = getattr(message, "type", None)
                if msg_type == "AIMessageChunk" or "AIMessageChunk" in type(message).__name__ or msg_type == "ai":
                    text_delta = _message_text_delta(message, metadata)
                    if text_delta:
                        streamed_text += text_delta
                        final_text = streamed_text
                        _render_agent_answer(streamed_text)
                continue

            if not is_main_agent:
                continue

            chunk = chunk_data
            if not isinstance(chunk, dict):
                continue

            step_count += 1
            for _node, node_output in chunk.items():
                if _is_cancelled():
                    _evt("🛑", "Refresh requested — stopping current run", "error", refresh=False)
                    return False

                # Unwrap LangGraph Overwrite wrapper if present
                if not isinstance(node_output, dict):
                    node_output = getattr(node_output, "value", None) or {}
                if not isinstance(node_output, dict):
                    continue

                # messages may also be wrapped in Overwrite
                raw_msgs = node_output.get("messages", [])
                if not isinstance(raw_msgs, list):
                    raw_msgs = getattr(raw_msgs, "value", None) or []
                if not isinstance(raw_msgs, list):
                    raw_msgs = [raw_msgs] if raw_msgs else []

                for msg in raw_msgs:
                    msg_type = getattr(msg, "type", None)

                    if msg_type == "ai":
                        tool_calls = getattr(msg, "tool_calls", [])
                        if tool_calls:
                            for tc in tool_calls:
                                name = _tool_call_value(tc, "name", "unknown")
                                args = _tool_call_value(tc, "args", {}) or {}
                                if _is_subagent_tool(name):
                                    atype, full_desc = _subagent_args(name, args)
                                    desc = _escape_html(full_desc[:60])
                                    # Track locally so Mermaid shows it immediately
                                    tracked_idx = _track_spawn(atype, full_desc)
                                    tool_call_id = _tool_call_value(tc, "id")
                                    if tool_call_id:
                                        tool_call_agents[str(tool_call_id)] = tracked_idx
                                    _evt(
                                        AGENT_ICONS.get(atype, "🤖"),
                                        f"Spawning <b>{atype}</b> SubAgent via <b>{name}</b>: {desc}",
                                        "subagent",
                                    )
                                elif name == "list_subagents":
                                    _evt("📋", "Listing SubAgents status", "subagent")
                                elif "memory_store" in name:
                                    cat = args.get("category", "?")
                                    _evt("🧠", f"Storing memory → <b>{cat}</b>", "memory")
                                elif "memory_search" in name:
                                    q = _escape_html(args.get("query", "")[:40])
                                    _evt("🧠", f"Searching memory: {q}", "memory")
                                else:
                                    arg_summary = ", ".join(
                                        f"{k}={str(v)[:20]}" for k, v in list(args.items())[:3]
                                    )
                                    _evt("🔧", f"Calling <b>{name}</b>({_escape_html(arg_summary)})", "tool")

                        content = (
                            msg.content
                            if isinstance(msg.content, str)
                            else str(msg.content) if msg.content
                            else ""
                        )
                        if content and not tool_calls:
                            final_text = content
                            streamed_text = content
                            _evt(
                                "💬",
                                f"AI response received ({len(content):,} chars)",
                                "done",
                                refresh=False,
                            )
                            _refresh(True, result=final_text, model=current_model)
                            _render_agent_answer(final_text)

                    elif msg_type == "tool":
                        tool_name = getattr(msg, "name", "unknown")
                        tool_call_id = getattr(msg, "tool_call_id", None)
                        tracked_idx = tool_call_agents.get(str(tool_call_id)) if tool_call_id else None
                        tool_content_full = str(msg.content) if msg.content else ""
                        tool_content = tool_content_full[:300]
                        is_sa = _is_subagent_tool(tool_name) or tool_name == "list_subagents"
                        tools_used.append({
                            "name": tool_name,
                            "result": tool_content,
                            "is_subagent": is_sa,
                        })

                        if _is_subagent_tool(tool_name):
                            # Extract info from registry history for model/elapsed
                            model_label = ""
                            if tracked_idx is None:
                                tracked_idx = _track_spawn("general", f"{tool_name} result")
                            sa_type = (
                                tracked_agents[tracked_idx]["type"]
                                if tracked_idx is not None and tracked_idx < len(tracked_agents)
                                else ""
                            )
                            sa_elapsed = ""
                            sa_model_short = ""
                            try:
                                for t in reversed(sa_mw.registry.history):
                                    if not sa_type:
                                        sa_type = getattr(t, "agent_type", "")
                                    if hasattr(t, "model_used") and t.model_used:
                                        sa_model_short = t.model_used.split("/")[-1][:20]
                                        model_label = f" · 🧠 <b>{sa_model_short}</b>"
                                    if hasattr(t, "completed_at") and hasattr(t, "created_at"):
                                        if t.completed_at and t.created_at:
                                            sa_elapsed = f" · {t.completed_at - t.created_at:.1f}s"
                                    break
                            except Exception:
                                pass

                            # Extract raw result from tool output (no truncation)
                            _result_raw = ""
                            if "Result:" in tool_content_full:
                                _ri = tool_content_full.index("Result:") + 7
                                _result_raw = tool_content_full[_ri:].strip()
                            elif tool_content_full.strip():
                                _result_raw = tool_content_full.strip()

                            if "Result:" in tool_content_full or "result" in tool_content_full.lower()[:30]:
                                if not _track_complete_by_index(tracked_idx, success=True, model=sa_model_short, result_summary=_result_raw):
                                    _track_complete(sa_type or "general", success=True, model=sa_model_short, result_summary=_result_raw)
                                icon = AGENT_ICONS.get(sa_type, "✅")
                                result_preview = _escape_html(tool_content[:80])
                                _evt(icon, f"SubAgent <b>{sa_type}</b> completed{sa_elapsed}{model_label}: {result_preview}", "done")
                            elif "failed" in tool_content_full.lower():
                                if not _track_complete_by_index(tracked_idx, success=False, model=sa_model_short, result_summary=_result_raw):
                                    _track_complete(sa_type or "general", success=False, model=sa_model_short, result_summary=_result_raw)
                                err_preview = _escape_html(tool_content[:80])
                                _evt("❌", f"SubAgent failed: {err_preview}", "error")
                            else:
                                if not _track_complete_by_index(tracked_idx, success=True, model=sa_model_short, result_summary=_result_raw):
                                    _track_complete(sa_type or "general", success=True, model=sa_model_short, result_summary=_result_raw)
                                _evt("🔄", f"SubAgent returned: {_escape_html(tool_content[:60])}", "subagent")
                            # SubAgent 상태 변경 → Mermaid 즉시 갱신
                            _refresh(True)

                        elif tool_name == "list_subagents":
                            count = tool_content.count("[")
                            _evt("📋", f"SubAgent list returned ({count} entries)", "subagent")
                            _refresh(True)

                        elif "memory_store" in tool_name:
                            _evt("✅", f"Memory stored: {_escape_html(tool_content[:60])}", "done")

                        elif "memory_search" in tool_name:
                            n_results = tool_content.count("---") + (1 if tool_content.strip() and "No relevant" not in tool_content else 0)
                            _evt("✅", f"Memory search returned {n_results} results", "done")

                        else:
                            preview = _escape_html(tool_content[:60])
                            _evt("✅", f"<b>{tool_name}</b> → {preview}", "done")

                # 매 chunk마다 모델명 갱신 시도
                if fallback_mw.current_model:
                    current_model = fallback_mw.current_model

        # ── Extract final text if not captured ────────────

        if not final_text:
            try:
                state = agent.get_state(config)
                for msg in reversed(state.values.get("messages", [])):
                    if getattr(msg, "type", None) == "ai" and msg.content:
                        final_text = (
                            msg.content
                            if isinstance(msg.content, str)
                            else str(msg.content)
                        )
                        if not streamed_text:
                            streamed_text = final_text
                        break
            except Exception:
                pass

        if not final_text:
            final_text = "*(No response generated)*"

        current_model = fallback_mw.current_model or current_model or "unknown"
        _model_tag = f"<div class='agent-bubble-model'>🧠 {_escape_html(current_model)}</div>"
        elapsed_s = f"{time.time() - t_start:.1f}"
        _evt(
            "🏁",
            f"Completed — <b>{current_model}</b> · {step_count} steps · {elapsed_s}s · {len(final_text):,} chars",
            "done",
            refresh=False,
        )
        # 최종 Mermaid를 먼저 갱신한 뒤 답변 bubble을 채워서 둘이 같이 나타나는 느낌을 준다.
        _refresh(False, result=final_text, model=current_model)
        with result_ph:
            safe_final_text = _escape_bubble_html(final_text)
            st.markdown(
                f"<div class='agent-bubble'>{safe_final_text}{_model_tag}</div>",
                unsafe_allow_html=True,
            )

        # Mermaid 최종 스냅샷 저장 (History 탭용)
        final_agents = _agents_state()
        final_mdef, final_tips = _build_mermaid(
            final_agents, False, prompt,
            result_text=final_text, model_name=current_model,
        )

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": final_text,
            "model": current_model,
            "tools_used": tools_used,
            "activity_log": [(e["icon"], e["text"]) for e in events],
            "mermaid_def": final_mdef,
            "mermaid_tooltips": final_tips,
            "mermaid_events": list(events),
            "num_agents": len(final_agents),
        })
        return True

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Agent error: %s\n%s", e, tb)
        elapsed_s = f"{time.time() - t_start:.1f}"
        _evt("❌", f"Error after {elapsed_s}s: {_escape_html(str(e))}", "error")
        with result_ph:
            st.error(f"Error: {e}")
            with st.expander("Traceback"):
                st.code(tb, language="python")
        _refresh(False)
        err_agents = _agents_state()
        err_mdef, err_tips = _build_mermaid(err_agents, False, prompt)
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": f"Error: {e}",
            "model": None,
            "tools_used": [],
            "mermaid_def": err_mdef,
            "mermaid_tooltips": err_tips,
            "mermaid_events": list(events),
            "num_agents": len(err_agents),
        })
        return True


# ─────────────────────────────────────────────────────────
#  Page renderer
# ─────────────────────────────────────────────────────────

def render_chat() -> None:
    """Render the Chat page.

    Layout:
      ┌──────────────────────────────────────────────────────┐
      │  (idle) Danny's Coding AI Agent  (중앙 타이틀)       │
      │  (active) 🤖 Agent answer                             │
      │           🔍 Agent 동작 분석                          │
      │           👤 User prompt                              │
      ├──────────────────────────────────────────────────────┤
      │  📌 PROMPT 프리셋 버튼                                │
      │  📝 입력창  │ 🚀 Send / 🔄 Refresh                  │
      └──────────────────────────────────────────────────────┘
    """
    comp = st.session_state.get("agent_components")
    if not comp:
        st.warning("Agent not initialized.")
        return

    sa_mw = comp["subagent_middleware"]

    # ── Session state defaults ────────────────────────────
    for k, v in [
        ("_is_running", False),
        ("_has_result", False),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    # Pending prompt: set by Send button, consumed this render cycle
    pending = st.session_state.pop("_pending_prompt", None)
    if pending:
        st.session_state["_is_running"] = True
    is_running = st.session_state["_is_running"]

    # 전송 후 입력창 비우기 — 위젯 렌더링 전에 처리해야 함
    if st.session_state.pop("_clear_prompt", False):
        st.session_state["_prompt_area"] = ""

    # ── Page-level CSS ────────────────────────────────────
    st.markdown("""
    <style>
    section[data-testid="stMain"] .block-container {
        padding-top: 1.2rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100%;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
    }
    /* Chat bubble styles — User (right, blue) */
    .user-bubble {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 16px 16px 4px 16px;
        padding: 14px 18px;
        margin: 0 0 8px auto;
        max-width: 92%;
        font-size: 0.95em;
        color: #1e40af;
        line-height: 1.55;
        word-break: break-word;
        box-shadow: 0 4px 14px rgba(59, 130, 246, .08);
    }
    .user-bubble-label {
        font-size: .75em;
        font-weight: 700;
        color: #3b82f6;
        margin-bottom: 4px;
        letter-spacing: .3px;
        text-align: right;
        padding-right: .25rem;
    }
    /* Chat bubble styles — Agent (left, green) */
    .agent-bubble {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 16px 16px 16px 4px;
        padding: 14px 18px;
        margin: 0 auto 8px 0;
        max-width: 92%;
        font-size: 0.95em;
        color: #166534;
        line-height: 1.55;
        word-break: break-word;
        max-height: 500px;
        overflow-y: auto;
        box-shadow: 0 4px 14px rgba(22, 163, 74, .08);
    }
    .agent-bubble-label {
        font-size: .75em;
        font-weight: 700;
        color: #16a34a;
        margin-bottom: 4px;
        margin-top: 22px;
        letter-spacing: .3px;
        padding-left: .25rem;
    }
    .agent-bubble-model {
        font-size: .7em;
        color: #6b7280;
        margin-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Determine conversation state ─────────────────────
    has_conversation = bool(st.session_state.chat_messages) or pending or is_running

    # ── 1. Main content area ─────────────────────────────
    graph_ph = st.empty()
    result_ph_ref = {"ph": None}

    if not has_conversation:
        # ── Idle state: centered title (no heavy Mermaid render) ──
        st.markdown(
            "<div style='text-align:center;padding:100px 20px 60px'>"
            "<h1 style='color:#1e293b;font-size:2em;margin-bottom:8px'>"
            "Danny's Coding AI Agent</h1>"
            "<p style='color:#94a3b8;font-size:1.05em'>"
            "메시지를 입력하거나 프롬프트를 클릭하세요</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Lightweight hidden placeholders (no iframe rendering)
        result_ph_ref["ph"] = st.empty()

    else:
        # ── Active conversation: chat-style layout ────────

        # Show previous conversation pairs (history within session)
        # Layout: Agent answer → Mermaid analysis → User prompt.
        _last_user_content = ""
        _assistant_total = sum(
            1 for msg in st.session_state.chat_messages
            if msg["role"] == "assistant"
        )
        _assistant_idx = 0
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                _last_user_content = msg["content"]

            elif msg["role"] == "assistant":
                _assistant_idx += 1
                _is_latest_assistant = _assistant_idx == _assistant_total

                model_html = ""
                if msg.get("model"):
                    model_html = f"<div class='agent-bubble-model'>🧠 {_escape_html(msg['model'])}</div>"
                safe_content = _escape_bubble_html(msg["content"])
                st.markdown(
                    f"<div class='agent-bubble-label'>🤖 Agent</div>"
                    f"<div class='agent-bubble'>{safe_content}{model_html}</div>",
                    unsafe_allow_html=True,
                )

                if msg.get("mermaid_def"):
                    _hist_html = _build_page_html(
                        msg["mermaid_def"],
                        msg.get("mermaid_events", []),
                        False,
                        tooltips=msg.get("mermaid_tooltips", {}),
                    )
                    _h = max(350, 220 + msg.get("num_agents", 0) * 70)
                    analysis_col, _ = st.columns([23, 2])
                    with analysis_col:
                        with st.expander("🔍 Agent 동작 분석", expanded=_is_latest_assistant):
                            st.iframe(_hist_html, height=_h)

                st.markdown(
                    f"<div class='user-bubble-label'>👤 User</div>"
                    f"<div class='user-bubble'>{_escape_bubble_html(_last_user_content)}</div>",
                    unsafe_allow_html=True,
                )

                st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:12px 0'>",
                            unsafe_allow_html=True)

        # ── Live interaction area (current pending/running) ──
        # Layout: Agent progress/answer → Mermaid analysis → User prompt.
        if pending or is_running:
            st.markdown(
                "<div class='agent-bubble-label'>🤖 Agent</div>",
                unsafe_allow_html=True,
            )
            result_ph_ref["ph"] = st.empty()
            if pending or is_running:
                result_ph_ref["ph"].markdown(
                    "<div class='agent-bubble'>"
                    "Thinking...<div class='agent-bubble-model'>Waiting for model output</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                "<p style='margin:10px 0 4px;font-size:.8em;font-weight:700;"
                "color:#64748b;letter-spacing:.4px'>🔍 AGENT 동작 분석</p>",
                unsafe_allow_html=True,
            )
            analysis_col, _ = st.columns([23, 2])
            with analysis_col:
                graph_ph = st.empty()
                idle_def, tips = _build_mermaid([], True, pending or "")
                _render_mermaid(graph_ph, idle_def, [], True, num_agents=0, tooltips=tips)

            prompt_display = pending or "(processing…)"
            st.markdown(
                f"<div class='user-bubble-label'>👤 User</div>"
                f"<div class='user-bubble'>{_escape_bubble_html(prompt_display)}</div>",
                unsafe_allow_html=True,
            )
        else:
            result_ph_ref["ph"] = st.empty()

    # ── Bottom section: Prompt presets + Input ────────────
    st.markdown(
        "<hr style='border:none;border-top:1px solid #e2e8f0;margin:16px 0 8px'>",
        unsafe_allow_html=True,
    )

    # ── Prompt 프리셋 버튼 ────────────────────────────────
    st.markdown(
        "<p style='margin:4px 0 6px;font-size:.8em;font-weight:700;"
        "color:#64748b;letter-spacing:.4px'>📌 PROMPT</p>",
        unsafe_allow_html=True,
    )
    tp_cols = st.columns(len(TEST_PROMPTS))
    for i, (label, p) in enumerate(TEST_PROMPTS.items()):
        with tp_cols[i]:
            if st.button(
                f"▶ {label}",
                key=f"test_{label}",
                use_container_width=True,
                disabled=is_running,
            ):
                st.session_state["_prompt_area"] = p
                st.rerun()

    # ── 질의 입력창 + Send/Refresh ───────────────────────
    input_col, action_col = st.columns([6, 1])
    with input_col:
        # ★ 입력창: is_running일 때만 disabled (idle 상태에서는 항상 활성)
        user_input = st.text_area(
            "prompt",
            key="_prompt_area",
            height=80,
            disabled=is_running,
            label_visibility="collapsed",
            placeholder="Ask me anything about coding…",
        )
    with action_col:
        # ★ Send: 실행 중일 때만 비활성. 빈 입력은 클릭 후 안내로 처리한다.
        send_clicked = st.button(
            "🚀 Send",
            use_container_width=True,
            disabled=is_running,
            type="primary",
        )
        refresh_clicked = st.button(
            "🔄 Refresh",
            use_container_width=True,
            type="secondary",
        )
    if send_clicked:
        if user_input and user_input.strip():
            st.session_state["_pending_prompt"] = user_input.strip()
            st.session_state["_clear_prompt"] = True
            st.rerun()
        else:
            st.info("메시지를 입력한 뒤 Send를 눌러주세요.")
    if refresh_clicked:
        st.session_state["_refresh_requested"] = True
        st.session_state["_is_running"] = False
        st.session_state.pop("_pending_prompt", None)
        st.session_state["_has_result"] = False
        st.session_state["chat_messages"] = []
        st.session_state["_clear_prompt"] = True
        st.rerun()

    # ── Pending prompt 실행 ───────────────────────────────
    if pending:
        st.session_state["_refresh_requested"] = False
        st.session_state["_is_running"] = True
        completed = False
        try:
            completed = _stream_response(pending, graph_ph, result_ph_ref["ph"], sa_mw)
        finally:
            st.session_state["_is_running"] = False
            st.session_state["_has_result"] = completed
            # ★ 실행 완료 후 rerun → 입력창 활성화 + New Chat 활성화
            st.rerun()
