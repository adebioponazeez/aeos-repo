# BENCHMARK 2026 — AEOS vs the global field

*Scored at v27.0.0 · 50 modules · 338+1 tests · 36 ADRs · zero
dependencies. Comparators are the named best-in-class for each
dimension (LangGraph, CrewAI, Claude Agent SDK, OpenAgents/mcp-agent,
Letta, Pydantic AI), per the 2026 comparisons cited inline. "Lead"
and "behind" are per-dimension verdicts with the seam named — no
single framework wins everything, including us.*

| Dimension | Best in class | AEOS at v22 | Verdict |
|---|---|---|---|
| Durable execution | LangGraph checkpoints; Pydantic AI via Temporal/DBOS | v17 `PlanCheckpoint` — atomic write after EVERY task, resume with side effects exactly once | **PARITY** at single-host scale; behind at distributed (seam: checkpoint schema is portable to a broker) |
| Tool interop (MCP) | Native in LangGraph/CrewAI/Claude SDK/OpenAgents | v21 client + v24 `mcp_server` (read-only by law) — roundtrip proven | **PARITY** both directions; behind on transports beyond stdio (seam: HTTP transport) |
| Observability | OTel everywhere (LangSmith, Strands, MAF) | v16 `EventBus` + v24 `otel` span export (byte-stable, content-addressed) | **PARITY** at file level; behind on collector integrations (seam: OTLP HTTP push) |
| Persistent memory | Letta/MemGPT; ClaudeMem layered recall | v14 economics + v15 three-layer FTS recall + rent law | **LEAD** — nobody prices memory (negative marginal, squatters); parity on layering; behind at vector scale (deliberate) |
| Context engineering | Claude Code / DeepAgents harnesses | v10 tiers + v14 byte-stable prefixes + v22 cache telemetry | **LEAD** on measurability — the cache payoff is READ, not asserted |
| Governance & safety | (no leader ships this whole set) | inline budget cutoff, revocable autonomy, sponsorship-gated self-mod, quarantine-before-trust, boundaries-with-revert | **LEAD** — the industry's gap, our spine |
| Determinism & testing | (frameworks need deps/servers) | 287 proofs, fully offline, zero runtime deps | **LEAD** |
| Multi-agent orchestration | CrewAI roles; MAF graphs/swarms | roster + federation + v16 fleet + v25 `Colony` explicit DAG (cannot hang) | **PARITY** on graphs; behind on emergent swarm patterns (deliberate — untestable routing) |
| Evaluation suites | Mastra/LangSmith evals | v23 `EvalSuite` — predicate judges, weights, thresholds; self-eval grades AEOS's own laws | **PARITY**; LEAD on determinism (no LLM-as-judge anywhere) |
| Cost governance | providers meter after the fact | simulated default, live opt-in, inline cutoff mid-call | **LEAD** |

**Where we are still behind (honest list at v25):** distributed
durability (broker-class checkpoint fan-out), MCP transports beyond
stdio, OTLP push to collectors, vector-scale retrieval (deliberate),
and emergent swarm patterns (deliberate — untestable routing). Each
has a named seam above; none requires abandoning stdlib-only.

**Sources:** 2026 framework comparisons — openagents.org (Feb 2026),
langfuse.com (2025-03/2026-07), uvik.net (Aug 2026), arize.com
(2026-09), the-agent-report.com (May 2026). URLs on record in the
session log; conclusions re-derived against our own receipts.
