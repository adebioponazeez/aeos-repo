# PART III — AGENT ARCHITECTURE

## Chapter 14. Designing Specialized Agents

The spec's roster fantasy is twenty-three named agents; AEOS ships
six, because the roster rule is: **specialize only when specialization
creates measurable value.** An agent exists because its boundary,
evaluation, and failure modes differ from its neighbors' — not
because an org chart had a gap.

The v1.0 org: **executive** (intent → one testable sentence),
**researcher** (uncertainty reduction, sourced),
**architect** (objective → validated graph), **builder**
(implementation inside a write boundary), **evaluator** (independent
verification), **release** (packaging verified output only). Six
contracts, no personas, no invented titles.

What makes an agent a *contract* rather than a prompt with ambitions
is that every field is mandatory and validated. `AgentSpec.validate()`
rejects: empty success criteria ("agent cannot be evaluated"), missing
escalation conditions ("agent cannot hand back control"), and — the
one that catches real designs — a WRITE action class without a
declared `writes:` boundary. Each is a test in `test_contracts.py`.

The anti-pattern this chapter exists to kill: **agents as
organizational theater.** "Let's add a DevOps agent" is not an
architecture decision until someone states its inputs, outputs,
authority, success criteria, evaluation, escalation and termination —
and shows the measured repetition that justifies its existence. The
capability ladder (Chapter 24) is the promotion path; the org chart is
its *output*, not its input.

## Chapter 15. Agent Contracts, Authority, and Failure Modes

Three of the contract's fields do the heavy lifting, and each has a
chapter's worth of consequence packed into a list.

**Authority** is declared twice, deliberately: `action_classes` (what
kinds of action this agent may attempt at all — the governor enforces
per execution) and `writes` (which paths its writes may survive — the
harness enforces per phase). Two mechanisms, two moments, one
principle: *the agent's authority is what the system enforces for it,
not what the agent believes it has.*

**Success and evaluation criteria are separate fields** because they
are separate questions — did it achieve the mission, and can we
*check* that it did? An agent whose success criteria are uncheckable
("improve developer experience") fails validation in spirit; the
envelope/gate machinery fails it in practice, because gates check
artifacts and evidence, not sincerity.

**Escalation and termination conditions** are the agent's off-ramps.
Escalation conditions ("3 failed attempts", "no sources found",
"requirements contradict") route control back to a human through the
governor; termination conditions stop work cleanly. An agent without
off-ramps is a loop with a personality. The orchestrator gives both
teeth: ESCALATED and SKIPPED are first-class task states, and the
event log records the *why* every time.

The full failure-mode taxonomy — what if the model hallucinates, a
tool fails, context is stale, two agents disagree, an agent loops, an
agent is over-permissioned — is answered mechanically across the OS:
gates (hallucination), harness rollback (tools and permission),
freshness (context), graph serialization (disagreement over shared
state), bounded retries (loops), the governor matrix (over-permission).
Adversarial review is not a meeting in this system; it is a test file.

## Chapter 16. Agent Communication: The Envelope

Agents talk to each other through exactly one data structure:

```python
@dataclass
class Envelope:
    agent: str
    objective: str
    claims: list[str]           # untrusted assertions
    evidence: list[Evidence]    # what the harness can check
    artifacts: list[str]        # files produced
    changed_files: list[str]    # files claimed modified
    notes: str                  # free prose lives here, and only here
```

The envelope's grammar is its politics. `claims` are *untrusted by
construction* — they are what the agent believes. `evidence` is what
the system can verify. Free prose is quarantined in `notes`, where it
can inform humans and never drive machinery. Nothing downstream —
not the orchestrator's state machine, not the release gate, not the
learning loop — reads prose to make a decision. Prose does not
compile.

The type is enforced at the boundary: a handler returning anything
but an `Envelope` fails its task immediately
(`test_handler_must_return_envelope`). This one rule eliminates an
entire genre of agentic failure — the downstream phase that parsed
"sure, done!" as success — and it costs one `isinstance` check.

The envelope also carries the run's institutional memory in
miniature: evaluations attach to envelopes, learning lessons cite
envelope evidence, and the evidence bundle that closes each run is
envelopes-plus-verdicts. When Chapter 25's memory stores "what
happened," it stores envelopes, not vibes.

## Chapter 17. Multi-Agent Coordination in One Graph

Coordination problems are dependency problems with feelings. Strip the
feelings and what remains is a DAG plus a serialization rule, which is
exactly what `Orchestrator.waves` computes: a topological sort (Kahn's
algorithm) grouping independent tasks into parallel waves, with
dependencies forcing order and — the part that makes parallelism safe
— the write-collision validator (Chapter 13) guaranteeing that no two
unordered tasks can write overlapping territory.

Within a wave, tasks run in a thread pool. Agents are I/O-shaped
(model calls, subprocess tests), so threads are honest concurrency at
this scale; the design deliberately avoids async ceremony, because the
orchestrator's job is *correctness of ordering*, not throughput
heroics. Every wave emits `wave.start` with its task list; every task
emits started/succeeded/failed/escalated/skipped with reasons; the run
closes with `run.finished` carrying the acceptance verdict.

Failure propagates like an adult: an upstream FAILED task marks its
dependents SKIPPED (`test_upstream_failure_skips_dependents`) rather
than letting them run on fiction; a repair cycle gets exactly one
bounded chance to revive failed tasks that have attempts left
(`test_repair_cycle_revives_failed_task`); and a run is *accepted*
only if every task reached SUCCEEDED —
`RunReport.accepted` is a property of the whole graph, not a
vibe of the strongest phase.

The 2026 pattern this mirrors — orchestrator-worker subagents as the
default multi-agent shape, chosen for context isolation and parallel
payoff at manageable complexity — is not followed here because it is
fashionable. It is followed because the graph validator can *prove*
properties about it.
