"""Contract tests: every agent is a contract, every envelope is typed."""

import pytest

from aeos.contracts import (ActionClass, AgentSpec, Envelope, Evidence,
                            TaskSpec, Verdict, _uid)


def _good_agent(**over):
    base = dict(
        name="builder", mission="Implement modules to spec",
        inputs=["spec"], outputs=["code"], tools=["fs.write"],
        constraints=["stay in boundary"],
        success_criteria=["tests pass"], evaluation_criteria=["gates pass"],
        escalation_conditions=["3 failures"], termination_conditions=["done"],
    )
    base.update(over)
    return AgentSpec(**base)


class TestAgentSpec:
    def test_valid_agent_has_no_problems(self):
        assert _good_agent().validate() == []

    def test_missing_success_criteria_is_invalid(self):
        agent = _good_agent(success_criteria=[])
        assert "no success criteria — agent cannot be evaluated" in agent.validate()

    def test_missing_escalation_is_invalid(self):
        agent = _good_agent(escalation_conditions=[])
        assert any("escalation" in p for p in agent.validate())

    def test_write_class_requires_boundary(self):
        agent = _good_agent(action_classes=[ActionClass.WRITE], writes=[])
        assert any("writes:" in p for p in agent.validate())


class TestEnvelope:
    def test_envelope_starts_with_no_claims_and_no_evidence(self):
        env = Envelope(agent="a", objective="o")
        assert env.claims == [] and env.evidence == []

    def test_uids_are_unique(self):
        assert _uid("x") != _uid("x")

    def test_verdict_vocabulary_is_closed(self):
        assert {v.value for v in Verdict} == {"PASS", "FAIL", "PARTIAL", "UNVERIFIED"}
