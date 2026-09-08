"""v39.5 Hooks: lifecycle interception as a first-class surface.

Cole Medin's advocacy, compiled: the bash-command hook as guardrail is
not an add-on — hooks ARE the critical mechanism. A hook is decoupled
from the agent (infrastructure-level, consistent regardless of model),
composable (many small hooks, ordered), and it can REDIRECT, not just
reject (a veto names its reason; a rewrite preserves intent while
removing the danger). The pre-execution hook answers "is this safe to
run?"; the post-execution hook answers "is this outcome safe to keep?".

AEOS had the semantics scattered (the governor is an access+pre-exec
hook; attach_persistence is a monkey-patch hook). This module makes
the surface first-class: named points on the harness scaffold, ordered
registrations, vetoes in plain language, observers that can never
crash the run. The kernel stays readable (ADR-002): points are emitted
from the orchestrator's existing seams, never inlined logic.

Scope, honestly (ADR-051): hooks are in-process Python callables —
the same trust boundary as the OS itself. They are guardrails against
AGENT behavior, not a plugin sandbox against hostile code.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

# The named points on the harness scaffold (law: closed vocabulary)
POINTS = (
    "task.pre",       # before a task runs; may REDIRECT (rewrite) or VETO
    "task.post",      # after a task settles; observer only
    "wave.pre",       # before a wave dispatches; observer only
    "wave.post",      # after a wave settles; observer only
    "subplan.pre",    # before a nested harness spawns; may VETO
    "refusal",        # anything refused, anywhere; observer only
)


class HookVeto(Exception):
    """A pre-hook refusal. The message IS the reason the operator
    sees — plain language, never a traceback (ADR-013)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class Registration:
    point: str
    fn: Callable[[dict], Any]
    order: int = 100          # lower runs first
    name: str = ""
    registered_at: float = field(default_factory=time.time)


class HookBus:
    """Ordered, thread-safe, inspectable. Emit-into-a-copy: handlers
    get a dict payload and pre-hooks may return a REPLACEMENT dict
    (redirect, don't just reject)."""

    def __init__(self) -> None:
        self._regs: list[Registration] = []
        self._lock = threading.Lock()

    # -- registration ------------------------------------------------
    def register(self, point: str, fn: Callable[[dict], Any], *,
                 order: int = 100, name: str = "") -> Registration:
        if point not in POINTS:
            raise ValueError(
                f"unknown hook point {point!r} — the vocabulary is law: "
                f"{', '.join(POINTS)}")
        if not callable(fn):
            raise TypeError("a hook must be callable")
        reg = Registration(point=point, fn=fn, order=order,
                           name=name or getattr(fn, "__name__", "hook"))
        with self._lock:
            self._regs.append(reg)
            self._regs.sort(key=lambda r: (r.order, r.registered_at))
        return reg

    def unregister(self, reg: Registration) -> None:
        with self._lock:
            self._regs = [r for r in self._regs if r is not reg]

    def registered(self, point: str | None = None) -> list[Registration]:
        with self._lock:
            regs = list(self._regs)
        return [r for r in regs if point is None or r.point == point]

    # -- emission ----------------------------------------------------
    def emit_pre(self, point: str, payload: dict) -> dict:
        """Run pre-hooks in order. A hook may raise HookVeto (refusal,
        named) or return a dict to REPLACE the payload (redirect)."""
        for reg in self.registered(point):
            try:
                out = reg.fn(dict(payload))
            except HookVeto:
                raise
            if isinstance(out, dict):
                payload = out
        return payload

    def emit_post(self, point: str, payload: dict) -> list[str]:
        """Run observers. A raising observer is COLLECTED and named —
        an observer can never crash the run it observes."""
        errors: list[str] = []
        for reg in self.registered(point):
            try:
                reg.fn(dict(payload))
            except Exception as exc:            # noqa: BLE001 — by law
                errors.append(f"{reg.name}: {type(exc).__name__}: {exc}")
        return errors

    def describe(self) -> str:
        lines = [f"HOOKS — {len(self.registered())} registration(s) "
                 f"across {len(POINTS)} named points"]
        for p in POINTS:
            regs = self.registered(p)
            if regs:
                lines.append(f"  {p}: " + ", ".join(
                    f"{r.name}(order={r.order})" for r in regs))
        lines.append("  vocabulary: " + ", ".join(POINTS))
        return "\n".join(lines)


# The process-wide default bus. The orchestrator accepts an injected
# bus; this one is the fallback so registration is global and simple.
BUS = HookBus()
