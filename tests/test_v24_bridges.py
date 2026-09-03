"""v24 tests: the bridges — MCP server mode + OTel export."""

import json
import sys
from pathlib import Path

import pytest

from aeos.fleet import EventBus
from aeos.mcp_client import MCPClient
from aeos.mcp_server import AEOS_TOOLS, READONLY_TOOLS, handle_request
from aeos.otel import event_to_span, export


class TestMCPServer:
    def test_initialize_announces_aeos(self):
        info = handle_request("initialize", {})
        assert info["serverInfo"]["name"] == "aeos-server"

    def test_tools_listed_and_all_readonly(self):
        res = handle_request("tools/list", {})
        names = {t["name"] for t in res["tools"]}
        assert names == READONLY_TOOLS            # the law, testable
        assert len(AEOS_TOOLS) == 3

    def test_leverage_audit_tool_reads_a_workspace(self, tmp_path):
        res = handle_request("tools/call", {
            "name": "leverage_audit",
            "arguments": {"workspace": str(tmp_path)}})
        text = res["content"][0]["text"]
        assert "LEVERAGE AUDIT" in text and "0/12" in text

    def test_standards_check_tool_gates(self, tmp_path):
        from aeos.standards import init_template
        init_template(tmp_path)
        res = handle_request("tools/call", {
            "name": "standards_check",
            "arguments": {"plan_text": "ship it blind",
                          "workspace": str(tmp_path)}})
        assert "ok=False" in res["content"][0]["text"]

    def test_unknown_method_raises(self):
        from aeos.mcp_server import UnknownMethod
        with pytest.raises(UnknownMethod):
            handle_request("no/such", {})

    def test_real_interop_with_v21_client(self, tmp_path):
        """The bridge both ways: our client talks to our server."""
        c = MCPClient([sys.executable, "-m", "aeos.mcp_server"],
                      timeout_s=15.0)
        c.start()
        try:
            info = c.initialize()
            tools = c.tools()
            res = c.call("leverage_audit",
                         {"workspace": str(tmp_path)})
        finally:
            c.close()
        assert info["serverInfo"]["name"] == "aeos-server"
        assert {t.name for t in tools} == READONLY_TOOLS
        assert "LEVERAGE AUDIT" in res.text


class TestOTelExport:
    def _bus(self, tmp_path):
        bus = EventBus(tmp_path / ".aeos" / "events.jsonl")
        bus.publish("AGENT_REGISTERED", "scout", "role=research")
        bus.publish("NODE_FAILED", "smith", "ValueError: gate refused")
        bus.publish("AGENT_TASK_DONE", "scout", "ack")
        return bus

    def test_event_becomes_otel_span(self, tmp_path):
        bus = self._bus(tmp_path)
        spans = [event_to_span(ev, bus.path.name) for ev in bus.replay()]
        assert all("traceId" in s and "spanId" in s
                   and "startTimeUnixNano" in s for s in spans)
        assert len({s["traceId"] for s in spans}) == 1   # one stream
        assert len({s["spanId"] for s in spans}) == 3    # content-addressed

    def test_failures_map_to_error_status(self, tmp_path):
        bus = self._bus(tmp_path)
        spans = [event_to_span(ev, bus.path.name) for ev in bus.replay()]
        by_name = {s["name"]: s for s in spans}
        assert by_name["NODE_FAILED"]["status"]["code"] == "ERROR"
        assert by_name["AGENT_TASK_DONE"]["status"]["code"] == "UNSET"

    def test_export_is_byte_stable(self, tmp_path):
        bus = self._bus(tmp_path)
        out = tmp_path / "spans.jsonl"
        assert export(bus, out) == 3
        first = out.read_text(encoding="utf-8")
        export(bus, out)
        assert out.read_text(encoding="utf-8") == first

    def test_otel_command_renders(self, tmp_path, capsys):
        from aeos.cli import main
        ws = tmp_path / "ws"
        main(["fleet", "--workspace", str(ws)])
        rc = main(["otel", "--workspace", str(ws)])
        out = capsys.readouterr().out
        assert rc == 0 and "OTEL" in out and "span" in out
        assert (ws / ".aeos" / "otel-spans.jsonl").exists()

    def test_mcp_serve_roundtrip_command(self, capsys):
        from aeos.cli import main
        rc = main(["mcp", "--serve"])
        out = capsys.readouterr().out
        assert rc == 0 and "aeos-server" in out and "LEVERAGE AUDIT" in out
