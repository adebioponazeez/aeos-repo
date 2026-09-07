# ADR-049: The Field Test — receipts must name their environment

**Status: ACCEPTED (v39.3.0)**

## Context

The operator's challenge, after v39.2.0 shipped with its
production gauntlet: *"will the SHIPPED build be resilient and
survive real live sandbox and OTHER environment constraints?"*
A receipt produced inside one sandbox proves only that sandbox.
The gauntlet of ADR-048 varied *load and hostility*; it did not
vary the *environment*: same user, same writable HOME, same
disk, same locale, same import path.

## Decision

1. **Field gauntlet**: run the shipped build in genuinely
   different environments, not simulations of them:
   - empty environment (`env -i`, PATH only);
   - read-only workspace (`chmod -R a-w`, recursive — a
     non-recursive chmod tests nothing);
   - read-only HOME (config/state must degrade by name);
   - a real 256KB tmpfs mounted under `unshare -rm` — true
     kernel ENOSPC, not a mock;
   - a 64MB tmpfs workspace with a full run + recall roundtrip;
   - a shadow package earlier on sys.path shadowing the import;
   - deep unicode paths under `LC_ALL=C`;
   - TZ/locale flips — receipts must stay deterministic;
   - all of it as non-root (we already run as `user`).
2. **Receipts disclose their environment honestly**: a receipt
   states which environment produced it; "built and tested here"
   never silently stands in for "resilient everywhere."
3. **Verify the wheel, not just the checkout**: install the
   built wheel on real alternate interpreters (CPython
   3.10/3.11/3.12 via uv) and run the suite and CLI there.
   A built wheel that was never installed is an unverified wheel.

## What run 2 found (the field test working)

Two defect classes, both violations of the plain-language law
(ADR-013) under environmental — not adversarial — pressure:

1. `WorkspaceLock.acquire` opened the lock file outside its
   guard: on a read-only workspace the operator got a raw
   `PermissionError` traceback instead of a named refusal.
2. With the disk truly full, the `OSError 28` escaped raw from
   the foreman's durable history append — the run died before
   delivering its verdict.

## Consequences

- `refusal_reason()` is now the single source of lock truth:
  "held by a live run (kernel-released; a dead holder cannot
  strand you)" vs "could not be opened — check permissions/disk".
  Doctor, pipeline, and render() all speak it.
- History and receipts degrade best-effort: a run that cannot
  append history marks the entry `unwritten`; a run that cannot
  write its receipt sets `receipt_unwritten` — the verdict is
  still delivered to stdout. Best-effort is honest when it is
  labeled.
- Field confounds must be separated from defects before a
  verdict: harness bugs (set -e swallowing checks, machine HOME
  leaking into namespaces) and repo-context drift (README counts
  read from the checkout) can masquerade as environment
  failures. The gauntlet harness is now hermetic.
- The ladder gains a field-test row; every future release
  receipt names its environment.
