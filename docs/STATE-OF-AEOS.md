# THE STATE OF AEOS — a critical audit (at v39.7.1)

*Asked by the operator: "why is everything disjointed... why is
almost everything built so far less than 40% of what it should be,
end-to-end?" This report answers with evidence, not narrative. It
was produced by stopping the feature treadmill entirely and
auditing what exists: import graphs, pyflakes, CLI inventory,
integration traces, and a step-by-step walk of the end-to-end
path an operator would actually take.*

> **POST-SPINE UPDATE (v39.8.0).** Phase B of the plan below has
> shipped: an operator's graph now executes on the REFERENCE
> pipeline (`aeos run --graph plan.dot`; ADR-055) — real roster,
> real handlers, real artifacts, live events on one bus, memory
> that accumulates the graph's own lessons, contract law at the
> door. Spine steps **2 (intent → plan)** and **7 (operator
> watches live)** move to WORKS: end-to-end completeness
> **~39% → ~50%**. The integration also surfaced two latent
> defects the audit had not found (the builder's literal-name
> branching that silently mis-built; the example graph's WRITE task
> on the READ-only executive) — both fixed, both regression-tested.
> The matrix below is the v39.7.1 baseline, kept as audited.
>
> **LOOP-CLOSURE UPDATE (v39.9.0).** Spine step 9 now closes for
> the pipeline (ADR-056): before a plan executes, prior runs'
> evidence-validated lessons are recalled into its context, and the
> architect cites what it applied in the spec. Two runs in one
> workspace demonstrably compound. Honest boundary: under the
> EchoModel this is structural closure — lessons reaching context
> and spec; lessons changing executor BEHAVIOR takes a real model
> (First Light, operator opt-in). The foreman's repairs still do
> not feed the planner. End-to-end completeness **~50% → ~53%**.
>
> **FRONT-DOOR-DIET UPDATE (v40.0.0).** The register's "cli.py is a
> 1,129-line god module" entry is resolved (ADR-057): one thin door
> (grouped menu, routing) + four surface modules, registration ==
> menu == routing held by test. The README's "37 commands" was
> drifted (real: 39) — now counted honestly.

---

## 1. What was actually built (the inventory)

68 modules · 579 tests · 54 ADRs · 36 CLI commands · zero runtime
dependencies · 39 versions shipped, every one tagged, CI'd
(3.10–3.13), receipted, and doctor-verified. By LAYER:

- **Kernel (v1):** contracts (typed envelopes), orchestrator
  (waves), governor (L0–L7), evaluation (gates), context, memory,
  skills, observability, harness, entropy, learning, discovery.
- **Platform (v2–v31):** factory + sponsorship, federation,
  providers (live-model seam), companions, triangle, dividend,
  recall (FTS5), fleet, resume (durable checkpoints), leverage
  rubric, standards gate, MCP client+server, OTel, colony.
- **Operations (v32–v39.7):** doctor, scribe, save-proof notary,
  outbox, ignition (staged boot), foreman (autonomous operator),
  storm/gauntlet/field harnesses, holdout (sealed evaluation),
  hooks (lifecycle interception), graphlang (declarative DOT),
  stream (SSE shopfloor).

The receipts are real: the storm, gauntlet and field batteries
found and fixed eleven genuine defects across v39.2–v39.4; the
holdout is cryptographically sealed; the wheel is verified on
four interpreters. **None of that is theater.** But inventory is
not the question. The question is composition.

## 2. The verdict on "disjointed": CONFIRMED — with evidence

The system is a **collection of well-tested organs that have
never been assembled into one animal.** Proof, step by step along
the path an operator would actually take (the SPINE):

| # | Spine step | State at v39.7.0 | Evidence |
|---|---|---|---|
| 1 | Operator states intent | **WORKS** | `aeos up`, hostile intents verdicted (holdout family) |
| 2 | Intent becomes a versioned plan | **WORKS, DISCONNECTED** | graphlang compiles DOT beautifully — but `aeos graph --run` executes a DEMO roster; the reference pipeline still builds its own hardcoded 7 tasks. The two planners never meet. |
| 3 | Plan executes under governor + hooks + gates | **WORKS** (both paths, separately) | 578 tests; hooks fire through both |
| 4 | Execution uses a REAL model | **NEVER HAPPENED** | providers.py's own docstring: "The OS has spoken only to the deterministic EchoModel since v1.0." Live adapters shipped at v11, exercised zero times. |
| 5 | Evidence + verdicts land | **WORKS** | bundles, receipts, save-proof certs |
| 6 | Memory/learning compounds | **MECHANISM ONLY** | every memory record in every receipt came from EchoModel demo runs — the system has zero real experience |
| 7 | The operator watches live | **PARTIAL** | shopfloor streams pipeline runs; graph runs were INVISIBLE to it until this audit fixed it; foreman receipts live in a separate ledger |
| 8 | Holdout evaluates honestly | **WORKS** | sealed vault, twin, tamper-refusing |
| 9 | The loop closes (foreman heals, next run improves) | **PARTIAL** | foreman heals workspaces, but nothing it learns changes the next plan |

**Steps truly working end-to-end: 3.5 of 9 ≈ 39%. The operator's
"less than 40%" was not an insult — it was accurate.**

## 3. Why it happened (root causes, no excuses)

1. **The cadence was version-per-directive.** Every operator
   message became a NEW capability + release. Nothing forced the
   LAST capability to be integrated into the spine before the
   NEXT one shipped. 39 versions; integration debt grew
   monotonically.
2. **Receipts measured modules, not composition.** Scribe,
   doctor, gauntlets, CI — all excellent at proving WHAT EXISTS
   is truthful and tested; all blind to whether the pieces
   COMPOSE. "27/27 gauntlet green" and "the graph and the
   pipeline never meet" were simultaneously true.
3. **No user ever used it.** Every run in every receipt was
   builder-verified. A product with zero users accumulates
   disjointedness silently — nothing forces the seams to meet.
4. **No real model ever ran.** With EchoModel as the only
   engine, every "end-to-end demo" was deterministic theater —
   honest theater (the receipts said so), but it meant the
   biggest gap (step 4) survived 39 releases because nothing
   ever needed it.
5. **Breadth was rewarded, integration wasn't.** Each ladder row
   celebrates a new pattern closed. There is no ladder row for
   "made the last three things work together" — so that work
   lost every scheduling conflict. v39.7 shipped a shopfloor
   before the shopfloor could see graph runs.

## 4. What the audit found when it actually looked (the hidden places)

**Latent defects that 577 tests never caught** (all fixed in
this release, each verifiable in the diff):

1. `storm.py` — the socket-blackout FAILURE path interpolated an
   unbound name: had that scenario ever failed, the harness would
   have crashed with NameError instead of naming the failure.
   The failure path had simply never been exercised. (Fixed:
   capture-inside-the-except; Python deletes `as` names at block
   exit.)
2. `pipeline.py` — a vestigial `dir()`-guarded CostTracker line:
   dead code that only worked because of a short-circuit.
3. `evaluation.py` — a quoted type annotation with no import:
   benign at runtime, wrong for every type checker.
4. `mcp_http_server.py` — a re-export removed by the hygiene
   sweep and caught by the SUITE (the one safety net that did
   its job; the sweep's casualty is now pinned by `__all__`).

**Structural debt (the honest register):**

- **Three graph engines** (orchestrator waves, colony, graphlang)
  — colony is demo+bench only.
- **Four event ledgers** (runs/*-events.jsonl, fleet bus,
  foreman history, boot ledger) — no unification.
- **Hooks reach the orchestrator only** — foreman, holdout and
  ignition emit no hook events.
- **cli.py is a 1,048-line god module** with 36 commands and
  drifted defaults (fixed one: aeos-graph-demo → aeos-demo).
- **Wording pins**: tests assert exact refusal strings; every
  wording change breaks tests (paid three times now).
- **The count fixed-point ritual**: every feature triggers
  six-file doc edits, and the README must claim the GREEN-state
  count because scribe counts passed+failed — subtle, wasteful.
- **Single-sandbox, single-author**: one builder wrote the code,
  the tests, and the audits. The fox designed the henhouse tests.
- **Test-count theater risk**: 579 tests sounds like proof; a
  large fraction pin demo-path behavior, not product behavior.

## 5. The honest scorecard (two numbers, one methodology each)

- **Mechanism coverage vs the specifications: ~85%.** Founding
  spec 57/57 (SPEC-AUDIT, machine-checked), TAC lessons re-audited
  (5 of 6 gaps closed), 41 principles, 18 dark-factory patterns
  (4 exceeds / 11 parity / 3 partial), zero-dep law enforced by
  doctor. The organs exist and are tested.
- **End-to-end product completeness: ~39%** (the spine matrix
  above). The organs have never been assembled, and the single
  load-bearing missing piece is step 4: **no real model has ever
  executed a real task through this system.**

Both numbers are true simultaneously. The receipts were honest
about the first and silent about the second — this report is the
correction.

## 6. The plan: close the gap to real execution

- **Phase A — this release (done):** hygiene zero (pyflakes
  87→0), three latent defects fixed, graph runs stream through
  the shopfloor, one demo factory (the demo path is a product
  path or it is a lie).
- **Phase B — THE SPINE (next):** one command, end to end:
  `aeos run --graph plan.dot` → the compiled graph executes on
  the REFERENCE pipeline (same roster, same handlers, same
  evidence law — not a demo) → bundle + leverage → memory and
  learning accumulate → events stream live → holdout verdict →
  receipt. Acceptance: an operator's DOT file produces a full
  evidence bundle in the shopfloor, live, with no demo roster
  anywhere in the path. Unify the event ledgers behind one bus.
- **Phase C — FIRST LIGHT:** one REAL model call through the
  whole spine — metered, dollar-capped, key never logged, the
  receipt disclosing model, cost and latency. **Requires the
  operator's explicit opt-in** (the paywall law stands). Until
  this happens, AEOS is a harness that has never worn a horse.
- **Phase D — THE FRONT DOOR DIET:** 36 commands → grouped
  surfaces (run / inspect / operate / extend); cli.py split by
  surface; consistent defaults everywhere.
- **Phase E — OUTSIDE EYES:** the standing offer becomes
  explicit — the operator runs ONE task themselves and files
  everything confusing; and the audit docs invite external
  review. One author's blind spots are the biggest hidden place
  of all.

## 7. What this report does not claim

It does not claim the prior receipts were dishonest — they were
narrow. It does not claim the mechanisms are fake — they are
tested and real. It claims exactly this: **a well-audited pile of
excellent parts is not a working product, and the distance
between the two is 5.5 spine steps, one real model call, one CLI
diet, and one honest operator session.** The order of work is
written. The treadmill is off.
