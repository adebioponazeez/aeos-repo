"""v25 Colony: the graph is explicit — nodes, requires, conditions.

CrewAI has crews, LangGraph has graphs; AEOS has the colony: a
declarative DAG of nodes (fn(ctx) -> value) with `requires` edges and
optional `condition` gates. Waves execute in dependency order; every
transition is an event on the bus; failures block dependents (fail
closed); cycles and unrunnable nodes end as BLOCKED — the colony
never hangs. ctx carries every node's output: the graph is the plan,
the context is the ledger of its execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .fleet import EventBus


@dataclass
class Node:
    name: str
    fn: Callable | None = None
    requires: tuple = ()
    condition: Callable | None = None      # gate: run only if truthy


@dataclass
class ColonyReport:
    executed: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    failed: dict = field(default_factory=dict)
    blocked: list = field(default_factory=list)
    waves: int = 0

    @property
    def ok(self) -> bool:
        return not (self.failed or self.blocked or self.skipped)

    def render(self) -> str:
        head = (f"COLONY — {len(self.executed)} ran in {self.waves} "
                f"wave(s) — {'OK' if self.ok else 'DEGRADED'}")
        lines = [head]
        if self.executed:
            lines.append(f"  order: {' -> '.join(self.executed)}")
        if self.skipped:
            lines.append(f"  skipped (condition): {self.skipped}")
        if self.failed:
            lines.append(f"  failed: {self.failed}")
        if self.blocked:
            lines.append(f"  blocked (fail closed): {self.blocked}")
        return "\n".join(lines)


class Colony:
    def __init__(self, bus: EventBus | None = None):
        self.bus = bus
        self.nodes: dict = {}

    def add(self, node: Node) -> "Colony":
        if node.name in self.nodes:
            raise ValueError(f"duplicate node: {node.name}")
        self.nodes[node.name] = node
        return self

    def _emit(self, kind: str, agent: str, detail: str = "") -> None:
        if self.bus is not None:
            self.bus.publish(kind, agent, detail)

    def run(self, ctx: dict | None = None,
            max_waves: int | None = None) -> ColonyReport:
        ctx = dict(ctx or {})
        status = {name: "pending" for name in self.nodes}
        rep = ColonyReport()
        # the cap is belt-and-suspenders (the no-progress break catches
        # cycles in one idle wave); it must allow legitimate depth:
        # a 60-node chain is a legal graph that needs 60 waves.
        max_waves = max_waves or (len(self.nodes) + 10)
        for _ in range(max_waves):
            runnable, gate_off = [], []
            for name, node in self.nodes.items():
                if status[name] != "pending":
                    continue
                if not all(status[r] == "done" for r in node.requires):
                    if any(status[r] in ("failed", "skipped")
                           for r in node.requires):
                        status[name] = "blocked"   # fail closed early
                        rep.blocked.append(name)
                        self._emit("NODE_BLOCKED", name,
                                   "dependency failed or skipped")
                    continue
                if node.condition is not None and not node.condition(ctx):
                    gate_off.append(name)
                elif node.fn is not None:
                    runnable.append(name)
            if not runnable and not gate_off:
                break
            rep.waves += 1
            for name in runnable:
                node = self.nodes[name]
                self._emit("NODE_STARTED", name)
                try:
                    ctx[name] = node.fn(ctx)
                    status[name] = "done"
                    rep.executed.append(name)
                    self._emit("NODE_DONE", name)
                except Exception as exc:
                    status[name] = "failed"
                    rep.failed[name] = f"{type(exc).__name__}: {exc}"
                    self._emit("NODE_FAILED", name, rep.failed[name])
            for name in gate_off:
                status[name] = "skipped"
                rep.skipped.append(name)
                self._emit("NODE_SKIPPED", name, "condition gate off")
        for name, st in status.items():
            if st == "pending":                 # cycles, missing deps
                rep.blocked.append(name)
                self._emit("NODE_BLOCKED", name, "unreachable (cycle?)")
        return rep
