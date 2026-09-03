# TAC COMPLIANCE AUDIT — AEOS vs IndyDevDan's *Tactical Agentic Coding*

*v14.0.0 · 36 modules · 221+1 tests · 23 ADRs. Curriculum names below are
from public course listings only (no paid content was accessed or used);
the mapping is to our own shipped mechanisms and their tests.*

**Headline: core 8 — 6 strong/full, 2 partial. Horizon 6 — 3 strong, 3
partial. ~75% tactical coverage; every mapped concept is enforced by a
test, not a vibe. Where we're thin, the gap list below is the roadmap.**

## Core 8 (Tactical Agentic Coding)

| # | Lesson | AEOS mechanism (version) | Verdict | Proof |
|---|---|---|---|---|
| 1 | Hello Agentic Coding (stack setup) | Kernel, install, `selftest`, harness-as-product (v1) | **FULL** | `aeos selftest` |
| 2 | The 12 Leverage Points (stdout, types, tests, architecture… stacked) | Verification gates parse **stdout into a closed verdict vocabulary** (v3); tests as strict gates (v5); architecture as contracts — action classes + `writes:` (v6); leverage itself **measured** per run (v4) | **STRONG, one gap** — the points exist as mechanisms, not as an enumerated 12-row rubric an operator can audit a workspace against | `test_claims_without_evidence_fail_the_gate`, every bundle's `leverage` |
| 3 | Success is Planned (80-20: templates > prompts; standards encoded up front) | Learned **skills** (3× proven), plan-then-evidence flow, canonical memory with evidence gate (v2, v8) | **PARTIAL** — we encode standards *after* they're learned; nothing forces a plan to *cite* the operator's engineering standards up front | `test_proven_skill_proposes_agent_promotion` |
| 4 | AFK Agents (PITER: problem → template → pipeline; runs while you're away) | Autonomy ladder L1–L7 with earned promote/demote (v5); checkpoint-forever classes; wave executor; companions run external agents AFK with wall-clock + boundary revert (v12) | **STRONG, one gap** — single-session only; no cross-restart resume/heartbeat | `test_destructive_checkpoints_even_at_l6`, `test_roguish_pi_is_reverted_and_killed` |
| 5 | Close The Loops (closed-loop prompting, self-correcting pipelines) | Error taxonomy + bounded repair at the right layer (v7); governor EMA feedback; entropy eviction; distillation feedback → dividend (v14) | **FULL** | `test_context_overflow_never_retries`, `test_failures_demote` |
| 6 | Let Your Agents Focus (context discipline) | ContextOS: tiered, expiring, loud-drop, budgeted assembly (v10); cache-stable prefixes + distilled recall (v14) | **FULL — arguably exceeds** | `test_budget_is_enforced`, `test_same_stable_set_same_prefix_different_tail` |
| 7 | ZTE (eliminate the common failure modes) | Fail-closed defaults: unknown class → DENY; UNVERIFIED first-class; quarantine-before-trust; boundaries not promises (revert); inline budget cutoff (v5–v8, v12) | **FULL** | `test_unknown_class_denies`, `test_quarantined_install_refused_even_with_token` |
| 8 | The Agentic Layer (the operating tier) | AEOS itself — org/exec/builder roster, triangle stances with floors, companions, dividend (v1–v14); the thumbnail's law is a test | **FULL** | `test_control_measures_more_control_than_speed` |

## Agentic Horizon 6 (advanced)

| # | Lesson | AEOS mechanism (version) | Verdict | Proof |
|---|---|---|---|---|
| 9 | Elite Context Engineering | ContextOS tiers + expiry (v10); canonical-JSON stable prefixes (v14); measured compression ×4.07 | **STRONG, one gap** — no FTS/layered *retrieval* (linear key scan today); no measured cache-hit rate (live-only metric) | `test_marginal_is_negative` |
| 10 | Agentic Prompt Engineering (7-level hierarchy → meta prompts) | Skills are our prompt-equivalent; meta-loop self-modification under spent sponsorship (v11) | **PARTIAL by choice** — we compile mechanisms, not prompt ladders; the stable-prefix assembler is our prompt compiler. Deliberate divergence, documented | `test_spend_is_one_shot` |
| 11 | Domain-Specific Agents (Agent SDK mastery) | Factory builds agents from proven skills (v9); federation import w/ quarantine; provider/model adapters; companions (v12) | **STRONG, one gap** — no external *tool* registration surface (SDK-style custom tools / MCP) | `test_quarantined_install_refused_even_with_token` |
| 12 | Multi-Agent Orchestration (one orchestrator, fleet CRUD, real-time observability) | Federation of factories (v9); dashboard + console; roster assignments | **PARTIAL** — observability is post-hoc; no live event stream, no single-orchestrator fleet CRUD | federation demo suite |
| 13 | Agent Experts (agents that actually learn) | Learning loop, evidence-gated canon, governor EMA, skill promotion, distillation + rent (v2, v5, v14) | **FULL — exceeds**: we add the *economics* of learning (rent, negative marginal) | `test_failure_never_becomes_canonical`, `test_unrecalled_memory_is_squatting` |
| 14 | The Codebase Singularity (the repo that improves itself) | Bounded meta-loop + sponsorship tokens (v11); versions earned not worn (ADR-008); the book writes its own addenda; PRINCIPLES charter | **STRONG** | `test_out_of_bounds_threshold_refused_even_with_token` |

## Where AEOS already goes beyond the course

Governed real money (inline cutoffs), sponsorship-scoped self-modification,
memory economics (rent/negative marginal — nobody's teaching this),
measured control/cost/speed triangle, honesty ledger (UNVERIFIED verdicts),
zero-dependity portability. The course teaches the tactics; we compiled
them into law and priced them.

## GAP ROADMAP — **STATUS: ALL 8 GAPS CLOSED in the v15–v22 Horizon March**
(kept for the record; every row below now ships — RecallFTS=v15, Fleet=v16, Resume=v17, rubric=v18, Standards=v19, Companions-2=v20, MCP=v21, telemetry=v22. See BENCHMARK-2026.md for the global scoring.)

Priority = closes a PARTIAL + stays stdlib-only + testable.

| Pri | Gap (lesson) | Build | Acceptance criteria |
|---|---|---|---|
| **1** | Layered retrieval (9) | **v15 RecallFTS**: `sqlite3` FTS5 (confirmed in stdlib build) — 3-layer progressive recall: key hit → FTS snippet → full record; replaces linear scan | measured layer tokens; recall-order test; zero deps |
| **2** | Leverage rubric (2) | **`aeos leverage-audit`**: the 12 points as an enumerated rubric, each row = an AEOS mechanism, scored against a workspace | 12 rows, each maps to a mechanism + test; audit runs offline |
| **3** | Standards up front (3) | **STANDARDS.md template skill**: plan gate requires citing operator standards before build starts | `test_plan_without_standards_citation_fails` |
| **4** | Fleet orchestration + live view (12) | **v16 Fleet**: orchestrator CRUD over federation agents + stdlib event bus; `aeos dashboard --live` tails the stream | event-order test; CRUD lifecycle test; live tail deterministic replay |
| **5** | AFK resume (4) | **`aeos resume`**: checkpointed wave plans persisted; idempotent restart mid-plan across processes | kill-mid-wave test → resume completes; no duplicated side effects |
| **6** | External tools (11) | **Companions round 2**: Aider + headless Claude Agent SDK (`claude -p --output-format json`) via the existing SubprocessRunner/fs-diff boundary | same contract as Pi: findings capped, never self-reported, writes reverted |
| **7** | Tool standard (11) | **MCP client (stateless core)**: JSON-RPC over subprocess, stdlib only; imported tools enter as UNTRUSTED action classes | quarantine-before-use test; timeout kill test |
| **8** | Cache-hit proof (9) | **Live cache telemetry**: read provider cache-usage fields into the TokenLedger (AEOS_LIVE=1 only) | ledger gains `cache_hit_rate`; opt-in test |

Not planned (deliberate divergences, on record): prompt-level ladders as
first-class objects (we compile mechanisms, prompts are derived); any
runtime dependency; vector DBs (FTS5 + distillation cover the need at our
scale, and SQLite *is* the stdlib answer).
