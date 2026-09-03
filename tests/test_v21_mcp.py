"""v21 tests: MCP client — handshake, tools, calls, walls, quarantine."""

import sys
import time
from pathlib import Path

import pytest

from aeos.mcp_client import (MCPClient, MCPError, import_tools)

SERVER = [sys.executable, "-m", "aeos.mcp_demo_server"]


def client(timeout_s=10.0):
    c = MCPClient(SERVER, timeout_s=timeout_s)
    c.start()
    return c


class TestHandshake:
    def test_initialize_returns_server_info(self):
        c = client()
        try:
            info = c.initialize()
            assert info["serverInfo"]["name"] == "aeos-demo-server"
        finally:
            c.close()

    def test_tools_listed_after_initialize(self):
        c = client()
        try:
            c.initialize()
            tools = c.tools()
            assert [t.name for t in tools] == ["echo"]
        finally:
            c.close()


class TestCalls:
    def test_tool_call_returns_text(self):
        c = client()
        try:
            c.initialize()
            res = c.call("echo", {"text": "the law travels"})
            assert res.ok and res.text == "echo: the law travels"
        finally:
            c.close()

    def test_unknown_method_is_an_error(self):
        c = client()
        try:
            with pytest.raises(MCPError, match="no such method"):
                c.request("bogus/method")
        finally:
            c.close()


class TestImportLaw:
    def test_imported_tools_enter_untrusted(self):
        c = client()
        try:
            c.initialize()
            imported = import_tools(c.tools())
            assert imported["echo"]["trust"] == "UNTRUSTED"
        finally:
            c.close()


class TestWalls:
    def test_hanging_server_is_killed_by_the_wall(self, tmp_path):
        hang = tmp_path / "hang_server.py"
        hang.write_text("import sys, time\n_time = time.sleep(30)\n",
                        encoding="utf-8")
        c = MCPClient([sys.executable, str(hang)], timeout_s=1.0)
        c.start()
        with pytest.raises(MCPError, match="timeout"):
            c.initialize()
        assert c.proc is None            # killed, not leaked

    def test_garbage_line_fails_closed(self, tmp_path):
        garbage = tmp_path / "garbage.py"
        garbage.write_text(
            "import sys\nsys.stdout.write('not json at all\\n');"
            "sys.stdout.flush()\nimport time\ntime.sleep(5)\n",
            encoding="utf-8")
        c = MCPClient([sys.executable, str(garbage)], timeout_s=5.0)
        c.start()
        with pytest.raises(MCPError):
            c.initialize()
        c.close()


class TestCLI:
    def test_mcp_command_runs_the_protocol_demo(self, capsys):
        from aeos.cli import main
        rc = main(["mcp"])
        out = capsys.readouterr().out
        assert rc == 0 and "MCP" in out and "UNTRUSTED" in out \
            and "echo:" in out
