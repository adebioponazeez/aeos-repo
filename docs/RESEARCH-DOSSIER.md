# Research Dossier — Public Resource Map (September 2026)

**What this is:** the legitimate intelligence brief behind the build —
every public, free, forkable resource in the target ecosystem, the
September-2026 standards picture, and the architecture principles the
elite tier is actually shipping. **What this is not:** pirated course
material.

## 1. The straight answer on the paywall

The attached screenshots point at IndyDevDan's two paid courses at
agenticengineer.com — *Tactical Agentic Coding* and *Principled AI
Coding*. Those are paid products; copying their videos/PDFs behind the
paywall is theft, and this project doesn't do it. It also doesn't need
to: **the courses teach a methodology whose substance is public** — in
his GitHub repos, his free YouTube catalog, and public gists. Everything
below was obtained legitimately and is what the OS build absorbed.

## 2. The forkable inventory (all MIT-licensed, all public)

Forked into `forks/` for this project:

| Repo | What it is | What we absorbed |
|---|---|---|
| `disler/super-simple-software-factory` | "Agents + code" factory: deterministic Python ADW scripts own sequencing; coding agents are bounded nodes; typed JSON envelopes; SQLite traces | 10 hard rules — especially: agent proposes/code disposes; gates validate claims not guesses; `writes:` boundary enforced post-hoc; every phase earns a real description; `run.finish(accepted=)` decides exit code with the banner |
| `disler/fusion-harness` | Multi-model fusion harness (architect + primary builder + secondary builders, N-way opinions, gate-first validation) | Model-agnostic seam; gate-first validation; combining compute instead of selecting compute |
| `disler/the-verifier-agent` | Verification-first agent pattern | Independent evaluator discipline |
| `disler/claude-code-hooks-multi-agent-observability` | Hook-event tracking for real-time agent monitoring | Event-log-first observability |

Also public in his catalog (not forked, noted): `claude-code-hooks-mastery`
(3.9k★), `pi-vs-claude-code`, `nano-agent` (MCP server for small
agents), `bowser` (browser automation via composable skills), `mac-mini-agent`,
`infinite-agentic-loop`, `the-library` (private-first distribution of
agentics), `big-3-super-agent`.

Free ecosystem extras: the VS Code snippets gist for agentic prompts /
SKILL.md / subagent templates (updated 2026-01), and the free YouTube
catalog (@indydevdan — 5.1M+ views, weekly agentic engineering content
since the GPT-3.5 era).

## 3. September-2026 standards the build targets

Verified against current public sources:

1. **MCP is vendor-neutral infrastructure.** Donated by Anthropic to
   the Linux Foundation's Agentic AI Foundation (Dec 2025; co-sponsored
   with OpenAI, Block). The 2026-07-28 spec RC: stateless protocol core,
   `ext-*` extension framework (Tasks, MCP Apps), 12-month deprecation
   policy. Server Cards + `.well-known` discovery; SEP-2085 makes tools
   untrusted-by-default with SBOM support. Implication: treat protocols
   as adapters, never as architecture (ADR-007).
2. **AGENTS.md is the universal repo-context standard** across Claude
   Code, Codex, Cursor, Aider, Copilot, Gemini CLI, Windsurf — and
   research (138 repos) shows *smaller is better*. This repo ships one
   deliberately short.
3. **Harness engineering is the discipline.** The 2026 framing
   (Böckeler et al.): feedforward guides + feedback sensors — the
   harness self-corrects before output reaches human eyes. Proven
   patterns: planner/generator/evaluator separation, sprint contracts,
   git-as-checkpoint, skills with progressive disclosure,
   self-instrumented agents.
4. **The eval stack consolidated:** Inspect AI (UK AISI) as the open
   standard; Braintrust for CI-gating PR diffs; Phoenix for OTel-native
   production tracing; METR time-horizons for capacity planning.
5. **Security posture:** zero-trust agents, sandboxing (gVisor-class),
   cryptographic write signatures, deterministic semantic gateways
   outside LLM context; 8,000+ unprotected MCP servers found scanning
   in Feb 2026 — the threat model is real, defense sits in the host.
6. **Protocols beyond tools:** A2A for remote agent-to-agent
   delegation; ACP for editor/client surfaces; Google's June-2026
   Agentic Resource Discovery spec for capability catalogs.

## 4. What the elite 0.0000001% actually ship (distilled)

From the above sources, the common spine across top-tier agentic
systems in 2026:

- **Determinism owns control flow; models own judgment.** Python (or
  TypeScript) owns the graph, retries, and acceptance; agents are
  bounded nodes (SSSF's entire thesis).
- **Claims are checked, never trusted.** Gates verify artifacts and
  evidence; "the agent says it works" is not a verdict anywhere
  serious.
- **Context is curated, not dumped.** Progressive disclosure, budgets,
  freshness. Bloated context measurably hurts.
- **Permissions are boundaries, not tool lists.** Enforced post-hoc by
  the harness, with checkpoints and rollback.
- **Autonomy is earned per class and revocable.** Reliability drives
  the ladder automatically.
- **Everything emits events.** Append-only traces; replayable runs;
  production failures become permanent test cases.

Every one of those six is implemented and tested in `aeos/` — that
convergence is the thesis of the book.

## 5. Sources

- agenticengineer.com public course pages (free descriptions)
- github.com/disler (all repos listed above; MIT)
- gist.github.com/disler — agentic VS Code snippets (public)
- modelcontextprotocol.io — 2025-11-25 spec; 2026-07-28 RC roadmap
- ai-boost/awesome-harness-engineering (curated 2026 harness canon)
- Innobu, Metacto, MachineLearningMastery 2026 state-of-agentic guides
- "Modern Agent Harness Blueprint 2026" (community blueprint gist)
