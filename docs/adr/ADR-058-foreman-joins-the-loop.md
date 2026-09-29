# ADR-058: The foreman joins the loop — repairs feed the next plan

**Status: ACCEPTED (v40.1.0)**

## Context

The audit's last named loop gap (spine step 9, residual after
ADR-056): "the foreman heals workspaces, but nothing it learns
changes the next plan." The foreman's memory was a private ledger
(`.aeos/foreman/history.jsonl`, signature-deduped counts) that the
pipeline never read — one of the four disjoint event ledgers, and
the reason the autonomous operator and the execution spine could
not compound.

## Decision

1. **The foreman writes its outcomes into WORKSPACE memory** — the
   same `MemoryStore` the pipeline recalls — as
   `lesson::foreman::<kind>` EPISODIC records, source `foreman`,
   confidence 0.7 resolved / 0.5 open, one record per finding kind:
   `MemoryStore.write` keys by record key, so the newest outcome
   replaces the stale one (updated, never duplicated).
2. **Apply-mode only.** Survey mode writes nothing to memory: a
   foreman that only LOOKED learned nothing it can claim; a foreman
   that ACTED owes the workspace its lesson. (Survey keeps its own
   bookkeeping ledger, as before — disclosed.)
3. **The pipeline recalls the foreman's notes on the same rail**
   (ADR-056): the most recent three `lesson::foreman::*` records
   enter the ContextOS as `authority="foreman"` units — they match
   no plan term (workspace state, not task/agent names), so they
   get their own explicit recall, capped separately.
4. **The architect discloses them in the spec**: `spec/graph.json`
   gains `workspace_notes` (distinct from `prior_lessons` — plan
   experience vs workspace state), with envelope evidence; the
   bundle records `memory.foreman_lessons` and
   `memory.foreman_notes_in_spec`; the spine prints the count.
5. **Best-effort write, disclosed**: on a full disk the lesson
   write is skipped and the verdict survives — the same law as the
   foreman's history writes.

## What this does NOT claim

Structural closure again, honestly: the notes reach the plan's
context and are disclosed in its spec. A foreman note changing what
the plan DOES requires a model that acts on what it reads — First
Light, operator opt-in. And the foreman's own history ledger still
exists alongside memory (unification of the event ledgers remains
open, named in the state report).

## Consequences

- After `aeos foreman --apply`, the very next `aeos run` in that
  workspace recalls the foreman's lessons and its spec carries the
  workspace notes — pinned by test, including the read-only survey
  guarantee and the update-not-duplicate law.
- End-to-end completeness re-scored ~53% → ~56% (state report).
