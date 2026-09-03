# PART IV — RESEARCH AND OPERATIONS

## Chapter 10. Autonomous Research with Untrusted Sources

v5's research pipeline applies the anti-hallucination law one layer
earlier than the gates: at *ingestion*. Every finding from the search
tool carries a source and a confidence derived from the source's
measured authority — and anything below threshold lands in `unverified`,
never in the brief's conclusions.

The deterministic demo search ships three sources on purpose: a spec
document (authority 0.95), a research summary (0.9), and a forum hot
take (0.2). The pipeline's verdict on them is the test:
two findings accepted, the lore quarantined, average confidence of the
accepted set ≥0.8 (`test_low_authority_sources_go_to_unverified`).
When the governor denies the tool call outright — a network-restricted
tenant, say — the pipeline returns an *empty* brief, which upstream
evaluates as UNVERIFIED: **no sources, no brief, no fabrication**
(`test_tool_denied_means_empty_brief`).

This is the 2026 research-agent discipline in miniature: authority
caps confidence, confidence gates inclusion, and the absence of
evidence is a verdict, not a gap to be filled with confident prose.

## Chapter 11. Operations: Sweeps and the Regression Book

Entropy control graduated from "a scan at the end of a run" to a
*schedule* — the posture Chapter 27 of Volume I argued for
(continuous small corrections, never quarterly archaeology). The
`SweepScheduler` registers jobs with intervals and executes exactly
the due ones — `test_due_jobs_run_and_not_before` pins the "not
before" half, because a scheduler that fires early is just a loop with
ambitions.

The `RegressionBook` is the Braintrust pattern at repository scale: a
production failure, once recorded against a file pattern, becomes a
**permanent gate**. `regression_gate` in the gate library consults the
book; an envelope whose changed files match a recorded signature fails
—— the same mistake cannot ship twice
(`test_recorded_failure_blocks_matching_change`). The book persists as
JSONL, so organizational scar tissue survives restarts.

Together they close the operations loop: sweeps shrink the entropy the
system produces; the regression book converts the failures that leak
through into permanent immunities. Reliability stops being a property
of heroics and becomes a property of the ledger.

# PART V — THE META-LOOP

## Chapter 12. Self-Improvement Inside Hard Floors

v6 is the version the whole architecture was built to make *safe*:
the system proposing changes to itself. `MetaLoop.analyze()` reads the
skills registry and the governor's reliability and returns proposals
of exactly three kinds — retire a failing skill, tune the promotion
threshold within bounds, or draft an ADR stub for human review. Each
kind is bounded by **data floors**:

- Retirement requires ≥5 uses AND ≤0.4 win-rate — enough history to
  condemn, not a bad first date (`test_young_skill_not_condemned`).
- Threshold tuning is clamped to [0.90, 0.99]; a forged value outside
  the clamp is refused **even with a valid sponsorship token** — the
  bounds outrank the human's key, deliberately, because the floors are
  what the key *means* (`test_out_of_bounds_threshold_refused_even_
  with_token`).
- Application always requires a spent, scoped, one-shot sponsorship
  token (`test_apply_requires_sponsorship`), and every applied change
  writes an ADR stub so the change is reviewable after the fact.

Note what the meta-loop *cannot* propose: there is no proposal kind
that reaches the immutable rows — the high-impact checkpoint-forever
rule, fail-closed unknowns, the closed verdict vocabulary.
Self-improvement without floors is just a runaway system with good
intentions; the floors are the feature (ADR-015).

This is L6 in the spec's ladder, earned rather than declared: the
system improves itself exactly as much as its evidence and its humans
can defend, and not one parameter further.
