# PART II — THE FOUNDATIONS

## Chapter 7. Models as Components

The first architectural decision in the repository is a refusal:
**the OS will not know which model it is talking to.** All of
`aeos/models.py` exists to make that refusal enforceable.

The seam is one protocol:

```python
class ModelAdapter(Protocol):
    def complete(self, call: ModelCall) -> ModelReply: ...
```

`ModelCall` carries everything any provider needs (system, prompt,
agent identity, context accounting) and nothing provider-specific.
`ModelReply` returns text plus usage facts. A `Router` chooses models
by *capability rule* — reasoning difficulty, context needs, cost —
and logs every routing decision with its reason, because model choice
should be as auditable as any other action.

The default adapter is `EchoModel`: deterministic, in-process, free.
It can be bound per-agent to any behavior, and it can *defect* on
command — `fail_on_next("raise")` or `"junk"` — because the harness
must survive models that fail, lie, or produce nonsense. A test double
that only ever behaves is a test double that tests nothing.

This is where "the harness is the product" stops being a slogan. The
entire 68-test suite runs against EchoModel. If a guarantee — gates
revert violations, governors deny unknown classes, orchestrators
reject cyclic graphs — holds against a deterministic engine, it holds
by *code*. Nothing about it depends on the goodwill or genius of a
frontier model. When a real adapter is plugged in, it inherits every
guarantee unchanged; that is ADR-001, and it is why model churn —
which consumed the industry twice a year since 2023 — is a
configuration event here, not an architectural one.

The strategic corollary: **combine compute, don't select compute.**
The fusion-harness lineage (Chapter 28's bibliography) runs one
architect and several builders from different providers through the
same seam, fusing opinions before a gate. AEOS's seam makes that an
adapter policy, not a rewrite.

## Chapter 8. Context Engineering

Context engineering replaces a superstition — "more context is
better" — with an engineering discipline: context is a **budgeted,
expiring, classified resource** with provenance and conflict
detection.

Every `ContextUnit` carries: a `key`, a `body`, a `tier`
(ESSENTIAL / USEFUL / OPTIONAL / IRRELEVANT / STALE / CONFLICTING /
UNKNOWN), an `authority` (who vouches for it), a `created_at`, an
optional `expires_at`, and `conflict_keys` (which other units it may
contradict). Assembly (`ContextOS.assemble`) is then a deterministic
algorithm with six laws, each of which is a test:

1. **Freshness is checked, not assumed.** Expired units are retiered
   to STALE and dropped *loudly* — the drop list records
   `("old", "expired")`. (`test_expired_units_become_stale_and_drop`)
2. **Irrelevance never enters.** IRRELEVANT units are dropped before
   ranking. (`test_irrelevant_never_enters_prompt`)
3. **The budget drops the lowest tier first — and says so.** Every
   dropped unit is recorded with a reason. Silence is the enemy.
   (`test_drops_are_recorded_not_silent`,
   `test_budget_is_enforced`)
4. **An ESSENTIAL unit that cannot fit is a hard flag**, not a
   silent truncation: "compress or raise budget."
   (`test_essential_over_budget_is_flagged_loudly`)
5. **Conflicts are surfaced, not averaged.** Two units from different
   authorities disagreeing on the same decision appear in
   `result.conflicts` for a human or a referee agent.
   (`test_conflicts_are_surfaced`)
6. **Disclosure is progressive.** `progressive_disclosure()` returns
   an index — first line per unit — and bodies are pulled on demand.
   This is how repository knowledge (AGENTS.md-class files) should
   enter context: as a table of contents the agent can pull from,
   never a dump. (`test_metadata_first_not_full_dump`)

The 2026 evidence behind these laws is worth restating: a study of
138 real repositories found auto-generated context files *reduced*
agent success while raising inference cost over 20%. Context is not a
gift to the model; it is a load on it. The Context OS is the load's
manager.

## Chapter 9. Prompt Engineering, Reconsidered

Prompt engineering does not disappear in an agentic OS. It gets an
engineering envelope around it.

In AEOS, a prompt is an *output artifact* of the Context OS: assembled
from classified units under budget, stamped with tier and authority
inside the prompt text itself (`[key | TIER | authority]\nbody`), and
logged in the assembly history. Three consequences follow.

First, **prompts become explainable post-hoc.** When a run misbehaves,
"what did the model see and why" is answerable from the assembly log —
which units entered, which were dropped and why, which conflicts were
flagged. Debugging agent behavior becomes debugging an input pipeline,
not psychoanalyzing a model.

Second, **prompt patterns become skills.** The agentic-prompt
structure the public canon converged on — purpose, variables,
codebase structure, instructions, workflow, report — is exactly the
shape of a `SkillSpec` (Chapter 11): purpose, trigger, procedure,
constraints, failure modes, evidence. A prompt that works twice is a
candidate skill; a prompt that works five times with evidence is a
procedure the org owns, versioned and win-rate-tracked.

Third, **prompts lose their authority.** No prompt in the system, no
matter how clever, can unlock an action class, widen a write boundary,
or pass a gate. Prompts influence models; policy belongs to the
governor; truth belongs to the gates. The most important prompt
engineering in 2026 is knowing which of your problems are not prompt
problems at all.

## Chapter 10. Tools and Tool Design

Tools are the agent's hands, and hand design determines what the agent
can safely touch. The 2026 canon — MCP under the Linux Foundation's
Agentic AI Foundation, with its 2026-07 stateless-core candidate,
Server Cards discovery, and SEP-2085's untrusted-by-default tool
validation — is one long lesson in this chapter's three rules.

**Rule 1: narrow, namespaced, typed.** Small stable action spaces
beat large vague ones: tool *selection* quality degrades as the tool
surface grows, and every tool is an injection surface. AEOS's
in-process tools are exactly this — the harness exposes `write`,
`read`, `exists`, `snapshot`, `enforce_boundary`; each does one
thing and returns typed facts.

**Rule 2: a capability list is not a boundary.** Because a shell tool
can do anything, listing tools an agent may *call* can never make
"this agent changes nothing" true. Authority lives in `writes:` globs
enforced *after the fact* by the harness (Chapter 21). Tool lists
organize; boundaries protect.

**Rule 3: protocols are adapters, not architecture.** MCP servers,
A2A remote agents, ACP editor surfaces — all of it lands at the
handler seam (ADR-007). The OS's contracts (envelope, action class,
write boundary) stay protocol-free so the protocol churn of 2025–2027
— which is real and ongoing — never reaches the trust boundary.
v1.0 ships the seam and not the adapters, and says so; a seam you
honestly lack is a gap you can close, an architecture welded to a
mid-flight spec is a liability you can only endure.

## Chapter 11. Skills Engineering

A skill is a **reusable, versioned, evidence-carrying capability** —
the unit of organizational leverage between "a task that happened
once" and "an agent that exists."

```python
@dataclass
class SkillSpec:
    name: str
    purpose: str
    trigger: str
    procedure: list[str]
    version: str = "0.1.0"
    dependencies: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    success_evidence: list[str] = field(default_factory=list)
    origin: str = "hand-written"     # or "promoted:<task uid>"
    usage_count: int = 0
    win_rate: float = 0.0
```

Three disciplines make the registry more than a folder of prompts.

**Versioning that refuses regressions.** Registering a skill at a
version ≤ the existing one, from a different origin, raises — the
downgrade path does not exist silently (`test_version_regression_rejected`).
Skills are organizational law; law does not regress quietly.

**Measured economics.** `record_use()` maintains validated win-rate;
`promotion_candidate()` will only say "promote to a dedicated agent"
at ≥5 uses and ≥0.8 win-rate (`test_promotion_needs_five_uses`,
`test_win_rate_tracking_and_promotion`). Opinions about what deserves
an agent are welcome after the numbers are in.

**Entropy-awareness.** Near-duplicate skills are detected by purpose
similarity (`test_duplicate_detection`) and surfaced by the entropy
scanner as MONITOR findings. Skill libraries rot by accretion; the
registry watches its own weight.

Where do skills come from? Hand-written, or **promoted by the
learning loop** from validated success (Chapter 23) — never from
failure, and never without evidence. The `origin` field records
provenance so that every skill in the library can answer "why do you
exist?"

## Chapter 12. Memory Engineering

Memory is where most agent projects drown: they store everything,
retrieve the wrong things, and poison their own future runs. The
Memory OS takes the opposite vow — *store only what improves future
outcomes* — and enforces it structurally.

Six memory classes, with different rules:

| Class | Scope | Write rule | Example |
|---|---|---|---|
| WORKING | this run | free | assembled context |
| TASK | one objective | free | task graph, envelopes |
| EPISODIC | what happened | free | "deploy failed: wrong env" |
| SEMANTIC | distilled facts | **evidence required** | "MCP sessions fight load balancers" |
| PROCEDURAL | how we work | **evidence required** | promoted skills |
| ORGANIZATIONAL | decisions | **evidence required** | ADR-equivalents |

The load-bearing line is in `MemoryStore.write`:

```python
if (canonical_requires_evidence and record.mclass in self.CANONICAL
        and not record.evidence):
    raise ValueError("refusing canonical write ... Unvalidated "
                     "knowledge may not become organizational memory.")
```

`test_canonical_write_requires_evidence` proves the refusal; the
learning-loop tests prove the flip side — failure is *always*
recorded episodically (`test_failure_never_becomes_canonical`), so
lessons are searchable without ever being canonicalized.

Every record carries provenance (`source`), `confidence`, and
freshness (`expires_at`), and reads are freshness-filtered by default
(`test_freshness_filter_and_expiry`): memory that expires, does.
Persistence is JSONL under `.aeos/` — the OS's own state lives inside
the fence, where agents cannot edit their own history
(`test_aeos_state_dir_is_always_writable`).

## Chapter 13. Specification-First Engineering

The pipeline's first writing artifact is not code — it is a **graph**.
The architect agent emits `spec/graph.json` describing the work as
tasks, agents, and dependencies; the orchestrator *validates* it
before anything runs; only then do builders touch files.

This ordering is the discipline the whole 2026 harness canon converged
on ("sprint contracts" negotiated before work; acceptance criteria
written before code), and it is cheap because the validator does the
policing. `Orchestrator.validate_graph` rejects, before execution:

- tasks referencing unknown agents;
- dependency cycles (DFS tri-color detection);
- **unordered parallel writers with overlapping write boundaries** —
  the silent state-corruption bug of every naive multi-agent setup.

All three are tests. The last one deserves its sentence: two WRITE
tasks whose agents' `writes:` globs overlap *must* be explicitly
ordered, or the graph is invalid — so "we'll parallelize and hope"
is not a graph the system will run. Hope is not a scheduler.

The specification-first loop also repairs correctly. When a phase
fails, the runbook's failure playbook asks *which layer is missing* —
specification, model, context, skill, permission, evaluation,
orchestration, architecture — instead of blindly retrying. Bounded
repair (one cycle, `max_attempts` per task) exists, but the system's
posture toward repeated failure is diagnosis, not persistence:
repeated failure is information that the spec was wrong.
