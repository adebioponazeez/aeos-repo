"""Governor tests: the safety kernel must behave exactly as specified."""

import pytest

from aeos.contracts import ActionClass, AutonomyLevel, Decision
from aeos.governor import Governor
from aeos.observability import EventLog


@pytest.fixture
def gov():
    return Governor(level=AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL, log=EventLog())


class TestMatrix:
    def test_read_allowed_from_l1(self, gov):
        gov.level = AutonomyLevel.L1_AI_ASSISTANCE
        assert gov.decide(ActionClass.READ).decision is Decision.ALLOW

    def test_write_checkpoints_at_l2(self, gov):
        assert gov.decide(ActionClass.WRITE).decision is Decision.CHECKPOINT

    def test_write_allowed_at_l3(self, gov):
        gov.level = AutonomyLevel.L3_CHECKPOINTED_AUTONOMY
        assert gov.decide(ActionClass.WRITE).decision is Decision.ALLOW

    def test_destructive_checkpoints_even_at_l6(self, gov):
        """High-impact classes checkpoint every single occurrence."""
        gov.level = AutonomyLevel.L6_SELF_IMPROVING_AUTONOMY
        assert gov.decide(ActionClass.DESTRUCTIVE).decision is Decision.CHECKPOINT

    def test_irreversible_denied_below_sponsorship(self, gov):
        gov.level = AutonomyLevel.L4_GUARDED_AUTONOMY
        assert gov.decide(ActionClass.IRREVERSIBLE).decision is Decision.DENY

    def test_explicit_approval_overrides_checkpoint(self, gov):
        d = gov.decide(ActionClass.WRITE, task_uid="t1")
        assert d.decision is Decision.CHECKPOINT
        gov.approve("t2")
        assert gov.decide(ActionClass.WRITE, task_uid="t2").decision is Decision.ALLOW

    def test_approval_is_one_shot(self, gov):
        gov.approve("t1")
        gov.decide(ActionClass.WRITE, task_uid="t1")
        assert gov.decide(ActionClass.WRITE, task_uid="t1").decision is Decision.CHECKPOINT


class TestFailClosed:
    def test_unknown_class_denies(self, gov):
        gov.policy.pop(ActionClass.NETWORK)
        assert gov.decide(ActionClass.NETWORK).decision is Decision.DENY


class TestReliability:
    def test_failures_demote(self, gov):
        gov.level = AutonomyLevel.L4_GUARDED_AUTONOMY
        for _ in range(6):
            gov.observe_outcome(False)
        assert gov.level.value < AutonomyLevel.L4_GUARDED_AUTONOMY.value

    def test_sustained_success_promotes(self, gov):
        gov.reliability = 0.97
        gov.level = AutonomyLevel.L3_CHECKPOINTED_AUTONOMY
        for _ in range(10):
            gov.observe_outcome(True)
        assert gov.level.value > AutonomyLevel.L3_CHECKPOINTED_AUTONOMY.value

    def test_decisions_are_logged(self, gov):
        log = EventLog()
        gov.log = log
        gov.decide(ActionClass.WRITE)
        assert log.events("governor.checkpoint")
