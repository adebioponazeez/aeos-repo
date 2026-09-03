"""v30 MCP over HTTP: the streamable-HTTP transport, same client law.

The stdio client (v21) and the read-only server (v24) speak JSON-RPC
over a pipe; the ecosystem's other transport is HTTP — single POST
per request, response as JSON or as text/event-stream `data:` lines.
Same law on the wire: walls on every read, malformed bodies fail
closed as MCPError, and the endpoint is ALWAYS explicit — this
module is a room you enter on purpose, never ambient network.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .mcp_client import MCPError, MCPResult, MCPTool

PROTOCOL_VERSION = "2025-06-18"


class MCPHTTPClient:
    def __init__(self, endpoint: str, timeout_s: float = 10.0):
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self._id = 0

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            self.endpoint, data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                ctype = r.headers.get("Content-Type", "")
                body = r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise MCPError(f"http {exc.code}: {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MCPError(f"transport failed: {exc}") from exc

        obj = self._parse(body, ctype)
        if not isinstance(obj, dict):
            raise MCPError("unparseable response body")
        if "error" in obj:
            raise MCPError(f"{payload.get('method')}: "
                           f"{obj['error'].get('message')}")
        return obj.get("result") or {}

    @staticmethod
    def _parse(body: str, ctype: str) -> dict | None:
        if "text/event-stream" in ctype:
            for line in body.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    try:
                        return json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def request(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        return self._post({"jsonrpc": "2.0", "id": self._id,
                           "method": method, "params": params or {}})

    def initialize(self) -> dict:
        info = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "aeos-http", "version": "30.0"}})
        self.request("notifications/initialized")   # fire-and-forget POST
        return info

    def tools(self) -> list:
        res = self.request("tools/list")
        return [MCPTool(name=str(t.get("name", "")),
                        description=str(t.get("description", "")),
                        input_schema=t.get("inputSchema") or {})
                for t in res.get("tools", [])]

    def call(self, name: str, arguments: dict | None = None) -> MCPResult:
        res = self.request("tools/call", {"name": name,
                                          "arguments": arguments or {}})
        texts = [b.get("text", "") for b in res.get("content", [])
                 if isinstance(b, dict) and b.get("type") == "text"]
        return MCPResult(ok=not res.get("isError", False),
                         text="\n".join(texts),
                         error="tool reported error" if res.get("isError") else "")
