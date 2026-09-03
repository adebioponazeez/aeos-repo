"""v20 tests: companions round 2 — aider + headless claude, same law."""

import stat
from pathlib import Path

import pytest

from aeos.companions import (SubprocessRunner, aider_handler,
                             claude_handler, parse_report, run_aider,
                             run_claude, round2_status,
                             verify_against_disk)
from aeos.harness import Harness


def make_exe(path: Path, body: str) -> str:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


GOOD_AIDER = r'''
mkdir -p src
printf "def feature2():\n    return 42\n" > src/feature2.py
printf '{"artifacts": ["src/feature2.py"], "summary": "added feature2"}\n'
'''
PHANTOM_AIDER = r'''
printf '{"artifacts": ["src/never-written.py"], "summary": "lied"}\n'
'''
GOOD_CLAUDE = r'''
mkdir -p src
printf "VALUE = 7\n" > src/config.py
printf '{"result": "done. {\"artifacts\": [\"src/config.py\"], \"summary\": \"config written\"}"}\n'
'''


def task(name="build", desc="add the feature"):
    from aeos.contracts import TaskSpec
    return TaskSpec(name=name, agent="builder", description=desc)


class TestRunners:
    def test_good_aider_reports_and_delivers(self, tmp_path, monkeypatch):
        exe = make_exe(tmp_path / "aider", GOOD_AIDER)
        monkeypatch.setenv("AIDER_PATH", exe)
        ws = tmp_path / "ws"
        ws.mkdir()
        out = run_aider("add feature2", ws, timeout_s=15)
        assert out.ok and (ws / "src" / "feature2.py").exists()
        assert out.report["artifacts"] == ["src/feature2.py"]
        verified, phantom = verify_against_disk(out.report, ws)
        assert verified == ["src/feature2.py"] and phantom == []

    def test_phantom_artifacts_are_detected(self, tmp_path, monkeypatch):
        exe = make_exe(tmp_path / "aider", PHANTOM_AIDER)
        monkeypatch.setenv("AIDER_PATH", exe)
        ws = tmp_path / "ws"
        ws.mkdir()
        out = run_aider("lie to me", ws, timeout_s=15)
        verified, phantom = verify_against_disk(out.report, ws)
        assert phantom == ["src/never-written.py"]

    def test_headless_claude_result_is_parsed(self, tmp_path, monkeypatch):
        exe = make_exe(tmp_path / "claude", GOOD_CLAUDE)
        monkeypatch.setenv("CLAUDE_PATH", exe)
        ws = tmp_path / "ws"
        ws.mkdir()
        out = run_claude("write config", ws, timeout_s=15)
        assert out.ok and (ws / "src" / "config.py").exists()
        assert out.report["summary"] == "config written"

    def test_timeout_yields_not_ok(self, tmp_path, monkeypatch):
        exe = make_exe(tmp_path / "aider", "sleep 5\n")
        monkeypatch.setenv("AIDER_PATH", exe)
        out = run_aider("slow", tmp_path, timeout_s=1)
        assert out.timed_out and not out.ok

    def test_missing_binary_is_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIDER_PATH", str(tmp_path / "nonexistent"))
        out = run_aider("x", tmp_path, timeout_s=5)
        assert out.rc == 127 and not out.ok


class TestHandlers:
    def test_aider_handler_verifies_and_gates(self, tmp_path, monkeypatch):
        from aeos.observability import EventLog
        exe = make_exe(tmp_path / "aider", GOOD_AIDER)
        monkeypatch.setenv("AIDER_PATH", exe)
        harness = Harness(tmp_path / "ws")
        log = EventLog(tmp_path / "ws" / ".aeos" / "events.jsonl")
        env = aider_handler("aider", harness, log,
                            timeout_s=15)(task(), None)
        assert env.artifacts == ["src/feature2.py"]

    def test_phantom_companion_raises(self, tmp_path, monkeypatch):
        from aeos.observability import EventLog
        exe = make_exe(tmp_path / "aider", PHANTOM_AIDER)
        monkeypatch.setenv("AIDER_PATH", exe)
        harness = Harness(tmp_path / "ws")
        log = EventLog(tmp_path / "ws" / ".aeos" / "events.jsonl")
        with pytest.raises(RuntimeError, match="phantom"):
            aider_handler("aider", harness, log,
                          timeout_s=15)(task(), None)

    def test_claude_handler_same_law(self, tmp_path, monkeypatch):
        from aeos.observability import EventLog
        exe = make_exe(tmp_path / "claude", GOOD_CLAUDE)
        monkeypatch.setenv("CLAUDE_PATH", exe)
        harness = Harness(tmp_path / "ws")
        log = EventLog(tmp_path / "ws" / ".aeos" / "events.jsonl")
        env = claude_handler("claude", harness, log,
                             timeout_s=15)(task(), None)
        assert env.artifacts == ["src/config.py"]

    def test_boundary_violation_is_reverted(self, tmp_path, monkeypatch):
        from aeos.observability import EventLog
        rogue = r'''
mkdir -p secrets
printf "stolen\n" > secrets/keys.txt
printf '{"artifacts": ["secrets/keys.txt"], "summary": "oops"}\n'
'''
        exe = make_exe(tmp_path / "aider", rogue)
        monkeypatch.setenv("AIDER_PATH", exe)
        harness = Harness(tmp_path / "ws")
        log = EventLog(tmp_path / "ws" / ".aeos" / "events.jsonl")
        with pytest.raises(RuntimeError, match="boundary"):
            aider_handler("aider", harness, log,
                          timeout_s=15)(task(), None)


class TestStatus:
    def test_round2_status_lists_names(self):
        names = round2_status()
        assert isinstance(names, list)
        assert all(n in ("aider", "claude", "pi", "deerflow") for n in names)
