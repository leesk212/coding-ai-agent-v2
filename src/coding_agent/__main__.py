"""CLI entry point for the Coding AI Agent.

Usage:
    python -m coding_agent [--webui] [--debug] [--memory-dir DIR]

Built on DeepAgents CLI with custom extensions for:
- Long-term memory (ChromaDB)
- Dynamic sub-agents
- Model fallback (OpenRouter open-source -> Ollama local)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from coding_agent.config import settings

console = Console()
logger = logging.getLogger("coding_agent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coding AI Agent")
    parser.add_argument(
        "--memory-dir",
        type=str,
        default=None,
        help="Override memory persistence directory",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--webui",
        action="store_true",
        help="Launch the Streamlit WebUI instead of CLI",
    )
    return parser.parse_args()


def print_banner() -> None:
    banner = Text()
    banner.append("Coding AI Agent", style="bold cyan")
    banner.append(" v0.2.0\n", style="dim")
    banner.append(
        "DeepAgents CLI + Long-Term Memory + Dynamic SubAgents + Model Fallback\n",
        style="dim",
    )

    model_info = settings.get_all_models()
    model_list = " -> ".join(m.name for m in model_info[:3])
    banner.append(f"Models: {model_list} -> local\n", style="dim green")

    memory_stats = ""
    try:
        from coding_agent.memory.store import LongTermMemory

        ltm = LongTermMemory(str(settings.memory_dir))
        stats = ltm.get_stats()
        total = sum(stats.values())
        memory_stats = f"Memory: {total} entries across {len(stats)} categories"
    except Exception:
        memory_stats = "Memory: initializing..."
    banner.append(memory_stats, style="dim yellow")

    console.print(
        Panel(banner, title="[bold]Welcome[/bold]", border_style="cyan")
    )
    console.print("[dim]Type your request. Press Ctrl+C to exit.[/dim]")
    console.print("[dim]Commands: /status /memory /subagents /quit[/dim]\n")


async def run_agent_loop(agent_components: dict) -> None:
    """Main interactive loop."""
    from langchain_core.messages import HumanMessage

    agent = agent_components["agent"]
    fallback_mw = agent_components["fallback_middleware"]
    loop_guard = agent_components["loop_guard"]

    config = {"configurable": {"thread_id": "cli-session"}}

    while True:
        try:
            user_input = console.input("[bold green]You>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "/quit"):
            console.print("[dim]Goodbye![/dim]")
            break

        # Slash commands
        if user_input.lower() == "/status":
            status = fallback_mw.get_status()
            console.print(Panel(str(status), title="Model Status"))
            continue

        if user_input.lower() == "/memory":
            memory_mw = agent_components["memory_middleware"]
            stats = memory_mw.store.get_stats()
            console.print(Panel(str(stats), title="Memory Stats"))
            continue

        if user_input.lower() == "/subagents":
            sa_mw = agent_components["subagent_middleware"]
            proc_rows = sa_mw.get_all_tasks()
            if proc_rows:
                console.print("[bold]Processes[/bold]")
                for t in proc_rows[:10]:
                    console.print(
                        f"  [{t['id']}] {t['status']} ({t['agent_type']}): "
                        f"{t['task_description'][:60]}"
                    )
            tracker = agent_components.get("async_task_tracker")
            task_rows = tracker.get_tasks("cli-session") if tracker else []
            if task_rows:
                console.print("[bold]Tracked Tasks[/bold]")
                for t in task_rows[:10]:
                    console.print(
                        f"  [{t['task_id']}] {t['status']} ({t['agent_type']}) "
                        f"run={t['run_id'][:12]}"
                    )
            if not proc_rows and not task_rows:
                console.print("  (no sub-agents)")
            continue

        # Reset loop guard for new request
        loop_guard.reset()

        try:
            inputs = {"messages": [HumanMessage(content=user_input)]}

            with console.status("[bold cyan]Thinking...[/bold cyan]"):
                response_text = ""
                async for event in agent.astream_events(
                    inputs, config=config, version="v2"
                ):
                    kind = event.get("event", "")

                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            content = chunk.content
                            if isinstance(content, str):
                                console.print(content, end="")
                                response_text += content

                    elif kind == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        console.print(
                            f"\n[dim cyan]> Tool: {tool_name}[/dim cyan]", end=""
                        )

                    elif kind == "on_tool_end":
                        console.print(" [dim green]done[/dim green]")

                console.print()

                # Show model used
                current_model = fallback_mw.current_model
                if current_model:
                    console.print(f"[dim]Model: {current_model}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
            continue
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Agent error")
            continue


def main() -> None:
    args = parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if args.memory_dir:
        from pathlib import Path

        settings.memory_dir = Path(args.memory_dir)

    if args.webui:
        import subprocess
        import os

        webui_path = os.path.join(os.path.dirname(__file__), "webui", "app.py")
        env = os.environ.copy()
        if args.debug:
            env["CODING_AGENT_DEBUG"] = "1"
        # Log level for streamlit subprocess
        env.setdefault("PYTHONUNBUFFERED", "1")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                webui_path,
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
                "--logger.level",
                "debug" if args.debug else "info",
            ],
            env=env,
            check=True,
        )
        return

    print_banner()

    try:
        from coding_agent.agent import create_coding_agent

        components = create_coding_agent()
        with console.status("[bold cyan]Starting local async subagents...[/bold cyan]"):
            components["subagent_manager"].ensure_all_started()
    except Exception as e:
        console.print(f"[red]Failed to initialize agent: {e}[/red]")
        logger.exception("Init failed")
        sys.exit(1)

    asyncio.run(run_agent_loop(components))


if __name__ == "__main__":
    main()
