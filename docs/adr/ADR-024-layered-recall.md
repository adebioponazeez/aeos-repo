# ADR-024: Recall pays in layers

**Status: ACCEPTED (v15.0)**

## Context
ClaudeMem's third leg (with distillation and economics) is layered
retrieval: pay for keys before snippets before transcripts. Our
memory recall was a linear key scan — retrieval located records but
never priced the layers.

## Decision
`RecallIndex` over stdlib `sqlite3` FTS5 (compiled into CPython, zero
new dependencies): three budgeted layers — L0 key hits (~1 token
each), L1 FTS MATCH snippets trimmed to remaining budget, L2 the full
top record only when budget remains. The budget is law: a snippet
that does not fit is skipped, an empty layer is not reported. Recall
never mutates the store; rebuild is idempotent; savings vs full scan
ship in every bundle's dividend.

## Alternatives
Vector embeddings + ANN store: rejected as default — a dependency and
a model at query time for a corpus whose size does not yet justify
it; FTS5 + distillation covers the need deterministically.

## Consequences
`test_snippets_respect_the_budget`, `test_layered_recall_beats_full_scan`,
`test_full_layer_only_when_budget_remains`, `test_recall_never_mutates_the_store`.
The seam for embeddings is `RecallIndex.recall`'s L1 query.
