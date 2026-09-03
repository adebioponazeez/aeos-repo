"""Typed contracts for every moving part of the OS.

Law of the codebase (inherited from SSSF, hardened here):
    EVERY agent boundary is a typed envelope. Free-form text never
    crosses a phase boundary as "the result". Agents produce claims;
    the harness owns verification.

All types are stdlib dataclasses. Zero runtime dependencies by design
(ADR-002): the OS must be auditable line-by-line, which is impossible
when the trust boundary depends on a dependency tree.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------- statuses

class Verdict(str, Enum):
    """Evaluation verdicts. 'the agent says it works' is NOT in this set."""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"


class TaskState(str, Enum):
    PENDING = "PENDING"
    READY = "READY"          # dependencies satisfied, awaiting a worker
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"      # waiting on a checkpoint / approval
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"      # prerequisite failed; cascade stopped safely
    ESCALATED = "ESCALATED"  # sent to a human by the autonomy governor


# ---------------------------------------------------------------- security

class ActionClass(str, Enum):
    """Every meaningful action is classified before it runs (spec §19)."""
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    DEPLOY = "DEPLOY"
    FINANCIAL = "FINANCIAL"
    DESTRUCTIVE = "DESTRUCTIVE"
    CREDENTIAL = "CREDENTIAL"
    IRREVERSIBLE = "IRREVERSIBLE"


# Autonomy ladder (spec §25). Autonomy is earned with evidence, never assumed.
class AutonomyLevel(int, Enum):
    L0_HUMAN_ONLY = 0
    L1_AI_ASSISTANCE = 1
    L2_AI_EXECUTION_WITH_APPROVAL = 2
    L3_CHECKPOINTED_AUTONOMY = 3
    L4_GUARDED_AUTONOMY = 4
    L5_CONTINUOUS_AUTONOMY = 5
    L6_SELF_IMPROVING_AUTONOMY = 6
    L7_CAPABILITY_DISCOVERY = 7


# The governor's only three answers. When uncertain: FAIL CLOSED.
class Decision(str, Enum):
    ALLOW = "ALLOW"
    CHECKPOINT = "CHECKPOINT"   # proceed only after human approval
    DENY = "DENY"


# ---------------------------------------------------------------- context

class ContextTier(str, Enum):
    """Context classification (spec §9). More context is NOT better."""
    ESSENTIAL = "ESSENTIAL"
    USEFUL = "USEFUL"
    OPTIONAL = "OPTIONAL"
    IRRELEVANT = "IRRELEVANT"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class MemoryClass(str, Enum):
    WORKING = "WORKING"           # this run only, volatile
    TASK = "TASK"                 # scoped to one objective
    EPISODIC = "EPISODIC"         # what happened, when, to whom
    SEMANTIC = "SEMANTIC"         # distilled facts with confidence
    PROCEDURAL = "PROCEDURAL"     # how we do things here (skills)
    ORGANIZATIONAL = "ORGANIZATIONAL"  # decisions, ADRs, lessons


# ---------------------------------------------------------------- envelopes

@dataclass
class Evidence:
    """One mechanically checkable fact supporting a claim."""
    kind: str                    # e.g. "test_run", "file_exists", "gate"
    detail: str
    verdict: Verdict = Verdict.UNVERIFIED


@dataclass
class Envelope:
    """The ONLY thing an agent may return across a phase boundary.

    `claims` are untrusted assertions. `evidence` is what the harness
    checks. An envelope whose claims outrun its evidence fails gates.
    """
    agent: str
    objective: str
    claims: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)   # file paths produced
    changed_files: list[str] = field(default_factory=list)
    notes: str = ""
    uid: str = field(default_factory=lambda: _uid("env"))
    created_at: float = field(default_factory=time.time)

    def add_evidence(self, kind: str, detail: str,
                     verdict: Verdict = Verdict.PASS) -> "Envelope":
        self.evidence.append(Evidence(kind, detail, verdict))
        return self

    # ---- v8: envelopes cross process/network boundaries as data ----

    def to_dict(self) -> dict:
        return {
            "agent": self.agent, "objective": self.objective,
            "claims": list(self.claims),
            "evidence": [{"kind": e.kind, "detail": e.detail,
                          "verdict": e.verdict.value} for e in self.evidence],
            "artifacts": list(self.artifacts),
            "changed_files": list(self.changed_files),
            "notes": self.notes, "uid": self.uid,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Envelope":
        env = cls(agent=d["agent"], objective=d["objective"],
                  claims=list(d.get("claims", [])),
                  artifacts=list(d.get("artifacts", [])),
                  changed_files=list(d.get("changed_files", [])),
                  notes=d.get("notes", ""), uid=d.get("uid", _uid("env")),
                  created_at=float(d.get("created_at", time.time())))
        for e in d.get("evidence", []):
            env.evidence.append(Evidence(e["kind"], e["detail"],
                                         Verdict(e.get("verdict", "UNVERIFIED"))))
        return env


# ---------------------------------------------------------------- agents

@dataclass
class AgentSpec:
    """A specialized agent is a CONTRACT, not a persona (spec §11).

    Every field below is mandatory on purpose: an agent without success
    criteria, evaluation criteria and escalation conditions is a prompt
    with delusions of architecture.
    """
    name: str
    mission: str
    inputs: list[str]
    outputs: list[str]
    tools: list[str]
    constraints: list[str]
    success_criteria: list[str]
    evaluation_criteria: list[str]
    escalation_conditions: list[str]
    termination_conditions: list[str]
    writes: list[str] = field(default_factory=list)   # write boundary (glob patterns)
    action_classes: list[ActionClass] = field(default_factory=lambda: [ActionClass.READ])
    model_hint: str = "default"     # routed, never hardcoded (spec §26)
    uid: str = field(default_factory=lambda: _uid("agent"))

    def validate(self) -> list[str]:
        problems: list[str] = []
        required = [("mission", self.mission), ("name", self.name)]
        for field_name, value in required:
            if not value.strip():
                problems.append(f"{field_name} is empty")
        if not self.success_criteria:
            problems.append("no success criteria — agent cannot be evaluated")
        if not self.escalation_conditions:
            problems.append("no escalation conditions — agent cannot hand back control")
        if ActionClass.WRITE in self.action_classes and not self.writes:
            problems.append("WRITE class without a writes: boundary")
        return problems


# ---------------------------------------------------------------- tasks

@dataclass
class TaskSpec:
    """One node in an execution graph produced by the orchestrator."""
    name: str
    description: str               # must state WHY, not restate the name (SSSF rule 7)
    agent: str                     # agent name from the registry
    depends_on: list[str] = field(default_factory=list)
    action_class: ActionClass = ActionClass.READ
    envelope: Envelope | None = None
    state: TaskState = TaskState.PENDING
    attempts: int = 0
    max_attempts: int = 2          # bounded retries: never loop blindly (spec §14)
    uid: str = field(default_factory=lambda: _uid("task"))
    started_at: float | None = None
    ended_at: float | None = None

    # ---- v2.0: durable runtime support (state survives the process) ----

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "agent": self.agent, "depends_on": list(self.depends_on),
            "action_class": self.action_class.value,
            "state": self.state.value, "attempts": self.attempts,
            "max_attempts": self.max_attempts, "uid": self.uid,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskSpec":
        return cls(name=d["name"], description=d["description"],
                   agent=d["agent"], depends_on=list(d.get("depends_on", [])),
                   action_class=ActionClass(d.get("action_class", "READ")),
                   state=TaskState(d.get("state", "PENDING")),
                   attempts=int(d.get("attempts", 0)),
                   max_attempts=int(d.get("max_attempts", 2)),
                   uid=d.get("uid", _uid("task")))


@dataclass
class SkillSpec:
    """A reusable capability (spec §12). Promotion from task -> skill is
    an EVIDENCE decision made by the learning loop, never a vibe."""
    name: str
    purpose: str
    trigger: str
    procedure: list[str]
    version: str = "0.1.0"
    dependencies: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    success_evidence: list[str] = field(default_factory=list)
    origin: str = "hand-written"    # or "promoted:<task uid>"
    usage_count: int = 0
    win_rate: float = 0.0          # validated wins / validated uses
    uid: str = field(default_factory=lambda: _uid("skill"))
