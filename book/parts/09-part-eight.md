# PART VII — THE PATTERNS VAULT

*The public patterns the elite tier actually ships, annotated against
this repository's implementation. Each pattern: the source, the idea,
what AEOS kept, what it changed, and why.*

## Chapter 31. "Agent Proposes, Code Disposes"

**Source:** `super-simple-software-factory` (MIT) — the load-bearing
sentence of the whole factory pattern: *deterministic Python owns
sequencing, retries, and acceptance; coding agents work inside
bounded phases; typed JSON envelopes carry context between them.*

**The idea:** invert the usual agent-framework arrangement. In most
stacks, the model is the program counter — it decides what happens
next, and the framework exists to serve it. In the factory pattern,
*Python is the program counter* and the model is a sensorimotor
peripheral: the graph, the retries, the acceptance rules, and the
exit codes are ordinary deterministic code that a human can read,
test, and blame.

**What AEOS kept:** everything. The orchestrator is pure Python
control flow; handlers are bounded nodes; envelopes are typed; the
run's acceptance is a property of the graph, computed, not narrated.
The reference run's `run.finished accepted=True` event *is* SSSF's
`run.finish(accepted=)` rule, generalized to graphs.

**What AEOS changed:** the factory's phases were linear chains
(plan→build→test→review→document); AEOS's are dependency-ordered
waves with a validator that rejects unordered overlapping writers —
parallelism, but only the provably safe kind. And where the factory
polled SQLite for observation, AEOS writes append-only JSONL that any
tailer can watch.

**Why it matters:** every guarantee in this book is only possible
because control flow is deterministic. You cannot gate what you cannot
predict; you cannot repair what you cannot replay; you cannot trust
what you cannot read.

## Chapter 32. Evidence Gates: "Claims, Not Guesses"

**Source:** SSSF's gate discipline — `gate(envelope, run) ->
violations`; failures return to the same session as corrections;
every check recorded either way, "so a green gate says WHAT it
verified instead of only that it passed."

**The idea:** verification is not a verdict, it is a *record*. A gate
that only says PASS has told you nothing; a gate that says
"3 artifacts exist, parse, and are non-empty; 2 claimed files on
disk; 0 unbacked claims" has produced audit-grade evidence.

**What AEOS kept:** the recorded-check shape verbatim —
`CheckResult(name, verdict, detail)` — and the same-session repair
posture: a failed gate fails the task, the bounded repair cycle
re-presents it, and the correction path is the same handler with the
same graph context, never a restart-from-scratch.

**What AEOS added:** the anti-hallucination gate
(`claims_are_backed`) — SSSF checked artifacts against claims; AEOS
also checks *evidence against claims*, closing the loophole where an
agent truthfully lists artifacts and untruthfully narrates outcomes.
Plus the closed verdict vocabulary with UNVERIFIED as a first-class
citizen: no checks, no credit.

**The transferable rule:** whenever you build a gate, make it emit
*what it looked at*, not just what it concluded. The log line is the
product; the boolean is a summary.

## Chapter 33. Fusion: Combine Compute, Don't Select Compute

**Source:** `fusion-harness` (MIT) — one architect, one primary
builder, up to three secondary builders, N-way opinions, debate, and
gate-first validation; the thesis that racing models against each
other ("A vs B") wastes the loser, while *fusing* them keeps every
opinion and adjudicates before the merge.

**The idea:** model choice is not a vendor decision but a *portfolio*
decision. Different models fail differently; a gate can adjudicate
disagreement cheaper than a procurement cycle can find a single model
that never fails.

**How AEOS's seam makes this an adapter policy, not a rewrite:** the
`ModelAdapter` protocol plus the `Router` mean a fusion policy is one
adapter that fans a `ModelCall` to N providers and returns the reply
the gates accept — or an envelope *marked* with disagreement for the
evaluator to treat as PARTIAL. Nothing in the graph, governor, gates,
or log changes. ADR-001's real payoff is precisely this: fusion
arrives as configuration.

**Why v1.0 ships without it, honestly:** fusion multiplies cost and
latency per phase and pays off on high-stakes phases (architecture,
security review), not on every call. It is a v2.0 adapter with a
policy knob — the seam is ready; the judgment about *where* to spend
it belongs to the run's economics, which Chapter 30's OUTCOME VALUE /
HUMAN ATTENTION metric governs.

## Chapter 34. The Verifier Agent and Structural Independence

**Source:** `the-verifier-agent` (MIT) — verification as a
first-class agent whose only job is to check the work of builder
agents, with its own tools, its own prompts, and no stake in the
outcome.

**The idea:** self-grading is the original sin of agentic systems.
The fix is not a better rubric — it is *structural separation*: the
verifier is a different process identity, reading the artifacts cold,
re-deriving the checks from the specification rather than from the
builder's narrative.

**AEOS's encoding:** the evaluator agent contract forbids building
what it grades; it re-runs the test suite itself as a subprocess
(it does not read the builder's test report); its verdict comes from
the closed vocabulary; and its failure mode is *raising*, not
negotiating — `RuntimeError("evaluator refuses to pass unverified
work")` when checks disagree. In the graph, release is unreachable
unless the evaluator's artifact says PASS, because release depends on
`evaluate` and the graph skips dependents of failures.

**The 2026 context:** the eval stack that consolidated this year —
Inspect AI as the open standard, CI-gating eval diffs on PRs,
production failures promoted into permanent test cases — is this
pattern at industry scale. The principle scales down to one repo and
one file: *the thing that checks must not be the thing that builds,
and it must show its work.*

## Chapter 35. Context Craft: AGENTS.md, Progressive Disclosure, and the File That Reads You

**Sources:** the AGENTS.md convergence of 2026 (Claude Code, Codex,
Cursor, Aider, Copilot, Gemini CLI, Windsurf); the 138-repository
study finding auto-generated context files *reduce* success; SSSF's
lazy-load routing table; the awesome-harness-engineering canon's
"skills with progressive disclosure."

**The synthesis AEOS ships:** three practices, one discipline.

**1. Short routing-table context files.** This repo's `AGENTS.md` is
~40 lines: build commands, architecture map, *deviating* conventions,
anti-patterns. Not a manual. The study's lesson inverted: the best
context file is the one an agent can finish reading and still have
attention left.

**2. Progressive disclosure everywhere.** `progressive_disclosure()`
returns an index; bodies load on demand. Skills in the public canon
work identically — frontmatter description in, procedure body only on
trigger. The unit of context engineering is the *table of contents*,
not the dump.

**3. Classification before retrieval.** Tier, authority, freshness,
conflict-keys — because retrieval without classification is a fire
hose with a search box. The assembly log then answers the only
question that matters post-incident: *why did the model see that?*

**The transferable rule:** treat every byte of context as a cost
center with a measured failure mode (rot, bloat, staleness,
conflict), and give every byte a paper trail. Context is a liability
you curate until it becomes an asset.
