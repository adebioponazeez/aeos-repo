# ENVELOPE — measured performance at v34

*Receipts from `aeos bench --full` (10k scale), this machine class:
2 vCPU / 2GB RAM. Budgets are law (a blown budget fails the command);
limits below are ACCEPTED characteristics with named seams — not
surprises.*

| Case | n | Measured | Budget | Verdict |
|---|---|---|---|---|
| memory load (tolerant parse) | 10,000 | 0.065s | 10s | 150x headroom |
| recall FTS build + budgeted query | 10,000 | 0.064s (paid 94 tokens) | 10s | dividend holds at scale |
| fleet tail(20) after 10k events | 10,000 | ~0.000s | 0.05s | O(1) since v34 (was O(N)) |
| backup create (10k-state ws) | 10,000 | 0.024s (5.9MB tar) | 20s | deterministic, cheap |
| groom archive | 10,000 files | 0.347s (9,990 archived) | 30s | retention is fast |
| doctor sweep over all of it | 10,000 | 0.177s | 10s | audit is cheap |
| colony 100 nodes (fan-in) | 100 | ~0.000s, 2 waves | 5s | width is free |
| colony 60-deep chain (unit) | 60 | 60 waves | — | depth costs waves, now uncapped by default |

## Accepted limits (named seams, not bugs)

- **`MemoryStore.write()` rewrites the file**: one write at 10k
  records ≈ 0.10s (2.7MB rewrite). Fine at thousands; at hundreds of
  thousands, writes want an append journal — seam: `_flush`.
- **`replay()` reads the whole stream**: full replay at 10k events is
  fast; `tail()` is O(1) but complete-history reads grow linearly —
  seam: pagination if dashboards need it.
- **FTS5 index rebuild** is full-rebuild per `build()` (0.06s @10k);
  incremental sync is a seam, not a need, at this scale.

## Fixed by the gauge (on record)

- `EventBus.tail` read the entire stream to show 20 lines → now
  seeks the final 64KB block (O(1)); torn fragments dropped exactly
  as replay quarantines them.
- `Colony.run` capped waves at 50, blocking legitimate 60-deep
  chains → cap now scales with graph size (nodes + 10); cycles are
  caught by the no-progress break, which needs one idle wave.
