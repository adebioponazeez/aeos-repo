"""v2.0 — Tool layer in the MCP idiom, with the 2026 security posture.

Shape follows the MCP 2026-07 stateless core (JSON-RPC-ish requests,
structured results, `isError` semantics) so a real transport can slot
in at `Transport`. Posture follows SEP-2085: **tools are untrusted by
default** — a tool result enters the system as a *claim*, never as an
instruction, and every call passes the governor before it executes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .contracts import ActionClass, Decision
from .governor import Governor


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    action_class: ActionClass = ActionClass.READ


@dataclass
class ToolResult:
    """JSON-RPC-flavored, MCP-shaped. `untrusted` is not configurable —
    it is the posture, not a flag."""
    name: str
    result: dict[str, Any] | None = None
    error: str | None = None
    is_error: bool = False
    untrusted: bool = True
    ts: float = field(default_factory=time.time)

    def to_rpc(self) -> dict[str, Any]:
        out: dict[str, Any] = {"jsonrpc": "2.0", "tool": self.name,
                               "untrusted": self.untrusted}
        if self.is_error:
            out["error"] = {"message": self.error, "code": -32000}
        else:
            out["result"] = self.result
        return out


class ToolError(RuntimeError):
    pass


class ToolRegistry:
    def __init__(self, governor: Governor) -> None:
        self.tools: dict[str, ToolSpec] = {}
        self.governor = governor
        self.call_log: list[ToolResult] = []

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self.tools:
            raise ToolError(f"tool '{spec.name}' already registered")
        self.tools[spec.name] = spec

    def call(self, name: str, params: dict[str, Any] | None = None,
             *, task_uid: str = "") -> ToolResult:
        if name not in self.tools:
            # Unknown tool: unknown action class -> governor fails closed.
            decision = self.governor.decide(ActionClass.IRREVERSIBLE, task_uid)
            result = ToolResult(name=name, error=f"unknown tool '{name}'",
                                is_error=True)
            self.call_log.append(result)
            return result
        spec = self.tools[name]
        decision = self.governor.decide(spec.action_class, task_uid)
        if decision.decision is Decision.DENY:
            result = ToolResult(name=name, error=f"denied: {decision.reason}",
                                is_error=True)
            self.call_log.append(result)
            return result
        if decision.decision is Decision.CHECKPOINT:
            # In-process tools are checkpoint-resolved by policy only for
            # read-class tools; anything heavier escalates to the caller.
            if spec.action_class not in (ActionClass.READ, ActionClass.NETWORK):
                result = ToolResult(name=name,
                                    error=f"checkpoint required: {decision.reason}",
                                    is_error=True)
                self.call_log.append(result)
                return result
        try:
            out = spec.handler(params or {})
            result = ToolResult(name=name, result=out)
        except Exception as exc:
            result = ToolResult(name=name, error=f"{type(exc).__name__}: {exc}",
                                is_error=True)
        self.call_log.append(result)
        return result

    def declared_names(self) -> list[str]:
        return sorted(self.tools)


# ---------------------------------------------------- demo tool set
# Deterministic, in-process — same philosophy as EchoModel: the tool
# layer must be testable without network or keys.

def fake_web_search(query: str = "", *, seed: int = 7) -> dict[str, Any]:
    """Deterministic stand-in for a search provider. Sources carry
    authority ratings so downstream confidence math is realistic."""
    return {
        "query": query,
        "results": [
            {"source_id": "spec/mcp", "title": "MCP 2026-07 stateless core",
             "snippet": "Spec drop of 2026-07-28: stateless core, ext-* tasks.",
             "authority": 0.95},
            {"source_id": "research/context", "title": "Context rot study",
             "snippet": "138 repos: bloated context files reduce success 20%+.",
             "authority": 0.9},
            {"source_id": "forum/lore", "title": "Hot take blog",
             "snippet": "agents will just work trust me bro",
             "authority": 0.2},
        ],
        "seed": seed,
    }


def install_default_tools(registry: ToolRegistry) -> None:
    registry.register(ToolSpec(
        name="web_search", description="Search public sources (deterministic demo)",
        input_schema={"query": "string"},
        handler=lambda p: fake_web_search(p.get("query", "")),
        action_class=ActionClass.NETWORK))
    registry.register(ToolSpec(
        name="list_files", description="List files under a relative path",
        input_schema={"path": "string"},
        handler=lambda p: {"path": p.get("path", ".")},
        action_class=ActionClass.READ))
