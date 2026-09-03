# PART VI — ENTROPY, AUTONOMY, AND THE CAPABILITY OS

## Chapter 27. Entropy Control: The Eleventh Entropy

Every system that runs long enough begins to lie — stale docs
describing deleted code, duplicate skills drifting apart, canonical
"facts" nobody would re-derive, dead modules, unused tools, security
regressions sliding in as "fixes." The founding spec lists eleven
entropies; AEOS ships a scanner for the four that rot fastest, with
the vocabulary to act: **IGNORE / MONITOR / REPAIR / REMOVE /
ESCALATE** — prefer continuous small corrections over quarterly
archaeology.

The v1.0 scan and its dispositions:

- **Stale documentation** — markdown older than the newest code by
  more than a day → REPAIR. (In this repo, that finding fires on this
  book's own drafts during active development, which is the scanner
  being *right*, not annoying.)
- **Duplicate skills** — purpose similarity ≥0.6 (Jaccard over
  meaningful words) → MONITOR, cheap false positives by design; a miss
  would be the expensive error.
- **Memory pollution** — canonical records under 0.5 confidence →
  REPAIR: revalidate or demote to episodic.
- **Dead code** — empty shell modules → REMOVE.

Entropy control pairs with learning the way a gardener pairs with a
planter: the learning loop adds capability; the scanner prunes what
capability left behind. A system that only accumulates is a landfill
with a roadmap. The scanner runs at the close of every reference run,
and its findings ship in the evidence bundle next to the promotion
proposals — growth and decay, side by side, in the same report.

## Chapter 28. The Autonomy Governor in Operation

Part IV specified the governor's matrix; this chapter watches it
*live*, because the difference between a policy and a mechanism is
what happens when nobody is watching.

The reference run starts the governor at L3 (checkpointed autonomy)
with reliability 1.0 inherited from validation. Seven tasks execute.
Each outcome feeds `observe_outcome`, the EMA holds at 1.0, and the
governor promotes itself: L3 → L4 (guarded) → L5 (continuous) — every
transition an event (`governor.level`), every promotion carrying its
reason string. The run's evidence bundle closes with
`"governor_level": "L5_CONTINUOUS_AUTONOMY"` and
`"governor_reliability": 1.0` — numbers with a log behind them.

Now the same system on a bad day: failures feed the EMA losses; at
0.95 the level drops to L3; at 0.90, to L2 — writes start
checkpointing again automatically (`test_failures_demote`). Nobody
files a ticket; the fleet loses its own privileges the way ships
shorten sail. Recovery is equally mechanical: sustained success
promotes again, and the *log* is the argument.

What the governor refuses to do is the chapter's real content. It
refuses blanket trust: FINANCIAL, DESTRUCTIVE, CREDENTIAL actions
checkpoint at L6, on every occurrence, forever — "high-impact class
checkpoints every time." It refuses the unknown: an unclassified
action denies. It refuses permanence: approvals are one-shot. The
ladder's top rungs (L6 self-improving, L7 capability discovery) are
reached by exactly the machinery of the previous chapter — validated
learning and measured discovery — so the governor, the learner, and
the discoverer form one triangle of earned escalation, not three
features that happen to coexist.

## Chapter 29. From Coding Agent to Capability Factory

The founding spec's grand arc — TASK → SKILL → AGENT → WORKFLOW →
SERVICE → AUTONOMOUS CAPABILITY → SELF-IMPROVING SYSTEM → CAPABILITY
FACTORY — is usually drawn as a ladder diagram in a slide deck. In
AEOS it is a finite state machine with measured transitions, and this
chapter walks one object up the ladder to show the rungs are real.

A task: *run the tests.* It repeats. At the third repetition,
discovery proposes TASK→SKILL ("codify the procedure"). The skill —
purpose, trigger, procedure, success evidence — is registered,
versioned, and now counts usage and wins. At five uses and 80%
validated wins, discovery proposes SKILL→AGENT: the capability has
earned a resident specialist with its own contract, boundary, and
evaluation. Agents with stable interdependencies become a WORKFLOW —
a graph like the reference pipeline, itself a first-class object.
Workflows invoked by other systems become SERVICES. Services that
earn reliability become AUTONOMOUS CAPABILITIES — governed, observed,
self-repairing. And the loop that promotes validated lessons into
skills and skills into agents is the SELF-IMPROVING SYSTEM; the
discovery engine watching it all is the CAPABILITY FACTORY.

The discipline that keeps the ladder honest is the same at every
rung: **evidence precedes existence.** Three repetitions before a
skill; five wins before an agent; a validated graph before a
workflow; earned reliability before autonomy. The factory can only
build what its measurements can defend — which is why a capability
factory built this way gets *safer* as it gets bigger, the inverse of
every org chart you have ever worked in.

## Chapter 30. The AI-Native Engineering Organization

Zoom out from the repo: the same architecture is an org design, and
the mapping is one-to-one.

The **contracts layer** is your operating agreements — every role
(biological or otherwise) with mission, inputs, outputs, authority,
success criteria, escalation. The **Context OS** is your knowledge
management: curated, fresh, provenance-tagged, budgeted — the end of
the four-hundred-page wiki nobody reads. The **governor** is your
delegation policy: explicit classes of decision, earned autonomy,
irreversible actions reserved to humans — not by policy memo but by
mechanism. The **evaluation OS** is your quality function, structurally
independent from delivery. **Memory** is your institutional knowledge,
where canonical status is earned by evidence. **Entropy control** is
your spring cleaning, continuous and small. **Discovery** is your
strategy function, proposing what to build next from measured
repetition rather than executive weather.

The human layer ascends the same ladder the capabilities do — coder
→ supervisor → workflow designer → architect → capability designer →
strategic human — and the ascent is *literal*: each rung is the human
spending attention one level higher while the layers below execute
verified work. The economic shape is the founding spec's single
sentence: **optimize OUTCOME VALUE / HUMAN ATTENTION.**

What this org refuses is also the design: no accountability-free
automation (high-impact classes checkpoint forever), no folklore
memory (evidence-gated canonical writes), no self-grading (independent
evaluators), no growth without pruning (entropy), no promotions
without numbers (discovery). It is a boring company, in the way
bridges are boring. Bridges are the compliment.
