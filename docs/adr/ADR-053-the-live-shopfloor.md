# ADR-053: The Live Shopfloor — SSE streaming, read-only, stdlib

**Status: ACCEPTED (v39.7.0)**

## Context

The dark-factory validation's roadmap gap #5: "events are durable
JSONL; not streamed." Fabro ships run observability with SSE event
streaming and a web UI; AEOS had the durable events but the only
way to watch a run was to read the file. The gap was real, and the
closure had to respect two standing laws: zero runtime
dependencies (stdlib only) and the offline law (nothing leaves the
machine unless explicitly directed).

## Decision

1. **SSE over the Consulate pattern** (`stream.py`): the same
   ThreadingHTTPServer approach as the v31 HTTP consulate, with
   the same character — READ ONLY. `GET /events` serves
   `text/event-stream`: the workspace's newest
   `.aeos/runs/*-events.jsonl` replayed from the start, then
   tailed live; when a newer run file appears (a new run started),
   the stream rolls over to it. `GET /health` reports state;
   `GET /` serves the console.
2. **The console is self-contained**: one HTML page, inline CSS
   and JS, no CDN, no framework, no external URL — it works with
   the network stack off (the offline law applies to the UI too).
   Live feed, per-kind counters, client-side filter.
3. **Read-only by law**: POST/PUT/DELETE are named 405s — "the
   shopfloor streams events; it never accepts commands; the write
   surface is the CLI, under the governor." Streaming adds zero
   new trust and zero new truth: every event served is the same
   durable line already on disk.
4. **Loopback by default** (the consulate law): `--bind` widens
   the door only by explicit operator decision.
5. **Named refusals everywhere**: busy port, missing workspace,
   no run history (with remedy), unknown path.

## Honest scope

- The tail poll (0.4s) is polling, not inotify: stdlib-only means
  no filesystem watch; sub-second latency is good enough for a
  shopfloor console and the cost is one stat() per beat.
- One workspace per server: the shopfloor is scoped, not a fleet
  dashboard (the fleet event bus remains the durable source).
- No authentication on the stream: it is loopback-bound by
  default and read-only; exposing it beyond loopback is an
  operator decision taken in the open (and should sit behind a
  real proxy).

## Consequences

- A test-harness lesson went on the record: an SSE stream never
  EOFs, so a helper that read() the whole body hung — the hang was
  the stream working. The tests now treat /events as a stream.
- DARK-FACTORY-VALIDATION pattern #10 (run observability) upgrades
  from PARITY-without-streaming to PARITY with streaming; roadmap
  gap #5 closes.
- The console is the natural home for future read-only surfaces
  (recall readers, leverage dashboards) — all GET, all local.
