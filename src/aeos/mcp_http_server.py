"""v31 The Consulate: AEOS served over HTTP — read-only, loopback by default.

The stdio server (v24) serves pipes; this serves the wire. One law,
unchanged: the tool set is exactly the READERS (audit, check,
recall) — no verb that writes is exposed, on any transport. The
default bind is 127.0.0.1: the consulate opens its door only when
the operator says so, and to whom. Bodies are bounded, malformed
input fails closed as JSON-RPC errors (never a crash), and the
handler is the SAME `handle_request` the stdio server uses — one
source of tool law, two transports.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .mcp_server import READONLY_TOOLS, UnknownMethod, handle_request

MAX_BODY_BYTES = 1_000_000


class ConsulateHandler(BaseHTTPRequestHandler):
    server_version = "aeos-consulate/1.0"

    def do_POST(self):
        if self.path not in ("/", "/mcp"):
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0:
            return self._json(400, {"error": "empty body"})
        if length > MAX_BODY_BYTES:
            return self._json(413, {"error": "body too large"})
        raw = self.rfile.read(length)
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return self._json(400, {"error": "malformed json"})
        if not isinstance(msg, dict) or "id" not in msg:
            return self._json(202, None)     # notification: accepted, silent
        try:
            result = handle_request(msg.get("method", ""),
                                    msg.get("params") or {})
            self._json(200, {"jsonrpc": "2.0", "id": msg["id"],
                             "result": result})
        except UnknownMethod as exc:
            self._json(200, {"jsonrpc": "2.0", "id": msg["id"],
                             "error": {"code": -32601,
                                       "message": f"no such method: {exc}"}})
        except Exception as exc:             # fail closed, never crash
            self._json(200, {"jsonrpc": "2.0", "id": msg["id"],
                             "error": {"code": -32602,
                                       "message": f"{type(exc).__name__}: "
                                                  f"{exc}"}})

    def _json(self, code, obj):
        payload = b"" if obj is None else json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def log_message(self, *args):
        pass


class Consulate:
    """A running HTTP consulate. Default bind 127.0.0.1 — the door
    opens on purpose (0.0.0.0 must be explicit)."""

    def __init__(self, bind: str = "127.0.0.1", port: int = 0):
        self.server = ThreadingHTTPServer((bind, port), ConsulateHandler)
        self.bind, self.port = self.server.server_address[:2]
        self._thread = threading.Thread(target=self.server.serve_forever,
                                        daemon=True)

    @property
    def url(self) -> str:
        return f"http://{self.bind}:{self.port}/mcp"

    def __enter__(self) -> "Consulate":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()
