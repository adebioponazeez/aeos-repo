"""v2.0 — Durable runtime: runs persist, die, and resume.

The event log was already replayable; now the RUN is resumable. After
every task transition the orchestrader flushes a minimal state file;
`resume()` rebuilds the graph, keeps completed work on disk (never
re-runs a SUCCEEDED task), and continues the remainder. Crash-safety
for agent fleets is not magic — it is a JSON file written at the
right moments.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .contracts import TaskSpec, TaskState


@dataclass
class RunState:
    run_id: str
    objective: str
    tasks: list[TaskSpec]
    accepted: bool | None = None
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id, "objective": self.objective,
            "tasks": [t.to_dict() for t in self.tasks],
            "accepted": self.accepted,
            "updated_at": self.updated_at or time.time(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunState":
        return cls(run_id=d["run_id"], objective=d["objective"],
                   tasks=[TaskSpec.from_dict(t) for t in d["tasks"]],
                   accepted=d.get("accepted"),
                   updated_at=d.get("updated_at", 0.0))


class RunStore:
    """One directory per run under `.aeos/runs/`; atomic-ish writes
    (write-then-rename) so a crash mid-write never corrupts state."""

    def __init__(self, base: Path) -> None:
        self.base = base / ".aeos" / "runs"
        self.base.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        return self.base / run_id / "state.json"

    def save(self, state: RunState) -> Path:
        state.updated_at = time.time()
        target = self.path_for(state.run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(target)
        return target

    def load(self, run_id: str) -> RunState | None:
        p = self.path_for(run_id)
        if not p.exists():
            return None
        return RunState.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def unfinished(self) -> list[str]:
        out = []
        for d in self.base.iterdir():
            if not d.is_dir():
                continue
            state = self.load(d.name)
            if state and state.accepted is None:
                out.append(d.name)
        return out


def attach_persistence(orchestrator, run_id: str, store: RunStore,
                       objective: str, tasks: list[TaskSpec]) -> None:
    """Hook a live orchestrator: persist after each task transition.

    Implemented as a thin wrapper around the orchestrator's
    _execute_task so the core loop stays untouched (ADR-002 spirit:
    features compose, the kernel stays readable)."""
    inner = orchestrator._execute_task

    def persisted(task: TaskSpec) -> None:
        inner(task)
        state = RunState(run_id=run_id, objective=objective, tasks=tasks,
                         accepted=None)
        store.save(state)

    orchestrator._execute_task = persisted


def resume_plan(state: RunState) -> tuple[list[str], list[str]]:
    """Which tasks to keep (already terminal-good) vs re-run."""
    keep, rerun = [], []
    for t in state.tasks:
        if t.state is TaskState.SUCCEEDED:
            keep.append(t.name)
        else:
            rerun.append(t.name)
    return keep, rerun
