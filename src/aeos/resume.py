"""v17 Resume: AFK durability — checkpointed plans, idempotent restart.

An AFK agent that dies at task 3 of 5 and restarts from 0 was never
AFK. LangGraph sells durable execution; this is the stdlib version:
a plan checkpointed after EVERY task (atomic write), and a resume
that executes only what remains — side effects once, proven by the
call log.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PlanTask:
    id: str
    kind: str
    detail: str = ""


class ResumeNeeded(RuntimeError):
    """Raised mid-plan when a task fails; the checkpoint survives."""


class PlanCheckpoint:
    """Atomic JSON checkpoint: written tmp-then-rename after each task."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, plan_id: str, tasks: list, done: list) -> None:
        from .vault import durable_write
        durable_write(self.path, json.dumps(
            {"aeos_schema": 1,
             "plan_id": plan_id,
             "tasks": [{"id": t.id, "kind": t.kind, "detail": t.detail}
                       for t in tasks],
             "done": done}, sort_keys=True))

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        from .vault import STATE_SCHEMA, SchemaError
        data = json.loads(self.path.read_text(encoding="utf-8"))
        v = data.get("aeos_schema", 1)      # legacy: unversioned = 1
        if not isinstance(v, int) or v > STATE_SCHEMA:
            raise SchemaError(f"checkpoint schema {v!r} newer than this "
                              f"aeos understands; upgrade first")
        return data

    def state(self) -> dict:
        st = self.load() or {"plan_id": None, "tasks": [], "done": []}
        done = set(st["done"])
        return {"plan_id": st["plan_id"], "done": sorted(done),
                "pending": [t["id"] for t in st["tasks"]
                            if t["id"] not in done]}


def execute_plan(plan_id: str, tasks: list, execute, checkpoint: PlanCheckpoint,
                 fail_at: str | None = None) -> dict:
    """Run pending tasks, marking done atomically after each.

    `execute(task)` performs the side effect; the returned call log is
    the idempotency proof. Resume = call again with the same checkpoint.
    """
    state = checkpoint.state()
    done = set(state["done"]) if state["plan_id"] == plan_id else set()
    if state["plan_id"] != plan_id:
        checkpoint.save(plan_id, tasks, [])
    calls: list = []
    for task in tasks:
        if task.id in done:
            continue
        if fail_at == task.id:
            checkpoint.save(plan_id, tasks, sorted(done))
            raise ResumeNeeded(
                f"task '{task.id}' failed mid-plan; "
                f"{len(done)}/{len(tasks)} done, checkpoint durable")
        execute(task)
        calls.append(task.id)
        done.add(task.id)
        checkpoint.save(plan_id, tasks, sorted(done))
    return {"plan_id": plan_id, "executed": calls,
            "done": sorted(done), "total": len(tasks)}
