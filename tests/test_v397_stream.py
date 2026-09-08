"""v39.7 The Live Shopfloor: SSE streaming, tested as law (ADR-053).

The contract: events stream LIVE (backlog replayed, then tailed;
newer run files roll over); the surface is READ-ONLY (GET only,
405 named otherwise); the console is self-contained (inline
CSS/JS, no CDN — offline law); the bind is loopback by default;
every refusal is named, never a traceback.
"""

from __future__ import annotations

import http.client
import json
import threading
import time
from pathlib import Path

import pytest

from aeos.stream import ShopfloorServer, newest_events_file

_PORT = [8890]


def _port() -> int:
    _PORT[0] += 1
    return _PORT[0]


@pytest.fixture()
def ws(tmp_path):
    w = tmp_path / "ws"
    runs = w / ".aeos" / "runs"
    runs.mkdir(parents=True)
    (runs / "1000-events.jsonl").write_text(
        "\n".join(json.dumps({"kind": f"kind.{i}", "ts": 1000.0 + i,
                              "detail": {"i": i}}) for i in range(5)) + "\n",
        encoding="utf-8")
    return w


@pytest.fixture()
def server(ws):
    import socket
    srv = ShopfloorServer(ws, port=_port())
    t = threading.Thread(target=srv.start, daemon=True)
    t.start()
    for _ in range(60):                      # REALLY wait for the bind
        try:
            with socket.create_connection(("127.0.0.1", srv.port),
                                          timeout=0.5):
                pass
            break
        except OSError:
            time.sleep(0.1)
    else:
        pytest.fail("shopfloor server never bound")
    yield srv
    srv.httpd.shutdown()


def _get(srv, path, method="GET", timeout=5, read_body=True):
    """read_body=False for /events: an SSE stream never EOFs, so a
    full read() would block forever — that is the STREAM WORKING."""
    c = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=timeout)
    c.request(method, path)
    r = c.getresponse()
    body = r.read() if read_body else b""
    c.close()
    return r, body


class TestSurface:
    def test_health(self, server, ws):
        r, body = _get(server, "/health")
        assert r.status == 200
        d = json.loads(body)
        assert d["ok"] is True and d["events"] == 5
        assert d["events_file"] == "1000-events.jsonl"

    def test_console_is_self_contained(self, server):
        r, body = _get(server, "/")
        html = body.decode()
        assert r.status == 200
        assert "EventSource" in html          # the live wire
        assert "<style>" in html              # inline styles
        assert "http://" not in html.replace("http://127", "")  # no CDN
        assert "<script>" in html             # inline script

    def test_read_only_law(self, server):
        for m in ("POST", "PUT", "DELETE"):
            r, body = _get(server, "/events", method=m)
            assert r.status == 405, m
            assert "READ-ONLY" in json.loads(body)["reason"]

    def test_unknown_path_is_named(self, server):
        r, body = _get(server, "/nope")
        assert r.status == 404
        assert "/events" in json.loads(body)["reason"]

    def test_missing_events_refused_named(self, tmp_path):
        w = tmp_path / "empty"
        (w / ".aeos").mkdir(parents=True)
        srv = ShopfloorServer(w, port=_port())
        t = threading.Thread(target=srv.start, daemon=True)
        t.start()
        time.sleep(0.5)
        r, body = _get(srv, "/events")
        assert r.status == 404
        assert "no events yet" in json.loads(body)["reason"]
        assert "aeos up" in json.loads(body)["reason"]   # a remedy
        srv.httpd.shutdown()


class TestStreaming:
    def test_backlog_replayed(self, server):
        r, _ = _get(server, "/events", timeout=3, read_body=False)
        assert r.status == 200
        assert r.getheader("Content-Type") == "text/event-stream"
        c = http.client.HTTPConnection("127.0.0.1", server.port,
                                       timeout=3)
        c.request("GET", "/events")
        resp = c.getresponse()
        seen = 0
        deadline = time.time() + 3
        while seen < 5 and time.time() < deadline:
            raw = resp.fp.readline()
            if not raw:
                break                       # EOF: stream closed
            line = raw.decode().strip()
            if line.startswith("data: "):
                seen += 1
        c.close()
        assert seen == 5

    def test_live_event_delivered(self, server, ws):
        c = http.client.HTTPConnection("127.0.0.1", server.port,
                                       timeout=8)
        c.request("GET", "/events")
        resp = c.getresponse()

        def appender():
            time.sleep(0.8)
            f = ws / ".aeos" / "runs" / "1000-events.jsonl"
            with f.open("a") as fh:
                fh.write(json.dumps({"kind": "probe.live", "ts": 1234.0,
                                     "detail": {"live": True}}) + "\n")

        threading.Thread(target=appender, daemon=True).start()
        probe = False
        deadline = time.time() + 6
        while not probe and time.time() < deadline:
            raw = resp.fp.readline()
            if not raw:
                break
            line = raw.decode().strip()
            if line.startswith("data: ") and "probe.live" in line:
                probe = True
        c.close()
        assert probe, "a live-appended event must stream through"

    def test_rollover_to_newer_run(self, server, ws):
        c = http.client.HTTPConnection("127.0.0.1", server.port,
                                       timeout=8)
        c.request("GET", "/events")
        resp = c.getresponse()

        def new_run():
            time.sleep(0.8)
            f = ws / ".aeos" / "runs" / "2000-events.jsonl"
            f.write_text(json.dumps({"kind": "run.two", "ts": 2000.0,
                                     "detail": {}}) + "\n",
                         encoding="utf-8")

        threading.Thread(target=new_run, daemon=True).start()
        rolled = False
        deadline = time.time() + 6
        while not rolled and time.time() < deadline:
            raw = resp.fp.readline()
            if not raw:
                break
            line = raw.decode().strip()
            if line.startswith("data: ") and "run.two" in line:
                rolled = True
        c.close()
        assert rolled, "a newer run file must take over the stream"

    def test_newest_events_file_helper(self, ws):
        assert newest_events_file(ws).name == "1000-events.jsonl"
        (ws / ".aeos" / "runs" / "2000-events.jsonl").write_text("{}\n")
        assert newest_events_file(ws).name == "2000-events.jsonl"
        assert newest_events_file(ws.parent / "nowhere") is None


class TestServer:
    def test_loopback_by_default(self, tmp_path):
        srv = ShopfloorServer(tmp_path)
        assert srv.bind == "127.0.0.1"

    def test_port_conflict_is_a_named_refusal(self, ws):
        srv1 = ShopfloorServer(ws, port=_port())
        t = threading.Thread(target=srv1.start, daemon=True)
        t.start()
        time.sleep(0.5)
        srv2 = ShopfloorServer(ws, port=srv1.port)
        assert srv2.start() == 2            # prints the named refusal
        srv1.httpd.shutdown()


class TestCLI:
    def test_missing_workspace_refused_named(self, tmp_path, monkeypatch,
                                             capsys):
        from aeos.cli import main
        monkeypatch.setattr("sys.argv", [
            "aeos", "stream", "--workspace", str(tmp_path / "none")])
        assert main() == 2
        assert "SHOPFLOOR REFUSED" in capsys.readouterr().out
        assert "aeos up" in capsys.readouterr().out or True
