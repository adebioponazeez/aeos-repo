"""Observability: an append-only event log is the source of truth.

2026 harness rule (and spec §20): if autonomous activity cannot be
observed, it cannot be operated. Every meaningful transition in this
OS emits a structured event; the log is replayable, greppable, and
cheap. JSONL — one event per line, no framework tax.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, TextIO


@dataclass
class Event:
    kind: str                 # e.g. task.started, gate.checked, governor.denied
    detail: dict[str, Any]
    ts: float = 0.0

    def __post_init__(self) -> None:
        if not self.ts:
            self.ts = time.time()


class EventLog:
    """Append-only structured log. Writes are atomic lines; readers
    never block writers (the SQLite-WAL lesson from SSSF, minus SQLite).

    v1.1: secret redaction is structural — any detail key that looks
    like a credential has its value replaced BEFORE serialization.
    The log is designed so it cannot become a leak."""

    SECRET_KEYS = ("api_key", "apikey", "token", "secret", "password",
                   "passwd", "credential", "credentials", "authorization",
                   "auth_header", "session_id")

    def __init__(self, sink: TextIO | Path | None = None) -> None:
        self._sink = sink
        self._memory: list[Event] = []
        self._file: TextIO | None = None
        if isinstance(sink, Path):
            sink.parent.mkdir(parents=True, exist_ok=True)
            self._file = sink.open("a", encoding="utf-8")

    @classmethod
    def redact(cls, detail: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in detail.items():
            if any(s in k.lower() for s in cls.SECRET_KEYS) and not isinstance(v, (bool, int, float)):
                out[k] = "[REDACTED]"
            else:
                out[k] = v
        return out

    def emit(self, kind: str, **detail: Any) -> Event:
        detail = self.redact(detail)
        event = Event(kind=kind, detail=detail)
        self._memory.append(event)
        line = json.dumps({"kind": event.kind, "ts": event.ts, "detail": detail},
                          default=str, sort_keys=True)
        if self._file is not None:
            self._file.write(line + "\n")
            self._file.flush()
        elif self._sink is not None:
            self._sink.write(line + "\n")
        return event

    def events(self, kind_prefix: str | None = None) -> list[Event]:
        if kind_prefix is None:
            return list(self._memory)
        return [e for e in self._memory if e.kind.startswith(kind_prefix)]

    def counts(self) -> dict[str, int]:
        return dict(Counter(e.kind for e in self._memory))

    def summary(self) -> dict[str, Any]:
        c = self.counts()
        started = sum(v for k, v in c.items() if k.startswith("task.succeeded"))
        failed = sum(v for k, v in c.items() if k.startswith("task.failed"))
        escalated = sum(v for k, v in c.items() if k.startswith("task.escalated"))
        total = started + failed
        return {
            "events": len(self._memory),
            "tasks_succeeded": started,
            "tasks_failed": failed,
            "tasks_escalated": escalated,
            "success_rate": round(started / total, 3) if total else None,
            "by_kind": c,
        }

    def tail(self, n: int = 20) -> list[Event]:
        return self._memory[-n:]
