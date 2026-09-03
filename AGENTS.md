# AGENTS.md — repo context for coding agents

The 2026-universal context file. Deliberately short: research (138 real
repos, Gloaguen et al. 2026) shows bloated agent-context files *reduce*
task success. This file is a routing table, not a manual.

## Build & test

- `python -m pytest` — all tests, no network, no API keys, ~5s.
- `pip install -e .` — install; **zero runtime dependencies** (stdlib only).
- `aeos run-demo --workspace /tmp/demo` — full reference pipeline.

## Architecture map

- `src/aeos/contracts.py` — every type that crosses a boundary (read first).
- `src/aeos/pipeline.py` — the reference loop wiring everything together.
- `src/aeos/{adapters,runtime,tools,catalog,sponsorship,economics,research,ops,meta,factory,transport,sandbox_runner,codesign,federation,console,visualizer}.py` — the v2–v10 platform layers; each has an ADR in `docs/adr/`.
- `tests/` — the executable specification; behavior lives in tests.

## Conventions that deviate from defaults

- **No new runtime dependencies.** Ever. Take it to an ADR first.
- **Envelopes, not strings.** Agent handlers return `Envelope`, or the
  orchestrator fails the task (`test_handler_must_return_envelope`).
- **Evidence or silence.** Claims without evidence fail gates; memory
  writes without evidence raise. Do not "fix" this by loosening gates.
- **Fail closed.** Unknown action classes deny; unclassified context is
  STALE-side; missing fields invalidate specs.
- **Write boundaries are harness-enforced.** A handler's authority is
  its agent's `writes:` glob list, checked after every call.

## Anti-patterns (tried and rejected here)

- Passing free-text "results" between phases — unverifiable.
- Unbounded retries — masks the real missing layer (spec §14).
- Grading your own output — evaluator must be a different role.
- Storing everything in memory — pollution is a tested failure mode.
- Agents for known commands — if you can write the invocation down, it
  is a `kind="code"` phase, not an agent.

## When editing

Run `python -m pytest` before declaring anything works. If you change
`contracts.py`, expect every other module to care.
