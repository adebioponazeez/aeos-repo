"""AEOS — The AI Engineering OS.

A working, model-agnostic operating system for agentic engineering:
contracts, orchestration, context, memory, skills, governance,
evaluation, observability, harness, entropy control, learning,
capability discovery — plus the v2–v7 platform layers: provider
adapters with fusion, durable resumable runtime, MCP-idiom tool
layer, capability catalog with sponsorship, economics and budgets,
autonomous research and ops, the bounded meta-loop, and the
capability factory.

Design law: THE HARNESS IS THE PRODUCT. Models are interchangeable
components (ADR-001); every reliability property in this package is
implemented and enforced by deterministic code.
"""

__version__ = "33.0.0"
__all__ = [
    "contracts", "models", "observability", "context_os", "memory",
    "skills", "orchestrator", "governor", "evaluation", "harness",
    "entropy", "learning", "discovery", "pipeline",
    # v2–v7
    "adapters", "runtime", "tools", "catalog", "sponsorship",
    "economics", "research", "ops", "meta", "factory", "visualizer",
    # v8-v10
    "transport", "sandbox_runner", "remote_worker", "console",
    "codesign", "federation", "providers", "companions", "triangle", "dividend", "recall", "fleet", "resume", "leverage-audit", "standards", "mcp", "telemetry", "eval", "otel", "colony", "vault", "storm", "groom", "backup", "restore", "soak", "doctor",
]
