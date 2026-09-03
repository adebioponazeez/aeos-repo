"""The Autonomy Governor: autonomy is earned, bounded, and revocable.

This is the safety kernel of the OS (spec §19 + §25). Every action is
classified; every class maps through the current autonomy level to
exactly one of ALLOW / CHECKPOINT / DENY. When the decision inputs are
insufficient, the governor fails CLOSED: it checkpoints, never assumes.

The matrix below is the whole security posture in one table, and the
table is data — auditable, testable, overridable only explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .contracts import ActionClass, AutonomyLevel, Decision
from .observability import EventLog


# class -> (min level to ALLOW unsupervised, is it ever DENY-by-default?)
_DEFAULT_POLICY: dict[ActionClass, tuple[AutonomyLevel, bool]] = {
    ActionClass.READ:        (AutonomyLevel.L1_AI_ASSISTANCE, False),
    ActionClass.WRITE:       (AutonomyLevel.L3_CHECKPOINTED_AUTONOMY, False),
    ActionClass.EXECUTE:     (AutonomyLevel.L3_CHECKPOINTED_AUTONOMY, False),
    ActionClass.NETWORK:     (AutonomyLevel.L4_GUARDED_AUTONOMY, False),
    ActionClass.DEPLOY:      (AutonomyLevel.L4_GUARDED_AUTONOMY, False),
    ActionClass.FINANCIAL:   (AutonomyLevel.L5_CONTINUOUS_AUTONOMY, True),
    ActionClass.DESTRUCTIVE: (AutonomyLevel.L6_SELF_IMPROVING_AUTONOMY, True),
    ActionClass.CREDENTIAL:  (AutonomyLevel.L6_SELF_IMPROVING_AUTONOMY, True),
    ActionClass.IRREVERSIBLE: (AutonomyLevel.L7_CAPABILITY_DISCOVERY, True),
}


@dataclass
class GovernorDecision:
    decision: Decision
    action_class: ActionClass
    level: AutonomyLevel
    reason: str
    approvals_used: list[str] = field(default_factory=list)


@dataclass
class Governor:
    """Stateful authority. Holds the current level and its evidence trail."""

    level: AutonomyLevel = AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL
    policy: dict[ActionClass, tuple[AutonomyLevel, bool]] = field(
        default_factory=lambda: dict(_DEFAULT_POLICY))
    log: EventLog | None = None
    reliability: float = 1.0          # rolling success rate driving the level
    tenant_policies: dict[str, dict[ActionClass, tuple[AutonomyLevel, bool]]] = field(
        default_factory=dict)        # v3.0: per-tenant policy scopes
    _approved: set[str] = field(default_factory=set)   # (task uid) one-shot approvals

    def set_tenant_policy(self, tenant: str, action_class: ActionClass,
                          rule: tuple[AutonomyLevel, bool]) -> None:
        """Multi-tenancy: a tenant may tighten (or, deliberately, loosen)
        specific classes. Overrides never touch the global matrix."""
        self.tenant_policies.setdefault(tenant, {})[action_class] = rule

    # ---- the core decision function -------------------------------------
    def decide(self, action_class: ActionClass, task_uid: str = "",
               *, approved: bool = False, tenant: str | None = None) -> GovernorDecision:
        policy = (self.tenant_policies.get(tenant, {}).get(action_class)
                  if tenant else None)
        if policy is not None:
            min_level, deny_by_default = policy
            reason = (f"{action_class.value} under tenant '{tenant}': "
                      f"requires >= {min_level.name}; current={self.level.name}")
        else:
            min_level, deny_by_default = self.policy.get(
                action_class, (AutonomyLevel.L7_CAPABILITY_DISCOVERY, True))
            reason = (f"{action_class.value} requires >= {min_level.name}; "
                      f"current={self.level.name}")

        if policy is None and action_class not in self.policy:
            # Unknown action class: fail closed, always (spec §19).
            return self._record(GovernorDecision(
                Decision.DENY, action_class, self.level,
                "unclassified action — fail closed"))

        if approved or task_uid in self._approved:
            self._approved.discard(task_uid)
            return self._record(GovernorDecision(
                Decision.ALLOW, action_class, self.level,
                "explicit human approval on record"))

        if self.level.value >= min_level.value and not deny_by_default:
            return self._record(GovernorDecision(
                Decision.ALLOW, action_class, self.level, reason))

        if self.level.value >= min_level.value and deny_by_default:
            # Allowed at this level in principle, but high-impact:
            # every single occurrence checkpoints.
            return self._record(GovernorDecision(
                Decision.CHECKPOINT, action_class, self.level,
                reason + "; high-impact class checkpoints every time"))

        if min_level.value <= AutonomyLevel.L4_GUARDED_AUTONOMY.value:
            return self._record(GovernorDecision(
                Decision.CHECKPOINT, action_class, self.level, reason))
        return self._record(GovernorDecision(
            Decision.DENY, action_class, self.level,
            reason + "; beyond guarded autonomy requires human sponsorship"))

    def approve(self, task_uid: str) -> None:
        self._approved.add(task_uid)

    # ---- level management: earned with evidence, lost on failure --------
    def observe_outcome(self, success: bool) -> float:
        """Exponential moving average of reliability; drives the level."""
        k = 0.3
        self.reliability = round((1 - k) * self.reliability + k * float(success), 4)
        target = self._level_for_reliability()
        if target.value > self.level.value and self.reliability >= 0.95:
            self._set_level(target, f"reliability {self.reliability} supports promotion")
        elif target.value < self.level.value:
            self._set_level(target, f"reliability {self.reliability} forces demotion")
        return self.reliability

    def _level_for_reliability(self) -> AutonomyLevel:
        if self.reliability >= 0.995:
            return AutonomyLevel.L5_CONTINUOUS_AUTONOMY
        if self.reliability >= 0.98:
            return AutonomyLevel.L4_GUARDED_AUTONOMY
        if self.reliability >= 0.95:
            return AutonomyLevel.L3_CHECKPOINTED_AUTONOMY
        return AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL

    def _set_level(self, new_level: AutonomyLevel, why: str) -> None:
        if new_level is not self.level:
            if self.log:
                self.log.emit("governor.level", old=self.level.name,
                              new=new_level.name, why=why)
            self.level = new_level

    def _record(self, d: GovernorDecision) -> GovernorDecision:
        if self.log:
            self.log.emit(f"governor.{d.decision.value.lower()}",
                          action_class=d.action_class.value, reason=d.reason)
        return d
