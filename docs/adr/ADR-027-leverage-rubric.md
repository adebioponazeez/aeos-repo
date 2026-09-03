# ADR-027: Mindsets become rubrics

**Status: ACCEPTED (v18.0)**

## Context
"The 12 leverage points" taught as a mindset cannot be audited; a
vibe is not a leverage point.

## Decision
Each of the 12 points is a named row bound to one AEOS mechanism,
checked against artifacts ON DISK (bundle keys, FTS index, event
stream, checkpoint, STANDARDS.md). PASS requires evidence; GAP names
what is missing. The rubric runs offline against any workspace.

## Alternatives
Scoring agent transcripts with a model: rejected — an auditor that
can be charmed is not an auditor.

## Consequences
`test_empty_workspace_scores_low`, `test_full_workspace_scores_high`,
`test_every_row_names_its_evidence`.
