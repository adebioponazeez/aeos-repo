# AEOS — The AI Engineering OS

**Version 40.0.0 — The Front Door Diet. A working, model-agnostic operating system for agentic engineering — one command end-to-end, with its remaining gaps on the front page.**

A typed-envelope kernel (contracts, orchestration, context,
memory, skills, governance, evaluation, observability, harness,
entropy, learning, discovery) plus the platform around it:
factory, federation, live-model seam, companions, recall,
durable plans, hooks, declarative graphs, sealed holdouts and a
live shopfloor. **599 tests. Zero runtime dependencies.**

> The law of this codebase: **the harness is the product.** Models
> are interchangeable slots; every reliability property is enforced
> by deterministic code you can read end-to-end.

## The honest state (read this first)

AEOS is **two true things at once**: mechanism coverage against its
specifications is ~85% (machine-checked in
[docs/SPEC-AUDIT.md](docs/SPEC-AUDIT.md),
[docs/TAC-COMPLIANCE.md](docs/TAC-COMPLIANCE.md) and
[docs/DARK-FACTORY-VALIDATION.md](docs/DARK-FACTORY-VALIDATION.md))
— and, since v39.8.0, **end-to-end product completeness is ~53%**
(up from ~39% at the audit): one command (`aeos run --graph
plan.dot`) compiles an operator's workflow and executes it on the
reference pipeline — real roster, real handlers, real evidence law,
live events, no demo path anywhere — and, since v39.9.0, **the loop
closes**: each run's evidence-validated lessons are recalled into
the next run's plan (the architect cites what it applied in the
spec). What remains open is named in
[docs/STATE-OF-AEOS.md](docs/STATE-OF-AEOS.md):
**no real model has ever executed a task through this system** (the
live seam exists, metered and capped, awaiting the operator's
explicit opt-in — "First Light"); lessons reach the plan's context
and spec but cannot yet change executor *behavior* — that takes a
real model; and the foreman's repairs do not yet feed the planner.

## Quick start

```bash
pip install -e .                 # zero runtime dependencies
aeos                             # the grouped menu: RUN · INSPECT · OPERATE · EXTEND
python -m pytest                 # 599 proofs incl. the 9-scenario chaos storm, ~2 min

# THE SPINE — one command, end to end
aeos run --graph examples/ship-graph.dot --style examples/routing.style
                                 # your DOT workflow on the REFERENCE pipeline:
                                 # real roster + handlers + evidence law, live events
aeos run                         # ...or the reference objective through the same spine

# the other doors
aeos up [--workspace ws]         # staged boot: preflight · workspace · work · shutdown
aeos foreman --workspace ws --apply   # the autonomous operator: survey, fix, verify, receipt
aeos graph --file plan.dot       # compile + dry-run a DOT workflow (--run = the spine)
aeos stream --workspace ws       # the live shopfloor: SSE + console, read-only
aeos holdout --init && aeos holdout --run --workspace ws
                                 # sealed evaluation the agent cannot overfit to
aeos doctor                      # the system audits itself
```

## The command surfaces (39 commands, four modules)

Since v40.0.0 the CLI is one door, four rooms: `cli.py` is a thin
front door (registration + the grouped menu + routing) and behavior
lives in `cli_run`, `cli_inspect`, `cli_operate`, `cli_extend`
(ADR-057) — registration, menu and routing share one source of
truth, held by test.

| Surface | Commands |
|---|---|
| **Run** | `run` (the spine) · `up` · `run-demo` · `foreman` · `graph` · `factory-demo` · `colony` · `resume` · `soak` |
| **Inspect** | `doctor` · `scribe` · `triangle` · `leverage-audit` · `dividend` · `recall` · `bench` · `telemetry` · `eval` · `selftest` |
| **Operate** | `backup` · `restore` · `groom` · `storm` · `vault` · `save-proof` · `outbox` · `dashboard` · `console` · `stream` |
| **Extend** | `sponsor` · `skills via factory` · `mcp` (client/serve/serve-http) · `otel` · `companions` · `federation-demo` · `hooks` · `holdout` · `standards` · `fleet` · `live-check` |

(The Extend row lists `skills via factory` as a capability — the
command is `factory-demo`. Retiring or merging commands remains
open for the Outside-Eyes round, informed by a real operator's
confusion report rather than a builder's guess.)

## What is proven (reproduced in `evidence/`)

- **599/599 tests passing** (+1 opt-in live smoke) — the chaos
  storm runs inside the suite: SIGKILL mid-run ×3 with recovery,
  torn power-cut files quarantined, disk-full leaving evidence
  byte-intact, garbage inputs verdicted, a full run under 256MB,
  and a total socket blackout completed.
- **Constraint batteries, run for real:** an 11-group production
  gauntlet (27/27) and a 9-group field gauntlet (20/20 — empty
  env, read-only workspace/HOME, true tmpfs ENOSPC, unicode under
  LC_ALL=C, non-root) — which between them found and fixed eleven
  real defects across v39.2–v39.4.
- **The wheel, not just the checkout:** installed and verified on
  real CPython 3.10/3.11/3.12 on every release since v39.3.
- **Reference run:** 7/7 tasks, governor earns L5 from
  reliability 1.0, leverage ratio **7.0**, full evidence bundle.
- **Factory, no token:** proposals only — every install refused
  and logged. **With a scoped token:** exactly the scoped
  capability installed, one use.
- **Federation:** foreign unit → quarantined; install refused with
  a valid token in hand; local revalidation → sponsored install.

## The four invariants (unchanged since v1, still tested)

1. **No envelope, no result** — typed returns; gates check claims.
2. **No authority without a boundary** — `writes:` enforced post-hoc.
3. **No autonomy without reliability** — the ladder moves on evidence.
4. **No memory without validation** — failure never becomes folklore.

Plus the fifth, hardest-won: **no self-modification without a
spent human token.**

## Milestones (full history in [CHANGELOG.md](CHANGELOG.md))

| Era | Versions | What landed |
|---|---|---|
| Kernel | v1–v6 | Typed envelopes, governor L0–L7, gates, factory + sponsorship, meta-loop |
| Platform | v7–v20 | Live-model seam, federation, companions, triangle, dividend, recall, fleet, resume, leverage rubric, standards |
| Protocols | v21–v31 | MCP client + read-only server (both transports), OTel, colony, vault, storm, shipyard, soak, consulate |
| Self-audit | v32–v38 | Doctor, charter machine-checked, gauge, scribe, notary, outbox, ignition, curriculum |
| Production proofs | v39.0–v39.2 | Foreman, cross-validation from source PDFs, the production gauntlet |
| Real environments | v39.3–v39.4 | Field test (wheel verified on 3.10–3.12), the sealed holdout |
| Composition era | v39.5–v39.7 | Hooks + recursion, declarative graph language, live shopfloor |
| **The Reckoning** | **v39.7.1** | **The end-to-end audit: spine scored, latent defects fixed, hygiene zero, the integration plan** |
| **The Spine** | **v39.8.0** | **One command end-to-end: operator graphs execute on the reference pipeline — real artifacts, live events, contract law at the door** |
| **The Loop Closes** | **v39.9.0** | **Runs recall their predecessor's validated lessons into the next plan; the architect cites what it applied** |
| **The Front Door Diet** | **v40.0.0** | **cli.py split: one thin door (grouped menu, routing) + four surface modules; registration, menu and routing held equal by test** |

## Repository layout

```
src/aeos/            # 72 modules: kernel (v1) + platform (v2–v39) + cli front door + 4 surfaces
tests/               # 599 tests incl. adversarial + e2e + factory + federation + chaos storm
evidence/            # captured receipts: gauntlets, field test, holdout, shopfloor, save-proofs
docs/                # STATE-OF-AEOS (the audit), architecture, security, runbook, dossier,
                     # principles charter, TAC audit, global benchmark, spec audit,
                     # dark-factory validation, publishing guide, 57 ADRs
examples/            # ship-graph.dot + routing.style (the declarative workflow)
harness → /home/user/harness/   # the gauntlet programs (kept outside the repo)
book/                # Volumes I–IV + v11 addendum, HTML + markdown
AGENTS.md            # short repo context for coding agents
CHANGELOG.md         # every version, earned by tests
```

## Lineage and license

Original code, MIT. Principles absorbed with attribution from the
public canon — `disler/super-simple-software-factory` (agent
proposes / code disposes; typed envelopes; evidence gates; write
boundaries), `fusion-harness`, `the-verifier-agent`, MCP/SEP-2085
posture, the 2026 harness-engineering canon (IndyDevDan, Cole
Medin, the dark-factory literature — mapped in
[docs/DARK-FACTORY-VALIDATION.md](docs/DARK-FACTORY-VALIDATION.md)).
See `docs/RESEARCH-DOSSIER.md` and `docs/adr/`.
