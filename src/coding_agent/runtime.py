"""Runtime bootstrap for local split mode vs deployed single mode."""

from __future__ import annotations

from pathlib import Path

from coding_agent.agent import create_coding_agent
from coding_agent.config import Settings, settings
from coding_agent.langgraph_remote import create_remote_coding_agent


def create_runtime_components(
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
):
    cfg = custom_settings or settings
    topology = (cfg.deployment_topology or "single").strip().lower()

    if topology == "single":
        return create_remote_coding_agent(cfg, cwd=cwd or Path.cwd())

    if topology in {"split", "hybrid"}:
        return create_coding_agent(custom_settings=cfg, cwd=cwd, topology=topology)

    raise ValueError(f"Unknown deployment topology: {cfg.deployment_topology}")
