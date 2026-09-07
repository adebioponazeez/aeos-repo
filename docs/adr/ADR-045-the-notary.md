# ADR-045: The Notary — the SEF-X handover disposition

**Status: ACCEPTED (v36.0.0)**

## Context

The SEF-X / OMNI-OS V22 "Master Production Handover & Lifecycle
Specification" (33 pages, received 2026-09-07) demands, among other
things: completion certificates anchored to Merkle roots ("no task
completes on conversational confirmation alone"), an edge-resilient
SQLite WAL outbox for metered-bandwidth environments, permanent
capability abstractions over replaceable implementations — and, in
the same pages, H-JEPA latent-space planning with energy bounded at
0.085, PRM-guided MCTS at 12,000 rollouts/sec, Arrow Flight IPC at
12.8 GB/s, Firecracker/eBPF sandboxing, and 99.98% convergence on
benchmarks it names but does not run. The instruction was: "do the
above to make aeos more robust."

A spec like this gets exactly one honest treatment: take the
engineering, refuse the theater, and put both decisions on the
record. Anything else is either cargo-culting impossible numbers or
quietly ignoring the request.

## Decision

### ADOPTED — with mechanisms, tests, and receipts

| SEF-X demand | aeos mechanism (v36) |
|---|---|
| "No task completes on conversational confirmation" (Law 5, Tier 4, FR-04) | `saveproof.py` + `aeos save-proof`: pre/post Merkle roots (`merkle.py`) + a green proof command = a **certificate**. Outcomes are NAMED — `verified` / `drifted` (files listed) / `tests-failed` / `timed-out` — never narrated. Ledger: `evidence/save-proofs/`, excluded from the root it certifies (the receipt about the tree is not the tree). |
| Edge outbox, WAL, idempotent replay (§5.1, §6.5, NFR-05) | `outbox.py` + `aeos outbox enqueue|status|flush`: SQLite WAL, content-hash idempotency keys (same record twice = ONE row), bounded retries with dead letters, flush to ONE explicit endpoint only, `--dry` rehearsal. |
| "Capabilities are permanent abstractions" (Core Law) | Made machine-checkable: every CLI verb that ever shipped (all tags in history) still parses today. Tested at ship time from the full clone; CI clones shallow and skips — disclosed in the test body. |
| Error-matrix discipline (§4.2) | Doctor +2 rows: edge outbox (corruption FAIL, dead letters WARN, buffering PASS by design) and the save-proof ledger (an edited receipt is a FAIL; absence is honestly absence). |
| Offline-first, local-first (§5.1) | Already law since v26 (provable offline, blackout-tested); the outbox completes the story for records that WANT to leave eventually. |

### REJECTED — with reasons

| SEF-X demand | Why rejected |
|---|---|
| H-JEPA latent planning, E(Z) ≤ 0.085 | No such model exists here, cannot exist stdlib-only, and the number is unfalsifiable decoration. aeos plans in explicit, reviewable Python — auditable beats mystical. |
| MCTS ≥ 12,000 rollouts/s; PRM ≥ 0.92 | Nothing in aeos needs search at that scale; thresholds without a workload are marketing. Measured numbers live in `aeos bench` (ADR-043) — claimed numbers must be measured. |
| Arrow Flight IPC ≥ 12.8 GB/s | A third-party dependency (violates ADR-002) and pointless for a single-process CLI: aeos' IPC is zero-copy by construction — it doesn't copy. |
| Firecracker microVMs, eBPF, WASM isolation (NFR-04) | Kernel-level external dependencies break provider-neutrality and every non-Linux host. aeos sandboxing is subprocess + resource caps + socket blackout — storm-proven (v27). |
| "1,000,000+ tools", 99.98% convergence, 2.5 ms budgets | Unverifiable claims. aeos claims what it tests; silence otherwise. |

## Consequences

Three new modules (`merkle`, `saveproof`, `outbox` — 62 total), two
new verbs, two new doctor rows, charter principle 38. Signing is
honest about its ceiling: sha256 self-digest = tamper-EVIDENT;
AEOS_PROOF_KEY upgrades to HMAC-SHA256 = authentic between
key-sharers; asymmetric signatures need a dependency — rejected.
Certificates carry no timestamps (determinism is law); time lives in
the receipt around the artifact. Delivery semantics are stated, not
oversold: exactly-once locally, at-least-once toward the endpoint,
the consumer dedupes on the idem key we send.

Dogfooded on landing: the ship-time notarization of v36.0.0 is
itself a certificate in the ledger (`evidence/save-proofs/`), and
`git checkout v36.0.0 && aeos save-proof --verify <cert>
--against-tree` re-proves the tag's tree matches the certificate.

## Addendum (v36.0.1)

Cold-clone validation refused v36.0.0's certificate: build metadata
(egg-info) sat inside the Merkle root — regenerated per install,
content time-dependent, invisible in the warm worktree. The
exclusion law now covers `*.egg-info` / `*.dist-info` / `*.egg`
directories and `.DS_Store`; regression test added; the tag promise
re-proven from a fresh clone before shipping. The defect and the
repair are on the record in `evidence/handover-v36.txt`.

## Tests

`test_known_vector`, `test_rename_moves_the_root`,
`test_deterministic_across_rebuilds`, `test_clean_run_is_verified`,
`test_certificate_is_deterministic`, `test_drifted_run_names_the_files`,
`test_tampered_certificate_refused`, `test_digest_consistent_lie_still_refused`,
`test_hmac_upgrade_needs_the_key`, `test_replay_delivers_exactly_once`,
`test_failed_delivery_burns_attempts_then_deads`, `test_health_verdicts`,
`test_capability_verbs_never_removed`.
