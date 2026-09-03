# PRINCIPLES — The Charter

*One screen. Every principle maps to a mechanism with a test, or is
explicitly marked PRACTICED (held by discipline and audit, because no
test can force it). A value that can be a test must be a test; a value
that can't must be written down where it can be audited.*

## COMPILED — values with proofs

| # | Principle | Mechanism | Proof |
|---|---|---|---|
| 1 | Maximum leverage per unit of human attention — not max automation | `economics.leverage_ratio`, measured from real interventions | every bundle's `leverage` field |
| 2 | Never accept "the agent says it works" | `claims_are_backed` gate; closed verdict vocabulary | `test_claims_without_evidence_fail_the_gate` |
| 3 | Absence of failure is not success | UNVERIFIED is a first-class verdict | `test_empty_verdict_stays_unverified` |
| 4 | Autonomy is earned, measured, revocable | Governor reliability EMA; automatic promote/demote | `test_failures_demote` |
| 5 | High-impact authority is never a blank check | Checkpoint-forever classes; one-shot approvals | `test_destructive_checkpoints_even_at_l6` |
| 6 | Fail closed under uncertainty | Unknown action class → DENY; quarantine-before-token | `test_unknown_class_denies` |
| 7 | Boundaries, not promises | `writes:` enforced post-hoc — internal agents, live models, companions alike | `test_unauthorized_writes_are_reverted`, `test_roguish_pi_is_reverted_and_killed` |
| 8 | Repair the correct layer, never blind retry | Error taxonomy; bounded repair; failure playbook | `test_context_overflow_never_retries` |
| 9 | Failure never becomes folklore | Evidence-gated canonical memory; promotion requires proof | `test_failure_never_becomes_canonical` |
| 10 | Promotion is a measurement | 3 repetitions → skill; 5 wins → agent; sandbox PASS → install | `test_proven_skill_proposes_agent_promotion` |
| 11 | Creation never grades itself | Independent evaluator; re-runs tests itself | evaluator contract + graph skip |
| 12 | Context is a budget, not a gift | Tiered, expiring, loud-drop assembly | `test_budget_is_enforced` |
| 13 | The tradeoff is real (control costs speed) | Triangle stances with immutable floors; measured receipt | `test_control_measures_more_control_than_speed` |
| 14 | Self-modification needs spent human authority | Sponsorship tokens: scoped, one-shot, expiring, audited | `test_spend_is_one_shot` |
| 15 | Floors outrank keys | Meta-loop bounds refuse out-of-range even WITH a token | `test_out_of_bounds_threshold_refused_even_with_token` |
| 16 | Import is quarantine | Federation: no reputation substitutes for local validation | `test_quarantined_install_refused_even_with_token` |
| 17 | Money is governed inside the seam | Metered adapter; inline budget cutoff | `test_budget_cutoff_is_inline_and_permanent` |
| 18 | Versions are earned, never worn | ADR-008; each CHANGELOG entry cites capability + tests | the CHANGELOG itself |
| 19 | Memory pays rent | `dividend.rent()` flags never-recalled canonical records as squatting token-weight | `test_unrecalled_memory_is_squatting` |
| 20 | Consumption goes negative | `TokenLedger` marginal: recall + amortized overhead must beat the no-memory baseline — computed, not vibes | `test_marginal_is_negative` |
| 21 | Structure is the cache key | Canonical-JSON `stable_prefix()` — byte-identical prefixes across runs, volatile tails ride last | `test_same_stable_set_same_prefix_different_tail` |
| 22 | Plans survive their process | `resume.PlanCheckpoint` — atomic write after every task; resume runs only pending | `test_side_effects_happen_exactly_once` |
| 23 | Mindsets become rubrics | `leverage.audit` — 12 points checked against artifacts on disk | `test_full_workspace_scores_high` |
| 24 | Standards are cited, not remembered | `standards.check_plan` — uncited plans refused when law is registered | `test_plan_without_citation_is_refused` |
| 25 | The protocol is a boundary too | `mcp_client.import_tools` — every imported tool UNTRUSTED | `test_imported_tools_enter_untrusted` |
| 26 | Runs are graded, not watched | `evals.EvalSuite` — predicate judges, weights, thresholds; a raising case FAILS | `test_raising_case_fails_without_crashing` |
| 27 | Expose only verbs that read | `mcp_server.READONLY_TOOLS` — the server serves readers, never writers | `test_tools_listed_and_all_readonly` |
| 28 | The graph is explicit, cycles fail closed | `colony.Colony` — requires + conditions; blocked never loops | `test_cycles_block_instead_of_hanging` |
| 29 | Power loss loses moments, never memory | `vault.durable_write` — tmp+fsync+rename; a crash or full disk never touches the original | `test_failed_rename_leaves_original_intact` |
| 30 | Torn writes quarantine, never crash | `vault.load_jsonl_tolerant` — torn lines to a `.torn` sidecar, the system continues | `test_torn_tail_quarantined_not_fatal` |
| 31 | Network is optional | `vault.socket_blackout` — a full run with sockets impossible proves the default path is offline | `test_full_run_makes_zero_socket_calls` |
| 32 | Resilience is a receipt, not a claim | `storm.run_storm` — kill -9 x3, torn, ENOSPC, garbage, 256MB cap, blackout; runs inside the suite | `test_every_scenario_survives` |
| 33 | Backups are drilled, not assumed | `backup.restore_backup` — every member sha256-verified; tampered backups restore NOTHING | `test_tampered_backup_refused_fail_closed` |
| 34 | The door opens on purpose, and only to readers | `mcp_http_server` — READONLY_TOOLS is the whole wire catalog; loopback bind by default | `test_serves_readonly_tools_over_http` |
| 35 | The wire gets receipts, not exceptions | `otlp.push_spans` — hostile wire = named attempts, spans safe on disk | `test_hostile_wire_is_a_receipt_not_an_exception` |
| 36 | Claims become checks | `doctor` — the charter's cited tests must exist in the suite, machine-verified | `test_charter_is_load_bearing` |

## PRACTICED — held by discipline, auditable by record

| Principle | How it's held |
|---|---|
| Honesty in documentation | ADR-008; "Honest Gaps" chapters in every volume; gaps stay listed until closed |
| Attribution and refusal | Lineage dossier; no pirated material, ever; forks absorbed with credit, never copied silently |
| Restraint — don't over-engineer trivial work | Partially compiled ("a known command is code, not an agent"); the rest is taste, kept human |
| The human ascends | Not a mechanism — a direction. The book, the labs, and the leverage curve are its instruments |

## The spirit, in one paragraph

The first artifact this project began from carried a sentence: *"you
don't have to be perfect, you just have to try, over and over, in
success or failure."* That is the architecture. The harness assumes
imperfect agents — it can kill a hung worker, revert a rogue write,
refuse an unbacked claim, and learn from a failure without ever
letting it become canon. **"The harness is the product" is that
sentence said in engineering.** And the triangle is its honest
companion: you cannot have everything — name the trade, floor the
law, receipt the cost.

*The human moves upward. The machines execute downward. The system
learns between them.*
