# DEPLOYMENT REVIEW — AEOS v27.0.0

*A thorough audit of the engineering build and the honest gap list
between "built and proven" and "properly deployed." Every finding
below was verified against the repository this session, not from
memory. Date of audit: 2026-09-03.*

## Verdict

**Engineering-complete for its charter; NOT yet a deployed product.**
The system itself is deployment-grade as a self-contained CLI: it
builds (`aeos-27.0.0-py3-none-any.whl`, code-only, clean), proves
itself (338 tests + 1 opt-in live smoke, chaos storm 8/8 inside the
suite), runs offline by construction, and survives power cuts, full
disks, and hostile inputs with receipts. The *project* around it
lacks every deployment primitive: **no version control, no CI, no
LICENSE file, no published releases, no data retention policy, no
restore drill.** Those are the pending items, ranked below.

## 1. What is built (inventory, verified this session)

| Asset | Count / state | Receipt |
|---|---|---|
| Modules | 50 in `src/aeos/` | `ls \| wc -l` |
| Tests | 31 files, 338 passed + 1 skipped (opt-in live) | `evidence/test-run.txt` |
| ADRs | 36 accepted | `docs/adr/` |
| CLI | 24 subcommands, one entry point (`aeos`) | `[project.scripts]` |
| Docs | ARCHITECTURE, SECURITY, RUNBOOK, BENCHMARK-2026, PRINCIPLES (32 compiled/practiced), RESEARCH-DOSSIER, TAC-COMPLIANCE | `docs/` |
| Books | 3-volume Codex trilogy, HTML + MD + designed PDFs | `book/print/` |
| Code hygiene | **0** TODO/FIXME/XXX markers | grep |
| Dependencies | 0 runtime (MIT declared in pyproject) | `pyproject.toml` |
| Live path | Timeouts (60s default), 429/5xx→TRANSIENT retry taxonomy, context-overflow never-retried, metered + inline budget cutoff | `providers.py` |

## 2. Findings (F-01 … F-12)

| # | Severity | Finding | Evidence | Action |
|---|---|---|---|---|
| F-01 | **DONE** | ~~No version control.~~ git repo, tagged v27.0.0+v28.0.0 | 27 versions of discipline exist only as CHANGELOG prose; no history, no tags, no bisect, no rollback | `git status` → fatal | `git init`, commit, tag `v27.0.0` |
| F-02 | **DONE** | ~~No CI.~~ workflow on main; green matrix pending first push | The suite (storm included) runs only on this sandbox machine | no `.github/` | GitHub Actions: 3.10–3.13 matrix, pytest, `aeos storm`, wheel build |
| F-03 | **DONE** | ~~No LICENSE file.~~ MIT in repo + wheel-asserted | `pyproject` says MIT but the artifact carries no license text — legally ambiguous to distribute | `ls LICENSE*` → missing | Add MIT LICENSE (also ships in wheel) |
| F-04 | **DONE** | ~~Untested.~~ CI matrix 3.10-3.13 (first run = proof) | `requires-python >=3.10`, verified only on 3.13 | this box: 3.13.14 | CI matrix is the proof (F-02) |
| F-05 | **DONE (v28)** | schema headers + fail-closed future + `groom` migration | `memory.jsonl`, events, checkpoints have no format version; upgrades have no migration path | no `schema` field on disk | Add `{"schema": 1}` headers + a `migrate()` that refuses unknown versions (fail closed) |
| F-06 | **DONE (v28)** | `aeos groom` archives beyond newest N, deletes nothing | Per-run event files accumulate in `.aeos/runs/`; `events.jsonl` grows forever; `recall.sqlite` rebuilt but never pruned | retention grep | Retention policy: keep last N runs, archive+prune on a `aeos groom` command |
| F-07 | **DONE (v28)** | 240s walls, CI timeout 20m, one disclosed retry | 5 sleep-based waits (kill-storm delays) — flaky risk on loaded CI runners | grep `sleep(` | Storm marker + generous CI timeout budget, or retry-once policy — receipts must keep running |
| F-08 | **HARNESS DONE (v29)** | soak shipped (sim-proven); live execution awaits operator key — opt-in only | Budget cutoff and provider error taxonomy are simulation-tested; the opt-in live test is skipped without a key | 1 skipped test | One recorded live soak (operator opt-in, capped $) before any production claim |
| F-09 | **DONE (v29)** | deterministic verified backups; drill = storm scenario 9/9 | Atomic writes ≠ backups; `.aeos` state has no export/restore proof | RUNBOOK lacks it | `aeos backup` / `aeos restore` + a storm scenario that restores and re-runs |
| F-10 | **P2** | **Single-host, POSIX-only.** fcntl locks degrade loudly off-POSIX; no distributed durability (deliberate, on record in BENCHMARK) | `vault.py` | Document WSL requirement for Windows; brokers are a v3x decision |
| F-11 | **P2** | **Wheel ships code only.** Docs/book/LICENSE absent from the artifact; PyPI page would be bare | wheel manifest: 55 files, no docs | Ship LICENSE + README in the sdist/wheel; publish to PyPI (or private index) |
| F-12 | **FIXED** | Dead code: unreachable legacy flush block survived the v26 hardening after an early `return` | `memory.py` `_flush` | Removed this session; suite re-run green |

## 3. Pending, ranked

**P0 — cannot call anything "deployed" without these:**
1. Git repository, initial commit at current state, signed tag `v27.0.0` (F-01)
2. CI pipeline: matrix 3.10/3.11/3.12/3.13 × pytest (incl. storm) × wheel build (F-02, F-04)
3. MIT LICENSE file, referenced from the manifest (F-03)

**P1 — first month of real operation:**
4. Schema versioning + fail-closed migrations (F-05)
5. Retention/grooming for runs, events, and indexes (F-06)
6. CI flake policy for chaos timing (F-07)
7. One recorded live soak under a hard dollar cap (F-08, requires operator opt-in)
8. Backup/restore drill as a storm scenario (F-09)

**P2 — scale and ecosystem:**
9. Publish the artifact (PyPI or private index) with license + readme (F-11)
10. Windows story (WSL requirement documented) or a lockfile fallback (F-10)
11. OTLP push, MCP HTTP transport, distributed durability — the BENCHMARK-2026 seam list

## 4. Definition of Deployed (the checklist)

A second operator, on a fresh POSIX box, with no access to this
sandbox, must be able to:

- [x] `git clone` the repo and read the LICENSE          (F-01, F-03)
- [ ] `pip install .` → `aeos selftest` → v27 identity
- [ ] `python -m pytest` → 351 green **from CI, on 3.10–3.13** (F-02 — workflow shipped, first remote run pending push)
- [ ] `aeos storm` → 8/8 on that box
- [ ] run a **live** pipeline with a $-capped key (opt-in) and see the meter stop at the budget (F-08)
- [x] `aeos backup` → destroy workspace → `aeos restore` → re-run accepted (F-09 — storm scenario, drilled on every pytest)
- [ ] follow RUNBOOK.md start-to-finish without asking us anything

## 5. Proposed plan

- **v28 "The Shipyard"** — F-01/02/03/05/06/07: git + CI + LICENSE
  + schema versions + `aeos groom` + storm flake policy. All
  offline, all testable, closes every P0.
- **v29 "The Soak"** — F-08/09/11: recorded live soak (opt-in),
  backup/restore drill in the storm, packaged artifact ready to
  publish.

*Reviewed by the system that built it — which is exactly why every
row above carries evidence. The build was never the risk; the
packaging of the build is.*
