# ADR-047: The Curriculum — the founding spec, audited and answered

**Status: ACCEPTED (v38.0.0)**

## Context

The repository's founding document is a 48-page master-builder
specification ("Untitled document (1).pdf") whose final command is
*"Take this specification and actually build the entire thing now,"*
and whose Requirement 54 orders, after the first build: *"AUDIT
EVERYTHING — what is redundant, what is missing, what is unsafe,
what is outdated."* Thirty-seven versions of system-building later,
the operator's instruction was "try again" — decoded against that
document, the honest reading is: run the builder loop's second
turn. The system side of the spec was overwhelmingly satisfied; the
book side had a named gap — the 13-phase curriculum with mandated
per-phase sections (Requirements 30/31/52) — and no
requirement-by-requirement audit existed.

## Decision

1. **`docs/SPEC-AUDIT.md`**: all 57 numbered requirements of the
   founding spec carry verdicts — SATISFIED (with the artifact
   named), PARTIAL (with the reason), or GAP (kept visible). The
   16-clause Definition of Done is answered clause by clause; the
   12-rung project ladder is mapped to shipped versions (rungs
   11–12 honestly marked as the named frontier).
2. **Volume IV — The Curriculum** (`book/parts-v4/`): the mandated
   13 phases, each carrying the seven required sections —
   Objectives / Theory / Practice / Projects / Evaluation /
   Capabilities Unlocked / Advanced Project — grounded exclusively
   in shipped artifacts (modules, commands, tests). Phase 13 claims
   no unlocked capability: the frontier is drawn accurately.
3. **Machine-checks, not prose promises** (`test_v38_curriculum.py`):
   all 13 phases × 7 sections present; every `aeos <verb>` the
   curriculum teaches exists in the live CLI (the scribe's law,
   extended from the README to the book); the audit covers all 57
   requirements with no silent drops; the ladder maps all 12 rungs;
   the DoD's 16 clauses are answered one by one.

## Consequences

The book is now four volumes; the print pipeline builds volume-IV
(QUARTA). The audit becomes a standing artifact: re-audit at every
major version, and gaps may close but never quietly. Honest gaps on
the record at v38: total book length sits well under the spec's
~400 pages (the spec's own anti-inflation rule is honored instead —
depth over padding); project-ladder rungs 11–12 (autonomous
business workflow, AI-native enterprise) are not built, though
everything beneath them is; live frontier research remains opt-in
by law (ADR-039/040); PyPI activation remains an operator decision.

Charter principle 40: the founding contract is audited, not assumed.

## Tests

`test_all_thirteen_phases_present`, `test_every_phase_carries_the_seven_mandated_sections`,
`test_every_command_in_the_curriculum_is_real`, `test_the_frontier_is_honestly_marked`,
`test_spec_audit_covers_all_requirements`, `test_every_verdict_is_real_artifact_or_honest_gap`,
`test_project_ladder_twelve_rungs_mapped`, `test_definition_of_done_sixteen_clauses_answered`.
