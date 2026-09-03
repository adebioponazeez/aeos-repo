# ADR-002: Zero runtime dependencies

**Status: ACCEPTED (v0.1)**

## Context
The OS's job is to be trustworthy. A trust boundary that depends on a
package tree is a trust boundary nobody can audit.

## Decision
stdlib only. Dataclasses, not pydantic. JSONL, not SQLite. fnmatch,
not a glob library. `pip install -e .` pulls nothing but the package
itself.

## Alternatives considered
- **pydantic contracts** — nicer validation errors, but adds a
  dependency to the layer that least afford one; our contracts are
  small enough that hand-rolled validation is fully covered by tests.
- **SQLite event store** — SSSF uses it correctly (WAL, polled
  visualizer); we use JSONL because it is replayable, greppable and
  needs no binary state. A tailing visualizer gets the same facts.

## Tradeoffs
(+) Auditable end-to-end; installs anywhere Python ≥3.10 runs.
(−) No schema-evolution tooling; version discipline is manual.

## Consequences
The entire OS is a few thousand lines of readable Python with a test
suite that finishes in under five seconds. That is a feature, not a
limitation.
