"""v24 MCP server mode: AEOS on the other side of the protocol.

v21 was the client; this is the symmetric server — same JSON-RPC
framing, stdlib only, runnable as `python -m aeos.mcp_server`. The
safety law: the server exposes verbs that READ, never verbs that
WRITE. A remote caller may audit, check, and recall — never mutate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .leverage import audit, render
from .recall import RecallIndex
from .standards import check_plan

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "aeos-server", "version": "1.0"}

AEOS_TOOLS = [
    {"name": "leverage_audit",
     "description": "Run the 12-point leverage audit on a workspace "
                    "(read-only). Returns the scored rubric.",
     "inputSchema": {"type": "object",
                     "properties": {"workspace": {"type": "string"}}}},
    {"name": "standards_check",
     "description": "Check a plan against a workspace's STANDARDS.md "
                    "(read-only). Returns gate verdict.",
     "inputSchema": {"type": "object",
                     "properties": {"plan_text": {"type": "string"},
                                    "workspace": {"type": "string"}}}},
    {"name": "recall",
     "description": "Layered FTS recall over a workspace's memory "
                    "(read-only). Returns layers and savings.",
     "inputSchema": {"type": "object",
                     "properties": {"query": {"type": "string"},
                                    "workspace": {"type": "string"}}}},
]

# the law, testable: everything exposed is a reader
READONLY_TOOLS = {"leverage_audit", "standards_check", "recall"}


class UnknownMethod(Exception):
    pass


def handle_request(method: str, params: dict) -> dict:
    if method == "initialize":
        return {"protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO}
    if method == "tools/list":
        return {"tools": AEOS_TOOLS}
    if method == "tools/call":
        name = str(params.get("name", ""))
        args = params.get("arguments") or {}
        if name == "leverage_audit":
            text = render(audit(Path(args.get("workspace", "."))))
        elif name == "standards_check":
            res = check_plan(args.get("plan_text", ""),
                             Path(args.get("workspace", ".")) / "STANDARDS.md")
            text = (f"standards gate: gated={res['gated']} "
                    f"cited={res['cited']} ok={res['ok']}")
        elif name == "recall":
            from .memory import MemoryStore
            ws = Path(args.get("workspace", "."))
            idx = RecallIndex(str(ws / ".aeos" / "recall.sqlite"),
                              MemoryStore(ws / ".aeos" / "memory.jsonl"))
            idx.build()
            rep = idx.recall(args.get("query", ""), budget=120)
            idx.close()
            text = (f"recall: paid {rep.recall_tokens} vs full-scan "
                    f"{rep.full_scan_tokens} — saved {rep.saving}")
        else:
            raise UnknownMethod(name)
        return {"content": [{"type": "text", "text": text}],
                "isError": False}
    raise UnknownMethod(method)


def serve(stdin=None, stdout=None) -> None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:
            continue                          # notification
        try:
            result = handle_request(msg.get("method", ""),
                                    msg.get("params") or {})
            resp = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
        except UnknownMethod as exc:
            resp = {"jsonrpc": "2.0", "id": msg["id"],
                    "error": {"code": -32601,
                              "message": f"no such method: {exc}"}}
        except Exception as exc:              # fail closed, never crash
            resp = {"jsonrpc": "2.0", "id": msg["id"],
                    "error": {"code": -32602,
                              "message": f"{type(exc).__name__}: {exc}"}}
        stdout.write(json.dumps(resp) + "\n")
        stdout.flush()


if __name__ == "__main__":
    serve()
