# AEOS — The AI Engineering OS

**Version 27.0.0 — The Storm. Built, tested, torture-proven — not proposed.**

A working, model-agnostic operating system for agentic engineering. v1.0
shipped the kernel (contracts, orchestration, context, memory, skills,
governance, evaluation, observability, harness, entropy, learning,
discovery). v2–v7 ship the platform around it. **131 tests. Zero
runtime dependencies.**

> The law of this codebase: **the harness is the product.** Models are
> interchangeable slots; every reliability property is enforced by
> deterministic code you can read end-to-end.

## Quick start

```bash
pip install -e .            # zero runtime dependencies
python -m pytest            # 338 proofs incl. the chaos storm, ~73 seconds
aeos run-demo               # full reference loop, evidence bundle
aeos factory-demo           # v7: the capability factory (proposals only)
aeos factory-demo --token S # v7: ...with sponsorship (scoped installs)
aeos dashboard              # static Studio run report
aeos sponsor --scope S      # v8: issue a persistent, scoped, one-shot token
aeos console                # v8: the authority console
aeos federation-demo        # v10: quarantine -> revalidate -> sponsored install
aeos live-check             # v11: resolved live config — zero spend
aeos companions             # v12: Pi CLI / DeerFlow status + enable hints
aeos run-demo --profile control|speed|cost   # v13: pick your trade
aeos triangle               # v13: the measured control/cost/speed receipt
aeos dividend               # v14: memory economics — compression, negative marginal, rent
aeos recall                 # v15: layered FTS recall — keys, snippets, full records
aeos fleet                  # v16: fleet CRUD + live event stream (see dashboard --live)
aeos resume                 # v17: durable plans — crash, resume, side effects once
aeos leverage-audit         # v18: the 12 leverage points audited against disk
aeos standards [--init]     # v19: operator law as [STD-n] — plans must cite it
aeos mcp                    # v21: MCP client demo — handshake, tools, UNTRUSTED
aeos telemetry              # v22: cache hit rate + effective tokens
aeos eval                   # v23: the system grades its own laws
aeos otel                   # v24: fleet stream -> OTel spans
aeos mcp --serve            # v24: AEOS as a read-only MCP server (roundtrip)
aeos colony                 # v25: explicit graph orchestration
aeos vault                  # v26: fault-tolerance posture + environment scan
aeos storm                  # v27: THE NUCLEAR TEST — kill storms, torn files, disk full, blackout
OPENROUTER_API_KEY=... aeos run-demo --live   # v11: real models, metered, $2 cap
aeos selftest
```

## The version ladder (all shipped, all tested)

| Version | Name | What landed |
|---|---|---|
| v1.0 | Production Baseline | The kernel: 15 modules, 68 tests, reference pipeline |
| v1.1 | Hardening | Secret redaction, gate library, entropy coverage |
| v2.0 | Multi-Agent Platform | Provider adapters + error taxonomy + circuit breaker + **fusion**; durable resumable runtime; MCP-idiom tool layer (untrusted by default) |
| v3.0 | Capability OS | Content-hashed capability catalog; **sponsorship tokens**; multi-tenant governance |
| v4.0 | Economics | Cost tracking, budgets (ALLOW/CHECKPOINT/DENY), OUTCOME VALUE / HUMAN ATTENTION metric |
| v5.0 | Research & Ops | Autonomous research with untrusted-source discipline; sweep scheduler; regression book (failures become gates) |
| v6.0 | Meta-Loop | Bounded self-improvement: retire/tune proposals, hard floors, ADR stubs, sponsorship-gated |
| **v7.0** | **Capability Factory** | **L7 live: measure → design → sandbox-validate → propose → sponsored install. Studio dashboard.** |
| v8.0 | Distance | HTTP transports on the taxonomy; A2A-style remote workers; **process-isolated sandboxes** (killed on wall clock); persistent sponsorships + console |
| v9.0 | Co-Design | Design **slates**: conservative / minimal-privilege / reviewer-first, least-privilege scored, human sponsors one variant |
| **v10.0** | **Federation** | **The cross-org market: IMPORT IS QUARANTINE; TRUSTED only via local sandbox; provenance-bearing export** |
| **v11.0** | **Live Models** | **OpenRouter / Abacus RouteLLM / OpenAI behind the seam: taxonomy at the wire, metered usage, inline $-budget cutoff, keys never logged** |
| **v12.0** | **Companions** | **Pi CLI + DeerFlow as bounded nodes: fs-diff artifacts (never self-report), boundary revert for rogue agents, wall-clock kill, untrusted-source quarantine** |
| **v13.0** | **The Triangle** | **Control/Cost/Speed as one dial: 4 stances moving all knobs together, immutable floors, and the trade MEASURED per run with a receipt** |
| **v14.0** | **The Dividend** | **Negative marginal token consumption: measured distillation, cache-stable canonical-JSON prefixes, per-class token ledgers, and MEMORY MUST PAY RENT** |
| **v15.0** | **The Recall** | **Retrieval pays in layers: FTS5 keys → snippets → full records, budgeted, savings on every bundle** |
| **v16.0** | **The Fleet** | **One orchestrator, fleet CRUD, append-only event stream — observability as replayable proof** |
| **v17.0** | **The Resume** | **Durable plans: atomic checkpoints after every task; crash, resume, side effects exactly once** |
| **v18.0** | **The Rubric** | **The 12 leverage points as an auditable rubric — PASS requires evidence on disk** |
| **v19.0** | **The Standards** | **Success is planned: operator law registered as [STD-n]; uncited plans are refused** |
| **v20.0** | **The Emissaries** | **Companions round 2: aider + headless Claude under the Pi law — fs-verified, phantom-refused, boundary-reverted** |
| **v21.0** | **The Protocol** | **MCP client, stdlib stateless core; imported tools are UNTRUSTED material** |
| **v22.0** | **The Horizon** | **Cache telemetry (hit rate, effective tokens), the global benchmark, and the seams named** |
| **v23.0** | **The Mirror** | **Eval suites: predicate judges, weights, thresholds; the self-eval grades AEOS's own six laws** |
| **v24.0** | **The Bridges** | **MCP server mode (read-only by law) + OTel span export — the ecosystem's protocols, both directions** |
| **v25.0** | **The Colony** | **Explicit graph orchestration: requires + conditions, failures block, cycles BLOCK — never hang** |
| **v26.0** | **The Vault** | **Fault tolerance: atomic durable writes, torn-write quarantine, kernel-released locks, provable offline** |
| **v27.0** | **The Storm** | **Chaos as a command: kill -9 storms, torn files, disk-full, garbage, 256MB cap, socket blackout — 8/8 survived, receipts permanent** |

## What v7 proves (reproduced in `evidence/`)

- **338/338 tests passing** (+1 opt-in live smoke) — and the storm runs inside the suite: SIGKILL mid-run x3 with recovery, torn power-cut files quarantined, disk-full leaving evidence byte-intact, garbage inputs verdicted, a full run under a 256MB cap, and a total socket blackout completed — the system is provably offline and power-cut resistant.
- **Reference run:** 7/7 tasks, governor earns L5 from reliability 1.0,
  leverage ratio **7.0** (7 outcomes, 0 human interventions), full
  evidence bundle + dashboard.
- **Factory, no token:** 2 candidates validated in sandbox, 2 proposals,
  **0 installs** — every install refused and logged.
- **Factory, scoped token:** exactly the scoped capability installed;
  the second candidate **refused on scope mismatch**. One token, one
  power, one use.
- **Live sponsor flow:** `aeos sponsor --scope factory:install:builder-specialist`
  → factory installs exactly `builder-specialist`, refuses the rest.
- **Federation:** foreign unit → QUARANTINED; install refused **with a
  valid token in hand**; local revalidation → PASS → sponsored install.
- **Process sandbox:** a hung candidate is killed at its wall clock; a
  poisoned input yields a written verdict, never a stack trace.

## The four invariants (unchanged since v1, still tested)

1. **No envelope, no result** — typed returns; gates check claims.
2. **No authority without a boundary** — `writes:` enforced post-hoc.
3. **No autonomy without reliability** — the ladder moves on evidence.
4. **No memory without validation** — failure never becomes folklore.

v6/v7 add the fifth, and hardest-won: **no self-modification without a
spent human token.**

## Repository layout

```
src/aeos/            # 50 modules: kernel (v1) + platform (v2–v27)
tests/               # 177 tests incl. adversarial + e2e + factory + federation + live-wire
evidence/            # captured test runs, run bundles, factory runs, dashboard
docs/                # architecture, security, runbook, dossier, principles charter, TAC audit, global benchmark, 36 ADRs
book/                # Volumes I–III + v11 addendum (print/), HTML + markdown
AGENTS.md            # short repo context for coding agents
CHANGELOG.md         # every version, earned by tests
```

## Lineage and license

Original code, MIT. Principles absorbed with attribution from the
public canon — `disler/super-simple-software-factory` (agent
proposes / code disposes; typed envelopes; evidence gates; write
boundaries), `fusion-harness` (combine compute), `the-verifier-agent`
(independent verification), hooks-based observability, MCP/SEP-2085
posture, the 2026 harness-engineering canon. See
`docs/RESEARCH-DOSSIER.md` and `docs/adr/`.
