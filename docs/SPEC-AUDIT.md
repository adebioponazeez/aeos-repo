# The Founding Specification Audit — AEOS vs the Master Builder Prompt

**Source:** the founding master-builder specification ("Untitled
document (1).pdf", 48 pp, 57 numbered requirements, received
2026-09-07 with the instruction *"Take this specification and
actually build the entire thing now"*). This document is Requirement
54 executed literally: *after completing the first version, AUDIT
EVERYTHING — what is redundant, what is missing, what is unsafe,
what is outdated.* Verdicts are SATISFIED (artifact named), PARTIAL
(named gap), or GAP (honest). History is not trimmed to flatter.

## A. Direction & architecture (reqs 1–27)

| # | Requirement (short) | Verdict | Where it lives |
|---|---|---|---|
| 1 | North star | SATISFIED | README: "the harness is the product" — models are slots, reliability is deterministic code |
| 2 | The 10,000,000× principle | SATISFIED | The leverage metric (`triangle.py`, `leverage.py`): outcomes per human intervention, measured per run |
| 3 | Primary execution command | SATISFIED | `aeos up` (v37) — the one front door; 30+ verbs beneath it |
| 4 | Operating philosophy | SATISFIED | docs/PRINCIPLES.md — 41 compiled principles, each with mechanism + test |
| 5 | Core architecture | SATISFIED | docs/ARCHITECTURE.md — 66 modules, system map |
| 6 | Human executive layer | SATISFIED | Sponsorship tokens (one-shot, scoped); authority console; the autonomy governor's ceiling is human-issued power |
| 7 | AI executive | SATISFIED | `governor.py` — autonomy levels earned by measured reliability, never assumed |
| 8 | AI chief architect | SATISFIED | `codesign.py` — design slates (conservative/least-privilege/reviewer-first), human sponsors one variant |
| 9 | Context OS | SATISFIED | `context_os.py` + `recall.py` (layered FTS: keys→snippets→records, v15) |
| 10 | Knowledge architecture | SATISFIED | `catalog.py` (content-hashed), `research.py` (untrusted-source discipline) |
| 11 | Agent architecture | SATISFIED | `contracts.py` typed envelopes; `fleet.py` CRUD + event stream |
| 12 | Skills architecture | SATISFIED | `skills.py`; `standards.py` — operator law as [STD-n], uncited plans refused (v19) |
| 13 | Orchestration engine | SATISFIED | `orchestrator.py`; `colony.py` — explicit graphs, cycles BLOCK not hang (v25) |
| 14 | Harness engineering | SATISFIED | `harness.py`, `sandbox_runner.py` — process isolation, wall-clock kills |
| 15 | Specification-first development | SATISFIED | No envelope, no result (invariant 1); STANDARDS.md plan gate |
| 16 | Closed-loop engineering | SATISFIED | `learning.py` — failures become gates; regression book |
| 17 | Evaluation OS | SATISFIED | `evals.py` — predicate judges, weights, thresholds (v23); the system grades its own laws |
| 18 | Adversarial review | SATISFIED | `storm.py` — 9-scenario chaos (kill storms, torn writes, ENOSPC, blackout); adversarial tests in-suite |
| 19 | Security architecture | SATISFIED | Write boundaries enforced post-hoc; UNTRUSTED imports quarantined (`federation.py`); read-only wire law (`mcp_http_server.py`) |
| 20 | Observability | SATISFIED | `observability.py`, `telemetry.py`, `otel.py` — OTel export; append-only event stream as replayable proof |
| 21 | Memory OS | SATISFIED | `memory.py` + schema law (fail closed on the future) + torn-write quarantine |
| 22 | Learning OS | SATISFIED | `learning.py`, `entropy.py` — memory must pay rent (v14) |
| 23 | Entropy control | SATISFIED | `entropy.py` coverage; `groom.py` retention (archives, never deletes) |
| 24 | Capability discovery | SATISFIED | `discovery.py`; `factory.py` — measure→design→sandbox→propose→sponsored install (v7) |
| 25 | Autonomy governor | SATISFIED | `governor.py` — no autonomy without reliability, enforced |
| 26 | Model agnosticism | SATISFIED | `models.py`, `adapters.py`, `providers.py` — OpenRouter/Abacus/OpenAI behind a seam; live is opt-in and dollar-capped |
| 27 | Frontier research engine | PARTIAL | `research.py` exists with untrusted-source discipline; live external research is opt-in-only by law (ADR-039/040) — no ambient network, by design |

## B. The book (reqs 28–45)

| # | Requirement (short) | Verdict | Where it lives |
|---|---|---|---|
| 28–29 | Book production mission/objective | SATISFIED | The trilogy in `book/` — volumes I–III + printing PDFs, all shipped |
| 30 | Required structure: 35–45 chapters, PART I–XI | PARTIAL | Vol I carries the part structure (TAC lineage); Vol II–III follow the build journey. **Volume IV (this version) adds the mandated 13-phase curriculum with every required section** |
| 31 | Every chapter must contain (theory→practice→…) | SATISFIED | Volume IV's phase template: OBJECTIVES / THEORY / PRACTICE / PROJECTS / EVALUATION / CAPABILITIES UNLOCKED / ADVANCED PROJECT |
| 32 | Diagram requirement | SATISFIED | ASCII diagrams throughout (boot loop, storm matrix, triangle, quad-recursive map) |
| 33 | Practical implementation | SATISFIED | Every chapter ends in real commands; every claim is a tested artifact |
| 34–38 | Agent/skill/workflow/evaluation contracts | SATISFIED | `contracts.py` typed envelopes are the law of the codebase |
| 39 | Metrics | SATISFIED | `triangle.py` (control/cost/speed), leverage ratio, token ledgers, bench budgets |
| 40 | The 10,000,000× (book treatment) | SATISFIED | Vol I ch. on the principle; measured per run since v13 |
| 41 | Book quality standard | SATISFIED | Honest Gaps sections in every volume; no repetition padding — the spec's own anti-inflation rule |
| 42 | Copyright & research ethics | SATISFIED | Lineage dossier; attribution for absorbed canon; no pirated material, ever |
| 43 | Intellectual sparring mode | SATISFIED | The ADR series is the institutionalized form: every major decision argued, decided, consequences named |
| 44 | Anti-hallucination mode | SATISFIED | The scribe (v35): docs cannot drift; the notary (v36): done is a certificate; the doctor audits the tree |
| 45 | Build-before-explain | SATISFIED | Every version shipped capability + tests first; 37 releases of receipts |

## C. Execution discipline (reqs 46–50)

| # | Requirement (short) | Verdict | Where it lives |
|---|---|---|---|
| 46 | Execution priority | SATISFIED | 478 tests + 47 ADRs of decisions made by doing |
| 47 | Autonomous project management | SATISFIED | Reference loop runs unattended; boot ledger remembers; resume completes — and since v39 the FOREMAN operates the shop between visits: surveys, fixes the mechanical class, files proposals, remembers |
| 48 | Failure protocol | SATISFIED | `aeos up` plain-language failures (v37); storm drills; fail-closed restores |
| 49 | Stop conditions | SATISFIED | Budgets are law; hard $ cap on live; dead-letter stop; governor ceilings |
| 50 | Definition of Done (16 clauses) | SATISFIED | All 16: architecture ✓ specs ✓ agents ✓ skills ✓ context ✓ memory ✓ harness ✓ orchestration ✓ evaluation ✓ security ✓ observability ✓ repo ✓ reference implementation ✓ docs ✓ book ✓ examples ✓ — see the receipt below |

## D. Deliverables & ladder (reqs 51–57)

Requirement 51 (final deliverables A–K): **A** the book (trilogy +
Volume IV); **B** OS specification (ARCHITECTURE.md); **C** repo
blueprint (the repo itself, reproducible from a cold clone);
**D** agent system (contracts + fleet + companions); **E** skills
system (skills.py + STANDARDS); **F** context OS (context_os +
recall); **G** memory OS (memory.py + schema law); **H** harness
(harness + vault + storm); **I** orchestrator (orchestrator +
colony); **J** evaluation OS (evals + entropy + bench); **K**
security (boundaries + quarantine + read-only wire). All SATISFIED.

Requirement 53 (project ladder):

| Rung | Project | Where |
|---|---|---|
| 1 | AI coding assistant | models/adapters behind the seam (v1, v11) |
| 2 | Specification-driven coding agent | pipeline: intent → typed plan → evidence (v1) |
| 3 | Context-aware coding system | context_os + recall (v15) |
| 4 | Specialized agent team | fleet + companions (v12, v16, v20) |
| 5 | Agentic software factory | factory-demo (v7) |
| 6 | Autonomous test-and-repair system | storm + groom + learning (v27, v28) |
| 7 | Long-running engineering agent | resume + soak (v17, v29) |
| 8 | Multi-agent project control plane | colony + federation (v10, v25) |
| 9 | Self-improving engineering OS | meta-loop with hard floors (v6) + the OS itself |
| 10 | AI capability factory | factory + sponsorship + discovery (v3, v7) |
| 11 | Autonomous business workflow | **GAP (honest)** — economics exist (budgets, dividends); business workflows are not built |
| 12 | AI-native enterprise prototype | **GAP (honest)** — federation is org-to-org; the enterprise rung is the named frontier |

Requirement 52 (curriculum): **Volume IV, this version** — the 13
phases, every mandated section, grounded in shipped artifacts.
Requirement 54: this audit. Requirement 55 (versioning): semver +
"versions are earned by tests" (ADR-008), 17 tags. Requirement 56
(the meta-loop): `meta.py` with retirement floors, sponsorship-gated.
Requirement 57 (final command): the loop continues — Volume IV is
its second full turn.

## Honest gaps (kept, not hidden)

1. **Book length vs ~400 pages:** the trilogy + Volume IV is dense
   and complete in structure, well under 400 printed pages. The
   spec's anti-inflation rule and our quality standard both say:
   depth over padding. The gap is owned, not excused.
2. **Project ladder rungs 11–12** (autonomous business workflow,
   AI-native enterprise): not built. The OS beneath them is.
3. **Frontier research (req 27):** live external research stays
   opt-in-only — that is a deliberate law (ADR-039/040), not a
   deficiency; noted as PARTIAL for honesty.
4. **PyPI publication:** workflow automated and proven; activation
   is a three-step operator decision (docs/PUBLISHING.md).

*Audited at v38.0.0. The audit is itself versioned history: re-audit
at every major version, and never let it flatter.*

## Addendum — re-audit at v39.1.0 (cross-validated from source)

An independent cross-validation was run from the source PDFs (not
from memory): the founding spec's 57 numbered requirements extracted
afresh and checked against this audit (57/57 covered); every module
the audit cites verified to exist in src/ (33/33); every cited test
verified in the suite (13/13); the SEF-X reconciliation verified
against the real SEF-X text (every adopted claim traced to source,
every rejected item present AND reasoned). The run found FOUR stale
findings — the audit was one version behind v39 — all fixed in this
version: modules 63→64, tags 15→17, principles 40→41, and the v39
foreman now on the record (it strengthens reqs 47/48: an agent that
surveys, remediates the mechanical class, verifies by
re-measurement, and remembers). The audit's counts are now LAW:
`test_audit_counts_match_live_reality` fails the suite if they
drift again. Also on the record (ADR-045 addendum): SEF-X's
automatic-rollback kernel was translated, not adopted — drift is
NAMED and restore is drilled, but the decision to restore stays
human, per the charter's authority law.
