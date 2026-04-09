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
from coding_agent.state.store import DurableStateStore

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
    "frontend": {
        "description": "Frontend agent for web/mobile UI, UX flows, and client-side implementation.",
        "system_prompt": (
            "You are a frontend specialist. Focus on UI flows, component structure, responsive design, "
            "web/mobile interaction details, and client-side implementation. Be explicit about screens, "
            "state transitions, and user interaction behavior."
        ),
        "graph_id": "frontend",
        "transport": "http",
    },
    "backend": {
        "description": "Backend agent for APIs, domain logic, data model, persistence, and integrations.",
        "system_prompt": (
            "You are a backend specialist. Focus on data modeling, service boundaries, APIs, persistence, "
            "permissions, scheduling, and business logic. Be concrete about schemas, endpoints, and state transitions."
        ),
        "graph_id": "backend",
        "transport": "http",
    },
    "planner": {
        "description": "Planning agent for PRD decomposition, work breakdown, milestones, and execution sequencing.",
        "system_prompt": (
            "You are a planning specialist. Turn requirements into concrete PRD sections, atomic work items, "
            "milestones, acceptance criteria, dependencies, and execution order. Avoid vague wording."
        ),
        "graph_id": "planner",
        "transport": "http",
    },
    "architect": {
        "description": "Architecture agent for system design, module boundaries, technical decisions, and spec structure.",
        "system_prompt": (
            "You are a software architect. Define system boundaries, module responsibilities, interfaces, "
            "data flow, deployment shape, and technical tradeoffs in a spec-driven way."
        ),
        "graph_id": "architect",
        "transport": "http",
    },
    "mobile": {
        "description": "Mobile agent for app flows, cross-platform mobile UX, and mobile implementation concerns.",
        "system_prompt": (
            "You are a mobile specialist. Focus on mobile navigation, screens, responsive behavior, offline states, "
            "device constraints, and cross-platform implementation details."
        ),
        "graph_id": "mobile",
        "transport": "http",
    },
    "reviewer": {
        "description": "Review agent for correctness, regressions, and missing tests.",
        "system_prompt": (
            "You are a code review specialist. Focus on bugs, behavior regressions, and missing "
            "coverage. Be concrete and prioritize the highest-risk findings first. "
            "If the task is to review code produced in the same user turn, inspect the current "
            "working directory for the relevant file first and only ask for a path if no artifact exists."
        ),
        "graph_id": "reviewer",
        "transport": "http",
    },
    "remember": {
        "description": "Memory curation agent for selecting durable project artifacts worth storing in long-term memory.",
        "system_prompt": (
            "You are a memory curation specialist. Inspect the final project artifacts in the current working directory, "
            "identify up to 10 files that are most valuable for future reuse or recall, and explain briefly why each one "
            "should be remembered. Prefer PRD, specs, architecture decisions, important implementation files, API contracts, "
            "and tests that encode durable project knowledge."
        ),
        "graph_id": "remember",
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


def get_default_subagent_system_prompts() -> dict[str, str]:
    return {
        name: str(meta.get("system_prompt", "")).strip()
        for name, meta in DEFAULT_ASYNC_SUBAGENTS.items()
    }


def _read_async_subagent_section(config_path: Path | None = None) -> dict[str, Any]:
    """Read the raw `[async_subagents]` section from `config.toml`.

    This keeps config parsing separate from runtime enrichment so the code path
    can mirror the DeepAgents CLI reference more closely.
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
    return section if isinstance(section, dict) else {}


def load_async_subagent_specs(config_path: Path | None = None) -> list[AsyncSubAgent]:
    """Load DeepAgents-style `AsyncSubAgent` specs from `config.toml`.

    Expected format:

    ```toml
    [async_subagents.researcher]
    description = "Research agent"
    graph_id = "researcher"
    url = "http://127.0.0.1:30240"
    headers = { Authorization = "Bearer ..." }
    ```
    """
    section = _read_async_subagent_section(config_path)
    required = {"description", "graph_id"}
    specs: list[AsyncSubAgent] = []
    for name, raw_spec in section.items():
        if not isinstance(raw_spec, dict):
            logger.warning("Skipping async subagent %r: expected table", name)
            continue
        missing = required - raw_spec.keys()
        if missing:
            logger.warning("Skipping async subagent %r: missing fields %s", name, missing)
            continue
        description = str(raw_spec.get("description", "")).strip()
        graph_id = str(raw_spec.get("graph_id", "")).strip()
        if not description or not graph_id:
            logger.warning("Skipping async subagent %r: invalid description/graph_id", name)
            continue
        spec = AsyncSubAgent(
            name=name,
            description=description,
            graph_id=graph_id,
        )
        if "url" in raw_spec and isinstance(raw_spec.get("url"), str) and str(raw_spec["url"]).strip():
            spec["url"] = str(raw_spec["url"]).strip()
        if "headers" in raw_spec and isinstance(raw_spec.get("headers"), dict):
            spec["headers"] = dict(raw_spec["headers"])
        specs.append(spec)
    return specs


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
    section = _read_async_subagent_section(config_path)
    base_specs = {spec["name"]: spec for spec in load_async_subagent_specs(config_path)}
    loaded: dict[str, dict[str, Any]] = {}
    for name, raw_spec in section.items():
        if not isinstance(raw_spec, dict):
            continue
        base_spec = base_specs.get(name)
        if base_spec is None:
            continue
        loaded[name] = {
            "description": str(base_spec["description"]).strip(),
            "system_prompt": str(raw_spec.get("system_prompt", "")).strip(),
            "graph_id": str(base_spec["graph_id"]).strip() or name,
            "transport": str(raw_spec.get("transport", "http")).strip().lower() or "http",
            "url": str(base_spec.get("url", "")).strip() or None,
            "host": str(raw_spec.get("host", "")).strip() or None,
            "port": int(raw_spec["port"]) if raw_spec.get("port") is not None else None,
            "model": str(raw_spec.get("model", "")).strip() or None,
            "headers": dict(base_spec.get("headers", {})) if isinstance(base_spec.get("headers"), dict) else {},
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
        prompt_overrides = {
            name: {"system_prompt": prompt}
            for name, prompt in (self.cfg.subagent_system_prompt_overrides or {}).items()
            if str(prompt).strip()
        }
        self._subagents = self._merge_subagents(
            DEFAULT_ASYNC_SUBAGENTS,
            loaded,
            prompt_overrides,
            subagents or {},
        )
        self._state_store = DurableStateStore(self.cfg.state_dir / "agent_state.db")
        self._processes: dict[str, LocalAsyncSubagentProcess] = {}
        self._pending_lifecycle_ids: dict[str, list[str]] = {}
        self._events: list[dict[str, Any]] = []
        self._shutdown_registered = False

    @property
    def state_store(self) -> DurableStateStore:
        return self._state_store

    def _emit_event(self, event_type: str, spec: LocalAsyncSubagentProcess, **extra: Any) -> None:
        self._events.append(
            {
                "type": event_type,
                "name": spec.name,
                "graph_id": spec.graph_id,
                "transport": spec.transport,
                "host": spec.host,
                "port": spec.port,
                "url": spec.url,
                "pid": spec.pid,
                "time": time.time(),
                **extra,
            }
        )

    def begin_task(self, role: str, task_summary: str, parent_id: str = "main-agent") -> str:
        agent_id = self._state_store.create_subagent(
            role=role,
            task_summary=task_summary,
            parent_id=parent_id,
            metadata={"topology": self.topology},
        )
        self._state_store.update_subagent(
            agent_id,
            state="assigned",
            event_detail=task_summary,
        )
        self._pending_lifecycle_ids.setdefault(role, []).append(agent_id)
        return agent_id

    def _pop_pending_lifecycle_id(self, role: str) -> str | None:
        pending = self._pending_lifecycle_ids.get(role) or []
        return pending.pop(0) if pending else None

    def bind_task(self, task_id: str, *, role: str | None = None, run_id: str | None = None) -> str | None:
        row = self._state_store.find_subagent_by_task_id(task_id)
        if row:
            agent_id = str(row["agent_id"])
        else:
            if not role:
                return None
            agent_id = self._pop_pending_lifecycle_id(role)
            if not agent_id:
                return None
        self._state_store.update_subagent(
            agent_id,
            task_id=task_id,
            run_id=run_id,
            state="running",
            event_detail=f"task_id={task_id}",
        )
        return agent_id

    def update_task_state(
        self,
        *,
        task_id: str,
        state: str,
        detail: str = "",
        run_id: str | None = None,
    ) -> None:
        row = self._state_store.find_subagent_by_task_id(task_id)
        if not row:
            return
        self._state_store.update_subagent(
            str(row["agent_id"]),
            state=state,
            run_id=run_id,
            error=detail if state in {"failed", "blocked"} else None,
            event_detail=detail,
        )

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
        self._emit_event("spawned", spec)
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
            self._emit_event("reused", spec)
            return spec
        if spec.external:
            if not self._healthcheck(spec):
                raise RuntimeError(f"Configured async subagent '{name}' is unreachable at {spec.url}")
            spec.started_at = time.time()
            spec.last_error = None
            self._emit_event("attached", spec)
            return spec
        if self._port_is_listening(spec.host, spec.port) and self._healthcheck(spec):
            spec.external = True
            spec.started_at = time.time()
            spec.last_error = None
            self._emit_event("attached", spec)
            return spec
        self._spawn_process(spec)
        self._wait_until_healthy(spec)
        self._emit_event("healthy", spec)
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
                self._emit_event("stopping", spec)
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            finally:
                self._emit_event("stopped", spec, pid=spec.pid)
                spec.process = None

    def drain_events(self) -> list[dict[str, Any]]:
        events = list(self._events)
        self._events.clear()
        return events

    def shutdown_turn_subagents(self) -> None:
        for row in self.list_subagent_records():
            if row.get("state") in {"running", "assigned", "blocked", "completed", "failed", "cancelled"}:
                self._state_store.update_subagent(str(row["agent_id"]), state="destroyed", event_detail="turn cleanup")
        self.shutdown_all()

    def note_runtime_state(self, role: str, *, state: str, task_summary: str = "", error: str = "") -> None:
        pending = self._pending_lifecycle_ids.get(role) or []
        agent_id = pending[0] if pending else None
        if not agent_id:
            return
        self._state_store.update_subagent(
            agent_id,
            state=state,
            endpoint=f"127.0.0.1:{self._ensure_spec(role).port}",
            pid=self._ensure_spec(role).pid,
            model=self._ensure_spec(role).model,
            error=error or None,
            task_summary=task_summary or None,
            event_detail=error or task_summary,
        )

    def list_subagent_records(self, parent_id: str | None = None) -> list[dict[str, Any]]:
        return self._state_store.list_subagents(parent_id)

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

    def get_runtime_info(self, name: str) -> dict[str, Any]:
        spec = self._ensure_spec(name)
        return {
            "name": spec.name,
            "graph_id": spec.graph_id,
            "transport": spec.transport,
            "host": spec.host,
            "port": spec.port,
            "url": spec.url,
            "pid": spec.pid,
            "model": spec.model,
            "external": spec.external,
            "status": spec.status(),
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
