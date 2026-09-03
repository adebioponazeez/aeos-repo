"""v31 tests: the consulate — read-only over the wire, loopback-proven."""

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest

from aeos.mcp_client import MCPError
from aeos.mcp_http import MCPHTTPClient
from aeos.mcp_http_server import Consulate, READONLY_TOOLS


def post_raw(url, body: bytes, ctype="application/json"):
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


class TestConsulate:
    def test_serves_readonly_tools_over_http(self):
        with Consulate() as c:
            cli = MCPHTTPClient(c.url, timeout_s=5)
            info = cli.initialize()
            tools = cli.tools()
            assert info["serverInfo"]["name"] == "aeos-server"
            assert {t.name for t in tools} == READONLY_TOOLS  # the law

    def test_tool_call_lands_over_the_wire(self, tmp_path):
        with Consulate() as c:
            cli = MCPHTTPClient(c.url, timeout_s=5)
            cli.initialize()
            res = cli.call("leverage_audit", {"workspace": str(tmp_path)})
            assert res.ok and "LEVERAGE AUDIT" in res.text

    def test_default_bind_is_loopback_only(self):
        with Consulate() as c:
            assert c.bind == "127.0.0.1"      # the door opens on purpose

    def test_unknown_method_is_a_jsonrpc_error(self):
        with Consulate() as c:
            cli = MCPHTTPClient(c.url, timeout_s=5)
            with pytest.raises(MCPError, match="no such method"):
                cli.request("bogus/method")

    def test_malformed_body_fails_closed_server_survives(self):
        with Consulate() as c:
            status, _ = post_raw(c.url, b"{not json at all")
            assert status == 400
            cli = MCPHTTPClient(c.url, timeout_s=5)   # still alive
            assert cli.initialize()["serverInfo"]["name"] == "aeos-server"

    def test_notification_accepted_silently(self):
        with Consulate() as c:
            note = json.dumps({"jsonrpc": "2.0",
                               "method": "notifications/initialized"
                               }).encode()
            status, body = post_raw(c.url, note)
            assert status == 202 and body == ""

    def test_oversized_body_refused(self):
        with Consulate() as c:
            big = b"x" * (1_000_001)
            status, _ = post_raw(c.url, big)
            assert status == 413

    def test_wrong_path_404(self):
        with Consulate() as c:
            status, _ = post_raw(c.url.replace("/mcp", "/nope"), b"{}")
            assert status == 404

    def test_concurrent_requests_all_served(self):
        with Consulate() as c:
            def one(_):
                cli = MCPHTTPClient(c.url, timeout_s=5)
                cli.initialize()
                return cli.tools()[0].name
            with ThreadPoolExecutor(max_workers=5) as pool:
                names = list(pool.map(one, range(10)))
            assert names == ["leverage_audit"] * 10


class TestCLI:
    def test_consulate_roundtrip_receipt(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["mcp", "--serve-http", "--roundtrip",
                   "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0 and "CONSULATE" in out
        assert "leverage_audit" in out and "read-only" in out
