"""Model layer: models are interchangeable components (spec §26).

The OS never imports a vendor SDK. It speaks to a `ModelAdapter`
protocol; production adapters wrap real providers, and the default
`EchoModel` is a deterministic, zero-cost engine used by tests and the
self-hosted demo pipeline. This is the seam that keeps the entire
system model-independent: swap the adapter, keep the guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol, Sequence

from .contracts import Envelope


@dataclass
class ModelCall:
    """One request to a model. Everything the adapter needs, nothing more."""
    system: str
    prompt: str
    agent_name: str
    context_tokens: int = 0
    max_output_tokens: int = 4096


@dataclass
class ModelReply:
    text: str
    model: str
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


class ModelAdapter(Protocol):
    """The single seam between the OS and any model vendor."""

    def complete(self, call: ModelCall) -> ModelReply: ...


@dataclass
class RoutingRule:
    """Pick models by capability, not fashion (spec §26)."""
    match: Callable[[ModelCall], bool]
    model_name: str
    reason: str


class Router:
    """Deterministic model routing with an auditable decision log."""

    def __init__(self, default_model: str = "echo-1") -> None:
        self.default_model = default_model
        self.rules: list[RoutingRule] = []
        self.decisions: list[tuple[str, str, str]] = []  # (agent, model, reason)

    def add_rule(self, rule: RoutingRule) -> "Router":
        self.rules.append(rule)
        return self

    def route(self, call: ModelCall) -> str:
        for rule in self.rules:
            if rule.match(call):
                self.decisions.append((call.agent_name, rule.model_name, rule.reason))
                return rule.model_name
        self.decisions.append((call.agent_name, self.default_model, "default route"))
        return self.default_model


class EchoModel:
    """Deterministic in-process model used by tests and the demo.

    It simulates the only two behaviors a harness must survive:
    compliance (returns the bound reply) and defection (raises or
    returns junk). The harness's job is to make defection safe; the
    EchoModel lets us prove it does — thousands of times, for free.
    """

    def __init__(self) -> None:
        self.behaviors: dict[str, Callable[[ModelCall], str]] = {}
        self.calls: list[ModelCall] = []
        self.fail_next: str | None = None
        self.router = Router()

    def bind(self, agent_name: str,
             behavior: Callable[[ModelCall], str] | str) -> "EchoModel":
        self.behaviors[agent_name] = (behavior if callable(behavior)
                                      else (lambda _call: behavior))
        return self

    def fail_on_next(self, mode: str = "raise") -> None:
        self.fail_next = mode

    def complete(self, call: ModelCall) -> ModelReply:
        self.calls.append(call)
        if self.fail_next == "raise":
            self.fail_next = None
            raise RuntimeError("simulated model outage")
        if self.fail_next == "junk":
            self.fail_next = None
            return ModelReply(text="the mitochondria is the powerhouse", model="echo-1")
        behavior = self.behaviors.get(call.agent_name, lambda _c: "")
        return ModelReply(text=behavior(call), model=self.router.route(call),
                          tokens_in=max(1, call.context_tokens // 4),
                          tokens_out=64)


def envelope_from_reply(agent: str, objective: str, reply: ModelReply) -> Envelope:
    """Lift a raw model reply into a typed envelope.

    Untrusted by construction: claims start empty and evidence starts
    empty. Downstream gates decide what becomes true.
    """
    return Envelope(agent=agent, objective=objective, notes=reply.text)
