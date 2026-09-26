# AEOS — The AI Engineering OS

**Version 39.7.1 — The Reckoning. A working, model-agnostic operating system for agentic engineering — audited end-to-end, with its gaps on the front page.**

A typed-envelope kernel (contracts, orchestration, context,
memory, skills, governance, evaluation, observability, harness,
entropy, learning, discovery) plus the platform around it:
factory, federation, live-model seam, companions, recall,
durable plans, hooks, declarative graphs, sealed holdouts and a
live shopfloor. **579 tests. Zero runtime dependencies.**

> The law of this codebase: **the harness is the product.** Models
> are interchangeable slots; every reliability property is enforced
> by deterministic code you can read end-to-end.

## The honest state (read this first)

AEOS is **two true things at once**: mechanism coverage against its
specifications is ~85% (machine-checked in
[docs/SPEC-AUDIT.md](docs/SPEC-AUDIT.md),
[docs/TAC-COMPLIANCE.md](docs/TAC-COMPLIANCE.md) and
[docs/DARK-FACTORY-VALIDATION.md](docs/DARK-FACTORY-VALIDATION.md))
— and **end-to-end product completeness is ~39%** (the spine
matrix in [docs/STATE-OF-AEOS.md](docs/STATE-OF-AEOS.md)): the
parts are tested but not yet assembled into one flow, and **no
real model has ever executed a task through this system** (the
live seam exists, metered and capped, awaiting the operator's
explicit opt-in). The full audit, the root causes, and the
close-the-gap plan (Spine → First Light → Front Door Diet →
Outside Eyes) are in the state report.

## Quick start

```bash
pip install -e .                 # zero runtime dependencies
python -m pytest                 # 579 proofs incl. the 9-scenario chaos storm, ~2 min

# the front doors
aeos up [--workspace ws]         # staged boot: preflight · workspace · work · shutdown
aeos foreman --workspace ws --apply   # the autonomous operator: survey, fix, verify, receipt
aeos graph --file examples/ship-graph.dot --style examples/routing.style --run
                                 # declarative DOT workflow; clusters are nested harnesses
aeos stream --workspace ws       # the live shopfloor: SSE + console, read-only
aeos holdout --init && aeos holdout --run --workspace ws
                                 # sealed evaluation the agent cannot overfit to
aeos run-demo                    # the reference loop end-to-end, evidence bundle
aeos doctor                      # the system audits itself
```

## The command surfaces (36 commands, grouped)

| Surface | Commands |
|---|---|
| **Run** | `up` · `run-demo` · `foreman` · `graph` · `factory-demo` · `colony` · `resume` · `soak` |
| **Inspect** | `doctor` · `scribe` · `triangle` · `leverage-audit` · `dividend` · `recall` · `bench` · `telemetry` · `eval` · `selftest` |
| **Operate** | `backup` · `restore` · `groom` · `storm` · `vault` · `save-proof` · `outbox` · `dashboard` · `console` · `stream` |
| **Extend** | `sponsor` · `skills via factory` · `mcp` (client/serve/serve-http) · `otel` · `companions` · `federation-demo` · `hooks` · `holdout` · `standards` · `fleet` · `live-check` |

(Consolidation of these surfaces is planned — see the state
report, Phase D.)

## What is proven (reproduced in `evidence/`)

- **579/579 tests passing** (+1 opt-in live smoke) — the chaos
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

## Repository layout

```
src/aeos/            # 68 modules: kernel (v1) + platform (v2–v39)
tests/               # 579 tests incl. adversarial + e2e + factory + federation + chaos storm
evidence/            # captured receipts: gauntlets, field test, holdout, shopfloor, save-proofs
docs/                # STATE-OF-AEOS (the audit), architecture, security, runbook, dossier,
                     # principles charter, TAC audit, global benchmark, spec audit,
                     # dark-factory validation, publishing guide, 54 ADRs
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
