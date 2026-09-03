"""v30 tests: the embassy — MCP over HTTP + OTLP push, loopback-proven."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from aeos.mcp_client import MCPError
from aeos.mcp_http import MCPHTTPClient
from aeos.otlp import push_file, push_spans


def capture_factory(statuses=()):
    seq = list(statuses)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            status = seq.pop(0) if seq else 200
            if status == 200:
                self.server.captured.append(body)   # BEFORE responding:
            self.send_response(status)              # no read-after-return race
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass
    return H


class Loopback:
    """A disposable local server — the embassy's test range."""

    def __init__(self, handler):
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.server.captured = []
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.requests = []

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def mcp_handler_factory(mode="json", delay=0.0):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            if delay:
                import time as _t
                _t.sleep(delay)
            length = int(self.headers.get("Content-Length", 0))
            msg = json.loads(self.rfile.read(length))
            if "id" not in msg:
                self.send_response(202)
                self.end_headers()
                return
            if msg["method"] == "initialize":
                result = {"protocolVersion": "2025-06-18",
                          "serverInfo": {"name": "embassy-test", "version": "1"}}
            elif msg["method"] == "tools/list":
                result = {"tools": [{"name": "echo", "description": "d"}]}
            elif msg["method"] == "tools/call":
                text = "echo: " + (msg["params"].get("arguments") or {}
                                   ).get("text", "")
                result = {"content": [{"type": "text", "text": text}],
                          "isError": False}
            else:
                result = {}
            body = json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                               "result": result})
            if mode == "sse":
                body = f"data: {body}\n\n"
                ctype = "text/event-stream"
            else:
                ctype = "application/json"
            payload = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass
    return H


class TestMCPHTTP:
    def test_json_transport_handshake_tools_call(self):
        with Loopback(mcp_handler_factory("json")) as lb:
            c = MCPHTTPClient(lb.url, timeout_s=5)
            info = c.initialize()
            assert info["serverInfo"]["name"] == "embassy-test"
            tools = c.tools()
            assert [t.name for t in tools] == ["echo"]
            res = c.call("echo", {"text": "over the wire"})
            assert res.ok and res.text == "echo: over the wire"

    def test_sse_transport_parsed(self):
        with Loopback(mcp_handler_factory("sse")) as lb:
            c = MCPHTTPClient(lb.url, timeout_s=5)
            assert c.initialize()["serverInfo"]["name"] == "embassy-test"

    def test_the_wall_applies_on_http(self):
        with Loopback(mcp_handler_factory(delay=2.0)) as lb:
            c = MCPHTTPClient(lb.url, timeout_s=0.4)
            with pytest.raises(MCPError, match="transport|timeout"):
                c.initialize()

    def test_dead_endpoint_fails_closed(self):
        c = MCPHTTPClient("http://127.0.0.1:9/mcp", timeout_s=1.0)
        with pytest.raises(MCPError):
            c.initialize()


class TestOTLPPush:
    def test_push_receipt_ok(self):
        with Loopback(capture_factory()) as lb:
            r = push_spans(lb.url, [{"name": "NODE_DONE"}], retries=0)
            assert r["ok"] and r["pushed"] == 1 and r["attempts"] == 1
            sent = json.loads(lb.server.captured[0])
            spans = sent["resourceSpans"][0]["scopeSpans"][0]["spans"]
            assert spans[0]["name"] == "NODE_DONE"

    def test_retry_then_success(self):
        with Loopback(capture_factory([503, 200])) as lb:
            r = push_spans(lb.url, [{"name": "x"}], retries=2,
                           backoff_s=0.05)
            assert r["ok"] and r["attempts"] == 2

    def test_hostile_wire_is_a_receipt_not_an_exception(self):
        with Loopback(capture_factory([503, 503, 503])) as lb:
            r = push_spans(lb.url, [{"name": "x"}], retries=2,
                           backoff_s=0.05)
            assert r["ok"] is False and r["attempts"] == 3
            assert "safe on disk" in r["note"]

    def test_client_error_is_not_retried(self):
        with Loopback(capture_factory([404])) as lb:
            r = push_spans(lb.url, [{"name": "x"}], retries=3,
                           backoff_s=0.05)
            assert r["ok"] is False and r["attempts"] == 1

    def test_nothing_to_push_is_ok(self):
        r = push_spans("http://127.0.0.1:9/x", [])
        assert r["ok"] and r["pushed"] == 0

    def test_push_file_roundtrip(self, tmp_path):
        f = tmp_path / "spans.jsonl"
        f.write_text(json.dumps({"name": "TICK"}) + "\n", encoding="utf-8")
        with Loopback(capture_factory()) as lb:
            r = push_file(lb.url, f)
            assert r["ok"] and r["pushed"] == 1


class TestCLI:
    def test_otel_push_flag(self, tmp_path, capsys):
        from aeos.cli import main
        from aeos.fleet import EventBus
        ws = tmp_path / "ws"
        bus = EventBus(ws / ".aeos" / "events.jsonl")
        bus.publish("TICK", "a")
        main(["fleet", "--workspace", str(ws)])
        with Loopback(capture_factory()) as lb:
            rc = main(["otel", "--workspace", str(ws), "--push", lb.url])
        out = capsys.readouterr().out
        assert rc == 0 and "PUSH" in out
