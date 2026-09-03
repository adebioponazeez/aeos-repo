"""v5 research/ops + v6 meta-loop + v7 factory tests."""

import pytest
from pathlib import Path

from aeos.contracts import ActionClass, AutonomyLevel, SkillSpec, Verdict
from aeos.discovery import CapabilityDiscovery
from aeos.governor import Governor
from aeos.skills import SkillsRegistry
from aeos.sponsorship import SponsorshipGate
from aeos.tools import ToolRegistry, install_default_tools


# ------------------------------------------------------------------ v5

class TestResearchPipeline:
    def test_low_authority_sources_go_to_unverified(self):
        from aeos.research import ResearchPipeline
        gov = Governor(level=AutonomyLevel.L5_CONTINUOUS_AUTONOMY)
        tools = ToolRegistry(gov)
        install_default_tools(tools)
        brief = ResearchPipeline(tools).run("mcp stateless core")
        assert len(brief.findings) == 2          # authority .95 and .9
        assert len(brief.unverified) == 1        # the forum lore (0.2)
        assert brief.average_confidence >= 0.8

    def test_tool_denied_means_empty_brief(self):
        from aeos.research import ResearchPipeline
        gov = Governor(level=AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL)
        # drop network from policy to force deny-by-default at L2
        gov.policy.pop(ActionClass.NETWORK)
        tools = ToolRegistry(gov)
        install_default_tools(tools)
        brief = ResearchPipeline(tools).run("anything")
        assert brief.findings == [] and brief.unverified == []


class TestSweeps:
    def test_due_jobs_run_and_not_before(self):
        from aeos.ops import SweepScheduler
        sched = SweepScheduler()
        ran = []
        def job():
            ran.append(1)
            return 3
        sched.every("entropy", interval_s=100, fn=job)
        t0 = 1_000_000.0
        assert sched.run_due(now=t0) == [("entropy", 3)]
        assert sched.run_due(now=t0 + 50) == []          # not due yet
        assert sched.run_due(now=t0 + 101) == [("entropy", 3)]

    def test_next_due_points_at_soonest(self):
        from aeos.ops import SweepScheduler
        s = SweepScheduler()
        s.every("fast", 10, lambda: {})
        s.every("slow", 100, lambda: {})
        assert s.next_due(now=0) == "fast"


class TestRegressionBook:
    def test_recorded_failure_blocks_matching_change(self, tmp_path):
        from aeos.ops import RegressionBook
        book = RegressionBook(tmp_path / "reg.jsonl")
        book.record("bad-migration", "dropped column", ["db/schema.py"])
        assert book.check(["db/schema.py"]) == ["bad-migration"]
        assert book.check(["docs/readme.md"]) == []

    def test_persists_and_reloads(self, tmp_path):
        from aeos.ops import RegressionBook
        p = tmp_path / "reg.jsonl"
        RegressionBook(p).record("sig", "why", ["x.py"])
        book2 = RegressionBook(p)
        assert book2.check(["x.py"]) == ["sig"]


# ------------------------------------------------------------------ v6

def _skills_with(skill):
    reg = SkillsRegistry()
    reg.register(skill)
    return reg


class TestMetaLoop:
    def test_bad_skill_proposed_for_retirement(self):
        from aeos.meta import MetaLoop
        skills = _skills_with(SkillSpec(
            name="lemon", purpose="p", trigger="t", procedure=["x"],
            usage_count=7, win_rate=0.2))
        meta = MetaLoop(skills, Governor())
        proposals = meta.analyze()
        assert any(p.kind == "retire_skill" and p.target == "lemon"
                   for p in proposals)

    def test_young_skill_not_condemned(self):
        from aeos.meta import MetaLoop
        skills = _skills_with(SkillSpec(
            name="young", purpose="p", trigger="t", procedure=["x"],
            usage_count=2, win_rate=0.0))          # bad but too young
        proposals = MetaLoop(skills, Governor()).analyze()
        assert not any(p.target == "young" for p in proposals)

    def test_threshold_tuning_stays_in_bounds(self):
        from aeos.meta import MetaLoop, SAFE_BOUNDS
        gov = Governor()
        gov.promotion_threshold = 0.99   # at ceiling -> no tighten proposal
        proposals = MetaLoop(_skills_with(SkillSpec(
            name="s", purpose="p", trigger="t", procedure=["x"])), gov).analyze()
        assert not any(p.kind == "tune_threshold" and (p.value or 0) > 0.99
                       for p in proposals)

    def test_apply_requires_sponsorship(self):
        from aeos.meta import MetaLoop
        skills = _skills_with(SkillSpec(
            name="lemon", purpose="p", trigger="t", procedure=["x"],
            usage_count=6, win_rate=0.1))
        meta = MetaLoop(skills, Governor())
        prop = meta.analyze()[0]
        ok, why = meta.apply(prop, token=None, gate=SponsorshipGate())
        assert not ok and "sponsorship required" in why

    def test_apply_with_token_retires(self):
        from aeos.meta import MetaLoop
        skills = _skills_with(SkillSpec(
            name="lemon", purpose="p", trigger="t", procedure=["x"],
            usage_count=6, win_rate=0.1))
        gate = SponsorshipGate()
        meta = MetaLoop(skills, Governor())
        prop = next(p for p in meta.analyze() if p.kind == "retire_skill")
        token = gate.issue(f"meta:retire_skill:lemon").token
        ok, why = meta.apply(prop, token=token, gate=gate)
        assert ok and skills.get("lemon") is None

    def test_out_of_bounds_threshold_refused_even_with_token(self):
        from aeos.meta import MetaLoop
        gov = Governor()
        meta = MetaLoop(_skills_with(SkillSpec(
            name="s", purpose="p", trigger="t", procedure=["x"])), gov)
        prop = next(p for p in meta.analyze() if p.kind == "tune_threshold")
        prop.value = 0.10                    # forge a wild value
        gate = SponsorshipGate()
        token = gate.issue(f"meta:tune_threshold:promotion_threshold").token
        ok, why = meta.apply(prop, token=token, gate=gate)
        assert not ok and "safe bounds" in why

    def test_adr_stub_written(self, tmp_path):
        from aeos.meta import MetaLoop
        skills = _skills_with(SkillSpec(
            name="lemon", purpose="p", trigger="t", procedure=["x"],
            usage_count=6, win_rate=0.1))
        meta = MetaLoop(skills, Governor())
        prop = meta.analyze()[0]
        path = meta.adr_stub(prop, tmp_path)
        assert path.exists() and "PROPOSED by meta-loop" in path.read_text()


# ------------------------------------------------------------------ v7

class TestFactory:
    def _factory(self, tmp_path, signatures=None):
        from aeos.catalog import Catalog
        from aeos.factory import CapabilityFactory
        from aeos.observability import EventLog
        skills = SkillsRegistry()
        skills.register(SkillSpec(
            name="verify-first", purpose="phase:evaluator:EXECUTE verify",
            trigger="t", procedure=["x"], usage_count=6, win_rate=0.9))
        discovery = CapabilityDiscovery(skills)
        for sig, n in (signatures or [("phase:evaluator:EXECUTE", 4)]):
            for _ in range(n):
                discovery.record_pattern(sig)
        return (CapabilityFactory(skills=skills, discovery=discovery,
                                  governor=Governor(log=EventLog()),
                                  gate=SponsorshipGate(),
                                  catalog=Catalog(tmp_path / "cat"),
                                  log=EventLog()),
                skills)

    def test_design_from_signature_is_contract_complete(self, tmp_path):
        from aeos.factory import design_agent
        spec = design_agent("phase:triage:WRITE")
        assert spec.validate() == []
        assert spec.writes == ["triage/*"]
        assert spec.name == "triage-specialist"

    def test_sandbox_validation_passes_good_design(self, tmp_path):
        factory, _ = self._factory(tmp_path)
        cand = factory.candidates()[0]
        verdict = factory.validate_in_sandbox(cand, tmp_path / "sb")
        assert verdict is Verdict.PASS

    def test_install_refused_without_sponsorship(self, tmp_path):
        factory, _ = self._factory(tmp_path)
        roster = {}
        cand = factory.candidates()[0]
        factory.validate_in_sandbox(cand, tmp_path / "sb")
        ok, why = factory.install(cand, roster, token=None)
        assert not ok and "sponsorship required" in why
        assert roster == {}

    def test_full_factory_run_installs_with_token(self, tmp_path):
        from aeos.sponsorship import SponsorshipGate
        factory, _ = self._factory(tmp_path)
        # reach into the factory's gate to issue a proper token
        token = SponsorshipGate().issue("x").token  # wrong-scope canary below
        roster = {}
        summary = factory.run(roster, tmp_path / "sb", token=None)
        assert summary["proposed"] and summary["installed"] == []

    def test_full_run_with_valid_token_installs(self, tmp_path):
        factory, _ = self._factory(tmp_path)
        gate = factory.gate
        s = gate.issue("factory:install:evaluator-specialist")
        roster = {}
        summary = factory.run(roster, tmp_path / "sb", token=s.token)
        assert summary["installed"], summary
        assert "evaluator-specialist" in roster
        # and the unit landed in the catalog
        assert any(u.name == "evaluator-specialist"
                   for u in factory.catalog.list_units())

    def test_failed_sandbox_never_installs(self, tmp_path):
        from aeos.factory import CapabilityFactory, design_agent
        from aeos.factory import FactoryCandidate
        factory, _ = self._factory(tmp_path)
        bad = FactoryCandidate(signature="phase:x:WRITE", count=5,
                               agent_name="broken")
        bad.design = design_agent("phase:x:WRITE")
        bad.design.success_criteria = []          # invalid contract on purpose
        verdict = factory.validate_in_sandbox(bad, tmp_path / "sb2")
        assert verdict is Verdict.FAIL
        ok, why = factory.install(bad, {}, token=None)
        assert not ok
