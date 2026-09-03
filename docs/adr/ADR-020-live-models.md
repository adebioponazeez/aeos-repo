# ADR-020: Live models behind the seam — metered, budget-capped, key-safe

**Status: ACCEPTED (v11.0)**

## Context
Since v1.0 the OS spoke only to the deterministic EchoModel — the
discipline that made every guarantee provable without a key. Users
now need the live path: OpenRouter (any frontier model, one key) and
Abacus AI RouteLLM (OpenAI-compatible, included with ChatLLM Teams),
plus any OpenAI-compatible endpoint. The risk was not technical but
cultural: live mode inviting exceptions — hidden keys, unmetered
spend, untested paths.

## Decision
One transport, `ChatCompletionsTransport`, speaks the OpenAI-compatible
wire for every preset (`openrouter`, `abacus`, `openai`, env-extensible
via AEOS_PROVIDER/AEOS_MODEL). Its error contract maps onto the
ADR-010 taxonomy at the wire (429/5xx→TRANSIENT, context-length 4xx→
CONTEXT_OVERFLOW, other 4xx→PERMANENT, timeouts→TRANSIENT), so retry,
backoff, and the circuit breaker apply to real providers unchanged.

Credentials resolve from the environment at call time, fail fast when
absent ("refuses to guess"), and never touch the event log — where
redaction was already structural since v1.1.

`MeteredAdapter` wraps any adapter and enforces the budget INLINE:
real usage (from provider `usage` fields) records into the economics
layer per agent/task, and spend past the cap (AEOS_MAX_COST, default
$2.00) fails the next call PERMANENT — a spend governor inside the
seam, so no graph, gate, or governor needs to know money exists.

The default remains EchoModel. Tests remain free and deterministic;
the live path is tested against localhost servers; the one real-money
smoke test is opt-in (AEOS_LIVE=1 + key) and skips otherwise.

## Alternatives
- Vendor SDKs per provider: rejected — three SDKs, three dependency
  trees, three definitions of "retry"; one wire format is durable.
- Budget enforcement at the orchestrator: rejected — the seam is where
  every call already passes; governance rides for free.

## Tradeoffs
(+) Any OpenAI-compatible provider is one env var away.
(+) Live runs produce real metered economics in the same evidence
  bundle shape as simulated ones (`mode: "live"`).
(−) Rate lookup falls back to "default" pricing for unmetered models —
  the cap is conservative, not exact, for exotic model ids.

## Consequences
`test_payload_and_auth_header`, `test_context_overflow_never_retries`,
`test_budget_cutoff_is_inline_and_permanent`,
`test_reference_run_accepts_live_adapter` (a live-shaped adapter on a
localhost wire drives the SAME graph to acceptance — the seam proof,
without spend).
