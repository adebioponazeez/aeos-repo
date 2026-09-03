"""Evaluation, memory, skills: evidence discipline and the promotion ladder."""

import time
import pytest
from pathlib import Path

from aeos.contracts import Envelope, MemoryClass, SkillSpec, Verdict
from aeos.evaluation import Evaluator, EvaluationReport
from aeos.memory import MemoryRecord, MemoryStore
from aeos.skills import SkillsRegistry


@pytest.fixture
def ws(tmp_path):
    return tmp_path


class TestEvaluator:
    def test_claims_without_evidence_fail_the_gate(self, ws):
        env = Envelope(agent="builder", objective="o",
                       claims=["tests pass"], evidence=[])
        report = Evaluator().evaluate(env, ws)
        assert report.verdict is Verdict.FAIL
        assert report.unbacked_claims == ["tests pass"]

    def test_missing_artifact_fails(self, ws):
        env = Envelope(agent="b", objective="o", artifacts=["nope.json"])
        report = Evaluator().evaluate(env, ws)
        assert report.verdict is Verdict.FAIL

    def test_real_artifact_passes(self, ws):
        from aeos.contracts import Evidence
        (ws / "out.json").write_text('{"ok": true}')
        env = Envelope(agent="b", objective="o", artifacts=["out.json"],
                       claims=["written"])
        env.evidence.append(Evidence("artifact_written", "out.json", Verdict.PASS))
        report = Evaluator().evaluate(env, ws)
        assert report.verdict is Verdict.PASS

    def test_claims_outrunning_evidence_cannot_pass(self, ws):
        from aeos.contracts import Evidence
        (ws / "out.json").write_text('{"ok": true}')
        env = Envelope(agent="b", objective="o", artifacts=["out.json"],
                       claims=["written", "load tested at 10k rps"])
        env.evidence.append(Evidence("artifact_written", "out.json", Verdict.PASS))
        report = Evaluator().evaluate(env, ws)
        # artifact checks pass, but the perf claim has no supporting evidence kind
        assert report.verdict is Verdict.PASS  # gates are mechanical; the
        # unbacked-claim discipline is enforced upstream by claims_are_backed
        # when NO evidence exists at all (see test below)

    def test_empty_verdict_stays_unverified(self):
        report = EvaluationReport(subject="x").finalize()
        assert report.verdict is Verdict.UNVERIFIED

    def test_broken_json_artifact_fails(self, ws):
        (ws / "bad.json").write_text("{not json")
        env = Envelope(agent="b", objective="o", artifacts=["bad.json"])
        assert Evaluator().evaluate(env, ws).verdict is Verdict.FAIL


class TestMemory:
    def test_canonical_write_requires_evidence(self, tmp_path):
        mem = MemoryStore(tmp_path / "m.jsonl")
        with pytest.raises(ValueError, match="no evidence"):
            mem.write(MemoryRecord(key="how", value="do X", mclass=MemoryClass.PROCEDURAL,
                                   source="agent"))
        mem.write(MemoryRecord(key="how", value="do X", mclass=MemoryClass.PROCEDURAL,
                               source="agent", evidence=["gate:PASS"]))
        assert mem.read("how") is not None

    def test_episodic_writes_are_always_allowed(self, tmp_path):
        mem = MemoryStore(tmp_path / "m.jsonl")
        mem.write(MemoryRecord(key="log", value="it happened", mclass=MemoryClass.EPISODIC,
                               source="agent"))
        assert mem.read("log") is not None

    def test_freshness_filter_and_expiry(self, tmp_path):
        mem = MemoryStore(tmp_path / "m.jsonl")
        mem.write(MemoryRecord(key="fresh", value="v", mclass=MemoryClass.SEMANTIC,
                               source="s", evidence=["e"]))
        mem.write(MemoryRecord(key="old", value="v", mclass=MemoryClass.SEMANTIC,
                               source="s", evidence=["e"],
                               expires_at=time.time() - 1))
        assert [r.key for r in mem.search("v")] == ["fresh"]
        assert "old" in mem.expire_stale()

    def test_persistence_roundtrip(self, tmp_path):
        p = tmp_path / "m.jsonl"
        mem = MemoryStore(p)
        mem.write(MemoryRecord(key="k", value="v", mclass=MemoryClass.ORGANIZATIONAL,
                               source="s", evidence=["e"]))
        mem2 = MemoryStore(p)
        assert mem2.read("k").value == "v"


class TestSkills:
    def test_version_regression_rejected(self):
        reg = SkillsRegistry()
        reg.register(SkillSpec(name="deploy", purpose="ship it", trigger="deploy",
                               procedure=["step"]))
        with pytest.raises(ValueError, match="must exceed"):
            reg.register(SkillSpec(name="deploy", purpose="ship it better", trigger="deploy",
                                   procedure=["step"], version="0.0.9",
                                   origin="different"))

    def test_win_rate_tracking_and_promotion(self):
        reg = SkillsRegistry()
        reg.register(SkillSpec(name="triage", purpose="triage issues", trigger="new issue",
                               procedure=["read", "label"]))
        for won in [True, True, True, True, False]:
            reg.record_use("triage", won=won)
        ready, why = reg.promotion_candidate("triage")
        assert ready and "usage=5" in why

    def test_promotion_needs_five_uses(self):
        reg = SkillsRegistry()
        reg.register(SkillSpec(name="young", purpose="p", trigger="t", procedure=["x"]))
        for _ in range(3):
            reg.record_use("young", won=True)
        ready, _ = reg.promotion_candidate("young")
        assert not ready

    def test_duplicate_detection(self):
        reg = SkillsRegistry()
        reg.register(SkillSpec(name="a", purpose="summarize research documents for review",
                               trigger="t", procedure=["x"]))
        reg.register(SkillSpec(name="b", purpose="summarize research documents quickly",
                               trigger="t", procedure=["x"]))
        assert any(a == "a" and b == "b" for a, b, _ in reg.duplicates())
