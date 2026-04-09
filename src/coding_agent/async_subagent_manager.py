"""DeepAgents AsyncSubAgent registry and local runtime manager.

This module has one job: define async subagents in the exact shape DeepAgents
expects, and optionally make local Agent Protocol runtimes available for those
specs when the transport is HTTP.
"""

from __future__ import annotations

import atexit
import logging
import os
import socket
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from deepagents import AsyncSubAgent

from coding_agent.config import Settings, settings

logger = logging.getLogger(__name__)


DEFAULT_ASYNC_SUBAGENTS: dict[str, dict[str, Any]] = {
    "researcher": {
        "description": "Research agent for information gathering and synthesis.",
        "system_prompt": (
            "You are a research specialist. Read code, inspect documentation, and gather facts "
            "before answering. Produce a structured result with concrete findings."
        ),
        "graph_id": "researcher",
        "transport": "http",
    },
    "coder": {
        "description": "Coding agent for code generation, implementation, and patching.",
        "system_prompt": (
            "You are a coding specialist. Implement the requested change directly, verify it, "
            "and return a concise summary of the result."
        ),
        "graph_id": "coder",
        "transport": "http",
    },
    "reviewer": {
        "description": "Review agent for correctness, regressions, and missing tests.",
        "system_prompt": (
            "You are a code review specialist. Focus on bugs, behavior regressions, and missing "
            "coverage. Be concrete and prioritize the highest-risk findings first."
        ),
        "graph_id": "reviewer",
        "transport": "http",
    },
    "debugger": {
        "description": "Debugging agent for reproduction, diagnosis, and targeted fixes.",
        "system_prompt": (
            "You are a debugging specialist. Reproduce the issue, isolate the root cause, and make "
            "or recommend the smallest correct fix."
        ),
        "graph_id": "debugger",
        "transport": "http",
    },
}


def load_async_subagents(config_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load optional async subagent overrides from `config.toml`.

    Expected format:

    ```toml
    [async_subagents.researcher]
    description = "Research agent"
    graph_id = "researcher"
    system_prompt = "..."
    transport = "http"
    url = "http://127.0.0.1:30240"
    host = "127.0.0.1"
    port = 30240
    model = "openrouter:qwen/qwen3.5-35b-a3b"
    ```
    """
    if config_path is None:
        config_path = Path.home() / ".deepagents" / "config.toml"

    if not config_path.exists():
        return {}

    try:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, PermissionError, tomllib.TOMLDecodeError) as exc:
        logger.warning("Could not read async subagent config from %s: %s", config_path, exc)
        return {}

    section = data.get("async_subagents")
    if not isinstance(section, dict):
        return {}

    loaded: dict[str, dict[str, Any]] = {}
    for name, raw_spec in section.items():
        if not isinstance(raw_spec, dict):
            logger.warning("Skipping async subagent %r: expected table", name)
            continue
        description = str(raw_spec.get("description", "")).strip()
        if not description:
            logger.warning("Skipping async subagent %r: missing non-empty description", name)
            continue
        loaded[name] = {
            "description": description,
            "system_prompt": str(raw_spec.get("system_prompt", "")).strip(),
            "graph_id": str(raw_spec.get("graph_id", name)).strip() or name,
            "transport": str(raw_spec.get("transport", "http")).strip().lower() or "http",
            "url": str(raw_spec.get("url", "")).strip() or None,
            "host": str(raw_spec.get("host", "")).strip() or None,
            "port": int(raw_spec["port"]) if raw_spec.get("port") is not None else None,
            "model": str(raw_spec.get("model", "")).strip() or None,
            "headers": dict(raw_spec.get("headers", {})) if isinstance(raw_spec.get("headers"), dict) else {},
        }
    return loaded


@dataclass
class LocalAsyncSubagentProcess:
    """Runtime metadata for one async subagent endpoint."""

    name: str
    description: str
    system_prompt: str
    graph_id: str
    transport: str
    host: str
    port: int
    root_dir: Path
    model: str
    headers: dict[str, str] = field(default_factory=dict)
    url_override: str | None = None
    process: subprocess.Popen[str] | None = None
    external: bool = False
    started_at: float | None = None
    last_error: str | None = None

    @property
    def url(self) -> str | None:
        if self.transport == "asgi":
            return None
        if self.url_override:
            return self.url_override
        return f"http://{self.host}:{self.port}"

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None

    @property
    def is_running(self) -> bool:
        return self.external or (self.process is not None and self.process.poll() is None)

    def status(self) -> str:
        if self.transport == "asgi":
            return "inprocess"
        if self.external:
            return "running"
        if self.process is None:
            return "stopped"
        if self.process.poll() is None:
            return "running"
        return "exited"


class LocalAsyncSubagentManager:
    """Create DeepAgents AsyncSubAgent specs and manage local HTTP runtimes."""

    def __init__(
        self,
        cfg: Settings | None = None,
        *,
        root_dir: Path | None = None,
        subagents: dict[str, dict[str, Any]] | None = None,
        topology: str | None = None,
    ) -> None:
        self.cfg = cfg or settings
        self.root_dir = (root_dir or Path.cwd()).resolve()
        self.topology = (topology or self.cfg.deployment_topology or "single").strip().lower()
        loaded = load_async_subagents()
        self._subagents = self._merge_subagents(DEFAULT_ASYNC_SUBAGENTS, loaded, subagents or {})
        self._processes: dict[str, LocalAsyncSubagentProcess] = {}
        self._shutdown_registered = False

    @staticmethod
    def _merge_subagents(*sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for source in sources:
            for name, meta in source.items():
                base = dict(merged.get(name, {}))
                base.update(meta)
                base.setdefault("graph_id", name)
                base.setdefault("transport", "http")
                base.setdefault("headers", {})
                merged[name] = base
        return merged

    def _register_shutdown(self) -> None:
        if not self._shutdown_registered:
            atexit.register(self.shutdown_all)
            self._shutdown_registered = True

    def _port_is_listening(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            return sock.connect_ex((host, port)) == 0

    def _runtime_from_meta(self, name: str, idx: int, meta: dict[str, Any]) -> LocalAsyncSubagentProcess:
        url_override = str(meta.get("url") or "").strip() or None
        host = str(meta.get("host") or self.cfg.async_subagent_host)
        port = int(meta.get("port") or (self.cfg.async_subagent_base_port + idx))
        transport = str(meta.get("transport", "http")).strip().lower() or "http"
        if self.topology == "single":
            transport = "asgi"
            url_override = None
        elif self.topology == "split":
            transport = "http"
        if url_override:
            parsed = urlparse(url_override)
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port:
                port = parsed.port

        return LocalAsyncSubagentProcess(
            name=name,
            description=str(meta.get("description", "")).strip(),
            system_prompt=str(meta.get("system_prompt", "")).strip(),
            graph_id=str(meta.get("graph_id", name)).strip() or name,
            transport=transport,
            host=host,
            port=port,
            root_dir=self.root_dir,
            model=str(meta.get("model") or self.cfg.primary_model_string),
            headers=dict(meta.get("headers") or {}),
            url_override=url_override,
            external=bool(url_override),
        )

    def _ensure_spec(self, name: str) -> LocalAsyncSubagentProcess:
        if name not in self._subagents:
            raise KeyError(f"Unknown async subagent type: {name}")
        if name not in self._processes:
            idx = list(self._subagents.keys()).index(name)
            self._processes[name] = self._runtime_from_meta(name, idx, self._subagents[name])
        return self._processes[name]

    def _healthcheck(self, spec: LocalAsyncSubagentProcess) -> bool:
        if spec.transport == "asgi":
            return True
        if not spec.url:
            return False
        try:
            response = httpx.get(f"{spec.url}/ok", timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False

    def _spawn_process(self, spec: LocalAsyncSubagentProcess) -> None:
        if spec.transport == "asgi" or spec.external:
            return

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        cmd = [
            sys.executable,
            "-m",
            "coding_agent.async_subagent_server",
            "--agent-type",
            spec.name,
            "--host",
            spec.host,
            "--port",
            str(spec.port),
            "--root-dir",
            str(spec.root_dir),
            "--model",
            spec.model,
            "--system-prompt",
            spec.system_prompt,
            "--graph-id",
            spec.graph_id,
        ]

        logger.info("Starting local async subagent %s on %s", spec.name, spec.url)
        spec.process = subprocess.Popen(
            cmd,
            cwd=str(self.root_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        spec.started_at = time.time()
        spec.last_error = None
        self._register_shutdown()

    def _wait_until_healthy(self, spec: LocalAsyncSubagentProcess) -> None:
        if spec.transport == "asgi":
            return
        deadline = time.time() + 30.0
        while time.time() < deadline:
            if spec.process is not None and spec.process.poll() is not None:
                spec.last_error = f"process exited with code {spec.process.returncode}"
                raise RuntimeError(
                    f"Async subagent '{spec.name}' failed to start: {spec.last_error}"
                )
            if self._healthcheck(spec):
                return
            time.sleep(0.2)

        spec.last_error = "health check timed out"
        raise TimeoutError(
            f"Async subagent '{spec.name}' did not become healthy on {spec.url}"
        )

    def ensure_started(self, name: str) -> LocalAsyncSubagentProcess:
        spec = self._ensure_spec(name)
        if spec.transport == "asgi":
            return spec
        if spec.is_running and self._healthcheck(spec):
            return spec
        if spec.external:
            if not self._healthcheck(spec):
                raise RuntimeError(f"Configured async subagent '{name}' is unreachable at {spec.url}")
            spec.started_at = time.time()
            spec.last_error = None
            return spec
        if self._port_is_listening(spec.host, spec.port) and self._healthcheck(spec):
            spec.external = True
            spec.started_at = time.time()
            spec.last_error = None
            return spec
        self._spawn_process(spec)
        self._wait_until_healthy(spec)
        return spec

    def ensure_all_started(self) -> list[LocalAsyncSubagentProcess]:
        specs = [self._ensure_spec(name) for name in self._subagents]
        for spec in specs:
            self.ensure_started(spec.name)
        return specs

    def shutdown_all(self) -> None:
        for spec in self._processes.values():
            proc = spec.process
            if spec.external or proc is None or proc.poll() is not None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            finally:
                spec.process = None

    def build_async_subagents(self) -> list[AsyncSubAgent]:
        """Return the actual DeepAgents AsyncSubAgent specs."""
        specs: list[AsyncSubAgent] = []
        for name in self._subagents:
            runtime = self._ensure_spec(name)
            agent = AsyncSubAgent(
                name=runtime.name,
                description=runtime.description,
                graph_id=runtime.graph_id,
            )
            if runtime.url:
                agent["url"] = runtime.url
            if runtime.headers:
                agent["headers"] = runtime.headers
            specs.append(agent)
        return specs

    def topology_summary(self) -> dict[str, Any]:
        return {
            "topology": self.topology,
            "num_subagents": len(self._subagents),
            "asgi_subagents": sum(1 for name in self._subagents if self._ensure_spec(name).transport == "asgi"),
            "http_subagents": sum(1 for name in self._subagents if self._ensure_spec(name).transport == "http"),
        }

    def get_async_subagent_specs(self) -> list[AsyncSubAgent]:
        """Backward-compatible alias for the DeepAgents spec list."""
        return self.build_async_subagents()

    def get_all_tasks(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in self._subagents:
            proc = self._ensure_spec(name)
            rows.append(
                {
                    "id": proc.name,
                    "agent_type": proc.name,
                    "graph_id": proc.graph_id,
                    "task_description": proc.description,
                    "status": proc.status(),
                    "pid": proc.pid,
                    "url": proc.url,
                    "transport": proc.transport,
                    "host": proc.host,
                    "port": proc.port,
                    "started_at": proc.started_at,
                    "completed_at": None,
                    "result": None,
                    "error": proc.last_error,
                }
            )
        return rows
