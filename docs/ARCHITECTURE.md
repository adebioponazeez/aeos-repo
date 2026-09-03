# Architecture — AEOS v1.0.0

This documents the system that **is**, not a system that might be. Every
claim below maps to a module and a test.

## 1. The one-paragraph mental model

A human states intent. The **Executive** formalizes it. **Research**
grounds it. The **Architect** turns it into a validated task graph. The
**Orchestrator** executes the graph as dependency-ordered parallel
waves of specialized agents, each wrapped by the **Harness** (checkpoint
before, write-boundary enforcement after), each producing a typed
**Envelope** that independent **Gates** check against reality. The
**Governor** classifies every action and answers ALLOW / CHECKPOINT /
DENY. The **Evaluator** issues verdicts from a closed vocabulary. The
**EventLog** records everything. The **Learning Loop** converts
evidence-backed successes into skills and proposals up the capability
ladder, while the **Entropy Scanner** hunts the decay that autonomy
inevitably produces.

```
HUMAN INTENT
   │
   ▼
┌──────────┐   ┌────────────┐   ┌───────────┐   ┌────────────────────┐
│ executive│──▶│ researcher │──▶│ architect │──▶│ ORCHESTRATOR        │
└──────────┘   └────────────┘   └───────────┘   │  waves of agents    │
                                                 │  ┌──────────────┐  │
                    ┌───────────────┐            │  │ GOVERNOR     │  │
                    │ LEARNING OS   │            │  │ ALLOW/CKPT/  │  │
                    │ validated ▲   │            │  │ DENY         │  │
                    │ promotion│   │            │  └──────┬───────┘  │
                    └──────────┼───┘            │         ▼          │
                               │                │  ┌──────────────┐  │
                    ┌──────────┴───┐            │  │ HARNESS      │  │
                    │ ENTROPY      │            │  │ checkpoint ▶ │  │
                    │ scan/reap    │            │  │ boundary ▶   │  │
                    └──────────────┘            │  │ rollback     │  │
                                                │  └──────┬───────┘  │
                                                 └────────┼─────────┘
                                          Envelope │
                                                  ▼
                                     ┌────────────────────┐
                                     │ EVALUATOR (gates)  │
                                     │ PASS/FAIL/PARTIAL/ │
                                     │ UNVERIFIED        │
                                     └─────────┬──────────┘
                                               ▼
                                     ┌────────────────────┐
                                     │ release + evidence │
                                     └────────────────────┘
```

## 2. Layers and their guarantees

| # | Layer | Guarantee | Proven by |
|---|---|---|---|
| 1 | Contracts | No untyped boundary crossings | `test_handler_must_return_envelope` |
| 2 | Models | Model-agnostic seam; deterministic test double | `models.py` protocol; whole suite runs on EchoModel |
| 3 | Context OS | Budget enforced; stale dropped; conflicts surfaced; disclosure progressive | `test_context_os.py` (9 tests) |
| 4 | Memory OS | Canonical writes need evidence; freshness filters reads | `test_evaluation_memory_skills.py` |
| 5 | Skills OS | Version regressions rejected; win-rate tracked | `test_skills` |
| 6 | Orchestrator | Cycles rejected; unordered overlapping writers rejected; upstream failure skips dependents; bounded repair | `test_orchestrator.py` (9) |
| 7 | Governor | Matrix fails closed; high-impact always checkpoints; autonomy earned by reliability | `test_governor.py` (11) |
| 8 | Evaluation | Closed verdict vocabulary; unbacked claims fail; absence of failure ≠ success | `test_evaluation` |
| 9 | Harness | Unauthorized writes reverted; checkpoints restore; OS state inside fence | `test_harness.py` (6) |
| 10 | Observability | Every transition an event; success rate computable | e2e `test_reference_run_is_observable` |
| 11 | Learning | Failure never canonicalized | `test_failure_never_becomes_canonical` |
| 12 | Discovery | Promotion from measured repetition + win-rate | `test_discovery` |

## 3. The four invariants (the whole OS in four sentences)

1. **No envelope, no result.** Everything an agent returns is typed and
   carries claims + evidence; gates check claims against the filesystem.
2. **No authority without a boundary.** WRITE-class agents declare
   `writes:` globs; the harness reverts anything outside them.
3. **No autonomy without reliability.** The governor's level moves with
   observed success; high-impact classes checkpoint forever.
4. **No memory without validation.** Lessons are episodic by default;
   only evidence-backed successes become procedural/canonical.

## 4. Execution model

`Orchestrator.run()` validates the graph (cycles, unknown agents,
unordered write collisions), computes waves by topological sort, runs
each wave in a thread pool (agents are I/O-shaped), evaluates each
envelope through the stock gates, feeds outcomes to the governor's
reliability EMA, and runs one bounded repair cycle for failed tasks
that have attempts left. A run is accepted only if every task reached
SUCCEEDED.

## 5. Extension points

- **New agent:** add an `AgentSpec` (contract-complete) + a handler
  returning `Envelope`. The graph does the rest.
- **New model:** implement `ModelAdapter` (one method). Nothing else
  changes — ADR-001 exists precisely so this is boring.
- **New gate:** subclass/construct `Gate` and append to the evaluator.
- **Real tool use:** handlers currently run in-process; the seam for
  MCP-style tool servers is the handler boundary (ADR-007).

## 6. What v1.0 deliberately does not do

Honest scope (spec §55: do not claim readiness without evidence):
- No remote/MCP tool layer (seam defined, adapter not shipped).
- No durable cross-process scheduler (in-process threads; the event log
  is replayable but the runtime is not yet resumable).
- No UI; observability is JSONL + summaries.
- EchoModel simulates model behavior for reproducibility; production
  adapters are configuration, not code, away.

---

## Addendum (v7.0.0): The Platform Layers

Volume I of the book documents this file's kernel. v2–v7 added the
platform — each layer with its own ADR and tests:

- `adapters.py` — provider error taxonomy, breaker, fusion (ADR-010/011)
- `runtime.py` — durable, resumable runs (ADR-009)
- `tools.py` — MCP-idiom tool layer, untrusted-by-default (ADR-012)
- `catalog.py` + `sponsorship.py` — hashed capability units; scoped,
  one-shot human authority (ADR-013)
- `economics.py` — costs, budgets, leverage ratio (ADR-014)
- `research.py` + `ops.py` — untrusted-source research; sweeps;
  regression book
- `meta.py` — bounded self-improvement (ADR-015)
- `factory.py` + `visualizer.py` — the L7 capability pipeline and the
  Studio dashboard (ADR-016)

See `book/print/volume-II.html` and `CHANGELOG.md`. The four invariants
are unchanged; a fifth was earned: no self-modification without a
spent human token.
