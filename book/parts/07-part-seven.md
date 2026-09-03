# PART IX — IMPLEMENTATION: THE SYSTEM, THE RUN, THE ROADMAP

## Chapter 42. The Repository Tour

Two thousand and twenty lines of Python across fifteen modules, zero
runtime dependencies, sixty-eight tests. This is the whole system,
and its size is the point — every line is auditable by one patient
human in an afternoon, which is the only trust model that scales
down to one person and up to a company.

```
src/aeos/
├── contracts.py       (≈230 LOC) types that cross boundaries
├── models.py          (≈120)     the model-agnostic seam + EchoModel
├── observability.py   (≈90)      append-only structured event log
├── context_os.py      (≈160)     budgeted, classified, fresh context
├── memory.py          (≈110)     six classes, evidence-gated writes
├── skills.py          (≈110)     versioned capabilities, win-rates
├── orchestrator.py    (≈250)     waves, validation, repair
├── governor.py        (≈150)     ALLOW/CHECKPOINT/DENY + reliability EMA
├── evaluation.py      (≈150)     gates, closed verdict vocabulary
├── harness.py         (≈160)     checkpoints, boundaries, rollback
├── entropy.py         (≈80)      the decay scanner
├── learning.py        (≈70)      evidence-gated promotion
├── discovery.py       (≈50)      the measured ladder
└── pipeline.py        (≈260)     the reference loop wiring it all
```

Around the code: `AGENTS.md` (the deliberately short 2026-standard
context file), `docs/ARCHITECTURE.md` (this book's map, compressed),
`docs/SECURITY.md` (threat model), `docs/RUNBOOK.md` (failure
playbook: repair the *correct* layer), eight ADRs (the decision
record with alternatives and tradeoffs), and `evidence/` — captured
test runs and reference-run bundles, the repository's ability to
prove itself without being re-run.

Reading order for a new engineer, tested on the author: contracts →
pipeline → governor → orchestrator → evaluation → harness; then the
tests for each, which are the executable specification. If you read
only one file, read `pipeline.py`: it is the entire book in one
screen.

## Chapter 43. The Run, Witnessed

What follows is the reference run's actual evidence, reproduced from
`evidence/run-bundle.json`, annotated like a flight recorder:

```
accepted:              True
summary:               7/7 tasks succeeded in 7 waves, 0 repair cycles, 1.01s
states:                define-objective SUCCEEDED
                       research SUCCEEDED
                       architect SUCCEEDED
                       build-core SUCCEEDED
                       build-cli SUCCEEDED
                       evaluate SUCCEEDED
                       release SUCCEEDED
observability:         37 events; success_rate 1.0
governor_level:        L5_CONTINUOUS_AUTONOMY   (started at L3)
governor_reliability:  1.0
learning_lessons:      7 recorded
checkpoints:           7 (one per writing phase)
```

The events underneath it, in order of appearance:
`task.started` → `task.succeeded` (executive) → `wave.start`
(research) → gates `gate.checked` per task → `governor.allow` for
NETWORK at checkpointed resolve → `boundary` snapshots enforced five
times with zero violations → `run.finished accepted=True` →
`governor.level L3→L4→L5` promotions interleaved throughout.

The artifacts on disk after the run — the part no diagram can fake:
`research/brief.json` (three sourced findings with confidences),
`spec/graph.json` (the validated plan), `seed/core.py` +
`seed/cli.py` + `tests/test_core.py` (the work itself),
`evaluation/report.json` (three evidence checks, verdict PASS),
`release/NOTES.md` (quoting the verdicts truthfully — the release
agent's contract forbids packaging anything the evaluator did not
pass).

And the closing loop, in the same bundle: seven lessons recorded
episodically; successes with evidence promoted to procedural memory;
discovery's proposals (six signatures at threshold, led by
`phase:builder:WRITE` at 8 repetitions — "codify the procedure");
entropy findings empty this run (a young system; check back after a
quarter).

One second of wall-clock time. Zero API calls. Every claim in this
book either ran like this or is labeled as not having run.

## Chapter 44. The Honest Gaps and the Road to v3.0

A system that hides its gaps is asking to be trusted where it cannot
verify. The gaps, stated as engineering work with exit criteria:

**v1.1 — Hardening (weeks).** Secret handling at the adapter seam
(events must be structurally incapable of carrying credentials);
entropy coverage for the remaining findings (architectural drift,
weak tests, unused tools); gate library growth (schema validation,
diff-quality checks). Exit: red-team suite green, zero
`text=True`-style leaks by construction.

**v2.0 — Multi-Agent Platform (a quarter).** Real `ModelAdapter`s
behind the existing seam (the fusion pattern — one architect, several
builders, opinions fused before the gate); git-as-checkpoint at repo
scale (ADR-006's planned successor); durable cross-process runtime —
the event log is already replayable, the runtime is not yet
resumable; MCP adapter at the handler seam under ADR-007, inheriting
every guarantee unchanged; first UI over the JSONL (the SSSF
visualizer pattern: poll the log, render the waves).

**v3.0 — Autonomous Capability OS.** L6/L7 in production posture:
discovery proposing *and* — above explicit human sponsorship only —
executing promotions; the capability catalog as a first-class object
(the-library pattern: private-first distribution of skills/agents
across teams); organizational multi-tenancy with per-tenant
governors; the meta-loop measured: this system rebuilding itself
under its own governance, which is the sentence the founding spec
ends on and the sentence this roadmap exists to earn.

What will *not* change across all three: the four invariants (no
envelope no result; no authority without boundary; no autonomy
without reliability; no memory without validation), the closed
verdict vocabulary, fail-closed unknowns, and the rule that every new
capability ships with the test that proves it and the ADR that
explains it. The architecture is designed so growth adds rungs, never
exceptions.

---

## Closing: The Human Moves Upward

The founding specification's final image is worth ending on, because
after forty-four chapters of machinery it is easy to forget what
the machinery is *for*:

*The human moves upward. The machines execute downward. The system
learns between them.*

Not "AI writes code." Not "agents work together." Not even "AI runs
a software company." The objective was always the compounding one:
human intent → intelligent system design → autonomous execution →
verified outcomes → organizational memory → learning → new
capabilities → 10,000,000× human effectiveness.

Every mechanism in this book — envelopes, gates, boundaries,
governors, ladders, lessons — exists to make one move safe: the human
letting go of a rung because the system below it has *earned* the
weight. Build systems that build systems. Then systems that improve
systems. Then systems that discover what systems should exist. The
ladder is long. It is also, finally, mechanical.
