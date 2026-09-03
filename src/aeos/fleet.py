"""v16 Fleet: one orchestrator, CRUD over agents, a live event stream.

The course's 'One Agent To Rule Them All' + the industry's OTel habit,
compiled stdlib-small: an append-only JSONL event bus (publish,
subscribe, replay — order is proof) and a fleet registry whose every
mutation is an event. Observability stops being post-hoc.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FleetEvent:
    ts: float
    kind: str
    agent: str
    detail: str = ""

    def as_line(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True)

    @classmethod
    def from_line(cls, line: str) -> "FleetEvent":
        d = json.loads(line)
        return cls(ts=d["ts"], kind=d["kind"], agent=d["agent"],
                   detail=d.get("detail", ""))


class EventBus:
    """Append-only JSONL log. File order is the truth; replay is proof."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._subs: list = []

    def publish(self, kind: str, agent: str, detail: str = "") -> FleetEvent:
        ev = FleetEvent(ts=time.time(), kind=kind, agent=agent, detail=detail)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(ev.as_line() + "\n")
        for sub in self._subs:
            sub(ev)
        return ev

    def subscribe(self, fn) -> None:
        self._subs.append(fn)

    def replay(self) -> list:
        from .vault import load_jsonl_tolerant, quarantine_torn
        if not self.path.exists():
            return []
        good, torn = load_jsonl_tolerant(self.path)
        events = []
        for d in good:
            try:
                events.append(FleetEvent(ts=d["ts"], kind=d["kind"],
                                         agent=d["agent"],
                                         detail=d.get("detail", "")))
            except (KeyError, TypeError, ValueError):
                torn.append("unrecoverable-event")
        if torn:
            quarantine_torn(self.path, torn)
        return events

    def tail(self, n: int = 20) -> list:
        return self.replay()[-n:]


@dataclass
class AgentSpec:
    name: str
    role: str
    skills: tuple = ()

    def as_dict(self) -> dict:
        return {"name": self.name, "role": self.role, "skills": list(self.skills)}


class FleetOrchestrator:
    """Single orchestrator with fleet CRUD; every mutation is an event."""

    def __init__(self, bus: EventBus):
        self.bus = bus
        self.agents: dict = {}

    def register(self, name: str, role: str, skills: tuple = ()) -> AgentSpec:
        if name in self.agents:
            raise ValueError(f"agent already registered: {name}")
        spec = AgentSpec(name=name, role=role, skills=tuple(skills))
        self.agents[name] = spec
        self.bus.publish("AGENT_REGISTERED", name,
                         f"role={role} skills={','.join(skills) or '-'}")
        return spec

    def retire(self, name: str) -> AgentSpec:
        if name not in self.agents:
            raise KeyError(f"unknown agent: {name}")
        spec = self.agents.pop(name)
        self.bus.publish("AGENT_RETIRED", name, f"role={spec.role}")
        return spec

    def dispatch(self, name: str, task: str) -> FleetEvent:
        if name not in self.agents:
            raise KeyError(f"unknown agent: {name}")
        self.bus.publish("AGENT_TASK_SENT", name, task)
        return self.bus.publish("AGENT_TASK_DONE", name,
                                f"acknowledged: {task}")

    def roster(self) -> list:
        return [s.as_dict() for _, s in sorted(self.agents.items())]
