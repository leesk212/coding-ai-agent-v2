"""Runtime bootstrap for local split mode vs deployed single mode."""

from __future__ import annotations

import logging
from pathlib import Path

from coding_agent.agent import create_coding_agent
from coding_agent.config import Settings, settings
from coding_agent.langgraph_remote import check_langgraph_deployment, create_remote_coding_agent

logger = logging.getLogger(__name__)


def create_runtime_components(
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
):
    cfg = custom_settings or settings
    topology = (cfg.deployment_topology or "split").strip().lower()

    if topology == "single":
        if not cfg.langgraph_deployment_url:
            logger.info("single topology requested without LANGGRAPH_DEPLOYMENT_URL; using split fallback")
            return create_coding_agent(custom_settings=cfg, cwd=cwd, topology="split")
        try:
            check_langgraph_deployment(cfg.langgraph_deployment_url, cfg.langgraph_assistant_id)
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "LangGraph deployment unavailable at %s for assistant %s; using split fallback: %s",
                cfg.langgraph_deployment_url,
                cfg.langgraph_assistant_id,
                exc,
            )
            return create_coding_agent(custom_settings=cfg, cwd=cwd, topology="split")
        return create_remote_coding_agent(cfg, cwd=cwd or Path.cwd())

    if topology in {"split", "hybrid"}:
        return create_coding_agent(custom_settings=cfg, cwd=cwd, topology=topology)

    raise ValueError(f"Unknown deployment topology: {cfg.deployment_topology}")
