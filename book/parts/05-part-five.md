# PART V — EVALUATION, MEMORY, AND LEARNING

## Chapter 23. Evaluation Engineering: Creation Never Grades Itself

The evaluation OS exists because of one sentence in the founding spec:
*"Never accept 'the agent says it works' as evidence. Require
observable evidence."* Everything in `evaluation.py` is that sentence
compiled.

The **closed verdict vocabulary** — PASS, FAIL, PARTIAL, UNVERIFIED —
is enforced by an enum, and its semantics are strict: a report with no
checks stays UNVERIFIED, because *absence of failure is not success*
(`test_empty_verdict_stays_unverified`); any FAIL check fails the
report; PARTIAL and UNVERIFIED rank below PASS. The vocabulary cannot
express "seems fine."

The **stock gates** are mechanical truth:

- `artifacts_exist` / `artifacts_non_empty` — declared files exist and
  have content;
- `json_artifacts_parse` — declared data actually parses;
- `changed_files_exist` — claimed edits are on disk;
- `claims_are_backed` — **the anti-hallucination gate**: claims with
  zero PASS evidence fail the envelope
  (`test_claims_without_evidence_fail_the_gate`).

A broken gate counts as a failed gate, never a crash — evaluators
degrade loudly, not silently.

The structural rule with teeth: **creation and evaluation are
separated by role.** The evaluator is a different agent with different
tools, forbidden by contract from building what it grades; in the
reference pipeline it independently re-runs the test suite as a
subprocess — it does not ask the builder how tests went. When its
checks do not all pass, it *raises* rather than emit a polite FAIL,
and release is unreachable because the graph skips on failure.

This mirrors the 2026 canon — planner/generator/evaluator separation
to kill self-grading bias, production failures converted into
permanent test cases, CI-gated eval diffs on every PR — at the scale
of a single repository, which is the only scale where you can read
every line of the evaluator and *know*.

## Chapter 24. Adversarial Evaluation and Security Testing

The spec's adversarial-review questionnaire — *what if the model
hallucinates? a tool fails? context is stale? two agents disagree? an
agent loops? the system is attacked?* — is answered in this repo the
only way answers count: as tests that attack the system on purpose.

**The model defects.** `EchoModel.fail_on_next("raise")` simulates
outage; `"junk"` returns confident nonsense. The orchestrator's
exception path fails the task, records it, feeds the governor's EMA a
loss, and repair stays bounded — the system's answer to a lying model
is a failed gate, not a negotiation.

**The agent oversteps.** The boundary tests tamper and create rogue
files on purpose and watch them revert. The governor tests push every
action class through every level and demand the matrix hold —
including the one nobody advertises: unknown classes deny.

**The graph attacks itself.** The validator is fed cyclic graphs,
phantom agents, and racing writers — and rejects each by name
(`test_cycle_is_rejected`, `test_parallel_writers_to_same_boundary_rejected`).

**The memory rots.** Canonical records below confidence 0.5 surface as
entropy findings (`test_memory_pollution_detected`); expired records
are filtered from reads and reaped (`test_freshness_filter_and_expiry`).

What v1.0 does not yet do — red-team prompt injection through tool
results at the protocol boundary, sandbox escapes, multi-tenant
isolation — is catalogued in ADR-008 and the final chapter, because a
threat model that hides its gaps is a threat model that will be
attacked through them.

## Chapter 25. Organizational and Agent Memory, Unified

Part II introduced the six memory classes; this chapter is about the
*loop* between them and the org. The founding spec's knowledge
architecture — every important fact carrying source, timestamp,
authority, status, confidence, applicability, relationships, update
mechanism — collapses into what `MemoryRecord` actually persists,
plus one rule with a referee: canonical classes demand evidence.

In practice the unified store gives the OS its institutional memory
across runs:

- **EPISODIC** rows are the audit trail of what happened (the learning
  loop writes one per observed task outcome);
- **PROCEDURAL** rows are the org's proven methods, each with its
  evidence attached and its `proven::<task>` key naming its origin;
- **ORGANIZATIONAL** rows are decisions — the machine-readable ADR
  layer;
- **SEMANTIC** rows are distilled facts with confidence that must
  survive the entropy scanner's 0.5 floor.

The forbidden operation is the interesting design: you *cannot* write
"we always do X" without attaching the evidence that X ever worked.
Organizational folklore — the "we've always done it this way" of
corporate legend — is mechanically impossible to persist. What remains
is a knowledge base where every canonical sentence can answer two
questions instantly: *who vouched for you, and what did you prove?*

## Chapter 26. Learning Loops and Capability Discovery

The learning OS is the book's thesis in miniature: **ACT → OBSERVE →
EXTRACT → VALIDATE → UPDATE → REUSE**, with the gate exactly where
folklore usually sneaks in.

```python
def validate_and_promote(self, lesson, evidence):
    if lesson.outcome != "success" or not evidence:
        lesson.validated = False
        return False
    ...
```

Failures are recorded episodically — always, cheaply, searchably —
and are *never* promoted; `promote_to_skill` on an unvalidated lesson
raises with the sentence this chapter could be named after: *"cannot
promote unvalidated lesson — that is how failure becomes folklore"*
(`test_failure_never_becomes_canonical`). Successes without evidence
are likewise refused (`test_success_without_evidence_not_promoted`).
Success *with* evidence becomes PROCEDURAL memory and, when a name
fits, a `SkillSpec` whose `origin` field cites the exact task that
earned it (`test_validated_success_promotes_to_skill`).

**Capability discovery** then watches the work itself. Signatures
(`phase:agent:class`) accumulate; three repetitions earn a
task→skill proposal (`test_three_repetitions_trigger_a_proposal`); a
skill at ≥5 uses and ≥0.8 win-rate earns a skill→agent proposal
(`test_proven_skill_proposes_agent_promotion`). Two repetitions earn
silence (`test_two_repetitions_do_not`) — discovery that proposed
everything would be noise wearing a dashboard.

The proposals, and the entropy findings (Part VII's next chapter
completes the pair), are exactly what a human executive should review:
the system's own measured argument for what it should become next.
That is L7 — capability discovery as a *proposal engine*, with
promotion still a decision that spends human authority deliberately.
