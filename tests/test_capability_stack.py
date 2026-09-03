"""v2.0 tool layer + v3.0 catalog/sponsorship + v4.0 economics tests."""

import time
import pytest
from pathlib import Path

from aeos.contracts import ActionClass, AutonomyLevel, Decision
from aeos.governor import Governor
from aeos.tools import ToolRegistry, install_default_tools


class TestToolLayer:
    def test_unknown_tool_fails_closed(self):
        gov = Governor(level=AutonomyLevel.L5_CONTINUOUS_AUTONOMY)
        reg = ToolRegistry(gov)
        out = reg.call("ghost_tool", {})
        assert out.is_error and "unknown tool" in out.error

    def test_network_tool_checkpoints_at_l2(self):
        gov = Governor(level=AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL)
        reg = ToolRegistry(gov)
        install_default_tools(reg)
        out = reg.call("web_search", {"query": "mcp spec"})
        # L2: NETWORK checkpoints; read/network class resolves in-process
        assert not out.is_error
        assert out.untrusted is True

    def test_results_are_always_untrusted(self):
        gov = Governor(level=AutonomyLevel.L5_CONTINUOUS_AUTONOMY)
        reg = ToolRegistry(gov)
        install_default_tools(reg)
        out = reg.call("web_search", {"query": "x"})
        assert out.untrusted is True
        rpc = out.to_rpc()
        assert rpc["untrusted"] is True and "result" in rpc

    def test_tool_exception_becomes_structured_error(self):
        gov = Governor(level=AutonomyLevel.L5_CONTINUOUS_AUTONOMY)
        reg = ToolRegistry(gov)
        from aeos.tools import ToolSpec
        reg.register(ToolSpec(
            name="bomb", description="always fails", input_schema={},
            handler=lambda p: 1 / 0, action_class=ActionClass.READ))
        out = reg.call("bomb", {})
        assert out.is_error and "ZeroDivisionError" in out.error
        assert out.to_rpc()["error"]["code"] == -32000

    def test_write_class_tool_escalates_at_checkpoint(self):
        gov = Governor(level=AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL)
        reg = ToolRegistry(gov)
        from aeos.tools import ToolSpec
        reg.register(ToolSpec(
            name="mutate", description="writes", input_schema={},
            handler=lambda p: {"ok": True}, action_class=ActionClass.WRITE))
        out = reg.call("mutate", {})
        assert out.is_error and "checkpoint" in out.error


# ------------------------------------------------------------- v3 catalog

class TestCatalog:
    def _skill(self, name="deploy", version="1.2.0"):
        from aeos.contracts import SkillSpec
        return SkillSpec(name=name, purpose="ship it", trigger="deploy",
                         procedure=["step"], version=version)

    def test_package_publish_install_roundtrip(self, tmp_path):
        from aeos.catalog import Catalog, package_skill
        cat = Catalog(tmp_path / "cat")
        unit = package_skill(self._skill())
        cat.publish(unit)
        installed = cat.install("skill", "deploy", "1.2.0", tmp_path / "target")
        assert installed.verify()
        assert (tmp_path / "target/.aeos/installed/skill.deploy.json").exists()

    def test_tampered_unit_refuses_install(self, tmp_path):
        from aeos.catalog import Catalog, package_skill
        cat = Catalog(tmp_path / "cat")
        unit = package_skill(self._skill())
        cat.publish(unit)
        target = next(tmp_path.joinpath("cat").glob("*.json"))
        import json as _json
        d = _json.loads(target.read_text())
        d["payload"]["purpose"] = "ship it (hacked)"   # tamper ON DISK
        target.write_text(_json.dumps(d))
        with pytest.raises(ValueError, match="tampered"):
            cat.install("skill", "deploy", "1.2.0", tmp_path / "t")

    def test_self_inconsistent_unit_refuses_publish(self, tmp_path):
        from aeos.catalog import Catalog, package_skill
        cat = Catalog(tmp_path / "cat")
        unit = package_skill(self._skill())
        unit.sha256 = "0" * 64   # forged hash
        with pytest.raises(ValueError, match="own hash"):
            cat.publish(unit)


class TestSponsorship:
    def test_issue_and_spend(self):
        from aeos.sponsorship import SponsorshipGate
        gate = SponsorshipGate()
        s = gate.issue("factory:install:builder-specialist")
        assert gate.authorize(s.token, "factory:install:builder-specialist")

    def test_spend_is_one_shot(self):
        from aeos.sponsorship import SponsorshipGate
        gate = SponsorshipGate()
        s = gate.issue("scope-a")
        assert gate.authorize(s.token, "scope-a")
        assert not gate.authorize(s.token, "scope-a")

    def test_scope_mismatch_refused(self):
        from aeos.sponsorship import SponsorshipGate
        gate = SponsorshipGate()
        s = gate.issue("scope-a")
        assert not gate.authorize(s.token, "scope-b")

    def test_expiry_refused(self):
        from aeos.sponsorship import SponsorshipGate
        gate = SponsorshipGate()
        s = gate.issue("scope", ttl_s=-1)   # already expired
        assert not gate.authorize(s.token, "scope")

    def test_no_token_refused(self):
        from aeos.sponsorship import SponsorshipGate
        assert not SponsorshipGate().authorize(None, "anything")


# ------------------------------------------------------------ v4 economics

class TestEconomics:
    def test_cost_math(self):
        from aeos.economics import CostTracker
        t = CostTracker()
        t.record("reasoning", tokens_in=1000, tokens_out=1000, task="arch")
        assert t.total_cost() == pytest.approx(3.0 + 15.0)

    def test_echo_is_free(self):
        from aeos.economics import CostTracker
        t = CostTracker()
        t.record("echo-1", 1_000_000, 1_000_000)
        assert t.total_cost() == 0.0

    def test_budget_escalates_then_denies(self):
        from aeos.economics import Budget, CostTracker
        t = CostTracker()
        t.record("default", 1_100_000, 1_100_000)  # 0.15*1100 + 0.6*1100 = 825
        b = Budget(max_cost=1000)
        d1, _ = b.check(t)
        assert d1 is Decision.CHECKPOINT           # within 20% of budget
        t.record("default", 1_100_000, 1_100_000)  # now 1650 > 1000
        d2, why = b.check(t)
        assert d2 is Decision.DENY and "exhausted" in why

    def test_leverage_ratio(self):
        from aeos.economics import leverage_ratio
        assert leverage_ratio(10, 0) == 10.0       # fully hands-off
        assert leverage_ratio(10, 2) == 5.0
        assert leverage_ratio(0, 0) is None        # nothing happened

    def test_interventions_counted_from_events(self):
        from aeos.economics import interventions_from_events
        from aeos.observability import EventLog
        log = EventLog()
        log.emit("governor.checkpoint", x=1)
        log.emit("governor.checkpoint", x=2)
        log.emit("task.escalated", task="t")
        log.emit("task.succeeded", task="t")
        cp, esc = interventions_from_events(log.events())
        assert (cp, esc) == (2, 1)


class TestTenantGovernance:
    def test_tenant_override_applies(self):
        gov = Governor(level=AutonomyLevel.L5_CONTINUOUS_AUTONOMY)
        gov.set_tenant_policy("acme", ActionClass.DEPLOY,
                              (AutonomyLevel.L7_CAPABILITY_DISCOVERY, False))
        assert gov.decide(ActionClass.DEPLOY, tenant="acme").decision \
            is Decision.DENY
        assert gov.decide(ActionClass.DEPLOY).decision is Decision.ALLOW

    def test_tenant_matrix_untouched_globally(self):
        gov = Governor(level=AutonomyLevel.L4_GUARDED_AUTONOMY)
        gov.set_tenant_policy("strict", ActionClass.WRITE,
                              (AutonomyLevel.L7_CAPABILITY_DISCOVERY, True))
        assert gov.decide(ActionClass.WRITE).decision is Decision.ALLOW
        assert gov.decide(ActionClass.WRITE, tenant="strict").decision \
            is Decision.DENY   # strict tenant demands L7; we are at L4
