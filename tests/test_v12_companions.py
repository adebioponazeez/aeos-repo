"""v12 tests: companions (Pi CLI, DeerFlow) as bounded nodes.

All against fake executables — the integration is proven without
installing pi, deerflow, or spending a key. The laws must hold even
(especially) when the worker is somebody else's program.
"""

import json
import os
import stat
import pytest
from pathlib import Path

from aeos.companions import (DEFAULT_DEERFLOW, DEFAULT_PI, PI_PATH_ENV,
                             DEERFLOW_BIN_ENV, companion_status,
                             deerflow_handler, final_message, parse_report,
                             run_deerflow, run_pi, pi_handler)
from aeos.contracts import TaskSpec
from aeos.evaluation import Evaluator
from aeos.governor import Governor
from aeos.harness import Harness
from aeos.models import EchoModel
from aeos.observability import EventLog
from aeos.orchestrator import Orchestrator


def make_exe(path: Path, body: str) -> str:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


GOOD_PI = r'''
mkdir -p src
printf "print('companion work')\n" > src/feature.py
printf '{"type":"assistant","text":"implementing"}\n'
printf '{"type":"result","text":"DONE {\"artifacts\":[\"src/feature.py\"],\"summary\":\"implemented the feature\"}"}\n'
'''

ROGUE_PI = r'''
printf "boom" > evil.sh
printf '{"type":"result","text":"DONE {\"artifacts\":[],\"summary\":\"did nothing suspicious\"}"}\n'
'''

HANG_PI = "sleep 60\n"

GOOD_DF = r'''
printf '{"type":"plan","content":"planning"}\n'
printf '{"type":"source","url":"https://mcp.io/spec","title":"MCP 2026-07 stateless core","snippet":"spec"}\n'
printf '{"type":"source","url":"https://research/rot","title":"Context rot study","snippet":"138 repos"}\n'
printf '{"type":"answer","content":"DeerFlow concludes: harnesses win."}\n'
'''

GARBAGE_DF = "hello not json\n{{{\n"


def _spec(name="coder"):
    from aeos.contracts import ActionClass, AgentSpec
    return AgentSpec(
        name=name, mission="implement via companion", inputs=["spec"],
        outputs=["code"], tools=["pi"], constraints=["stay in boundary"],
        success_criteria=["artifact exists"], evaluation_criteria=["gates"],
        escalation_conditions=["pi unavailable"], termination_conditions=["done"],
        writes=["src/*"], action_classes=[ActionClass.READ, ActionClass.WRITE])


def _orch(ws, handler, spec):
    return Orchestrator(agents={spec.name: spec},
                        handlers={spec.name: handler}, model=EchoModel(),
                        governor=Governor(log=EventLog()), evaluator=Evaluator(),
                        log=EventLog(), workspace=ws, max_workers=1)


class TestParsing:
    def test_final_message_shapes(self):
        assert final_message([{"type": "a", "text": "one"},
                              {"type": "result", "text": "two"}]) == "two"
        assert final_message([{"message": {"content": "via message"}}]) == "via message"
        assert final_message([{"type": "tool", "x": 1}]) == ""

    def test_report_extraction_takes_last_json(self):
        text = 'junk {"a":1} more {"artifacts":["x.py"],"summary":"s"} tail'
        assert parse_report(text)["summary"] == "s"


class TestPi:
    def test_good_pi_produces_gated_envelope(self, tmp_path, monkeypatch):
        fake = make_exe(tmp_path / "pi", GOOD_PI)
        monkeypatch.setenv(PI_PATH_ENV, fake)
        harness = Harness(tmp_path / "ws")
        log = EventLog()
        handler = pi_handler("coder", harness, log, writes=["src/*"],
                             timeout_s=15)
        report = _orch(tmp_path / "ws", handler, _spec()).run("o", [
            TaskSpec(name="build", description="add the feature",
                     agent="coder")], repair=False)
        assert report.states["build"].value == "SUCCEEDED"
        assert (tmp_path / "ws/src/feature.py").exists()

    def test_roguish_pi_is_reverted_and_killed(self, tmp_path, monkeypatch):
        fake = make_exe(tmp_path / "pi", ROGUE_PI)
        monkeypatch.setenv(PI_PATH_ENV, fake)
        harness = Harness(tmp_path / "ws")
        log = EventLog()
        handler = pi_handler("coder", harness, log, writes=["src/*"],
                             timeout_s=15)
        report = _orch(tmp_path / "ws", handler, _spec()).run("o", [
            TaskSpec(name="build", description="add the feature",
                     agent="coder")], repair=False)
        assert report.states["build"].value == "FAILED"   # boundary law
        assert not (tmp_path / "ws/evil.sh").exists()      # reverted

    def test_hanging_pi_dies_at_wall_clock(self, tmp_path, monkeypatch):
        fake = make_exe(tmp_path / "pi", HANG_PI)
        monkeypatch.setenv(PI_PATH_ENV, fake)
        out = run_pi("do it", tmp_path, timeout_s=0.5)
        assert out.ok is False and "wall clock" in out.why

    def test_missing_pi_fails_structurally(self, tmp_path, monkeypatch):
        monkeypatch.setenv(PI_PATH_ENV, "/nonexistent/pi")
        out = run_pi("do it", tmp_path)
        assert out.ok is False and "will not guess" in out.why


class TestDeerFlow:
    def test_findings_and_answer_quarantined(self, tmp_path, monkeypatch):
        fake = make_exe(tmp_path / "deerflow", GOOD_DF)
        monkeypatch.setenv(DEERFLOW_BIN_ENV, fake)
        brief = run_deerflow("agentic harnesses 2026")
        assert len(brief.findings) == 2
        assert all(f.source.startswith("http") for f in brief.findings)
        assert brief.findings[0].confidence == 0.75
        assert brief.unverified and brief.unverified[0].source == "deerflow:final"

    def test_garbage_stream_yields_empty_brief(self, tmp_path, monkeypatch):
        fake = make_exe(tmp_path / "deerflow", GARBAGE_DF)
        monkeypatch.setenv(DEERFLOW_BIN_ENV, fake)
        brief = run_deerflow("anything")
        assert brief.findings == [] and brief.unverified == []

    def test_missing_deerflow_empty_brief(self, tmp_path, monkeypatch):
        monkeypatch.setenv(DEERFLOW_BIN_ENV, "/nonexistent/deerflow")
        brief = run_deerflow("anything")
        assert brief.findings == []      # no sources, no fabrication

    def test_deerflow_handler_end_to_end(self, tmp_path, monkeypatch):
        fake = make_exe(tmp_path / "deerflow", GOOD_DF)
        monkeypatch.setenv(DEERFLOW_BIN_ENV, fake)
        harness = Harness(tmp_path / "ws")
        log = EventLog()
        handler = deerflow_handler("researcher", harness, log, timeout_s=15)
        spec = _spec("researcher")
        report = _orch(tmp_path / "ws", handler, spec).run("o", [
            TaskSpec(name="research", description="harness state of art",
                     agent="researcher")], repair=False)
        assert report.states["research"].value == "SUCCEEDED"
        data = json.loads((tmp_path / "ws/research/deerflow-brief.json")
                          .read_text())
        assert len(data["findings"]) == 2 and data["unverified"]


class TestStatus:
    def test_status_reports_both(self, monkeypatch):
        monkeypatch.setenv(PI_PATH_ENV, "/nonexistent/pi")
        monkeypatch.setenv(DEERFLOW_BIN_ENV, "/nonexistent/df")
        statuses = {s.name: s for s in companion_status()}
        assert statuses["pi"].available is False
        assert statuses["deerflow"].available is False
        assert "PI_PATH" in statuses["pi"].hint
