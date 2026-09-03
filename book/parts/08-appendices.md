# APPENDICES

## Appendix A — The Evidence

Reproduce everything:

```bash
pip install -e . && python -m pytest && aeos run-demo
```

**Test suite: 68 passed** (`evidence/test-run.txt`), distributed:
contracts 4, governor 11, context 9, memory/skills/eval 14,
orchestrator 9, harness 6, learning/entropy/discovery 9, e2e 4.

**Reference run** (`evidence/run-bundle.json`): accepted; 7/7 tasks;
7 waves; 0 repair cycles; 1.01s; 37 events; success rate 1.0;
governor L3→L5 on reliability 1.0; 7 lessons; 7 checkpoints; 0
boundary violations; 6 discovery proposals; 0 entropy findings.

**The four invariants and their proofs:**

| Invariant | Test |
|---|---|
| No envelope, no result | `test_handler_must_return_envelope` |
| No authority without a boundary | `test_unauthorized_writes_are_reverted` |
| No autonomy without reliability | `test_failures_demote`, `test_sustained_success_promotes` |
| No memory without validation | `test_canonical_write_requires_evidence`, `test_failure_never_becomes_canonical` |

## Appendix B — The Decision Record (Condensed)

- **ADR-001** Model-agnostic seam; EchoModel doubles. *Harness is the
  product; guarantees must not need a smart model to hold.*
- **ADR-002** Zero runtime dependencies. *Auditable trust boundary;
  ~2k LOC.*
- **ADR-003** Typed envelopes + evidence gates. *Claims are untrusted;
  `claims_are_backed`; closed verdict vocabulary.*
- **ADR-004** Governor as data table; fail closed. *High-impact
  classes checkpoint forever; one-shot approvals; reliability EMA
  drives the ladder.*
- **ADR-005** Context as budgeted resource. *Loud drops; essential
  overflow is a hard flag; conflicts surfaced; progressive
  disclosure.*
- **ADR-006** Checkpoints + harness-enforced writes. *Post-hoc
  mechanical enforcement; `.aeos/` inside the fence.*
- **ADR-007** MCP/A2A as adapters. *Protocol churn never reaches the
  trust boundary.*
- **ADR-008** Honest scope. *v1.0 claims exactly what the evidence
  supports.*

Full records with alternatives and tradeoffs: `docs/adr/`.

## Appendix C — Lineage and Sources

**Forked and absorbed (MIT, public):**
`disler/super-simple-software-factory` — agent-proposes/code-disposes,
typed envelopes, evidence gates, `writes:` boundaries, phase
descriptions, `run.finish(accepted=)`. `disler/fusion-harness` —
combine-compute-not-select-compute; gate-first validation.
`disler/the-verifier-agent` — verification-first shape.
`disler/claude-code-hooks-multi-agent-observability` — event-first
monitoring.

**2026 standards absorbed:** MCP under the Linux Foundation's
Agentic AI Foundation (2026-07-28 stateless-core RC; Server Cards;
SEP-2085 untrusted-by-default); AGENTS.md as the universal repo
context standard (and the 138-repo evidence that smaller is better);
harness engineering as feedforward guides + feedback sensors;
planner/generator/evaluator separation; git-as-checkpoint; skills
with progressive disclosure; the Inspect/Braintrust/Phoenix eval
stack; METR time-horizons; zero-trust agent posture (gVisor-class
sandboxing, write signatures, semantic gateways outside model
context).

**On paid courses:** this project did not pirate Tactical Agentic
Coding or Principled AI Coding. Their durable, load-bearing ideas are
public in the MIT repositories above; the videos teach the same
methodology in narrative form. Everything in this book traces to
public sources or original work.

## Appendix D — Public Resource Map (the "Fork the Forkable" Inventory)

| Resource | License | Status | What it's worth |
|---|---|---|---|
| github.com/disler (14+ repos) | MIT | public | the whole agentic-factory canon |
| `claude-code-hooks-mastery` | open | public, 3.9k★ | hooks as harness primitives |
| `pi-vs-claude-code` | MIT | public | open-vs-closed agent harness comparison |
| `nano-agent` | open | public | MCP server, multi-provider, small agents |
| `bowser` | open | public | composable browser automation skills |
| `the-library` | MIT | public | private-first distribution of agentics |
| VS Code agentic snippets gist | public | gist | SKILL.md / subagent / prompt templates |
| youtube.com/@indydevdan | free | public | 5.1M+ views of methodology |
| modelcontextprotocol.io | open spec | public | the protocol layer |
| ai-boost/awesome-harness-engineering | open | public | curated 2026 harness canon |
| Inspect AI (UK AISI) | open | public | the eval standard |

Paid and *not* used: the two agenticengineer.com courses. Listed for
completeness; their public artifacts did the work.

---


## Appendix E — The Ten Laws of the OS

1. **The harness is the product.** Models are slots; guarantees live in deterministic code.
2. **No envelope, no result.** Free text never crosses a phase boundary as truth.
3. **Claims are untrusted; evidence is checked.** "The agent says it works" is not in the vocabulary.
4. **Absence of failure is not success.** UNVERIFIED is a verdict, and it is the default.
5. **Authority is a boundary, enforced after the fact.** Tool lists organize; boundaries protect.
6. **Autonomy is earned per class, measured continuously, and revocable.** High-impact actions checkpoint forever.
7. **Fail closed.** Unknown action classes deny; unclassified context is stale-side; unvalidated memory is refused.
8. **Context is a budget.** Every drop is recorded with a reason; every unit carries provenance and expiry.
9. **Failure never becomes folklore.** Lessons are episodic until evidence makes them procedural.
10. **Promotion is a measurement.** Three repetitions before a skill; five wins before an agent; evidence precedes existence.

## Appendix F — Glossary

**Action class** — the nine-way classification of every meaningful action (READ…IRREVERSIBLE) the governor adjudicates. **Autonomy level** — L0–L7, the earned-trust ladder. **Boundary (`writes:`)** — glob patterns defining where an agent's writes may survive. **Checkpoint** — full-fidelity pre-phase snapshot; the rollback unit. **Discovery** — the measured engine proposing promotions up the ladder. **Envelope** — the typed, evidence-carrying return type every agent must produce. **Entropy** — the decay modes of a running system; the scanner hunts them. **Gate** — one mechanical truth-check on an envelope. **Governor** — the component answering ALLOW/CHECKPOINT/DENY. **Harness** — the owned, deterministic execution environment. **Ladder** — task→skill→agent→workflow→service→capability. **Wave** — a set of independent tasks executing in parallel. **Win-rate** — validated wins over validated uses; the promotion currency.

---

---

*10,000,000× AI Engineering, Volume I — The System v1.0.0. Written
from a repository that passes its own tests. The reader's move:
`python -m pytest`, then upward.*
