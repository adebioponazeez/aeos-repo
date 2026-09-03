# PART VI — THE FACTORY

## Chapter 13. L7: The System That Designs Systems

v7 is the spec's terminal object, shipped: *"systems that discover
what systems should exist."* The `CapabilityFactory` is a five-stage
pipeline, and every stage emits evidence into the event log:

**1. Measure.** Discovery reads the pattern history — which
`phase:role:class` signatures repeated past threshold. No signature,
no candidate; enthusiasm is not a measurable quantity.

**2. Design.** `design_agent(signature)` derives a *conservative
contract* from the signature itself: the action class determines the
boundary. A `phase:triage:WRITE` pattern yields `triage-specialist`
with `writes: ["triage/*"]`; a READ pattern yields an agent with no
write surface at all. The design is template-shaped on purpose —
templates are auditable, and novel architectures are a human's job
(ADR-016's honest tradeoff).

**3. Sandbox-validate.** The design must pass the full gauntlet in a
scratch workspace: contract validation (all thirteen fields, no
blanks), then a real smoke task through the real orchestrator, harness,
governor and gates on the deterministic engine. A candidate whose
sandbox verdict is anything but PASS **cannot reach the install
branch — there is no override** (`test_failed_sandbox_never_installs`
proves it by breaking the contract on purpose).

**4. Propose.** Survivors are proposed with their evidence: measured
signature, sandbox verdict, contract.

**5. Install — under sponsorship.** A scoped, one-shot token (ADR-013)
moves the agent into the roster and publishes a content-hashed catalog
unit. Without a token: proposals only, refusals logged
(`test_install_refused_without_sponsorship`).

## Chapter 14. The Run, Witnessed Twice

The demo runs the factory twice, and the difference between the two
runs *is* the chapter:

**Without a token** (`aeos factory-demo`): two candidates measured and
designed (`evaluator-specialist`, `builder-specialist`), two sandbox
validations PASS, two proposals — and **zero installs**. Every install
refused: *"sponsorship required for factory:install:…"*. The system
did everything it could and then stopped at the one door it cannot
open for itself.

**With a scoped token** (`--token`, registered for exactly one
candidate): the history run completes, the factory validates both
candidates, installs `evaluator-specialist` into the roster and the
catalog — and **refuses `builder-specialist` on scope mismatch**, in
the same breath, because one token is one power, not a mood
(`test_full_run_with_valid_token_installs`).

Read the pair slowly, because it is the entire safety thesis in
microcosm: the system's autonomy expanded to cover *designing its own
coworkers*, and the expansion itself stayed inside the same grammar —
evidence, bounds, spent human authority — that governed a single file
write in Volume I. The ladder did not weaken as it got taller.

## Chapter 15. The Studio: Observability You Can Hold

The last v7 artifact is a dashboard generator, and it is deliberately
the least clever module in the OS: `aeos dashboard` renders the run's
evidence bundle and event log into a single self-contained HTML file —
inline styles, embedded data, no network, no dependencies, opens
offline, prints to PDF.

The choice is a protest against a trend: agent observability is
drifting toward platforms, and platforms drift toward *someone else's*
diagram of your system. The studio's position: a run's report should
be as portable as its evidence — a file you can hold, archive, attach
to an incident, or hand to an auditor who trusts nothing but what they
can open. The heavy tooling (OTel collectors, trace backends) has its
place behind the seam; the *floor* of observability is a static page
anyone can read with the lights off.

The dashboard shows what the run actually argued: task states with
attempts, the governor's earned level and live reliability, cost and
leverage, the event timeline. If Volume I's event log made runs
*replayable*, the studio makes them *presentable* — the difference
between data and testimony.
