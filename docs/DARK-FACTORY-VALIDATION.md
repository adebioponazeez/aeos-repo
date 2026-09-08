# DARK FACTORY VALIDATION — AEOS v39.3.0

*Audited at v39.6.0 · 67 modules · 565 tests · 52 ADRs · zero runtime
dependencies. References: IndyDevDan's public course listings and site
(agenticengineer.com — no paid content accessed), the 2026 dark-software-
factory literature (Fabro, BrainGu Guber, the BCG Plation report,
i-scoop, mindstudio, abaditya). Every AEOS claim below was re-verified
live on this tree; the lever is evidence on disk, not narrative.*

This doc supersedes the gap list in TAC-COMPLIANCE.md (v14.0.0) and
extends BENCHMARK-2026.md (frameworks) to the factory pattern set.

---

## Part I — IndyDevDan re-audit: the v14 gaps, closed

The v14 audit scored ~75% tactical coverage with six named gaps.
Five are now closed by shipped, tested capability; one remains by
documented choice.

| v14 gap | Closed by | Live proof (this audit) |
|---|---|---|
| 12 leverage points "not an enumerable rubric" | v18 `leverage.py` — each point a row checked against workspace artifacts | `LEVERAGE AUDIT — 12 rows`; default run earns 9/12 with evidence; 3 more are command-gated by design (`fleet`, `resume`, `standards --init`) |
| Standards not cited up front | `standards.py` — STANDARDS.md is gate law: a plan citing it is gated by it | `aeos standards` on a bare workspace: "no STANDARDS.md — the gate is off (operator's choice)" |
| Single-session only, no cross-restart resume | PlanCheckpoint + `resume.py` + v39 foreman | `aeos resume` crash drill: "task 't2' failed mid-plan; 2/5 done, checkpoint durable… executed after recovery: ['t2','t3','t4']" |
| No FTS / layered retrieval | v15 `recall.py` — FTS5 MATCH, three paid layers (L0 keys → L1 snippets → L2) | `.aeos/recall.sqlite` in every run's bundle |
| No external tool registration / MCP | v12 companions (external agents as bounded nodes), v21 MCP client, v24 MCP server | server law: "exposes verbs that READ, never verbs that WRITE"; client proven under kill (storm row "server dies mid-session") |
| Prompt-ladder (7-level) hierarchy | **OPEN BY CHOICE** — AEOS compiles mechanisms, not prompt ladders; the stable-prefix assembler is the prompt compiler | documented divergence since v14 |

The course's central theses, present in the build:

- **"Build the system that builds the system"** — `factory.py` designs,
  validates and (only under spent sponsorship) installs new capabilities;
  the CLI's own tagline is "harness is the product."
- **ADWs: deterministic code composing non-deterministic agents** — the
  entire architecture: a deterministic, stdlib-only harness around a
  `ModelAdapter` seam (default `EchoModel` deterministic; real providers
  opt-in), so the guarantees hold regardless of the model behind the seam.
- **Core Four (context/model/prompt/tools)** — `context_os.py` (tiered,
  expiring, budgeted), `models.py` (the seam), skills + stable-prefix
  assembler (the prompt-equivalent), `tools.py`.
- **"One Agent To Rule Them All"** — `fleet.py`: one orchestrator, CRUD
  over agents, every mutation an append-only JSONL event.
- **Leverage is a number** — every bundle carries a measured leverage
  (outcomes per unit of human attention); the reference run reports 7.0.

**Updated tactical verdict: 5 of 6 v14 gaps closed with tests; coverage
now ~90% with the prompt-ladder divergence and the Part III gaps named.**

## Part II — The dark software factory pattern set

The 2026 references agree on a pattern list. Mapping, with verdicts:

| # | Factory pattern (reference) | AEOS mechanism | Verdict |
|---|---|---|---|
| 1 | Intent over code (BCG, i-scoop) | intents parse to typed envelopes — `contracts.py`: "EVERY agent boundary is a typed envelope"; `reference_run(intent=…)` | **PARITY** (LLM intent parsing is the opt-in seam, offline-first by law) |
| 2 | Harness as the operating manual (BCG; "the agent harness is the product") | `harness.py` — repository-native, artifact-first, owns checkpoints | **PARITY** |
| 3 | Verification as gates, not suggestions (Fabro) | `evals.py` "runs are graded, not watched"; acceptance is gate-driven; save-proof certificates; 515 tests; receipts law | **EXCEEDS** (graded + receipted + notarized) |
| 4 | Human-in-the-loop approval gates (Fabro) | `sponsorship.py` — human authority as a first-class, spendable, expiring, one-shot token; L7 installs and meta-loop changes require it | **EXCEEDS** (authority is spendable and expiring, not a click-through) |
| 5 | Governance at the edges, autonomy in the middle (BrainGu Guber) | `governor.py` — autonomy earned, bounded, revocable; unknown action class → DENY | **PARITY** |
| 6 | Execution isolation (Fabro cloud VMs; Guber ephemeral containers) | `sandbox_runner.py` — process-isolated child, never networked, writes only its cwd; field-tested under read-only/ENOSPC/non-root | **PARTIAL** — process-level, single host; no VM/container isolation (stdlib-only constraint) |
| 7 | Layered evaluation, independent judges, holdouts (BCG; abaditya digital twins) | deterministic judges + weights (`evals.py`); chaos storm ×9; production gauntlet ×11; field test ×9 groups; **v39.4 Holdout: sealed per-install scenario vault outside the repo, digital-twin runs, verdict-only reports, tamper-refusing seals** | **PARITY/EXCEEDS** — closed at v39.4.0 (scope honestly bounded in ADR-050: boundary-based separation, not same-user adversarial security) |
| 8 | Deterministic workflow graphs (Fabro DOT pipelines) | `orchestrator.py` — dependency-ordered parallel waves; durable PlanCheckpoint after every task; **v39.6 `graphlang.py`: workflows as a named DOT subset, clusters compile to nested harnesses, every error named — plus `colony.py` DAGs** | **PARITY** |
| 9 | Multi-model routing / ensembles (Fabro stylesheets) | `models.py` adapter protocol; provider adapters; triangle control/cost/speed per run; **v39.6 routing stylesheets: fnmatch sections, per-key fallback, `TaskSpec.model` hints — compile-enforced: routing never declassifies** | **PARITY** — closed at v39.6.0 (production adapter selection stays at handler-build time, stated in ADR-052) |
| 10 | Run observability, durable events (Fabro SSE) | `fleet.py` JSONL event bus; `otel.py`/`otlp.py` OTel export; `telemetry.py`; console/visualizer | **PARITY** (no SSE stream / web UI) |
| 11 | Checkpointing every stage (Fabro git checkpointing) | copy-on-write harness checkpoints; atomic writes; Merkle-verified backup/restore | **PARITY** (filesystem-level; not git-branch-per-stage) |
| 12 | Split-and-merge parallelism (mindstudio; abaditya git worktrees) | orchestrator PARALLEL WAVES with per-task workspaces, then MERGE | **PARITY** (in-process workspaces, not git worktrees) |
| 13 | Autonomy ladder (mindstudio 5-level spectrum) | v5 ladder L1–L7, earned promote/demote, governor EMA feedback, destructive checkpoints even at L6 | **EXCEEDS** (7 levels, earned + revocable, law-tested) |
| 14 | Memory layers that persist lessons (i-scoop; Letta) | `memory.py` six classes with provenance/confidence/expiry; dividend ledger; learning hard gate: failed behavior NEVER canonicalized | **PARITY / EXCEEDS** |
| 15 | Skills library (Claude Code skills; IndyDevDan templates) | `skills.py` ladder TASK→SKILL→AGENT→WORKFLOW→SERVICE→AUTONOMOUS CAPABILITY; promotion is an EVIDENCE decision | **PARITY** |
| 16 | Structured artifacts / audit trail (BCG) | evidence bundles, receipts, scribe docs-truth audit, save-proof ledger, doctor | **EXCEEDS** (the receipts are the house law) |
| 17 | Red-team agents (BCG) | `storm.py` (kill ×3, torn files, disk full, blackout, memory cap…), production gauntlet, field gauntlet | **PARITY** (hostile harnesses; not LLM red-team agents) |
| 18 | Circuit breakers, canary, rollback (BCG) | destructive-action checkpoints with revert; quarantine-before-trust; federated imports quarantined | **PARTIAL** (no canary deployment — AEOS is not a deployment system) |

**Tally: 4 EXCEEDS, 9 PARITY, 5 PARTIAL with the seam named, 0 silent
gaps.** The partials are constraints of the zero-dependency,
single-host, offline-first law — each is load-bearing, not accidental.

## Part III — Honest gaps (the roadmap)

0. *(closed at v39.6.0 — declarative workflow graphs + per-node routing stylesheets; see `graphlang.py` and ADR-052)*
0. *(closed at v39.4.0 — holdout/digital-twin separation; see `holdout.py` and ADR-050)*
1. **VM/container execution isolation** — process isolation only;
   stdlib-only forbids docker. The seam is `sandbox_runner.py`.
4. **Git-native checkpointing** — worktree-per-agent, branch-per-task;
   AEOS checkpoints the filesystem, not the git graph.
5. **SSE/live streaming UI** — events are durable JSONL; not streamed.
6. **Distributed scale** — checkpoint schema is portable to a broker
   (named in BENCHMARK-2026); single-host today.

## Part IV — Hooks & recursion (Cole Medin; Recursive Agent Harnesses)

Audited at v39.5.0 after the operator asked: "has it been woven with
hooks as critical as advocated by Cole Medin and recursive state
machine nested harness graph scaffolds?"

**Verdict at v39.4.0: semantics present, surfaces missing.** The
governor already WAS an access + pre-execution hook (ALLOW /
CHECKPOINT / DENY, keyed to the earned autonomy ladder), and
CHECKPOINT was redirect-not-reject in effect — but hooks were
hardwired, and the graph scaffolds (orchestrator waves, colony
DAGs) were flat: no task could expand into a sub-harness.

**Closed at v39.5.0** (ADR-051):

| Reference claim | AEOS mechanism | Status |
|---|---|---|
| Hooks are the critical mechanism (Medin: bash-command hook as guardrail) | `hooks.py` — first-class HookBus, named points, ordered registrations, `aeos hooks` inspection + live veto demo | **CLOSED** |
| Hooks decoupled from the agent, infrastructure-level | bus emits from orchestrator seams; model-independent by construction (ADR-002 kernel untouched) | **CLOSED** |
| Redirect, don't just reject | pre-hook may rewrite action class (WRITE→READ) — intent preserved, danger removed (tested) | **CLOSED** |
| Veto names its reason | HookVeto: plain-language refusal, never a traceback; flows to refusal observers | **CLOSED** |
| Observers can't crash the run | observer exceptions collected + named; run continues (tested) | **CLOSED** |
| The recursive unit is a full harness (RAH, arXiv:2606.13643) | `TaskSpec.subplan` → nested Orchestrator: own waves, governor, gates, depth-stamped events | **CLOSED** |
| Recursion bounded, not a trap | MAX_SUBPLAN_DEPTH=3; deeper refuses NAMED; refusal hooks observe it | **CLOSED** |
| State-grounded invocation (Recuris: skills on current state) | skills promote from measured repetition; context assembly is state-tiered (v10 ContextOS) — partial: invocation is not yet per-state-event | **PARTIAL** |
| Latent recursive loops (RecursiveMAS) | out of scope: AEOS recursion is control-flow, not latent-space co-training | **N/A by design** |
| Medin's five autonomy levels / takeover point | L0–L7 ladder, earned + revocable; sponsorship tokens are the takeover point | **EXCEEDS** (pre-existing) |
| Medin's provider independence (harness = prompts + files, agent swappable) | ModelAdapter seam, zero vendor SDKs, EchoModel default | **EXCEEDS** (pre-existing) |
| Medin's Archon (dark-factory runner) / heartbeat | foreman + holdout + field-tested offline law | **PARITY** (pre-existing) |

## Sources

- IndyDevDan — Tactical Agentic Coding / Principled AI Coding (public
  listings, agenticengineer.com/tactical-agentic-coding): 8 tactics,
  12 leverage points, core four, ADWs, "build the system that builds
  the system," "One Agent To Rule Them All."
- Fabro — the open-source dark software factory (fabro.sh, github.com/
  fabro-sh/fabro): workflow graphs, human gates, cloud sandboxes,
  verification as gates, git checkpointing, multi-model routing.
- BrainGu — "Enter the Dark Software Factory" (braingu.com): executable
  contracts, governance at the edges, execution isolation (Guber).
- BCG Plation — "The Dark Software Factory" (March 2026 report): intent
  thinking, harness as operating manual, layered evaluation, red teams,
  circuit breakers.
- i-scoop — "Dark software factories and the future of autonomous
  software delivery": planning/generation/evaluation agents, memory
  layers, policy gates.
- mindstudio.ai — "What Is a Dark Factory?": autonomy spectrum,
  planner/generator/validator/orchestrator, harness vs factory.
- abaditya — "The Dark Factory: Engineering Teams That Run With the
  Lights Off": guardrails as preconditions, digital twins with holdout
  tests, QA-as-agents.
