# PART IV — HARNESS ENGINEERING

## Chapter 18. Why the Harness Matters

Strip every model away and what remains is the harness: the execution
environment, the checkpoints, the boundaries, the event log. The
harness is what the humans *own* — and in 2026 it is where the elite
tier actually lives. The public evidence is unambiguous: the most
starred and most-copied agentic repositories of the era are harnesses
(deterministic factories, fusion harnesses, verifier agents,
observability layers), not models and not prompt libraries.

Three reasons the harness is the product:

**1. It is the only layer that can hold guarantees.** Models are
stochastic and rented; frameworks churn; protocols renegotiate
mid-flight. The harness is yours, deterministic, and testable — every
property this book claims lives in harness code with a test on it.

**2. It is where failures become cheap.** A hallucinated claim dies at
a gate; an unauthorized write dies at a boundary; a loop dies at
`max_attempts`; a bad graph dies at validation. Each harness mechanism
converts an expensive, late, human-discovered failure into a cheap,
early, machine-detected one. The harness is a failure-cost machine.

**3. It is what compounds.** Models improve without you; your harness's
checkpoints, skills, gates and lessons are the part of the system that
accumulates. A team that ships a harness owns its own leverage curve.

AEOS's harness layer is `harness.py` plus the governor and event log —
the subject of the next four chapters.

## Chapter 19. Repository-Native Engineering

The harness is **repository-native**: the filesystem is the working
memory. Artifacts are files; envelopes reference files; gates diff
files; checkpoints snapshot files. There is no side-database of truth
that can drift from the tree, because the tree *is* the truth.

This is the 2026 consensus shape — artifact-first working memory
offloading context, git-adjacent recovery, agents as tenants of a
workspace they can read freely and write narrowly. Consequences that
matter:

- **Recovery is boring.** Rollback is "restore these files from this
  snapshot" — no transaction log to replay against a schema.
- **Observability is greppable.** The event log is JSONL *inside* the
  workspace (`.aeos/runs/`), and evidence bundles are JSON *inside*
  the workspace (`.aeos/evidence/`). The run explains itself from its
  own corpse.
- **The fence is physical.** `.aeos/` is always writable by the
  system, never by agents' boundaries — system state lives inside the
  fence, agents outside it. An agent cannot edit the record of its own
  misbehavior (`test_aeos_state_dir_is_always_writable`).

The AGENTS.md file at the repo root completes the native posture: a
deliberately *short* routing table (build commands, architecture map,
deviating conventions, anti-patterns) — because the measured 2026
truth is that bloated context files hurt. The harness curates what
agents see about the repo with the same discipline the Context OS
applies to everything else.

## Chapter 20. Sandboxing, Permissions, and the Governor

The governor (ADR-004) is one screen of data and one function:

```
ActionClass        → (min level to ALLOW, deny-by-default?)
READ               → (L1, no)
WRITE / EXECUTE    → (L3, no)
NETWORK / DEPLOY   → (L4, no)
FINANCIAL          → (L5, checkpoint forever)
DESTRUCTIVE        → (L6, checkpoint forever)
CREDENTIAL         → (L6, checkpoint forever)
IRREVERSIBLE       → (L7, deny below human sponsorship)
unknown class      → DENY. Always. Fail closed.
```

`decide(action_class)` returns ALLOW, CHECKPOINT, or DENY — nothing
else — and logs every answer. The properties the tests pin down:

- Reads are free from L1 up (`test_read_allowed_from_l1`); writes
  checkpoint at L2 and allow at L3.
- **High-impact classes checkpoint at every occurrence even at L6**
  (`test_destructive_checkpoints_even_at_l6`) — promotion is earned
  per class and never becomes a blank check.
- **Explicit approval is one-shot** (`test_approval_is_one_shot`) —
  approving a task once cannot license its cousins.
- **Unknown is denied** (`test_unknown_class_denies`).

And the ladder is *alive*: `observe_outcome(success)` feeds a
reliability EMA that promotes and demotes the level automatically
(`test_failures_demote`, `test_sustained_success_promotes`). In the
reference run, seven clean tasks carry the governor from L3 to L5 —
autonomy earned in the log, in front of witnesses.

Full sandboxing (gVisor-class isolation, cryptographic write
signatures, the zero-trust ADK posture) is the production-hardening
item v1.0 explicitly does not claim; the *policy kernel* it plugs
into is complete and tested.

## Chapter 21. Checkpoints and Recovery

The harness's sharpest tooth is the write boundary, and its protocol
is mechanical: **checkpoint before, enforce after, revert on
violation.**

```python
def bounded(agent_name, fn):
    def wrapped(task, orch):
        cp = harness.snapshot(f"pre:{task.name}")     # full fidelity
        envelope = fn(task, orch)
        reverted = harness.enforce_boundary(cp, agent_name,
                                            patterns=roster[agent_name].writes)
        if reverted:
            raise RuntimeError(f"write-boundary violation ...")
        return envelope
    return wrapped
```

`enforce_boundary` diffs the tree against the checkpoint: files
changed or created outside the agent's `writes:` globs are reverted,
deleted boundary files are restored, violations are recorded with the
agent's name, and the phase dies.
`test_unauthorized_writes_are_reverted` shows a rogue agent's two
edits — one tamper, one new file — both undone, original content
restored. `test_authorized_writes_survive` shows the flip side:
declared work passes untouched.

Two subtleties the tests forced into the light. A *filtered* snapshot
would make pre-existing files outside the filter look new and get them
deleted — snapshots must be full-fidelity while enforcement stays
scoped (the bug was caught writing this book's pipeline, which is the
system working). And `.aeos/` must be exempted from boundary politics
or the system cannot keep its own books.

Full `rollback(cp)` restores the entire tree for destructive recovery
(`test_snapshot_captures_state`). At repository scale, git checkpoints
are the industrial form of the same idea (ADR-006); the in-workspace
form keeps v1.0 portable to scratch directories and sandboxes.

## Chapter 22. Autonomous Execution

Putting Parts III and IV together: what does it mean, mechanically,
for execution to be *autonomous* — and safe enough to leave alone?

The loop, per task: the governor classifies and decides; DENY
escalates, CHECKPOINT either resolves via recorded approval or
escalates for high-impact classes; ALLOW runs the handler inside the
harness (checkpoint → execute → enforce), the envelope meets the
gates, the verdict moves the state machine, outcomes feed the
reliability EMA, and everything — every decision, gate, violation,
duration — lands in the event log.

"Autonomous execution" is then not a mood but a *budget of trust
computed live*: the system continuously knows how reliable it is being
(watch `governor_reliability` in the evidence bundle), which classes
it has earned, and which it never will without a human. The run
finishes with an acceptance verdict that is a property of the graph —
all tasks SUCCEEDED — plus an evidence bundle that any auditor can
read without replaying anything.

The autonomy ladder's top rungs — L6 self-improving, L7 capability
discovery — are exactly where Parts VII and IX pick up: learning that
is gated by evidence, and discovery that is measured before it is
built. Autonomy without those two is just unsupervised speed; with
them, it compounds.
