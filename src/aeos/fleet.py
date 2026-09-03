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
        import json as _json
        from .vault import schema_header
        ev = FleetEvent(ts=time.time(), kind=kind, agent=agent, detail=detail)
        new_stream = not self.path.exists()
        with self.path.open("a", encoding="utf-8") as fh:
            if new_stream:
                fh.write(_json.dumps(schema_header("fleet")) + "\n")
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
        from .vault import check_schema, is_header
        if good and is_header(good[0]):
            check_schema(good[0])
            good = good[1:]
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
        """Last n events in O(1): read the final block, parse complete
        lines only (a torn tail fragment is dropped, as replay
        quarantines it). The v34 gauge caught this reading the whole
        stream; now it seeks."""
        import os as _os
        if not self.path.exists():
            return []
        block = 64 * 1024
        with self.path.open("rb") as fh:
            fh.seek(0, _os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - block))
            data = fh.read()
        text = data.decode("utf-8", errors="replace")
        lines = text.split("\n")
        if size > block and lines:
            lines = lines[1:]          # leading fragment (cut by seek)
        if not text.endswith("\n") and lines:
            lines = lines[:-1]         # torn tail fragment
        out = []
        for ln in reversed(lines):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if not isinstance(d, dict) or "aeos_schema" in d:
                continue               # header / non-events
            try:
                out.append(FleetEvent(ts=d["ts"], kind=d["kind"],
                                       agent=d["agent"],
                                       detail=d.get("detail", "")))
            except (KeyError, TypeError, ValueError):
                continue
            if len(out) >= n:
                break
        out.reverse()
        return out


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
