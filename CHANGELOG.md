# Changelog — AEOS

Every version below is earned by shipped, tested capability
(ADR-008). Test counts are at tag time.

## v27.0.0 — The Storm: Chaos as a First-Class Command (338 tests)
- **`storm.py`** (ADR-036): eight end-to-end chaos scenarios — kill
  -9 x3 + recovery, torn power-cut files (quarantined), disk-full at
  the bundle write (prior evidence byte-intact), garbage intents,
  TOTAL socket blackout, 256MB memory cap, concurrent runs refused,
  server killed mid-session. `aeos storm` prints the receipt; the
  storm runs inside the standard suite so receipts cannot rot.
  Found + fixed a real leak: MCP BrokenPipe now fails closed.

## v26.0.0 — The Vault: Fault Tolerance (334 tests)
- **`vault.py`** (ADR-035): the hostile-environment core —
  `durable_write` (tmp+fsync+rename), tolerant loads with `.torn`
  quarantine (a torn line can no longer crash the store), fcntl
  `WorkspaceLock` (kernel-released on death — no stale locks),
  `socket_blackout` (provable offline), `environment_scan` (never
  dials out). MemoryStore/EventBus/checkpoints/bundle all hardened;
  one workspace, one run; environment truth on every bundle.

## v25.0.0 — The Colony: Explicit Graph Orchestration (317 tests)
- **`colony.py`** (ADR-034): declarative DAG — nodes with `requires`
  edges and `condition` gates; wave execution in dependency order;
  failures block dependents (fail closed); skipped/failed deps block
  early; cycles end BLOCKED — the colony NEVER hangs. Every
  transition an event on the bus. CLI: `aeos colony`.

## v24.0.0 — The Bridges: MCP Server + OTel Export (307 tests)
- **`mcp_server.py`** (ADR-033): AEOS on the other side of the
  protocol — `python -m aeos.mcp_server`, same JSON-RPC framing,
  three tools (leverage_audit, standards_check, recall), ALL READERS
  BY LAW (`READONLY_TOOLS` — the server exposes verbs that read,
  never verbs that write). Proven by roundtrip with our own v21
  client. **`otel.py`**: the fleet stream exported as OTel-style
  spans — content-addressed ids, byte-stable, FAILED→ERROR. CLI:
  `aeos mcp --serve`, `aeos otel`.

## v23.0.0 — The Mirror: Eval Suites (296 tests)
- **`evals.py`** (ADR-032): the named v23 seam closed. `EvalSuite` —
  cases with deterministic judge predicates and weights; raising
  cases FAIL, never crash; scores clamp; thresholds gate.
  `run_self_eval` points the mirror at AEOS's own six laws
  (standards gate, recall budget, negative marginal, UNTRUSTED
  imports, phantom detection, byte-stable prefixes). CLI: `aeos eval`.

## v22.0.0 — The Horizon: Cache Telemetry + the Global Benchmark (287 tests)
- **`telemetry.py`** (ADR-031): provider usage blocks parsed into
  cache hit rates and EFFECTIVE tokens (reads discounted 0.9x) — the
  v14 byte-stable prefixes now have a readable payoff. Live mode is
  opt-in only (AEOS_LIVE=1); the fixture path says "fixture" out
  loud. Plus BENCHMARK-2026.md: AEOS scored against the global field
  (LangGraph, CrewAI, Claude Agent SDK, OpenAgents, Letta) — lead or
  gap, per dimension, with the closing versions named.

## v21.0.0 — The Protocol: MCP Client (276 tests)
- **`mcp_client.py`** (ADR-030): Model Context Protocol client,
  stateless core, stdlib only — JSON-RPC 2.0 over subprocess stdio:
  initialize handshake, tools/list, tools/call. Walls kill hanging
  servers; garbage fails closed; imported tools enter as UNTRUSTED
  (`import_tools` — federation law travels with the protocol).
  Bundled `aeos.mcp_demo_server` + CLI `aeos mcp`.

## v20.0.0 — The Emissaries: Companions Round 2 (267 tests)
- **`companions.py` round 2** (ADR-029): `run_aider` (aider headless:
  --yes, --no-auto-commits) and `run_claude` (Claude Agent SDK CLI:
  `claude -p --output-format json`) under the SAME law as Pi —
  report contract rides in the prompt, artifacts verified against the
  FILESYSTEM (`verify_against_disk`), phantom artifacts raise, walls
  kill, boundaries revert (`coding_handler` shared shape).
  `round2_status()` detects what is on PATH, honestly.

## v19.0.0 — The Standards: Success Is Planned (259 tests)
- **`standards.py`** — the 80-20 compiled (ADR-028): STANDARDS.md
  registers the operator's engineering law as `[STD-n]`; plans MUST
  cite registered ids BEFORE work starts — uncited plans are refused
  by the pipeline, unregistered citations are refused, no file = no
  gate (the operator's choice). CLI: `aeos standards [--init]`.

## v18.0.0 — The Rubric: 12 Leverage Points, Auditable (252 tests)
- **`leverage.py`** — the course's 12 leverage points as an auditable
  rubric (ADR-027): each point = one AEOS mechanism checked against
  EVIDENCE ON DISK (bundle keys, recall index, event stream,
  checkpoint, standards file) — PASS requires artifacts, not claims.
  CLI: `aeos leverage-audit --workspace`.

## v17.0.0 — The Resume: Durable AFK Plans (245 tests)
- **`resume.py`** — durable execution, stdlib-small (ADR-026):
  `PlanCheckpoint` (atomic tmp-then-rename after EVERY task),
  `execute_plan` with mid-plan failure (`ResumeNeeded`) leaving prior
  progress durable; resume executes only pending tasks — side effects
  exactly once, proven by the call log, across process restarts.
  CLI: `aeos resume` (simulated crash + recovery demo).

## v16.0.0 — The Fleet: One Orchinator, Live Observability (239 tests)
- **`fleet.py`** — fleet CRUD over a single orchestrator (ADR-025):
  `FleetOrchestrator` register/dispatch/retire with duplicate/unknown
  refused; `EventBus` append-only JSONL stream — publish, subscribe,
  replay (file order is the proof), tail. CLI: `aeos fleet` runs the
  governed demo; `aeos dashboard --live` tails the stream. The course's
  "One Agent To Rule Them All" + the industry's tracing habit,
  stdlib-small.

## v15.0.0 — The Recall: Layered FTS Retrieval (229 tests)
- **`recall.py`** — ClaudeMem's third leg compiled (ADR-024):
  `RecallIndex` over stdlib `sqlite3` FTS5; three budgeted layers — L0
  key hits (~1 token each), L1 MATCH snippets trimmed to budget, L2
  full record only when budget remains. Recall savings reported in
  every bundle's dividend. CLI: `aeos recall --query`. Never mutates
  the store; rebuild is idempotent.

## v14.0.0 — The Dividend: Negative Marginal Token Consumption (221 tests)
- **`dividend.py`** — memory economics as law and ledger (ADR-023):
  **`MemoryDistiller`** compresses repeated episodic lessons into one
  evidence-gated semantic record per task/outcome with MEASURED
  compression; **`stable_prefix()`** canonical-JSON assembly makes
  prefixes byte-identical across runs (prompt-cache eligible), with
  volatile tails riding last; **`TokenLedger`** computes per-class
  marginal curves — NEGATIVE MARGINAL CONSUMPTION (recall + amortized
  overhead below the no-memory baseline) is a computed fact; **`rent()`**
  enforces MEMORY MUST PAY RENT — never-recalled canonical records are
  flagged as squatting token-weight.
- CLI: `aeos dividend` renders the measured dividend of the last run.
  Reference run now seeds prior-session episodes (the cross-session
  memory thesis, ClaudeMem-style) and reports compression x3+, negative
  marginal per class, and rent status in every bundle.

## v13.0.0 — The Triangle: Control/Cost/Speed as One Dial, Measured (207 tests)
- **`triangle.py`** — the tradeoff the operating layer exists to
  manage, made explicit (ADR-022): `RunProfile` stances (CONTROL /
  BALANCED / SPEED / COST) move every knob together — autonomy
  ceiling, gate set, parallelism, sandbox isolation, fusion, budget,
  model route — with IMMUTABLE FLOORS (core gates, L5 ceiling on
  selection, boundaries, checkpoint-forever classes).
- **`measure_triangle()`** — the measured trade from what the run
  actually did (event log + economics + clock), with a plain-language
  "THE TRADE:" receipt. Every bundle carries it; `aeos triangle`
  re-renders it; `aeos run-demo --profile control|speed|cost|balanced`
  selects the stance. The law of the thumbnail is now a test:
  control stance MEASURES more control than speed stance.

## v12.0.0 — Companions: Pi CLI + DeerFlow as Bounded Nodes (188 tests)
- **`companions.py`** — external agents join the OS under the same
  laws (ADR-021). **Pi** (the SSSF/fusion lineage's coding agent):
  `pi -p --mode json --session-id` (stdin DEVNULL, their documented
  lesson); JSONL events stream to the log; artifacts derive from the
  FILESYSTEM DIFF, never the self-report; boundary violations revert
  and kill the phase; wall-clock kill on hang. **DeerFlow** (ByteDance
  deep research): `deerflow --json` NDJSON; sources become findings at
  capped confidence, the final answer quarantined as unverified; no
  sources, no fabrication (the v5 law).
- CLI: `aeos companions` (detection + enable hints). Tested entirely
  against fake executables — no install, no keys, no spend.

## v11.0.0 — Live Models Behind the Seam (177 tests + 1 opt-in)
- **`providers.py`** — the live path, zero new guarantees bent:
  `ChatCompletionsTransport` speaks the OpenAI-compatible wire for
  OpenRouter, Abacus RouteLLM, and OpenAI (env-resolved presets,
  AEOS_PROVIDER/AEOS_MODEL); errors map onto the ADR-010 taxonomy at
  the wire; keys come from the environment, fail fast, never logged.
- **`MeteredAdapter`** — real token usage into the economics layer,
  with an INLINE spend governor: past AEOS_MAX_COST (default $2.00)
  the next call fails PERMANENT (ADR-020).
- CLI: `aeos run-demo --live [--provider --model]`, `aeos live-check`
  (resolved config, zero spend). Default runs stay deterministic and
  free; the real-money smoke is opt-in (AEOS_LIVE=1).

## v10.0.0 — Federation (161 tests)
- **`federation.py`** — the cross-org capability market with one rule:
  IMPORT IS QUARANTINE. Foreign units land QUARANTINED; install is
  refused before any token check; the only road to TRUSTED is passing
  the local sandbox. Tampered artifacts refused at the border; export
  carries provenance. `aeos federation-demo` (ADR-019).
- Witnessed: quarantine -> refused-with-token -> revalidate PASS ->
  sponsored install.

## v9.0.0 — Co-Design (in 10.0.0)
- **`codesign.py`** — the factory now proposes a SLATE: conservative,
  minimal-privilege, and reviewer-first variants, least-privilege
  scored, all sandbox-validated, ranked for a human who sponsors
  exactly one variant (scope includes the variant label) (ADR-018).

## v8.0.0 — Distance (in 10.0.0)
- **`transport.py`** — HTTP model transport mapped onto the error
  taxonomy; remote tool calls that stay untrusted over the wire;
  A2A-style WorkerServer/RemoteWorker delegation (ADR-017).
- **Process-isolated sandboxes** — `run_isolated()` + defensive
  `sandbox_runner` child: wall-clock kill, rlimits, verdicts without
  stack traces. Factory gained `isolation="process"`.
- **`console.py` + `aeos sponsor`** — persistent sponsorship tokens
  (JSONL; spent stays spent across restarts) and the static authority
  console.

## v7.0.0 — The Capability Factory (131 tests)
- **`factory.py`** — L7 live: measures history → designs contracts from
  signatures → validates them in sandbox harnesses on the deterministic
  engine → proposes; installs ONLY under a scoped, one-shot
  sponsorship token. `aeos factory-demo`.
- **`visualizer.py`** — Studio dashboard: self-contained static HTML run
  report. `aeos dashboard`.
- Demo evidence: without token → 2 proposals, 0 installs, refusals
  logged; with scoped token → `evaluator-specialist` installed, second
  candidate refused on scope mismatch.

## v6.0.0 — The Meta-Loop, Bounded (in 7.0.0)
- **`meta.py`** — self-improvement inside hard data bounds: skill
  retirement needs ≥5 uses and ≤0.4 win-rate; promotion-threshold
  tuning locked to [0.90, 0.99]; every applied change requires a
  sponsorship token; ADR stubs auto-drafted for human review.

## v5.0.0 — Autonomous Research & Ops (in 7.0.0)
- **`research.py`** — research pipeline with untrusted-source
  discipline: low-authority findings land in `unverified`, never in
  conclusions.
- **`ops.py`** — SweepScheduler (continuous entropy control) +
  RegressionBook (a recorded production failure becomes a permanent
  gate — `regression_gate` in the gate library).

## v4.0.0 — Economics (in 7.0.0)
- **`economics.py`** — CostTracker (per-task, per-model rates), Budget
  (ALLOW/CHECKPOINT/DENY on spend), and the founding metric
  OUTCOME VALUE / HUMAN ATTENTION (`leverage_ratio`) computed from the
  event log. Reference run: leverage 7.0 (7 outcomes, 0 interventions).

## v3.0.0 — Capability OS (in 7.0.0)
- **`catalog.py`** — package/publish/install capability units with
  content hashes; tampered units refuse to install.
- **`sponsorship.py`** — human authority as a spendable, expiring,
  one-shot, scoped token; full audit trail.
- Multi-tenant governance: per-tenant policy overrides on the governor
  without touching the global matrix.

## v2.0.0 — Multi-Agent Platform (in 7.0.0)
- **`adapters.py`** — provider adapters with error taxonomy
  (TRANSIENT/CONTEXT_OVERFLOW/PERMANENT/JUNK/CIRCUIT_OPEN), exponential
  backoff, circuit breaker, and **FusionAdapter** (combine compute,
  don't select compute; disagreement surfaced, never averaged).
- **`runtime.py`** — durable runs: state persisted after every task
  transition; crash → `resume()` keeps SUCCEEDED work, re-runs the rest.
- **`tools.py`** — MCP-idiom tool layer (JSON-RPC shape, `isError`,
  untrusted-by-default posture per SEP-2085); every call passes the
  governor first.

## v1.1.0 — Hardening (in 7.0.0)
- Structural secret redaction in the event log (v1.1 ADR-008 item closed).
- Gate library: `schema_gate`, `tests_pass_gate`, `regression_gate`.
- Entropy coverage: weak tests, unused tools, architectural drift.

## v1.0.0 — Production Baseline (68 tests)
- The complete in-process OS: contracts, models seam, context, memory,
  skills, orchestrator, governor, evaluation, harness, observability,
  entropy, learning, discovery, reference pipeline. See Volume I.
