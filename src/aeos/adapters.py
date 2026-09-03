"""v2.0 — Provider adapters with a real error taxonomy, circuit breaker,
and fusion policy ("combine compute, don't select compute").

The transport is injectable: production wires an HTTP transport,
tests wire a fake. No vendor SDK, per ADR-001/010. Every failure is
classified — TRANSIENT, CONTEXT_OVERFLOW, PERMANENT, JUNK — because
the correct harness response depends on the class, not the message.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol

from .models import ModelCall, ModelReply


class ErrorKind(str, Enum):
    TRANSIENT = "TRANSIENT"                # retry with backoff
    CONTEXT_OVERFLOW = "CONTEXT_OVERFLOW"  # compress context, don't retry
    PERMANENT = "PERMANENT"                # fail fast, surface to repair
    JUNK = "JUNK"                          # confident nonsense: gate it
    CIRCUIT_OPEN = "CIRCUIT_OPEN"          # breaker protecting downstream


class AdapterError(RuntimeError):
    def __init__(self, kind: ErrorKind, detail: str) -> None:
        super().__init__(f"[{kind.value}] {detail}")
        self.kind = kind


class Transport(Protocol):
    """One request/response against a provider. Inject a fake in tests."""
    def post(self, call: ModelCall, model: str) -> ModelReply: ...


@dataclass
class FakeTransport:
    """Deterministic transport with scriptable failures."""
    script: list[Callable[[ModelCall], ModelReply]] = field(default_factory=list)
    replies: list[ModelReply] = field(default_factory=list)

    def post(self, call: ModelCall, model: str) -> ModelReply:
        if self.script:
            step = self.script.pop(0)
            out = step(call)          # may raise — that IS the script
            self.replies.append(out)
            return out
        reply = ModelReply(text=f"ok:{call.agent_name}", model=model)
        self.replies.append(reply)
        return reply


def raise_transient(call: ModelCall) -> ModelReply:
    raise ConnectionError("503 upstream")


def raise_overflow(call: ModelCall) -> ModelReply:
    raise ValueError("context length exceeded")


class ProviderAdapter:
    """Retry taxonomy + exponential backoff + circuit breaker."""

    def __init__(self, transport: Transport, model: str = "provider-1",
                 *, retries: int = 2, backoff_s: float = 0.001,
                 breaker_threshold: int = 3, breaker_cooldown: float = 0.005,
                 name: str = "adapter") -> None:
        self.transport = transport
        self.model = model
        self.retries = retries
        self.backoff_s = backoff_s
        self.breaker_threshold = breaker_threshold
        self.breaker_cooldown_s = breaker_cooldown
        self.name = name
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def _classify(self, exc: Exception) -> ErrorKind:
        msg = str(exc).lower()
        if "context" in msg and ("length" in msg or "exceeded" in msg):
            return ErrorKind.CONTEXT_OVERFLOW
        if isinstance(exc, (ConnectionError, TimeoutError)) or "503" in msg or "429" in msg:
            return ErrorKind.TRANSIENT
        return ErrorKind.PERMANENT

    def _breaker_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.time() - self._opened_at >= self.breaker_cooldown_s:
            self._opened_at = None           # half-open: next call is a probe
            return False
        return True

    def complete(self, call: ModelCall) -> ModelReply:
        if self._breaker_open():
            raise AdapterError(ErrorKind.CIRCUIT_OPEN,
                               f"{self.name} breaker open, cooldown active")
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                reply = self.transport.post(call, self.model)
                self._consecutive_failures = 0
                if not reply.text.strip():
                    raise AdapterError(ErrorKind.JUNK, "empty reply")
                return reply
            except AdapterError:
                self._trip()
                raise
            except Exception as exc:
                kind = self._classify(exc)
                last = exc
                if kind is ErrorKind.CONTEXT_OVERFLOW:
                    self._trip()
                    raise AdapterError(kind, str(exc)) from exc
                if kind is ErrorKind.TRANSIENT and attempt < self.retries:
                    time.sleep(self.backoff_s * (2 ** attempt))
                    continue
                if kind is ErrorKind.TRANSIENT and self.retries > 0:
                    # retries configured AND exhausted: still-down is, for
                    # the caller, permanent — repair, don't re-retry
                    self._trip()
                    raise AdapterError(
                        ErrorKind.PERMANENT,
                        f"transient failures exhausted {self.retries + 1} "
                        f"attempt(s): {exc}") from exc
                self._trip()
                raise AdapterError(kind, str(exc)) from exc
        self._trip()
        raise AdapterError(ErrorKind.PERMANENT, f"exhausted retries: {last}")

    def _trip(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.breaker_threshold:
            self._opened_at = time.time()


@dataclass
class FusedReply(ModelReply):
    agreement: str = "AGREED"           # AGREED | DISAGREED
    opinions: list[str] = field(default_factory=list)


def _norm(text: str) -> set[str]:
    return {w for w in text.lower().split() if len(w) > 3}


class FusionAdapter:
    """Fan one call out to N adapters; adjudicate before returning.

    Majority-by-similarity wins; disagreement is surfaced, never
    averaged away. The gate downstream sees `agreement` and can treat
    DISAGREED as PARTIAL — opinions are evidence, not truth."""

    def __init__(self, adapters: list[ProviderAdapter]) -> None:
        if len(adapters) < 2:
            raise ValueError("fusion needs >= 2 adapters — otherwise it is just a call")
        self.adapters = adapters

    def complete(self, call: ModelCall) -> FusedReply:
        opinions: list[ModelReply] = []
        errors: list[str] = []
        for a in self.adapters:
            try:
                opinions.append(a.complete(call))
            except AdapterError as exc:
                errors.append(str(exc))
        if not opinions:
            raise AdapterError(ErrorKind.PERMANENT,
                               f"all fusion streams failed: {errors}")
        # majority cluster by word overlap
        best, best_score = opinions[0], -1
        for candidate in opinions:
            score = sum(1 for other in opinions
                        if _sim(candidate.text, other.text) >= 0.5)
            if score > best_score:
                best, best_score = candidate, score
        agreement = "AGREED" if best_score == len(opinions) else "DISAGREED"
        return FusedReply(text=best.text, model=f"fusion({len(self.adapters)})",
                          tokens_in=max(o.tokens_in for o in opinions),
                          tokens_out=max(o.tokens_out for o in opinions),
                          agreement=agreement,
                          opinions=[o.text[:80] for o in opinions] +
                                   [f"stream-error: {e}" for e in errors])


def _sim(a: str, b: str) -> float:
    sa, sb = _norm(a), _norm(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
