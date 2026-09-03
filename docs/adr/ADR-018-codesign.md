# ADR-018: Co-design — the machine proposes a slate, the human shapes it

**Status: ACCEPTED (v9.0)**

## Context
v7's factory designs from one conservative template: safe, samey. Real
architecture is a set of tradeoffs; a single template hides the choices
instead of surfacing them.

## Decision
For each measured signature, generate three coherent *philosophies*:
**conservative** (the proven template), **minimal-privilege** (no write
surface at all; escalates on any doubt), **reviewer-first** (adds an
independent review artifact to the output contract). Score them with
least-privilege weighting (writes 0.5, evaluation strength 0.3,
escalation off-ramps 0.2), sandbox-validate ALL of them, and present
the ranked slate. The human sponsors exactly one variant — the
sponsorship scope includes the variant label
(`codesign:<agent>:<variant>`), so choosing is spending.

## Alternatives
- Generative design space search (mutate contracts, evolve): rejected
  for v9 — search needs a fitness landscape we only partially have;
  three honest philosophies beat thirty-six perturbations.
- Human designs from scratch: still available; the slate is a
  starting point, not a cage.

## Tradeoffs
(+) The design conversation becomes explicit: three options, one
  receipt, zero ambiguity about who chose.
(−) Variants share the template's ceiling — genuinely novel shapes
  remain human work (the honest gap, again).

## Consequences
`test_least_privilege_ranks_first`, `test_choice_with_token_and_scope`,
`test_wrong_variant_token_scope_refused`.
