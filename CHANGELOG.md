# Changelog — AEOS

Every version below is earned by shipped, tested capability
(ADR-008). Test counts are at tag time.

## v39.6.0 — The Graph Language: Declarative Workflows (565 tests)
- The dark-factory roadmap's #3 gap, closed: declarative workflow
  graphs + per-node model routing (Fabro's core ergonomics,
  compiled into AEOS law). `aeos graph --file plan.dot --style
  routing.style [--run]`.
- The language is a NAMED DOT SUBSET: digraph, node statements
  with [attrs], `->` chains, subgraph clusters, // and # comments,
  quoted strings. Every error is a plain-language GraphError with
  a line number — never a SyntaxError traceback.
- Clusters are nested harnesses: `subgraph cluster_build` compiles
  to ONE parent task whose subplan is the cluster's nodes — the
  v39.5 recursion, now declarative. Cross-level edges attach
  through the parent (no phantom nodes); intra-cluster edges stay
  inside; nesting deeper than MAX_SUBPLAN_DEPTH is a NAMED compile
  error ("recursion is a tool, not a trap").
- Routing stylesheets: INI sections matched by fnmatch on task
  names (a nested-harness parent also matches its cluster name),
  PER-KEY FALLBACK — each key takes the first matching section
  that defines it; [*] is the fallback. Keys: model, agent,
  max_attempts.
- SAFETY LAW, compile-enforced (ADR-052): stylesheets route, they
  never declassify. `class=` on a stylesheet section or on an edge
  is a NAMED refusal — classification lives on the node where the
  agent acts, and a routing layer that could move classes could
  hide danger.
- The compiled graph is the SAME TaskSpec the orchestrator
  already runs: same governor classification, same hooks
  (task/wave/subplan points fire through the compiled graph),
  same gates. A declarative graph gets zero new trust.
- Examples ship in-repo: examples/ship-graph.dot +
  examples/routing.style (research routes to echo-fast; the build
  cluster gets max_attempts=3; everyone falls back to echo).

## v39.5.0 — Hooks & Recursion: Interception First-Class (539 tests)
- Cole Medin's advocacy, compiled into law: hooks are THE critical
  mechanism — decoupled from the agent (infrastructure-level),
  composable (ordered registrations on a closed vocabulary of named
  points), and they REDIRECT, not just reject. New `hooks.py`: a
  thread-safe HookBus with task.pre/post, wave.pre/post,
  subplan.pre, and refusal points; HookVeto is a named refusal in
  plain language; a pre-hook may rewrite an action class
  (WRITE->READ) preserving intent while removing danger; observer
  errors are collected and named — an observer can never crash the
  run it observes. `aeos hooks` inspects the surface;
  `--register-demo` runs a live veto demo.
- Recursive harness graphs (the Recursive Agent Harness pattern,
  arXiv:2606.13643): the recursive unit is a full harness, not a
  model call. TaskSpec gains `subplan`; a task with a subplan
  expands into a NESTED Orchestrator with its own waves, governor,
  gates and events (subplan.start/end, depth-stamped), MAX_DEPTH=3
  — deeper nesting refuses NAMED ("recursion is a tool, not a
  trap"); child failures fail the parent named; hooks compose
  through every level.
- Honest scope (ADR-051): hooks are in-process callables inside
  the OS trust boundary — guardrails against agent behavior, not a
  plugin sandbox against hostile code; subplans are runtime
  constructs (durable checkpoints store settled parent state, the
  child re-derives — idempotent handlers, spec §14).

## v39.4.0 — The Holdout: Digital-Twin Separation (527 tests)
- The dark-factory validation's #1 honest gap, closed: evaluation
  the agent cannot overfit to. Scenarios live OUTSIDE the codebase
  in a sealed vault (~/.aeos/holdout by default — outside every
  repo and workspace); `aeos holdout --init` seals a per-install
  instance set (nonce-seeded: which hostile intents, which order,
  which parameters — reading the source reveals the families, never
  the instances); `aeos holdout --run` verifies the seal
  (sha256 + hmac + merkle root; a tampered blob refuses to run),
  copies the target workspace to a throwaway digital twin, runs
  every sealed family against the twin, renders a verdict-only
  report, and proves the original workspace byte-identical after.
- Five families, all graded against real runs: hostile intents
  verdicted (6 seeded injection/garbage/unicode intents — closed
  accept/reject, never a fatal), determinism (same intent on two
  twin copies -> identical canonical bundles, clock/env excluded),
  refusal named (read-only twin refuses NAMED — "could not be
  opened", not misdiagnosed as held), economics governed, leverage
  numbered.
- Honest scope, on the record (ADR-050): the separation is
  boundary-based — the sandbox law already confines workspace
  agents (writes only inside their cwd, never networked), and the
  vault is sealed against reading, not multi-tenant security
  against a same-user adversary with an arbitrary shell.
- The production-gauntlet re-run (part of this release's
  re-verification) caught a THIRD defect, rare but real: the boot
  preflight's writable probe used a FIXED path, so two simultaneous
  boots could unlink each other's probe and misreport a WRITABLE
  workspace as unwritable (the 1-in-20 rc=2 in the concurrent-boot
  group). Reproduced deterministically (51/320 misreports under a
  threaded hammer), fixed with a unique auto-cleaning probe
  (0/320), regression-tested forever.
- Wording: lock refusals now compose cleanly through every path
  ("workspace not available: the lock is held by a live run…" /
  "…the lock file could not be opened: … — check permissions/disk").
- DARK-FACTORY-VALIDATION updated: pattern #7 (layered evaluation
  with holdout separation) PARTIAL -> EXCEEDS-pending-audience; the
  roadmap's first gap is closed.

## v39.3.0 — The Field Test: Beyond One Sandbox (515 tests)
- Operator challenge: receipts produced inside one sandbox prove
  only that sandbox. Answered with a field gauntlet — the same
  build exercised in genuinely different environments: empty
  environment (env -i), read-only workspace, read-only HOME, a
  real 256KB tmpfs mounted under unshare (true kernel ENOSPC),
  a 64MB tmpfs workspace with a full roundtrip, a shadow package
  shadowing the aeos import, deep unicode paths under LC_ALL=C,
  TZ/locale flips for determinism, all as non-root.
  Receipt: evidence/field-test-v39.txt.
- **Run 2 found two defect classes** (that is the field test
  working):
  1. `WorkspaceLock.acquire` opened the lock file outside its
     guard — a read-only workspace surfaced as a raw
     PermissionError traceback instead of a named refusal;
  2. when the disk is truly full, the ENOSPC escaped raw from
     the foreman's durable history append, killing the run
     before it could deliver its verdict.
- **Both fixed**: `refusal_reason()` distinguishes "the lock is
  held by a live run" from "the lock file could not be opened —
  check permissions/disk"; the foreman refuses by name
  ("workspace is not available: ..."); history and receipts
  degrade best-effort (`unwritten` / `receipt_unwritten` flags)
  so a run's verdict survives a full disk; doctor and pipeline
  report the same honest reason; render() branches its advice.
- Harness confounds were separated from defects and eliminated
  (set -e swallowing checks; machine HOME leaking into
  namespaces; README count drift leaking through repo context) —
  the final field run is green with every failure named, never
  raw.
- The wheel (not just the editable install) verified on real
  CPython 3.10, 3.11 and 3.12.

## v39.2.0 — The Gauntlet: Production Constraints, For Real (511 tests)
- Operator demand: "test and validate and ensure this build
  survives real production grade constraints." Answered with an
  11-group gauntlet run against the real build — real subprocesses,
  real kills at RANDOM offsets, real kernel limits (ulimit -f/-v),
  real hostile HTTP endpoints, real concurrency, real corruption,
  real hostile paths. Receipt: evidence/production-gauntlet-v39.txt.
- **Run 1 found five defects** (that is the gauntlet working):
  1. two foremen could race on one workspace (no lock);
  2. an action exception under file-size starvation escaped as a
     raw traceback (OSError: File too large) — plain-language law
     violated;
  3. the failed backup left a .tmp corpse — the atomic-write
     contract broken;
  4. a lock-refused run surfaced as KeyError: 'leverage' instead of
     the refusal's own words;
  5. `aeos backup` itself tracebacks on ENOSPC.
- **All five fixed**: the foreman takes the kernel-released
  workspace lock (busy = named refusal, exit 2); action exceptions
  are named and stop the run; `_write_tar_body` failures clean
  their tmp; ignition speaks a refused run's reason; the backup
  verb names starvation. Five regression tests pin them.
- **Run 2: 27/27 green** — 15/15 random kills recovered, concurrent
  boots 1-winner-3-named, concurrent foremen serialized by the lock,
  starvation named with zero litter, 256MB boot, hostile wires
  bounded (500 -> dead letter; slow -> 10s timeout, no hang),
  corrupted state tolerated, hostile paths deterministic, fuzz
  bounded, bench within budgets, the whole core offline under
  unshare -rn.

## v39.1.0 — Cross-Validation: Everything Checked From Source (506 tests)
- Operator demand: "validate and cross-check that everything
  validates against source spec, aligned with broad aeos goals, and
  how have you reconciled sef-x-omni-os." Executed from the source
  PDFs, not from memory of them.
- **Founding spec**: 57/57 requirements re-extracted from the PDF
  and covered by docs/SPEC-AUDIT.md; all 33 modules the audit cites
  exist; all cited tests exist; all cited verbs exist in the live
  CLI.
- **SEF-X reconciliation**: every ADOPTED claim verified present in
  the real SEF-X text; every REJECTED item verified present AND
  reasoned in ADR-045. Two compressed items stated precisely now
  (ADR-045 addendum): the auto-rollback kernel was TRANSLATED, not
  adopted (drift is NAMED, restore is drilled, the decision stays
  human — charter authority law), and v39's foreman IS SEF-X 3.2's
  self-healing pipeline / drift-healing agent, built honestly.
- **Four stale audit findings caught and fixed**: modules 63->64,
  tags 15->17, principles 40->41, footer re-audit owed (its own
  law: re-audit every major version). The audit now carries a
  re-audit addendum and its counts are MACHINE-CHECKED LAW
  (test_audit_counts_match_live_reality,
  test_audit_artifacts_are_real) — the audit cannot drift again.
- Receipt: evidence/cross-validation-v39.txt (run 1 with findings,
  run 2 all green).

## v39.0.0 — The Foreman: The Autonomous Operator (504 tests)
- Operator direction, kept verbatim in spirit: "all the above is
  for you to actually use it to produce a compelling production
  grade autonomous agentic AI software system — and not a PDF —
  following the tradition of dhh, creator of Omarchy." Answered
  the only way that counts: the product is the code. No book
  chapter, no printing, no PDF assets on this release.
- **`foreman.py` + `aeos foreman [--apply]`** (ADR-048): the
  autonomous loop the harness always deserved — PERCEIVE (survey:
  state schema, torn writes, run retention, backup posture, boot
  ledger, machine outbox, and in a checkout README drift + the
  save-proof ledger), PLAN (every finding classified MECHANICAL —
  safe, deterministic, reversible — or PROPOSAL — human work,
  filed, never silently attempted), ACT (`--apply` only, fixed
  dependency order: schema → torn → groom → backup-drill; heal
  first, then capture the healed state; a failing action STOPS the
  run), VERIFY (re-survey; findings that survive their own remedy
  are named; pre/post workspace Merkle roots in every receipt),
  REMEMBER (append-only, signature-deduped history — recurring
  findings become patterns; no clocks, sequence is time).
- Omarchy discipline applied: one command, opinionated defaults
  (KEEP_RUNS=10, survey-is-safe), zero new config knobs, exit
  codes as a contract (0 clean/resolved · 1 attention · 2 failed).
- Doctor row: "foreman ledger" (last run: mode, resolved, remain).
  Charter principle 41: the shop runs itself between visits.
- Dogfooded before shipping: on a deliberately degraded workspace
  the foreman found 4 mechanical + 1 honest proposal, fixed all 4
  (schema upgraded, torn archived, 4 runs archived, backup drilled
  + restore verified 18 members), second pass quiet. The README
  drift it filed was real — this doc pass is the fix.

## v38.0.0 — The Curriculum: The Founding Spec, Audited (486 tests)
- The operator's "try again", decoded against the founding
  master-builder specification (the second uploaded document): its
  Requirement 54 commands "AUDIT EVERYTHING" after the first build,
  and its Requirements 30/52 demand a 13-phase curriculum the
  journey had not yet produced. This version is the loop's second
  full turn.
- **`docs/SPEC-AUDIT.md`**: all 57 numbered requirements of the
  founding spec carry verdicts (SATISFIED with artifact / PARTIAL /
  GAP) — the DoD's 16 clauses answered one by one, the 12-rung
  project ladder mapped to shipped versions, and the honest gaps
  kept visible: book length vs ~400pp, ladder rungs 11–12, live
  research opt-in by law, PyPI awaiting operator activation.
- **Volume IV — The Curriculum** (book/parts-v4 + print PDF): the
  mandated 13 phases (AI coding → agentic coding → context → skills
  → agents → harness → evaluation → orchestration → long-running →
  agent-native → autonomy → the OS → the enterprise frontier), each
  carrying the seven required sections (objectives / theory /
  practice / projects / evaluation / capabilities unlocked /
  advanced project) — every claim grounded in real modules,
  commands, and tests. Phase 13's capability is "None claimed":
  the frontier is drawn accurately, not relabeled.
- Tests: the curriculum must contain all 13 phases × 7 sections;
  every `aeos <verb>` it teaches must exist in the live CLI (the
  README's law, extended to the book); the audit must cover all 57
  requirements with no silent drops; the ladder must map all 12
  rungs; the 16-clause DoD must be answered clause by clause.
  Charter principle 40: the founding contract is audited, not
  assumed. ADR-047.

## v37.0.2 — Guard Patch: A Guard That Cannot Fail Protects Nothing (478 tests)
- v37.0.1's portability guard was itself non-portable: on Python
  < 3.12, ast positions INSIDE f-strings are approximations (the
  whole concatenated literal), so the guard reported 270 phantom
  violations on the very Pythons it protects — CI caught it within
  minutes of the tag.
- Fix: the ast-based guard runs only where ast is truthful (>= 3.12,
  where development and notarization happen); below 3.12 the
  INTERPRETER ITSELF is the guard — the 3.12-only syntax is a
  SyntaxError at import, failing the suite natively (exactly what
  CI demonstrated on v37.0.0). Plus `test_the_guard_actually_
  catches_the_pattern`: a synthetic module carrying the exact
  v37.0.0 defect must be flagged — a guard that cannot fail
  protects nothing.

## v37.0.1 — Portability Patch: The Floor Is 3.10 (477 tests)
- CI caught what the certificate could not: the v37.0.0 notarization
  proves the suite passes ON THE PYTHON THAT RAN IT — portability is
  the matrix's job, and the matrix spoke. Python 3.10/3.11 refused
  to even import ignition.py: one f-string expression spanned lines
  (PEP 701, legal only from 3.12); the local 3.13 parsed it happily.
- Fix: single-line expression. Guard: `test_no_multiline_fstring_
  expressions` — an ast scan over every module, so the entire class
  of 3.12-only syntax is unshippable while the floor is 3.10.
- The v37.0.0 tag stays (history); its release notes carry the
  correction; v37.0.1 is the version to run.

## v37.0.0 — The Ignition: One Front Door, Plain-Language Failure (476 tests)
- Operator feedback, kept verbatim in spirit: 35+ verbs and no
  single production door; and when a real environment fails to
  load — permissions, disk, state from the future, a missing key —
  a stack trace is not help. A production engine is judged at
  boot, in the dark, by someone in a hurry.
- **`ignition.py` + `aeos up`** (ADR-046): four stages — PREFLIGHT
  (python, disk, zero-dep law, writable workspace, state schema,
  torn writes, locks, live-key presence), WORKSPACE (create/heal,
  in-place schema upgrade), WORK (the reference loop + evidence
  bundle), SHUTDOWN (a numbered, atomically-written boot receipt).
  Exit codes scripts can branch on: 0 ok · 2 preflight ·
  3 workspace · 4 work · 5 shutdown.
- **The plain-language law**: every FAIL names WHAT HAPPENED and
  WHAT TO DO in one breath each — never a traceback; key VALUES are
  never read into receipts (presence only). A failed boot still
  writes its receipt, and the NEXT boot's preflight reports how the
  LAST one died ("crashed boot noted: work-failed; atomic writes
  mean no torn state — continuing").
- **Found the hard way, fixed the same hour**: `aeos up
  --save-proof` inside a test run spawned the suite inside the
  suite — a proof containing itself. Guard: proof commands run with
  AEOS_PROOF_INNER set; a notary asked for the DEFAULT SUITE
  COMMAND seeing it refuses ("one proof at a time"). The first
  guard was too blunt and the notary proved it — this release's own
  first notarization came back TESTS-FAILED (the guard was refusing
  honest certificate construction); sharpened, re-notarized,
  VERIFIED; the failed certificate stays in the ledger as history. First-cause preservation: a receipt-write failure can
  never overwrite the original boot failure.
- Doctor row: "boot preflight" (workspace context) — N check(s),
  which would block `aeos up`. Charter principle 39.

## v36.0.1 — Validation Patch: The Root Is Reproducible (457 tests)
- Found by COLD-CLONE validation (the exact discipline v35.1
  taught): `git clone && checkout v36.0.0 && aeos save-proof
  --verify --against-tree` REFUSED — src/aeos.egg-info, regenerated
  by every `pip install -e .` with content that depends on WHEN it
  ran, was inside the Merkle root. The warm worktree hid it; the
  fresh clone refused it. The notary caught its own author.
- Fix: build metadata (*.egg-info, *.dist-info, *.egg directories)
  and .DS_Store join the exclusion law — derived trees never count
  toward identity. Regression test:
  `test_build_metadata_never_counts`.
- The v36.0.0 certificate stays in the ledger (it truthfully
  describes the tree state it hashed); v36.0.1 re-notarizes with a
  root that reproduces from any clean clone — and the promise was
  re-proven from a cold clone BEFORE this entry shipped.

## v36.0.0 — The Notary: SEF-X Handover, Honestly Adopted (456 tests)
- The SEF-X / OMNI-OS V22 handover spec demanded cryptographic
  save-proofs, an edge WAL outbox, capability permanence — alongside
  a shelf of pseudo-quantitative vapor (H-JEPA energy bounds, Arrow
  Flight, microVMs). ADR-045 is the full disposition: adopt what is
  engineering, reject what is theater, each on the record.
- **`merkle.py` + `saveproof.py` + `aeos save-proof`**: the tree has
  a cryptographic identity — sha256, path-bound leaves (renames are
  not free), pairwise nodes, odd promoted, volatile trees excluded.
  Completion is a CERTIFICATE: pre/post roots + a green command.
  Outcomes are named, never narrated: verified / drifted (files
  listed) / tests-failed / timed-out. Tamper-evident by default
  (sha256 self-digest), HMAC-SHA256 with AEOS_PROOF_KEY; NO
  timestamps inside — determinism is law. The ledger is
  evidence/save-proofs/, excluded from the root it certifies (the
  receipt about the tree is not the tree — observer effect removed
  by rule, on the record).
- **`outbox.py` + `aeos outbox enqueue|status|flush`**: the edge
  outbox — SQLite WAL, content-hash idempotency keys (the same
  record twice is ONE row), bounded retries with dead letters, and
  flush to ONE explicit endpoint only (ADR-039/040 intact) with a
  --dry rehearsal. At-least-once toward the endpoint, exactly-once
  locally — the honest contract a queue can keep.
- **Capability permanence, machine-checked**: every CLI verb that
  ever shipped (all 10 tags) still parses today — tested at ship
  time from the full clone; CI clones shallow and skips, said
  plainly in the test.
- Doctor +2 rows: edge outbox (corruption = FAIL, dead letters =
  WARN, buffering = PASS by design) and the save-proof ledger (an
  edited receipt is a FAIL; an empty ledger is honestly empty).
  Charter principle 38. Receipt: evidence/handover-v36.txt.

## v35.1.0 — Validation Patch: Repo Context From Any Install (427 tests)
- Found by INDEPENDENT validation (fresh clone -> fresh venv ->
  non-editable install, evidence/validation-findings-v35.txt):
  `aeos scribe` and two doctor rows guessed the repo root from the
  package location, which is wrong for installed packages. Fix:
  shared `doctor.repo_root()` — CWD chain first (works from any
  install kind), package parents second, and NO context is an
  honest WARN ("skipped, not guessed"). Regression tests included.

## v35.0.0 — The Scribe: Documentation Cannot Drift (426 tests)
- **`scribe.py` + `aeos scribe`** (ADR-044): README claims — test/
  module/ADR counts, version headline, every `aeos <command>` —
  machine-checked against LIVE reality; drift FAILs with file:line.
  Version-table rows and the historical record are exempt by design
  (history is not a claim about the present). Doctor row: "README
  tells the truth". Charter principle 37.
- **Dogfooded on landing**: the scribe's first receipt found FOUR
  real stale claims in the README (a v1-era "131 tests" and v11-era
  "177 tests" among them) — fixed in this commit; RUNBOOK and
  ARCHITECTURE brought current.

## v34.0.0 — The Gauge: The Performance Envelope (414 tests)
- **`bench.py` + `aeos bench [--full]`** (ADR-043): seven measured
  cases with LAW budgets; at 10k scale all within budget (memory
  load 0.065s, recall 0.064s paying 94 tokens, backup 0.024s, groom
  0.347s, doctor 0.177s). docs/ENVELOPE.md records receipts, fixed
  defects, and accepted limits as named seams.
- **Fixed by the gauge**: `EventBus.tail` O(N)->O(1) (final-block
  seek, torn fragments dropped as replay quarantines); `Colony.run`
  wave cap now scales with graph size (a 60-deep chain is a legal
  graph; cycles still break in one idle wave).

## v33.0.0 — The Charter: Machine-Checked Constitution + Upgrade Drill (404 tests)
- **Charter check** (ADR-042): every test cited in PRINCIPLES.md is
  verified to exist in the suite — a cited-but-absent test FAILS
  `aeos doctor`. Receipt: 34 cited tests, all present. The
  constitution can no longer silently reference phantom laws.
- **Cross-version upgrade drill**: a genuine v27-era workspace
  (header-less state, 12 run files) must load back-compat, groom to
  current schemas, accept a fresh run, doctor clean, and survive
  backup/destroy/restore — one test, six versions of state distance.
- **Publishing last mile**: `.github/workflows/release.yml` — tag
  push proves the suite, builds, twine-checks, publishes via PyPI
  trusted publishing (no tokens); INERT until the operator enables
  (`PYPI_ENABLED=true` + pending publisher; three steps in
  docs/PUBLISHING.md).

## v32.0.0 — The Physician: Self-Audit + Docs Truth (397 tests)
- **`doctor.py`** (ADR-041): the system audits its own claims —
  `zero_dep_audit()` machine-checks ADR-002 (57 modules, 0 violations,
  ast-based import scan); workspace health (schema versions, torn
  sidecars, lock state, disk, retention hint); repo health (tree,
  tags). PASS/WARN/FAIL with named detail; FAIL exits nonzero. CLI:
  `aeos doctor`. The doctor caught two bugs in itself before shipping.
- **Docs truth pass**: RUNBOOK.md rewritten at v32 (operator journey:
  install → doctor → storm → soak → backup/restore → serving →
  troubleshooting → shipping); ARCHITECTURE.md system map at v32
  (8 layers, 57 modules).

## v31.0.0 — The Consulate: HTTP Server Mode + Publish Readiness (384 tests)
- **`mcp_http_server.py`** (ADR-040): AEOS served over HTTP — the
  SAME `handle_request` (one tool law, two transports), tool set
  exactly READONLY_TOOLS, default bind 127.0.0.1 (0.0.0.0 explicit),
  1MB body bound, malformed input fails closed as JSON-RPC errors,
  notifications 202'd silently. Wire roundtrip proven: our v30 HTTP
  client against the consulate. Build finding fixed: the client now
  sends true id-less notifications (the strict server refused the
  old id-carrying one). CLI: `aeos mcp --serve-http [--roundtrip]`.
  Closes the final named MCP seam.
- **Publish readiness (F-11)**: sdist + wheel build clean and PASS
  `twine check` (LICENSE + tests in artifacts); classifiers + repo
  URLs in metadata; `docs/PUBLISHING.md` — two paths (token upload /
  trusted publishing). Name `aeos` verified FREE on PyPI.

## v30.0.0 — The Embassy: HTTP Transports, Loopback-Proven (374 tests)
- **`mcp_http.py`** (ADR-039): the streamable-HTTP MCP transport —
  same client law (walls, fail-closed) over the wire; JSON and
  text/event-stream responses both parsed. Closes the "transports
  beyond stdio" seam, client side. CLI: `aeos mcp --http-url URL`.
- **`otlp.py`** (ADR-039): OTLP/HTTP push with bounded, typed
  retries (429/5xx only); a hostile wire is a receipt, never an
  exception. CLI: `aeos otel --push URL`. Closes the "OTLP push"
  seam. Both endpoint-explicit — the default path remains
  blackout-proven offline; all tests run on the loopback range.
- **GitHub Release v29.0.0** published with the Codex trilogy PDFs
  + the fresh-clone receipt as assets.

## v29.0.0 — The Soak: Backup Drills + Sustained Operation (363 tests)
- **`backup.py`** (ADR-038, F-09): deterministic backups — sorted
  members, sha256 manifest with no clocks/paths, so identical state
  yields byte-identical archives. Restore verifies EVERY member and
  fails closed on any mismatch; caches never carried (recall REBUILDS,
  proving it is a cache); locks never carried. CLI: `aeos backup` /
  `aeos restore`. The backup -> destroy -> restore -> re-run drill is
  now storm scenario 9 of 9.
- **`soak.py`** (F-08): `aeos soak --runs N` — sustained operation
  receipt: accepted count, wall mean/max, token/cost totals, memory
  growth, disk delta. Live soak opt-in only (AEOS_LIVE=1 + key) under
  a hard dollar cap; simulation is the honest, labeled default.

## v28.0.0 — The Shipyard: Deployment Closure (351 tests)
- **First-push commit carries LICENSE + CI** (F-01..F-04): git repo,
  tag v27.0.0, MIT license shipped in-repo and asserted in the built
  wheel; CI matrix 3.10-3.13 with selftest, full suite (storm
  included), `aeos storm`, clean wheel check.
- **`groom.py` + schema law** (ADR-037, F-05/F-06): long-lived state
  (memory, fleet stream, checkpoints) now opens with an
  `aeos_schema` header; legacy v27 files load back-compat; future
  schemas FAIL CLOSED (`SchemaError`). `aeos groom` upgrades legacy
  state in place and archives all but the newest N runs — nothing
  deleted, everything auditable.
- **Storm flake policy** (F-07): generous walls (240s), CI
  timeout-minutes 20, and one DISCLOSED retry on the two wall-clock
  sensitive scenarios.

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
