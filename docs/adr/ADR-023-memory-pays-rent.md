# ADR-023: Memory must pay rent — the dividend economy

**Status: ACCEPTED (v14.0)**

## Context
ClaudeMem demonstrated the field economics: capture raw context,
distill to ~500-token typed observations, retrieve layers not
transcripts — ~10x token efficiency. The underlying principle has a
name worth owning: **negative marginal token consumption** — each
additional run should consume FEWER tokens than the no-memory
baseline, because distilled recall replaces raw re-reading. Most
agent memory systems measure how much they store; almost none measure
what storage returns.

## Decision
Four mechanisms, one economy:
- **`MemoryDistiller`** — repeated episodic lessons compress into one
  semantic record per (task, outcome): tightest phrasing survives,
  validation counts attach as evidence (the canonical-write gate
  applies), and the compression ratio is MEASURED, never claimed.
- **`stable_prefix()`** — canonical-JSON (sorted keys, tight
  separators) stable-first assembly: byte-identical prefixes across
  runs make provider prompt caches eligible; volatile content rides
  last where it invalidates nothing before it.
- **`TokenLedger`** — per task-class curves of baseline (naive
  re-read) vs all-in (recall + amortized storage overhead).
  `negative_marginal` is a computed fact, and the cumulative dividend
  is reported per class.
- **`rent()`** — the law: every stored byte is token-weight carried
  into future assemblies; a canonical record never recalled is
  SQUATTING and flagged for the entropy path. Memory pollution is an
  economic crime, not just a confidence problem.

## Alternatives
- Vector-store recall with raw transcripts kept hot: rejected as the
  default — retrieval without distillation relocates the cost, it
  does not reduce it.
- LLM-powered summarization (ClaudeMem's compressor): excellent in
  production; deliberately not used here because the ledger must be
  deterministic to be testable — the distiller keeps the tightest
  phrasing instead of generating one.

## Tradeoffs
(+) The dividend is computed from measured record tokens — reproducible.
(−) Deterministic distillation compresses less artfully than an LLM
  summarizer; the seam for one is `MemoryDistiller.distill_lessons`.

## Consequences
`test_five_episodes_become_one_semantic_record`,
`test_same_stable_set_same_prefix_different_tail`,
`test_marginal_is_negative` (delta −1850 on the reference curve),
`test_unrecalled_memory_is_squatting`.
