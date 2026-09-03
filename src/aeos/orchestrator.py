"""Orchestrator: dynamic execution graphs with dependency-ordered waves.

DISCOVER -> DECOMPOSE -> DEPENDENCIES -> PARALLEL WAVES -> ASSIGN ->
WORKSPACES -> EXECUTE -> SYNCHRONIZE -> EVALUATE -> REPAIR -> MERGE.

Independent tasks run concurrently; tasks whose outputs feed each other
are serialized by the graph. Conflicting WRITE tasks against the same
boundary are serialized by construction (same wave never contains two
writers to the same path glob) — the orchestrator enforces what the
agent promised, not the other way round (SSSF rule 9, generalized).
"""

from __future__ import annotations

import fnmatch
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .contracts import (ActionClass, AgentSpec, Envelope, TaskSpec, TaskState,
                        Verdict)
from .evaluation import Evaluator
from .governor import Governor
from .models import ModelAdapter
from .observability import EventLog


@dataclass
class RunReport:
    objective: str
    states: dict[str, TaskState] = field(default_factory=dict)
    verdicts: dict[str, Verdict] = field(default_factory=dict)
    duration_s: float = 0.0
    waves: int = 0
    repair_cycles: int = 0

    @property
    def accepted(self) -> bool:
        return all(s is TaskState.SUCCEEDED for s in self.states.values()) and bool(self.states)

    def summary_line(self) -> str:
        ok = sum(1 for s in self.states.values() if s is TaskState.SUCCEEDED)
        return (f"{ok}/{len(self.states)} tasks succeeded in {self.waves} waves, "
                f"{self.repair_cycles} repair cycle(s), {self.duration_s:.2f}s")


Handler = Callable[[TaskSpec, "Orchestrator"], Envelope]


class Orchestrator:
    def __init__(self, *, agents: dict[str, AgentSpec],
                 handlers: dict[str, Handler], model: ModelAdapter,
                 governor: Governor, evaluator: Evaluator,
                 log: EventLog, workspace: Path,
                 max_workers: int = 4) -> None:
        self.agents = agents
        self.handlers = handlers
        self.model = model
        self.governor = governor
        self.evaluator = evaluator
        self.log = log
        self.workspace = workspace
        self.max_workers = max_workers
        self.runs: list[RunReport] = []

    # ---------------------------------------------------------------- plan
    def validate_graph(self, tasks: list[TaskSpec]) -> list[str]:
        problems: list[str] = []
        names = {t.name for t in tasks}
        for t in tasks:
            if t.agent not in self.agents:
                problems.append(f"task '{t.name}' references unknown agent '{t.agent}'")
            for dep in t.depends_on:
                if dep not in names:
                    problems.append(f"task '{t.name}' depends on unknown task '{dep}'")
        problems.extend(_find_cycles(tasks))
        problems.extend(_find_write_conflicts(tasks, self.agents))
        return problems

    def waves(self, tasks: list[TaskSpec]) -> list[list[TaskSpec]]:
        """Group into dependency-ordered parallel waves (Kahn topological)."""
        by_name = {t.name: t for t in tasks}
        indeg = {t.name: len(t.depends_on) for t in tasks}
        dependents: dict[str, list[str]] = {t.name: [] for t in tasks}
        for t in tasks:
            for dep in t.depends_on:
                dependents[dep].append(t.name)
        frontier = sorted(n for n, d in indeg.items() if d == 0)
        out: list[list[TaskSpec]] = []
        while frontier:
            out.append([by_name[n] for n in frontier])
            nxt: list[str] = []
            for n in frontier:
                for m in dependents[n]:
                    indeg[m] -= 1
                    if indeg[m] == 0:
                        nxt.append(m)
            frontier = sorted(nxt)
        if sum(len(w) for w in out) != len(tasks):
            raise ValueError("cycle detected in task graph")
        return out

    # --------------------------------------------------------------- execute
    def run(self, objective: str, tasks: list[TaskSpec], *,
            repair: bool = True) -> RunReport:
        started = time.time()
        problems = self.validate_graph(tasks)
        if problems:
            raise ValueError("invalid graph: " + "; ".join(problems))
        report = RunReport(objective=objective)
        pending = {t.name: t for t in tasks}
        waves = self.waves(tasks)

        for wave_no, wave in enumerate(waves, 1):
            runnable: list[TaskSpec] = []
            for t in wave:
                if any(pending[d].state is TaskState.FAILED for d in t.depends_on):
                    t.state = TaskState.SKIPPED
                    self.log.emit("task.skipped", task=t.name, why="upstream failure")
                    pending[t.name] = t
                else:
                    runnable.append(t)
            if not runnable:
                continue
            report.waves += 1
            self.log.emit("wave.start", number=wave_no,
                          tasks=[t.name for t in runnable])
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {pool.submit(self._execute_task, t): t for t in runnable}
                for fut in futures:
                    fut.result()
            for t in runnable:
                pending[t.name] = t

        if repair:
            for name, t in list(pending.items()):
                if t.state is TaskState.FAILED and t.attempts < t.max_attempts:
                    self.log.emit("task.repair", task=name, attempt=t.attempts + 1)
                    report.repair_cycles += 1
                    t.state = TaskState.PENDING
                    self._execute_task(t)
                    pending[name] = t

        for t in pending.values():
            report.states[t.name] = t.state
        report.duration_s = time.time() - started
        self.runs.append(report)
        self.log.emit("run.finished", objective=objective,
                      accepted=report.accepted, summary=report.summary_line())
        return report

    def _execute_task(self, task: TaskSpec) -> None:
        task.started_at = time.time()
        task.attempts += 1
        decision = self.governor.decide(task.action_class, task.uid)
        if decision.decision.value == "DENY":
            task.state = TaskState.ESCALATED
            self.log.emit("task.escalated", task=task.name, why=decision.reason)
            task.ended_at = time.time()
            return
        if decision.decision.value == "CHECKPOINT":
            # Checkpoint semantics in-process: policy can auto-approve
            # read-only classes after queueing; destructive ones escalate.
            if task.action_class in (ActionClass.DESTRUCTIVE, ActionClass.CREDENTIAL,
                                     ActionClass.FINANCIAL, ActionClass.IRREVERSIBLE):
                task.state = TaskState.ESCALATED
                self.log.emit("task.escalated", task=task.name, why=decision.reason)
                task.ended_at = time.time()
                return
            self.governor.approve(task.uid)
            decision = self.governor.decide(task.action_class, task.uid)

        task.state = TaskState.RUNNING
        self.log.emit("task.started", task=task.name, agent=task.agent,
                      attempt=task.attempts)
        try:
            handler = self.handlers[task.agent]
            envelope = handler(task, self)
            if not isinstance(envelope, Envelope):
                raise TypeError(f"handler for '{task.agent}' returned "
                                f"{type(envelope).__name__}, not Envelope")
            task.envelope = envelope
            evaluation = self.evaluator.evaluate(envelope, self.workspace)
            self.log.emit("gate.checked", task=task.name,
                          verdict=evaluation.verdict.value,
                          checks=[(c.name, c.verdict.value) for c in evaluation.checks])
            if evaluation.verdict in (Verdict.FAIL, Verdict.UNVERIFIED):
                task.state = TaskState.FAILED
                self.log.emit("task.failed", task=task.name,
                              why=f"evaluation {evaluation.verdict.value}")
                self.governor.observe_outcome(False)
            else:
                task.state = TaskState.SUCCEEDED
                self.governor.observe_outcome(True)
                task.ended_at = time.time()
                self.log.emit("task.succeeded", task=task.name,
                              duration_s=round(task.ended_at - (task.started_at or task.ended_at), 4))
        except Exception as exc:
            task.state = TaskState.FAILED
            self.governor.observe_outcome(False)
            task.ended_at = time.time()
            self.log.emit("task.failed", task=task.name, why=f"exception: {exc}")


# ----------------------------------------------------------------- helpers

def _find_cycles(tasks: list[TaskSpec]) -> list[str]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t.name: WHITE for t in tasks}
    edges = {t.name: list(t.depends_on) for t in tasks}
    cycles: list[str] = []

    def visit(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        for dep in edges.get(node, []):
            if color.get(dep) == GRAY:
                cycles.append(" -> ".join(stack + [node, dep]))
            elif color.get(dep) == WHITE:
                visit(dep, stack + [node])
        color[node] = BLACK

    for t in tasks:
        if color[t.name] == WHITE:
            visit(t.name, [])
    return [f"cycle: {c}" for c in cycles]


def _find_write_conflicts(tasks: list[TaskSpec],
                          agents: dict[str, AgentSpec]) -> list[str]:
    """Two WRITE tasks whose agents' write boundaries overlap must be
    explicitly ordered (one depends on the other) or the graph is invalid.
    Unordered overlapping writers are how parallel agents corrupt state."""
    problems: list[str] = []
    writers = [t for t in tasks if t.action_class is ActionClass.WRITE]
    for i, a in enumerate(writers):
        for b in writers[i + 1:]:
            if b.name in a.depends_on or a.name in b.depends_on:
                continue
            bounds_a = agents[a.agent].writes if a.agent in agents else []
            bounds_b = agents[b.agent].writes if b.agent in agents else []
            if _glob_overlap(bounds_a, bounds_b):
                problems.append(
                    f"unordered parallel writers may collide: '{a.name}' and "
                    f"'{b.name}' both write overlapping boundaries "
                    f"{bounds_a} vs {bounds_b} — add an explicit dependency")
    return problems


def _glob_overlap(patterns_a: list[str], patterns_b: list[str]) -> bool:
    """Conservative write-collision check: do two glob sets *may* overlap?

    We reduce each glob to its fixed prefix (everything before the first
    wildcard). Two globs can only match a common path if one fixed
    prefix is a path-prefix of the other. This can over-report (safe,
    fail-closed) but never under-report on real collisions.
    """
    def prefix(p: str) -> str:
        return p.split("*")[0].split("?")[0].rstrip("/")

    for a in patterns_a:
        pa = prefix(a)
        for b in patterns_b:
            pb = prefix(b)
            if not pa or not pb:
                return True  # a pattern rooted at "" matches everything
            if pa.startswith(pb + "/") or pb.startswith(pa + "/") or pa == pb:
                return True
    return False
