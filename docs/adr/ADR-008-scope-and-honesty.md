# ADR-008: v1.0 scope — what we ship, what we refuse to claim

**Status: ACCEPTED (v1.0)**

## Context
Spec §55: "Do not claim production readiness without evidence." The
failure mode of every impressive agent demo is claiming more than the
evidence supports.

## Decision
v1.0 "Production Baseline" means: the complete in-process OS, 68
passing tests, a reproducible reference run with evidence bundles. We
explicitly do NOT claim: remote tool integration, cross-process
durability, multi-tenant isolation, or real-model validation.
Versioning follows spec §55: v0.1 concept → v0.2 architecture → v0.3
prototype → v0.5 functional → v0.7 evaluated → **v1.0 production
baseline (this release)** → v2.0 multi-agent platform → v3.0
autonomous capability OS.

## Alternatives considered
- **Shipping "v3.0"** — trivially easy, infinitely cheaper, and a lie.

## Tradeoffs
(+) Trust survives contact with the evidence directory.
(−) Marketing must wait for v2/v3 capabilities to actually exist.

## Consequences
The book documents exactly this system at exactly this version —
including the gaps, which get chapters of their own.
