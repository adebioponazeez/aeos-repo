"""v14 tests: the dividend — distillation, cache-stable JSON prefixes,
negative marginal consumption, and memory that must pay rent."""

import json
import pytest
from pathlib import Path

from aeos.context_os import approx_tokens
from aeos.contracts import MemoryClass
from aeos.dividend import (MemoryDistiller, RentFinding, StableAssembly,
                           TokenLedger, canonical_json, rent, squatters,
                           stable_prefix)
from aeos.memory import MemoryRecord, MemoryStore


def lesson_store(tmp_path, repeats=5):
    store = MemoryStore(tmp_path / "m.jsonl")
    for i in range(repeats):
        store.write(MemoryRecord(
            key=f"lesson::deploy::{i}", mclass=MemoryClass.EPISODIC,
            value="deploy: SUCCEEDED via pytest-first then gate-check "
                  f"sequence run {i}",
            source="learning-loop", confidence=0.6))
    # noise that must NOT be grouped in
    store.write(MemoryRecord(
        key="lesson::research::0", mclass=MemoryClass.EPISODIC,
        value="research: SUCCEEDED via sourced brief", source="loop",
        confidence=0.6))
    return store


class TestDistiller:
    def test_five_episodes_become_one_semantic_record(self, tmp_path):
        store = lesson_store(tmp_path)
        report = MemoryDistiller(store).distill_lessons()
        assert report.groups == 1
        assert report.episodes_in == 5
        semantic = store.read("semantic::deploy")
        assert semantic is not None
        assert semantic.mclass is MemoryClass.SEMANTIC
        assert "validated 5x" in semantic.value

    def test_compression_is_measured_and_real(self, tmp_path):
        store = lesson_store(tmp_path)
        report = MemoryDistiller(store).distill_lessons()
        assert report.compression >= 2.0          # 5 episodes -> ~1/5 the tokens
        assert report.projected_saving_per_recall > 0

    def test_distilled_writes_pass_the_evidence_gate(self, tmp_path):
        store = lesson_store(tmp_path)
        MemoryDistiller(store).distill_lessons()
        rec = store.read("semantic::deploy")
        assert rec.evidence and rec.evidence[0].startswith("distilled from")

    def test_singleton_groups_left_alone(self, tmp_path):
        store = lesson_store(tmp_path, repeats=1)   # only the research one
        report = MemoryDistiller(store).distill_lessons()
        assert report.groups == 0                   # nothing worth compressing


class TestStablePrefix:
    def test_canonical_json_is_byte_stable(self):
        a = {"charter": "evidence or silence", "floors": ["gates", "bounds"],
             "n": 7}
        b = {"n": 7, "floors": ["gates", "bounds"],
             "charter": "evidence or silence"}
        assert canonical_json(a) == canonical_json(b)

    def test_same_stable_set_same_prefix_different_tail(self):
        stable = {"org": {"law": "claims are untrusted"}, "roster": ["exec", "builder"]}
        a1 = stable_prefix(stable, {"query": "deploy the thing"})
        a2 = stable_prefix(stable, {"query": "a completely different question"})
        assert a1.prefix == a2.prefix            # cache-eligible across runs
        assert a1.tail != a2.tail                # volatility rides last
        assert a1.prefix_tokens > 0 and a1.cache_eligible_fraction > 0.5

    def test_key_order_in_input_does_not_matter(self):
        s1 = stable_prefix({"a": 1, "b": {"x": [1, 2]}}, {"q": "same"})
        s2 = stable_prefix({"b": {"x": [1, 2]}, "a": 1}, {"q": "same"})
        assert s1.prefix == s2.prefix and s1.total_tokens == s2.total_tokens


class TestNegativeMarginal:
    def _ledger(self):
        led = TokenLedger()
        # naive run 1: read everything (baseline == actual)
        led.record("deploy", 1, baseline_tokens=2000, actual_tokens=2000)
        # runs 2..6: recall the ~120-token distilled record + amortized
        # storage overhead of 30 -> all-in 150 vs baseline 2000
        for run in range(2, 7):
            led.record("deploy", run, baseline_tokens=2000,
                       actual_tokens=120, memory_overhead_tokens=30)
        return led

    def test_marginal_is_negative(self):
        m = self._ledger().marginal("deploy")
        assert m["negative_marginal"] is True
        assert m["delta"] == -1850
        assert m["all_in"] == 150

    def test_cumulative_dividend_accumulates(self):
        d = self._ledger().dividend()
        assert d["any_negative"] is True
        # run1 saved 0, runs 2-6 saved 1850 each
        assert d["total_saved"] == 5 * 1850

    def test_no_memory_no_dividend(self):
        led = TokenLedger()
        led.record("deploy", 1, baseline_tokens=2000, actual_tokens=2000)
        led.record("deploy", 2, baseline_tokens=2000, actual_tokens=2000)
        assert led.marginal("deploy")["negative_marginal"] is False


class TestRent:
    def _records(self):
        return [
            MemoryRecord(key="semantic::deploy", value="x" * 400,
                         mclass=MemoryClass.SEMANTIC, source="distiller"),
            MemoryRecord(key="semantic::ghost", value="y" * 400,
                         mclass=MemoryClass.SEMANTIC, source="distiller"),
            MemoryRecord(key="working::tmp", value="z" * 100,
                         mclass=MemoryClass.WORKING, source="run"),
        ]

    def test_unrecalled_memory_is_squatting(self):
        findings = rent(self._records(), {"semantic::deploy"})
        by_key = {f.key: f for f in findings}
        assert by_key["semantic::deploy"].verdict == "PAYS_RENT"
        assert by_key["semantic::ghost"].verdict == "SQUATTING"
        assert "working::tmp" not in by_key        # working memory exempt

    def test_squatters_flagged_for_removal(self):
        findings = rent(self._records(), set())
        assert len(squatters(findings)) == 2
        assert all(f.recalls == 0 for f in squatters(findings))


class TestEndToEnd:
    def test_reference_run_reports_its_dividend(self, tmp_path):
        from aeos.pipeline import reference_run
        bundle = reference_run(tmp_path / "ws", intent="Ship it")
        assert bundle["accepted"] is True
        d = bundle["dividend"]
        assert d["distillation"]["groups"] >= 1
        assert d["distillation"]["compression"] >= 1.5
        assert d["ledger"]["any_negative"] is True
        assert d["rent"]["squatters"] >= 0

    def test_dividend_command_renders(self, tmp_path, capsys):
        from aeos.pipeline import reference_run
        reference_run(tmp_path / "ws2", intent="Ship it")
        from aeos.cli import main
        rc = main(["dividend", "--workspace", str(tmp_path / "ws2")])
        out = capsys.readouterr().out
        assert rc == 0 and "DIVIDEND" in out and "compression" in out
