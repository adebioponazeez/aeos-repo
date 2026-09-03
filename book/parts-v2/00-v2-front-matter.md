# 10,000,000× AI ENGINEERING — VOLUME II

## The Platform and the Factory

### From Multi-Agent Platform to Autonomous Capability Factory — the System at v7.0.0

---

## Preface: What Changed Between the Covers

Volume I documented a system at v1.0: the kernel of an AI Engineering
OS — contracts, orchestration, context, memory, skills, governance,
evaluation, harness, observability, entropy, learning, discovery —
68 tests, one reference run, and a book's worth of honesty about what
it did not yet do. The final chapter mapped a roadmap: v1.1 hardening,
a v2 platform, a v3 capability OS, and beyond.

This volume documents that roadmap **executed**. The system is now
v7.0.0: twenty-six modules, 131 tests, provider adapters with fusion,
a durable resumable runtime, an MCP-idiom tool layer, a content-hashed
capability catalog, sponsorship tokens, an economics layer, autonomous
research and operations, a bounded meta-loop, and the capability
factory — the L7 endgame in which the system designs, validates, and
(only under spent human authority) installs new capabilities.

The discipline did not change; that is the thesis of this volume. Every
new layer arrives with the same receipt: modules you can read, tests
that attack the system on purpose, evidence bundles you can regenerate
with one command, and ADRs that admit alternatives. Version numbers
were spent on capability, never on ceremony — the changelog is a list
of things that now exist and pass tests, nothing else.

The one-sentence summary of the seven versions: **the OS learned to
survive crashes (v2), to package and govern its own capabilities (v3),
to account for its cost and leverage (v4), to do research and
operations autonomously (v5), to improve itself inside hard bounds
(v6), and finally to build new capabilities end-to-end under human
sponsorship (v7)** — without ever relaxing the four invariants, and
while adding a fifth: *no self-modification without a spent human
token.*

**How to read Volume II.** Part I covers the platform mechanics
(adapters, fusion, runtime, tools). Part II the capability OS (catalog,
tenancy, sponsorship). Part III economics. Part IV research and
operations. Part V the meta-loop. Part VI the factory. Part VII the
witnessed runs and the honest gaps that remain. Appendices carry the
new ADRs, the evidence, and the updated ten laws.

Reproduce everything:

```bash
pip install -e . && python -m pytest   # 131 proofs
aeos run-demo && aeos factory-demo && aeos dashboard
```

The human moves upward. The machines execute downward. Between the
covers of these two volumes, the space between them — the system that
learns — is now built, end to end.
