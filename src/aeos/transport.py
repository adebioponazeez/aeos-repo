"""v8.0 — Distance: real transports, remote workers, process sandboxes.

The kernel kept everything in one process on purpose (auditable); the
platform now earns the right to spread out — over the wire and across
process boundaries — without dropping a single guarantee:

  HTTPModelTransport  adapters speak HTTP with the same error taxonomy
  MCPHTTPClient       tool calls over the wire, MCP-shaped, untrusted
  WorkerServer/RemoteWorker  A2A-style delegation: a task, an envelope
  run_isolated()      sandbox validation in a KILLED-ABLE subprocess
                      with wall-clock timeout and resource limits

ADR-017. Everything here is testable on localhost with deterministic
servers — the seam discipline does not pause for geography.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import AgentSpec, Envelope, TaskSpec
from .models import ModelCall, ModelReply
from .tools import ToolResult


# ----------------------------------------------------------- transports

class HTTPModelTransport:
    """POST ModelCall JSON -> ModelReply JSON. Exceptions raised here
    classify cleanly through ProviderAdapter's taxonomy."""

    def __init__(self, endpoint: str, timeout_s: float = 10.0) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s

    def post(self, call: ModelCall, model: str) -> ModelReply:
        payload = json.dumps({"system": call.system, "prompt": call.prompt,
                              "agent": call.agent_name, "model": model}).encode()
        req = Request(self.endpoint, data=payload,
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return ModelReply(text=data["text"], model=data.get("model", model),
                                  tokens_in=data.get("tokens_in", 0),
                                  tokens_out=data.get("tokens_out", 0))
        except HTTPError as exc:
            if exc.code in (429, 503):
                raise ConnectionError(f"{exc.code} upstream") from exc
            raise ValueError(f"http {exc.code}") from exc
        except URLError as exc:
            if "timed out" in str(exc).lower():
                raise TimeoutError(f"timeout after {self.timeout_s}s") from exc
            raise ConnectionError(str(exc)) from exc


def call_remote_tool(endpoint: str, tool: str,
                     params: dict[str, Any] | None = None,
                     *, timeout_s: float = 10.0) -> ToolResult:
    """MCP-shaped tool call over HTTP. The result is untrusted — still
    a claim, never an instruction, whatever the server says."""
    payload = json.dumps({"tool": tool, "params": params or {}}).encode()
    req = Request(endpoint, data=payload,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # wire trouble is a structured error, never a crash
        return ToolResult(name=tool, error=f"transport: {exc}", is_error=True)
    if data.get("isError"):
        return ToolResult(name=tool,
                          error=(data.get("error") or {}).get("message", "error"),
                          is_error=True)
    return ToolResult(name=tool, result=data.get("result"))


# ------------------------------------------------------ remote workers

Handler = Callable[[dict[str, Any]], dict[str, Any]]


class WorkerServer:
    """A2A-style worker: POST /task {agent, description, task} ->
    envelope dict. The handler registry is injectable; the server adds
    exactly one rule of its own: broken handlers become error envelopes,
    never 500s with stack traces."""

    def __init__(self, handlers: dict[str, Handler]) -> None:
        self.handlers = handlers
        outer = self

        class _H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_GET(self):
                body = json.dumps({"status": "ok",
                                   "agents": sorted(outer.handlers)}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                if self.path != "/task":
                    self.send_error(404, "unknown endpoint")
                    return
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                agent = req.get("agent", "")
                try:
                    handler = outer.handlers[agent]
                    envelope = Envelope.from_dict(handler(req))
                    reply = {"ok": True, "envelope": envelope.to_dict()}
                except Exception as exc:
                    reply = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                body = json.dumps(reply).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _H)
        self.port = self._server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"

    def serve_forever_in_thread(self) -> "WorkerServer":
        import threading
        t = threading.Thread(target=self._server.serve_forever, daemon=True)
        t.start()
        return self

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@dataclass
class RemoteWorker:
    """Client side: an agent that lives somewhere else. `as_handler()`
    wraps delegation into an orchestrator-ready handler — to the graph,
    a remote colleague is indistinguishable from a local one."""
    url: str
    agent: str
    timeout_s: float = 10.0

    def delegate(self, description: str) -> Envelope:
        payload = json.dumps({"agent": self.agent,
                              "description": description}).encode()
        req = Request(self.url.rstrip("/") + "/task", data=payload,
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ConnectionError(f"worker unreachable: {exc}") from exc
        if not data.get("ok"):
            raise RuntimeError(f"worker error: {data.get('error')}")
        return Envelope.from_dict(data["envelope"])

    def as_handler(self):
        def handler(task: TaskSpec, orch) -> Envelope:
            return self.delegate(task.description)
        return handler


# ------------------------------------------------- process sandboxing

def smoke_validate(design: AgentSpec, workspace: Path) -> dict:
    """The factory's smoke test, in callable form (shared by the
    in-process and the process-isolated paths)."""
    from .evaluation import Evaluator
    from .governor import Governor
    from .harness import Harness
    from .models import EchoModel
    from .observability import EventLog
    from .orchestrator import Orchestrator

    problems = design.validate()
    if problems:
        return {"verdict": "FAIL", "why": problems}

    harness = Harness(workspace)

    def smoke(task: TaskSpec, orch) -> Envelope:
        base = design.writes[0] if design.writes else "out"
        rel = f"{base}/smoke.json"
        harness.write(rel, json.dumps({"smoke": True, "agent": design.name}))
        env = Envelope(agent=design.name, objective=task.description,
                       claims=["smoke artifact written"], artifacts=[rel])
        env.add_evidence("artifact_written", rel)
        return env

    orch = Orchestrator(agents={design.name: design},
                        handlers={design.name: smoke}, model=EchoModel(),
                        governor=Governor(), evaluator=Evaluator(),
                        log=EventLog(), workspace=harness.workspace,
                        max_workers=1)
    report = orch.run(f"sandbox:{design.name}", [TaskSpec(
        name="smoke", description=f"Smoke-test the {design.name} contract",
        agent=design.name)], repair=False)
    return {"verdict": "PASS" if report.accepted else "FAIL",
            "summary": report.summary_line()}


def run_isolated(design: AgentSpec, workspace: Path,
                 *, timeout_s: float = 10.0) -> dict:
    """Run smoke_validate in a SUBPROCESS: wall-clock timeout, memory
    and CPU limits where the OS provides them, hard kill on overrun.
    A sandbox that cannot be killed is not a sandbox."""
    workspace.mkdir(parents=True, exist_ok=True)
    inp = workspace / ".sandbox-in.json"
    out = workspace / ".sandbox-out.json"
    out.unlink(missing_ok=True)

    from dataclasses import asdict
    d = asdict(design)
    d["action_classes"] = [a.value for a in design.action_classes]
    inp.write_text(json.dumps({"spec": d}), encoding="utf-8")

    def _limits():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
            resource.setrlimit(resource.RLIMIT_CPU, (max(1, int(timeout_s)),) * 2)
        except Exception:
            pass  # non-POSIX: the wall-clock kill still applies

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "aeos.sandbox_runner", str(inp), str(out)],
            cwd=str(workspace), timeout=timeout_s, capture_output=True,
            text=True, preexec_fn=_limits)
    except subprocess.TimeoutExpired:
        return {"verdict": "FAIL",
                "why": f"sandbox exceeded its {timeout_s}s wall clock and "
                       "was killed — a sandbox that cannot be killed is "
                       "not a sandbox"}

    if proc.returncode != 0:
        if out.exists():      # the defensive child may have written a reason
            try:
                return json.loads(out.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"verdict": "FAIL",
                "why": f"sandbox process exited {proc.returncode}: "
                       f"{(proc.stderr or '').strip()[:200]}"}
    if not out.exists():
        return {"verdict": "FAIL", "why": "sandbox produced no verdict"}
    return json.loads(out.read_text(encoding="utf-8"))
