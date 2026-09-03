"""v1.1 hardening tests: redaction, gate library, entropy coverage."""

import pytest
from pathlib import Path

from aeos.observability import EventLog
from aeos.evaluation import Evaluator, schema_gate, regression_gate
from aeos.evaluation import tests_pass_gate as run_tests_gate
from aeos.contracts import Envelope, Evidence, Verdict
from aeos.entropy import EntropyScanner, EntropyAction
from aeos.skills import SkillsRegistry
from aeos.memory import MemoryStore
from aeos.ops import RegressionBook


class TestRedaction:
    def test_api_key_never_enters_the_log(self):
        log = EventLog()
        log.emit("tool.call", api_key="sk-1234567890", task="t1")
        assert log.events()[0].detail["api_key"] == "[REDACTED]"

    def test_benign_keys_survive(self):
        log = EventLog()
        log.emit("task.started", task="deploy", attempts=1)
        assert log.events()[0].detail["task"] == "deploy"

    def test_file_sink_is_redacted_too(self, tmp_path):
        p = tmp_path / "events.jsonl"
        log = EventLog(p)
        log.emit("model.call", token="abc", agent="x")
        assert "abc" not in p.read_text()
        assert "[REDACTED]" in p.read_text()


class TestGateLibrary:
    def test_schema_gate_missing_key_fails(self, tmp_path):
        (tmp_path / "spec.json").write_text('{"name": "x"}')
        env = Envelope(agent="a", objective="o", artifacts=["spec.json"])
        ev = Evaluator(gates=[schema_gate({"spec.json": ["name", "version"]})])
        assert ev.evaluate(env, tmp_path).verdict is Verdict.FAIL

    def test_schema_gate_satisfied(self, tmp_path):
        (tmp_path / "spec.json").write_text('{"name": "x", "version": 2}')
        env = Envelope(agent="a", objective="o", artifacts=["spec.json"])
        ev = Evaluator(gates=[schema_gate({"spec.json": ["name", "version"]})])
        assert ev.evaluate(env, tmp_path).verdict is Verdict.PASS

    def test_tests_pass_gate_detects_failures(self):
        env = Envelope(agent="a", objective="o", claims=["tests pass"])
        env.add_evidence("test_run", "1 failed, 2 passed in 0.1s")
        ev = Evaluator(gates=[regression_gate(None)])
        # direct gate invocation
        result = run_tests_gate(env, Path("."))
        assert result[0] is False

    def test_tests_pass_gate_clean(self):
        env = Envelope(agent="a", objective="o")
        env.add_evidence("test_run", "5 passed in 0.2s")
        assert run_tests_gate(env, Path("."))[0] is True

    def test_regression_gate_blocks_known_failure(self, tmp_path):
        book = RegressionBook(tmp_path / "reg.jsonl")
        book.record("deploy-env-drift", "wrong env var",
                    ["deploy/config.py", "infra/*"])
        env = Envelope(agent="a", objective="o", changed_files=["deploy/config.py"])
        gate = regression_gate(book)
        ok, detail = gate.run(env, tmp_path), None
        assert ok.verdict is Verdict.FAIL


class TestEntropyExtensions:
    def test_weak_test_files_flagged(self, tmp_path):
        (tmp_path / "test_vacuous.py").write_text(
            "def test_nothing():\n    pass\n")
        scanner = EntropyScanner(SkillsRegistry(), MemoryStore(tmp_path / "m.jsonl"), tmp_path)
        findings = scanner.scan()
        assert any(f.kind == "weak_tests" and f.action is EntropyAction.REPAIR
                   for f in findings)

    def test_unused_tools_flagged(self, tmp_path):
        scanner = EntropyScanner(SkillsRegistry(), MemoryStore(tmp_path / "m.jsonl"), tmp_path)
        findings = scanner.unused_tools(["web_search", "legacy_search"],
                                        ["WEB_SEARCH"])
        assert [f.detail.split("'")[1] for f in findings] == ["legacy_search"]

    def test_architectural_drift_both_directions(self, tmp_path):
        scanner = EntropyScanner(SkillsRegistry(), MemoryStore(tmp_path / "m.jsonl"), tmp_path)
        findings = scanner.architectural_drift(
            documented=["models", "ghost"], actual=["models", "unmapped"])
        kinds = {f.detail for f in findings}
        assert any("ghost" in k for k in kinds)
        assert any("unmapped" in k for k in kinds)
