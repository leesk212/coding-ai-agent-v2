"""Runtime bootstrap for local split mode vs deployed single mode."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path

from coding_agent.agent import create_coding_agent, finalize_coding_agent, prewarm_coding_agent
from coding_agent.config import Settings, settings
from coding_agent.langgraph_remote import check_langgraph_deployment, create_remote_coding_agent

logger = logging.getLogger(__name__)


def create_runtime_components(
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
    progress_cb: Callable[[str], None] | None = None,
):
    cfg = custom_settings or settings
    topology = (cfg.deployment_topology or "split").strip().lower()
    if progress_cb:
        progress_cb(f"Runtime bootstrap starting (topology={topology})")

    if topology == "single":
        if not cfg.langgraph_deployment_url:
            logger.info("single topology requested without LANGGRAPH_DEPLOYMENT_URL; using split fallback")
            if progress_cb:
                progress_cb("single topology requested without deployment URL; falling back to split")
            cfg.deployment_topology = "split"
            os.environ["DEEPAGENTS_DEPLOYMENT_TOPOLOGY"] = "split"
            return create_coding_agent(custom_settings=cfg, cwd=cwd, topology="split", progress_cb=progress_cb)
        try:
            if progress_cb:
                progress_cb(f"Checking LangGraph deployment at {cfg.langgraph_deployment_url} (assistant={cfg.langgraph_assistant_id})")
            check_langgraph_deployment(cfg.langgraph_deployment_url, cfg.langgraph_assistant_id)
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "LangGraph deployment unavailable at %s for assistant %s; using split fallback: %s",
                cfg.langgraph_deployment_url,
                cfg.langgraph_assistant_id,
                exc,
            )
            if progress_cb:
                progress_cb("Deployment unavailable; continuing in split mode")
            cfg.deployment_topology = "split"
            os.environ["DEEPAGENTS_DEPLOYMENT_TOPOLOGY"] = "split"
            return create_coding_agent(custom_settings=cfg, cwd=cwd, topology="split", progress_cb=progress_cb)
        if progress_cb:
            progress_cb("Deployment reachable; creating remote supervisor adapter")
        return create_remote_coding_agent(cfg, cwd=cwd or Path.cwd(), progress_cb=progress_cb)

    if topology in {"split", "hybrid"}:
        return create_coding_agent(custom_settings=cfg, cwd=cwd, topology=topology, progress_cb=progress_cb)

    raise ValueError(f"Unknown deployment topology: {cfg.deployment_topology}")


def prewarm_runtime_components(
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
    progress_cb: Callable[[str], None] | None = None,
):
    cfg = custom_settings or settings
    topology = (cfg.deployment_topology or "split").strip().lower()
    if progress_cb:
        progress_cb(f"Runtime prewarm starting (topology={topology})")

    if topology in {"split", "hybrid"}:
        return prewarm_coding_agent(
            custom_settings=cfg,
            cwd=cwd,
            topology=topology,
            progress_cb=progress_cb,
        )

    if progress_cb:
        progress_cb("Remote deployment topology selected; local DeepAgents prewarm skipped")
    return {
        "prewarmed": False,
        "deployment_topology": topology,
        "custom_settings": cfg,
        "working_dir": str(cwd or Path.cwd()),
    }


def finalize_runtime_components(
    prewarmed: dict,
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
    progress_cb: Callable[[str], None] | None = None,
):
    if prewarmed.get("prewarmed"):
        return finalize_coding_agent(prewarmed, progress_cb=progress_cb)
    return create_runtime_components(
        custom_settings=custom_settings,
        cwd=cwd,
        progress_cb=progress_cb,
    )
