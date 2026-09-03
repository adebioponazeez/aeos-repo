# ADR-022: The Triangle — control/cost/speed as one dial, measured

**Status: ACCEPTED (v13.0)**

## Context
The tradeoff is physics: more control means less speed, and control
costs speed (and money). Systems fail at the seams when each knob —
autonomy, gates, parallelism, isolation, budget, model choice — is
tuned independently by whoever touched it last. And teams argue about
the trade in the absence of measurement.

## Decision
One named stance moves every knob together. `RunProfile.preset()` of
CONTROL (checkpoint-heavy, strict gates, process isolation, fusion,
serialized), BALANCED (the v1–v12 default), SPEED (wide parallelism,
high autonomy ceiling, lean-but-floored gates, fast models), COST
(tight budget, no fusion, cheap routing). **Floors are immutable**:
no profile may remove the `artifacts_exist`/`claims_are_backed` gates,
start above L5 (L6/L7 are earned by evidence, never selected), bypass
write boundaries, or touch checkpoint-forever classes. The dial bends
the trade; it cannot bend the law.

`measure_triangle()` computes the run's ACTUAL control (gate density,
boundaries enforced, permission friction, isolation), cost (metered
dollars + tokens), and speed (tasks/sec, waves, clock) from the event
log and economics — with a plain-language "THE TRADE:" line naming
what was bought and what it cost. Every run's bundle now carries its
measured triangle; `aeos triangle` re-renders it.

## Alternatives
- Per-knob config files: rejected — independent knobs are how the
  trade becomes accidental.
- Auto-tuning the stance from history: a v14+ candidate via the
  meta-loop, inside its floors — but the *first* version of a dial
  must be honest and manual.

## Tradeoffs
(+) The argument "should we be faster or safer?" becomes a named
  stance plus a measured receipt — decided per run, reviewable after.
(−) Stances are coarse by design; fine mixing uses `overrides`
  through the same validation.

## Consequences
`test_floor_gates_survive_every_stance`,
`test_no_profile_starts_above_l5`,
`test_control_measures_more_control_than_speed` — the thumbnail's
law, now a test.
