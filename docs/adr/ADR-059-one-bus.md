# ADR-059: One bus — the foreman and the boot join the shopfloor's stream

**Status: ACCEPTED (v40.2.0)**

## Context

The audit named four disjoint event ledgers. After the spine
(v39.8) the runs dir (`<ws>/.aeos/runs/<ts>-events.jsonl`) became
the pipeline's live bus and `aeos stream` tails it — but the two
AUTONOMOUS operators were invisible to the shopfloor: the foreman's
observability lived in receipts read after the fact, and ignition's
in the boot ledger. An operator watching the stream could not see
the foreman healing or the boot climbing.

## Decision

1. **Both operators emit their lifecycle onto the same bus.** The
   foreman: `foreman.start`, `finding.filed`, `actions.start`,
   `action.done`, `foreman.end`. The boot: `boot.start`,
   `boot.stage` (×4), `boot.failed`, `boot.end` — same file naming,
   same `EventLog` sink, so the shopfloor picks them up and rolls
   over with zero changes.
2. **The boot's work stage streams live**: ignition now runs the
   pipeline with `live_events=True`, so mid-boot the bus rolls from
   boot-stage events to the work run's events — the operator
   watches the whole climb. A same-second boot and work run share
   one bus file (append-mode JSONL, line-atomic) — both are the
   one bus working.
3. **Preflight is a pure look (field-caught, E4)**: the first draft
   created the event sink BEFORE preflight — which made stage 1
   touch the workspace, so the fresh-workspace disk check measured
   a workspace that now existed (256K tmpfs → "0MB free" → boot
   refused). Correct design: early boot events buffer in a memory
   EventLog and ATTACH to the file bus only after the workspace
   stage has prepared the workspace; a boot that fails before then
   leaves no bus (its receipt and the doctor's boot row carry the
   story).
4. **Best-effort by law, including at exit (field-caught, E4)**:
   sink creation and every emit are guarded — observability must
   never take the verdict. A refused emit CLOSES the sink
   (`EventLog.close()` swallows the refused flush): a partial
   buffer left open would raise `Exception ignored` at interpreter
   exit. A foreman/boot that cannot write events continues
   unwatched; the result discloses what it can.
5. **An events file is a run file**: groom counts it and keeps it
   newest-first like any other; the retention finding sees it. The
   foreman's own fresh bus file therefore survives its own groom
   without self-triggering retention.
6. **Receipts remain the ledger of record** — the bus is
   observability. What stays off the bus, named: the foreman's
   `history.jsonl` (signature-dedup bookkeeping) and the fleet
   demo's in-memory EventBus (with its OTel export).

## Consequences

- `aeos stream --workspace ws` now shows every autonomous actor:
  pipeline runs, graph runs, foreman applies, boots — one bus.
- The receipts and doctor rows are unchanged; renders gain an
  `events (live):` line when the bus was written.
- End-to-end completeness re-scored ~56% → ~58% (state report):
  the "four event ledgers" register item closes to "one bus + two
  disclosed exceptions".
- Found and fixed on the way: the work-stage signature change
  surfaced two stale test stubs (v37 ignition) that monkeypatched
  `reference_run` without the new kwarg.
