# ADR-050: The Holdout — evaluation the agent cannot overfit to

**Status: ACCEPTED (v39.4.0)**

## Context

The dark-factory validation (DARK-FACTORY-VALIDATION.md, Part III)
named the sharpest gap in the field's pattern set, after abaditya's
digital-twin write-up: test scenarios stored OUTSIDE the codebase —
separate from where the coding agents can see them — functioning
like holdout sets in machine learning. Agents cannot overfit to
tests they cannot access. AEOS's storm, production gauntlet and
field test were separate programs, but not hidden ones: every
scenario was plaintext in the repo.

## Decision

1. **A sealed vault outside the boundary.** `aeos holdout --init`
   creates `~/.aeos/holdout/` (configurable) — outside the repo and
   outside every workspace. A per-install 32-byte nonce (0600)
   derives the sealing key. Scenario instances are zlib-compressed,
   XOR'd against an HMAC-derived keystream and base64-wrapped: no
   plaintext instance is ever on disk in a workspace-reachable path.
   Integrity is sha256 + HMAC per blob, merkle root + HMAC over the
   manifest — a tampered blob refuses to run, NAMED, before any
   evaluation happens.
2. **Families are law; instances are the holdout.** The five
   families are public in `holdout.py` (hostile intents verdicted,
   determinism, refusal named, economics governed, leverage
   numbered) — the CATEGORIES are the contract. Which hostile
   intents, in which order, with which parameters is seeded from
   the per-install nonce: an agent that reads the entire source
   still cannot know the instances. Two installs of the same build
   hold different holdout sets (tested).
3. **The digital twin.** `aeos holdout --run` copies the target
   workspace to a throwaway twin in a temp dir, runs every family
   against the twin, deletes it, and re-digests the original —
   which must be byte-identical (order-stable tree digest, tested).
   Evaluation never mutates the thing it evaluates.
4. **Verdict-only reporting.** The rendered report carries family
   verdicts and counts — never scenario content. The full ledger
   stays in the vault. Scenario content does not leave the vault in
   any workspace-visible artifact (tested).
5. **Determinism with an honest boundary.** The determinism family
   compares canonical bundles excluding environment truth (disk
   free, absolute paths, timestamps) and the clock (durations,
   tasks/s) — physics is not a decision. What is compared: states,
   verdicts, leverage, economics, checkpoints, learning.

## Honest scope (what this is NOT)

This is boundary-based separation, not multi-tenant security. The
sandbox law already confines workspace agents — writes only inside
their cwd, never networked — and the vault sits outside that
boundary, sealed against reading. A same-user adversary with an
arbitrary shell owns the nonce file too; against that adversary the
seal is obfuscation, not cryptography. We say so here rather than
in a marketing doc. The holdout protects against OVERFITTING by
the system under evaluation, which is the pattern's actual purpose.

## Consequences

- The grading must have teeth: a family must be able to FAIL (a
  regression to unnamed refusals is caught — tested), else the
  holdout is theater.
- The holdout evaluation itself is deterministic: same vault, same
  workspace snapshot -> identical verdicts (tested).
- The dark-factory pattern map upgrades pattern #7 from PARTIAL;
  the roadmap's first gap is closed.
- Future families (holdout red-teams, holdout recalls) join the
  vault by the same seal; the manifest version allows migration.
