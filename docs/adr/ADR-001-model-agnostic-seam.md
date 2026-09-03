# ADR-001: The harness is the product; models are interchangeable slots

**Status: ACCEPTED (v0.1)**

## Context
Spec §26 forbids architecting around one model. 2026 field evidence
(fusion-harness, pi-vs-claude-code, the model-churn of the last 18
months) shows the durable asset is the surrounding harness, not the
model inside it.

## Decision
The OS speaks only to a `ModelAdapter` protocol (one method,
`complete`). The default adapter is `EchoModel` — a deterministic
in-process engine that can simulate compliance or defection (raise, or
return junk) on demand. No vendor SDK appears anywhere in the
dependency graph.

## Alternatives considered
- **Vendor SDK integration** — rejected: couples every guarantee to a
  vendor's uptime, pricing and deprecation cadence.
- **Agent framework core (LangGraph-class)** — rejected for core:
  frameworks are fine, but the trust boundary must be code we own
  line-by-line.

## Tradeoffs
(+) Tests are free, deterministic, and run in CI forever.
(+) Model upgrades are configuration, not surgery.
(−) Real-model integration quality is unproven until adapters ship —
flagged honestly in "what v1.0 does not do."

## Consequences
Every reliability property in this repo is provable without an API
key — which is precisely what makes it provable at all.
