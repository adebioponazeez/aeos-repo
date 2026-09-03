# ADR-025: The fleet is a stream

**Status: ACCEPTED (v16.0)**

## Context
Multi-agent orchestration without live observability is driving
blind: our dashboard was post-hoc, the industry default is OTel
tracing (LangSmith, Strands, Microsoft Agent Framework all ship it).

## Decision
`FleetOrchestrator` — single orchestrator with fleet CRUD
(register/dispatch/retire); duplicates and unknowns are refused, not
logged-and-ignored. `EventBus` — append-only JSONL event log:
publish/subscribe/replay/tail. File order is the truth; replay is
byte-stable proof. Every fleet mutation is an event. `aeos fleet`
runs the governed demo; `aeos dashboard --live` tails the stream.

## Alternatives
OTel SDK: rejected as default — runtime dependency and a collector
for what an append-only file already proves deterministically in
tests. The JSONL schema maps cleanly onto OTel export later.

## Consequences
`test_events_replay_in_publish_order`, `test_replay_is_byte_stable`,
`test_duplicate_registration_refused`, `test_dispatch_to_unknown_agent_refused`.
