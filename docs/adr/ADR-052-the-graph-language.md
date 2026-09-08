# ADR-052: The Graph Language — declarative workflows, routing that never declassifies

**Status: ACCEPTED (v39.6.0)**

## Context

The dark-factory validation's roadmap gap #3: AEOS plans were
programmatic (Python-constructed TaskSpec lists) while the field's
best ergonomics are declarative — Fabro's version-controlled DOT
workflow graphs and CSS-like routing stylesheets. Declarative
graphs are diffable in review, reusable across teams, and
generatable by agents themselves. But declarativeness is also a
risk: a config language that can quietly change safety properties
is a privilege-escalation surface.

## Decision

1. **A named DOT subset** (`graphlang.py`): digraph, node
   statements with attributes (label, agent, class,
   max_attempts, model), `->` edge chains, `subgraph cluster_*`,
   both comment styles, quoted strings with escapes. Not full DOT
   (no ports, records, HTML labels) — out-of-subset input is a
   plain-language GraphError with a line number, never a
   SyntaxError traceback. Bare-edge endpoints must be declared;
   the compiler does not invent phantom nodes.
2. **Clusters are nested harnesses.** `subgraph cluster_x`
   compiles to one parent TaskSpec whose `subplan` is the
   cluster's nodes (ADR-051 recursion, now declarative).
   Cross-level edges attach through the parent; intra-cluster
   edges stay inside; edges between two members of the same
   cluster declared at the parent level are placed inside.
   Nesting deeper than MAX_SUBPLAN_DEPTH is a named compile error.
3. **Routing stylesheets**: INI sections matched by fnmatch on
   task names; a nested-harness parent also matches its cluster
   name; PER-KEY FALLBACK (each key takes the first matching
   section that defines it; `[*]` is the fallback). Keys: model,
   agent, max_attempts.
4. **THE SAFETY LAW — stylesheets route, they never declassify.**
   `class=` on a stylesheet section or on an edge is a NAMED
   compile refusal. Classification lives on the node where the
   agent acts; a routing layer that could move classes could hide
   danger. This law is compile-enforced and regression-tested.
5. **Zero new trust.** The compiled graph is the same TaskSpec
   the orchestrator already runs: the governor classifies every
   task, hooks fire at every point, gates grade every envelope.
   A declarative graph buys ergonomics, not immunity.

## Honest scope

- The subset is deliberately small; full DOT compatibility is not
  a goal (Graphviz renders our files for free, we do not render
  theirs).
- Per-node model routing lands as a hint (`TaskSpec.model`);
  production adapter selection happens at handler-build time. The
  demo roster honors it end-to-end; the reference pipeline's
  single-model default is unchanged.
- `--run` executes with a demo roster of deterministic engines —
  the language is production-ready, the demo engines are demos.

## Consequences

- Workflows are now reviewable artifacts (`examples/` ships one).
- Agents can WRITE graphs (the compiler names every error), which
  makes the graph language the natural output surface for future
  planner agents — and the governor still classifies whatever
  they write.
- DARK-FACTORY-VALIDATION pattern #9 (declarative graphs) and
  pattern #9's routing half close; roadmap gap #3 closes.
