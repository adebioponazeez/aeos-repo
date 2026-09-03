# ADR-010: Adapter error taxonomy — classify before responding

**Status: ACCEPTED (v2.0)**

## Context
"Retry or fail?" is the most common wrong answer in agent harnesses.
It depends on the failure class, and vendors encode classes in prose,
not types.

## Decision
Every adapter exception is classified into TRANSIENT (retry with
exponential backoff), CONTEXT_OVERFLOW (never retry — compress),
PERMANENT (fail fast into repair), JUNK (confident nonsense — gate
it), CIRCUIT_OPEN (breaker protecting the downstream). Exhausted
transient retries surface as PERMANENT: still-down is, for the
caller, permanent. A circuit breaker opens after consecutive
failures and half-open probes after cooldown.

## Alternatives
- Vendor retry libraries: rejected — they classify for the vendor's
  client, not for the harness's decision grammar.

## Tradeoffs
(+) The runbook's "repair the correct layer" becomes mechanical.
(+) Fusion adapters inherit the taxonomy per stream.

## Consequences
`test_transient_retries_then_succeeds`, `test_context_overflow_never_retries`,
`test_circuit_opens_after_threshold`, `test_transient_exhausted_is_permanent`.
