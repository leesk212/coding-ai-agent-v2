"""Local process manager for DeepAgents async subagents."""

from __future__ import annotations

import atexit
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from coding_agent.config import Settings, settings

logger = logging.getLogger(__name__)


DEFAULT_ASYNC_SUBAGENTS: dict[str, dict[str, str]] = {
    "researcher": {
        "description": "Investigates a topic or codebase and returns a structured research summary.",
        "system_prompt": (
            "You are a research specialist. Read code, inspect documentation, and gather facts "
            "before answering. Produce a structured result with concrete findings."
        ),
    },
    "code_writer": {
        "description": "Implements code changes and returns the patch-oriented outcome summary.",
        "system_prompt": (
            "You are a code writing specialist. Implement the requested change directly, verify it, "
            "and return a concise summary of the result."
        ),
    },
    "reviewer": {
        "description": "Reviews code for correctness, regressions, and missing tests.",
        "system_prompt": (
            "You are a code review specialist. Focus on bugs, behavior regressions, and missing "
            "coverage. Be concrete and prioritize the highest-risk findings first."
        ),
    },
    "debugger": {
        "description": "Performs root-cause analysis and proposes or applies targeted fixes.",
        "system_prompt": (
            "You are a debugging specialist. Reproduce the issue, isolate the root cause, and make "
            "or recommend the smallest correct fix."
        ),
    },
}


@dataclass
class LocalAsyncSubagentProcess:
    name: str
    description: str
    system_prompt: str
    host: str
    port: int
    root_dir: Path
    model: str
    process: subprocess.Popen[str] | None = None
    external: bool = False
    started_at: float | None = None
    last_error: str | None = None
    graph_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.graph_id = self.name

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None

    @property
    def is_running(self) -> bool:
        return self.external or (self.process is not None and self.process.poll() is None)

    def status(self) -> str:
        if self.external:
            return "running"
        if self.process is None:
            return "stopped"
        if self.process.poll() is None:
            return "running"
        return "exited"


class LocalAsyncSubagentManager:
    """Starts and monitors one local process per async subagent type."""

    def __init__(
        self,
        cfg: Settings | None = None,
        *,
        root_dir: Path | None = None,
        subagents: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.cfg = cfg or settings
        self.root_dir = (root_dir or Path.cwd()).resolve()
        self._subagents = subagents or DEFAULT_ASYNC_SUBAGENTS
        self._processes: dict[str, LocalAsyncSubagentProcess] = {}
        self._shutdown_registered = False

    def _register_shutdown(self) -> None:
        if not self._shutdown_registered:
            atexit.register(self.shutdown_all)
            self._shutdown_registered = True

    def _port_is_listening(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            return sock.connect_ex((host, port)) == 0

    def _ensure_spec(self, name: str) -> LocalAsyncSubagentProcess:
        if name not in self._subagents:
            raise KeyError(f"Unknown async subagent type: {name}")
        if name not in self._processes:
            idx = list(self._subagents.keys()).index(name)
            meta = self._subagents[name]
            self._processes[name] = LocalAsyncSubagentProcess(
                name=name,
                description=meta["description"],
                system_prompt=meta["system_prompt"],
                host=self.cfg.async_subagent_host,
                port=self.cfg.async_subagent_base_port + idx,
                root_dir=self.root_dir,
                model=self.cfg.primary_model_string,
            )
        return self._processes[name]

    def _launch(self, spec: LocalAsyncSubagentProcess) -> None:
        if spec.is_running and self._healthcheck(spec):
            return

        if self._port_is_listening(spec.host, spec.port) and self._healthcheck(spec):
            spec.process = None
            spec.external = True
            spec.started_at = time.time()
            spec.last_error = None
            return

        self._spawn_process(spec)
        self._wait_until_healthy(spec)

    def _spawn_process(self, spec: LocalAsyncSubagentProcess) -> None:
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
        ]

        logger.info("Starting async subagent process %s on %s", spec.name, spec.url)
        spec.process = subprocess.Popen(
            cmd,
            cwd=str(self.root_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        spec.external = False
        spec.started_at = time.time()
        spec.last_error = None
        self._register_shutdown()

    def _wait_until_healthy(self, spec: LocalAsyncSubagentProcess) -> None:
        deadline = time.time() + 30.0
        while time.time() < deadline:
            if spec.process.poll() is not None:
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

    def _healthcheck(self, spec: LocalAsyncSubagentProcess) -> bool:
        try:
            response = httpx.get(f"{spec.url}/ok", timeout=1.0)
            return response.status_code == 200
        except Exception:
            return False

    def ensure_started(self, name: str) -> LocalAsyncSubagentProcess:
        spec = self._ensure_spec(name)
        self._launch(spec)
        return spec

    def ensure_all_started(self) -> list[LocalAsyncSubagentProcess]:
        specs = [self._ensure_spec(name) for name in self._subagents]
        for spec in specs:
            if spec.is_running and self._healthcheck(spec):
                continue
            if self._port_is_listening(spec.host, spec.port) and self._healthcheck(spec):
                spec.process = None
                spec.external = True
                spec.started_at = time.time()
                spec.last_error = None
                continue
            self._spawn_process(spec)
        for spec in specs:
            if not self._healthcheck(spec):
                self._wait_until_healthy(spec)
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

    def get_async_subagent_specs(self) -> list[dict[str, Any]]:
        specs = []
        for name in self._subagents:
            proc = self._ensure_spec(name)
            specs.append(
                {
                    "name": proc.name,
                    "description": proc.description,
                    "graph_id": proc.graph_id,
                    # We intentionally use explicit localhost URLs here rather than
                    # ASGI transport because the product requirement is one OS process
                    # per subagent.
                    "url": proc.url,
                    "headers": {"x-auth-scheme": "custom"},
                }
            )
        return specs

    def get_all_tasks(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in self._subagents:
            proc = self._ensure_spec(name)
            rows.append(
                {
                    "id": proc.name,
                    "agent_type": proc.name,
                    "task_description": proc.description,
                    "status": proc.status(),
                    "pid": proc.pid,
                    "url": proc.url,
                    "started_at": proc.started_at,
                    "completed_at": None,
                    "result": None,
                    "error": proc.last_error,
                }
            )
        return rows
