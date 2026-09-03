# PART VII — THE STATE OF THE SYSTEM

## Chapter 16. The Ledger at v7.0.0

Twenty-six modules. 131 tests. Zero runtime dependencies. One command
reproduces the ledger: `python -m pytest`.

| Layer | v | Proven by (selection) |
|---|---|---|
| Kernel (contracts→discovery) | 1.0 | 68 tests — Volume I |
| Secret redaction, gate library, entropy | 1.1 | `test_api_key_never_enters_the_log`, schema/tests/regression gates, drift+weak-test+unused-tool scans |
| Error taxonomy, breaker, fusion | 2.0 | `test_context_overflow_never_retries`, `test_circuit_opens_after_threshold`, `test_disagreement_is_surfaced_not_averaged` |
| Durable runtime | 2.0 | `test_failed_run_is_resumable_and_then_completes` |
| Tool layer (MCP idiom) | 2.0 | `test_results_are_always_untrusted`, `test_unknown_tool_fails_closed` |
| Catalog, sponsorship, tenancy | 3.0 | `test_tampered_unit_refuses_install`, `test_spend_is_one_shot`, tenant overlay tests |
| Economics | 4.0 | `test_budget_escalates_then_denies`, `test_leverage_ratio` |
| Research, sweeps, regressions | 5.0 | `test_low_authority_sources_go_to_unverified`, `test_recorded_failure_blocks_matching_change` |
| Meta-loop | 6.0 | `test_out_of_bounds_threshold_refused_even_with_token` |
| Factory + Studio | 7.0 | `test_failed_sandbox_never_installs`, `test_full_run_with_valid_token_installs` |

Witnessed runs: reference loop accepted at leverage 7.0 with the
governor earning L5; factory twice — proposals-only, then one scoped
install with a scope-mismatch refusal. All bundles in `evidence/`.

## Chapter 17. The Honest Gaps, v7 Edition

The discipline that produced ADR-008 still governs. What v7.0 does
**not** claim:

- **No real-model validation.** The suite proves the harness; adapters
  have not run against production providers at fleet scale. The seam
  makes that an operations exercise, not a rewrite — but it is not
  done, so it is not claimed.
- **No real MCP transport.** The tool layer speaks the shape with an
  injectable transport; a hardened client against live servers (with
  the SEP-2085 SBOM posture) is v8 work.
- **Sponsorship UX is plumbing.** Tokens are handled as strings; a
  human-facing console (issue, inspect, audit) does not exist yet.
- **Factory designs are templates.** Novel agent architectures still
  need human architects; the factory compounds *known* shapes.
- **Single-machine.** Multi-process fan-out, remote sandboxes, and
  A2A-style remote workers are beyond v7's in-process runtime.

The roadmap those gaps imply — v8 (hardened transports + console +
remote sandboxes), v9 (novel-design co-architecting with humans),
v10 (the cross-org capability market, catalog federation) — is stated
as engineering work with exit criteria, exactly as the v1→v7 roadmap
was, and for exactly the same reason: **a roadmap you can't be wrong
about is a poem.**

## Chapter 18. Closing: The Fifth Invariant

Volume I ended with four invariants. Seven versions later they hold
unmodified — no envelope no result; no authority without a boundary;
no autonomy without reliability; no memory without validation — and
the platform earned a fifth, the one that makes the other four
survive a system that edits itself:

**No self-modification without a spent human token.**

That sentence is the difference between the capability factory this
book documents and the "self-improving AI org" of the keynote
imagination. The factory designs its own coworkers, and every one of
them arrives holding a receipt: a measured signature, a passing
sandbox, a content hash, and a sponsor's spent authority. Growth, by
construction, leaves a paper trail.

Build systems that build systems. Then systems that improve systems.
Then systems that discover what systems should exist — and stop, at
every single door, to ask who is paying for the next one.

The human moves upward. The machines execute downward. And between
them, now, there is an OS — built, tested, documented, and *governed*.

---

# APPENDICES

## Appendix A — New Decision Records (Volume II)

- **ADR-009** Durable runtime: persist at transitions, resume without
  rework. *States, not event-sourced replay.*
- **ADR-010** Adapter error taxonomy: classify before responding.
  *Exhausted transients are permanent; still-down is permanent.*
- **ADR-011** Fusion: combine compute, surface disagreement.
  *Opinions are evidence, not truth.*
- **ADR-012** Tool layer: MCP shape, SEP-2085 posture, untrusted
  constant. *Injection is unparseable, not argued with.*
- **ADR-013** Sponsorship: scoped, one-shot, expiring, audited.
- **ADR-014** Economics: the objective function is a measurement or
  it is nothing.
- **ADR-015** Meta-loop bounds: floors outrank keys.
- **ADR-016** The factory: sandbox PASS is the only road to install;
  there is no override.

Full records with alternatives: `docs/adr/` (sixteen total).

## Appendix B — The Ten Laws at v7

The ten laws of Volume I hold verbatim. The platform stress-tested
each: adapters met Law 7 (fail closed) with a new vocabulary; fusion
met Law 3 (claims untrusted) with opinions-as-evidence; the catalog
met Law 9 (no folklore) with hashes; the factory met Law 6 (autonomy
earned) at architectural scale; and the meta-loop met every law at
once, which is why its floors exist. The laws were not maintained by
vigilance. They were maintained by *tests* — which is the only way
anything is.

## Appendix C — Reproducing Every Claim

```bash
pip install -e .            # nothing else installs
python -m pytest            # 131 proofs, ~4 seconds
aeos run-demo               # accepted run, leverage, evidence bundle
aeos dashboard              # the studio page
aeos factory-demo           # proposals only, refusals logged
aeos factory-demo --token S # scoped install, scope-mismatch refusal
```

Everything in both volumes is one of: a module you can read, a test
you can run, or an honest gap you can check is still listed as a gap.
*— end of Volume II —*
