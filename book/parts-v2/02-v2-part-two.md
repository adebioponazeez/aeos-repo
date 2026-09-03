# PART II — THE CAPABILITY OS

## Chapter 5. The Catalog: Capabilities with Content Hashes

v3 turns skills and agents into **distributable units**: a
`CapabilityUnit` wraps a SkillSpec or AgentSpec payload with a name,
kind, version, and a SHA-256 over the canonical serialization. The
catalog's rules read like a tiny package registry because that is what
it is — for organizational capability:

- A unit that fails its own hash cannot even be **published**
  (`test_self_inconsistent_unit_refuses_publish`).
- **Install verifies the hash on disk** — a tampered artifact is
  refused, loudly, before anything touches a roster
  (`test_tampered_unit_refuse_install` — the test tampers with the
  published *file*, because tampering with memory was never the threat
  model).
- The roundtrip — package → publish → install → verify — is one test,
  because a distribution mechanism that only works in halves is a
  liability with a UI.

This is the-library pattern from the public canon (private-first
distribution of agentics), implemented at the scale where every line
is auditable. The strategic property: **capabilities acquire
provenance**. An agent installed from the catalog can always answer
*who packaged you, from what payload, verifiable against what hash* —
the difference between a capability and a rumor.

## Chapter 6. Sponsorship: Human Authority, Spent Atomically

The hardest design question in an autonomous system is not "what may
the machine do on its own" — the governor answers that. It is "what
may the machine do *to itself*, and in whose name." v3's answer is the
sponsorship token, and its four properties are the whole design:

**Scoped.** A token names its target — `factory:install:builder-
specialist` — and a scope mismatch is refused
(`test_scope_mismatch_refused`).

**One-shot.** Spending is atomic; replaying a spent token is refused
(`test_spend_is_one_shot`). Approving one install does not license its
cousins — the v7 demo *shows* this: a token scoped for one candidate
installs it and the second candidate is refused, in the same run.

**Expiring.** Default one hour; expired tokens are refused
(`test_expiry_refused`).

**Audited.** Every issue, spend, and refusal lands in an audit trail
with an outcome — "who authorized this capability?" is a query, not an
investigation.

The tokens exist because the alternatives fail at human scale:
approval fatigue turns per-action confirmations into rubber stamps,
and standing admin rights are blank checks. A sponsorship is authority
in exactly the amount a change requires — strong enough to matter,
small enough to spend deliberately (ADR-013).

## Chapter 7. Multi-Tenant Governance: One Matrix, Many Leases

A single OS serving several teams cannot serve them one security
posture — the fintech tenant and the research tenant disagree about
DEPLOY the way their regulators disagree about money. v3 gives the
governor per-tenant policy overlays: `set_tenant_policy("acme",
DEPLOY, (L7, False))` makes deploys L7-and-sponsored for acme while
the global matrix is untouched.

The two tests are the contract. `test_tenant_override_applies`: at
global L5 a DEPLOY allows; under tenant "acme" (L7 required) the same
action denies — the overlay binds. `test_tenant_matrix_untouched_
globally`: the overlay never leaks; a "strict" tenant demanding L7 for
writes changes nothing for everyone else — global behavior is
byte-identical before and after the overlay exists.

What overlays cannot do matters as much: no tenant can weaken the
immutable rows. FINANCIAL, DESTRUCTIVE, CREDENTIAL checkpoint at every
occurrence whatever any overlay says, because the overlay API shapes
*levels*, and the checkpoint-forever rule is not a level — it is a law
of the kernel. Tenancy is a lease on the matrix, never a locksmith.
