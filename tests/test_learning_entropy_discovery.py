"""Entropy, learning, discovery: the loop that makes the OS compound."""

import pytest
from pathlib import Path

from aeos.contracts import MemoryClass, SkillSpec, TaskState
from aeos.discovery import CapabilityDiscovery
from aeos.entropy import EntropyScanner, EntropyAction
from aeos.learning import LearningLoop
from aeos.memory import MemoryRecord, MemoryStore
from aeos.skills import SkillsRegistry


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path / "m.jsonl")


class TestLearningLoop:
    def test_failure_never_becomes_canonical(self, store):
        skills = SkillsRegistry()
        loop = LearningLoop(store, skills)
        lesson = loop.observe("deploy", TaskState.FAILED, "ran with wrong env")
        assert loop.validate_and_promote(lesson, evidence=["would-be evidence"]) is False
        with pytest.raises(ValueError, match="folklore"):
            loop.promote_to_skill(lesson, "deploy-skill", evidence=["e"])

    def test_success_without_evidence_not_promoted(self, store):
        loop = LearningLoop(store, SkillsRegistry())
        lesson = loop.observe("build", TaskState.SUCCEEDED, "clean build")
        assert loop.validate_and_promote(lesson, evidence=[]) is False

    def test_validated_success_promotes_to_skill(self, store):
        skills = SkillsRegistry()
        loop = LearningLoop(store, skills)
        lesson = loop.observe("test", TaskState.SUCCEEDED, "pytest first, then lint")
        assert loop.validate_and_promote(lesson, evidence=["gate:PASS", "exit 0"])
        spec = loop.promote_to_skill(lesson, "verify-first", evidence=["gate:PASS"])
        assert spec.origin == "promoted:test"
        assert skills.get("verify-first").win_rate == 1.0
        assert store.read("proven::test").mclass is MemoryClass.PROCEDURAL

    def test_every_outcome_is_remembered_episodically(self, store):
        loop = LearningLoop(store, SkillsRegistry())
        loop.observe("a", TaskState.FAILED, "timeout")
        assert store.search("timeout", mclass=MemoryClass.EPISODIC)


class TestDiscovery:
    def test_three_repetitions_trigger_a_proposal(self):
        d = CapabilityDiscovery(SkillsRegistry())
        for _ in range(3):
            d.record_pattern("phase:builder:WRITE")
        assert any(p["proposal"] == "task -> skill"
                   for p in d.proposals())

    def test_two_repetitions_do_not(self):
        d = CapabilityDiscovery(SkillsRegistry())
        for _ in range(2):
            d.record_pattern("phase:builder:WRITE")
        assert d.proposals() == []

    def test_proven_skill_proposes_agent_promotion(self):
        skills = SkillsRegistry()
        spec = SkillSpec(name="triage", purpose="phase:triage:WRITE issues fast",
                         trigger="t", procedure=["x"])
        skills.register(spec)
        for won in [True] * 5:
            skills.record_use("triage", won=won)
        d = CapabilityDiscovery(skills)
        d.record_pattern("phase:triage:WRITE")
        d.record_pattern("phase:triage:WRITE")
        d.record_pattern("phase:triage:WRITE")
        assert any(p["proposal"] == "skill -> agent" for p in d.proposals())


class TestEntropy:
    def test_memory_pollution_detected(self, tmp_path, store):
        store.write(MemoryRecord(key="weak", value="v", mclass=MemoryClass.SEMANTIC,
                                 source="s", confidence=0.2, evidence=["one point"]))
        scanner = EntropyScanner(SkillsRegistry(), store, tmp_path)
        findings = scanner.scan()
        assert any(f.kind == "memory_pollution" and f.action is EntropyAction.REPAIR
                   for f in findings)

    def test_duplicate_skills_detected(self, tmp_path, store):
        skills = SkillsRegistry()
        skills.register(SkillSpec(name="a", purpose="summarize research documents",
                                  trigger="t", procedure=["x"]))
        skills.register(SkillSpec(name="b", purpose="summarize research documents",
                                  trigger="t", procedure=["x"]))
        findings = EntropyScanner(skills, store, tmp_path).scan()
        assert any(f.kind == "duplicate_skills" for f in findings)
