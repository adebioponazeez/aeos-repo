"""v21 MCP: Model Context Protocol client — stateless core, stdlib only.

JSON-RPC 2.0 over the subprocess's stdio (newline-delimited — the MCP
stdio transport). The law travels with the protocol: imported tools
are UNTRUSTED until evidence promotes them; a wall kills the server;
a malformed line ends the session, never the harness.
"""
from __future__ import annotations

import json
import select
import subprocess
import sys
from dataclasses import dataclass, field

PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    """Protocol failure or timeout — fail closed."""


@dataclass
class MCPTool:
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPResult:
    ok: bool
    text: str = ""
    error: str = ""


class MCPClient:
    def __init__(self, argv: list, timeout_s: float = 10.0):
        self.argv = list(argv)
        self.timeout_s = timeout_s
        self.proc: subprocess.Popen | None = None
        self._id = 0

    # ------------------------------------------------------------ transport
    def start(self) -> None:
        self.proc = subprocess.Popen(
            self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True)

    def close(self) -> None:
        if self.proc is None:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        finally:
            for pipe in (self.proc.stdin, self.proc.stdout,
                         self.proc.stderr):
                try:
                    if pipe is not None:
                        pipe.close()
                except (BrokenPipeError, OSError):
                    pass
            self.proc = None

    def _write(self, obj: dict) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise MCPError("session not started")
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as exc:
            self.close()
            raise MCPError(f"server gone mid-session: {exc}") from exc

    def _read_line(self) -> str:
        assert self.proc is not None and self.proc.stdout is not None
        ready, _, _ = select.select([self.proc.stdout], [], [],
                                    self.timeout_s)
        if not ready:
            self.close()
            raise MCPError(f"timeout after {self.timeout_s}s — server killed")
        line = self.proc.stdout.readline()
        if not line:
            raise MCPError("server closed the session")
        return line

    def request(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        rid = self._id
        self._write({"jsonrpc": "2.0", "id": rid, "method": method,
                     "params": params or {}})
        while True:
            try:
                msg = json.loads(self._read_line())
            except json.JSONDecodeError as exc:
                raise MCPError(f"malformed line from server: {exc}")
            if msg.get("id") != rid:
                continue                       # stale/notify — keep reading
            if "error" in msg:
                raise MCPError(f"{method}: {msg['error'].get('message')}")
            return msg.get("result") or {}

    def notify(self, method: str, params: dict | None = None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    # ------------------------------------------------------------ protocol
    def initialize(self) -> dict:
        info = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "aeos", "version": "22.0"}})
        self.notify("notifications/initialized")
        return info

    def tools(self) -> list:
        res = self.request("tools/list")
        out = []
        for t in res.get("tools", []):
            out.append(MCPTool(
                name=str(t.get("name", "")),
                description=str(t.get("description", "")),
                input_schema=t.get("inputSchema") or {}))
        return out

    def call(self, name: str, arguments: dict | None = None) -> MCPResult:
        res = self.request("tools/call", {"name": name,
                                          "arguments": arguments or {}})
        texts = [b.get("text", "") for b in res.get("content", [])
                 if isinstance(b, dict) and b.get("type") == "text"]
        return MCPResult(ok=not res.get("isError", False),
                         text="\n".join(texts),
                         error="tool reported error" if res.get("isError") else "")


def import_tools(tools: list) -> dict:
    """Federation law: an imported tool is UNTRUSTED material, no
    matter who served it. Promotion is evidence, not reputation."""
    return {t.name: {"trust": "UNTRUSTED", "tool": t} for t in tools}
