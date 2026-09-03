# ADR-019: Federation — import is quarantine

**Status: ACCEPTED (v10.0)**

## Context
A cross-organization capability market is where trust pressure is
maximal: foreign units arrive with reputation we cannot verify, from
hashes we did not compute, for workloads we did not measure.

## Decision
One sentence, enforced: **IMPORT IS QUARANTINE.** Foreign units that
pass their own hash enter as QUARANTINED; install is refused while
quarantined — explicitly *before* any token check, so no sponsorship
can outrank local validation. The only path to TRUSTED is passing OUR
sandbox under OUR gates. Tampered foreign artifacts are refused at the
border. Export carries provenance — the same rule seen from the other
side.

## Alternatives
- Web-of-trust / signed publisher hierarchies: the right *addition*
  someday, as a quarantine fast-lane — never as a substitute for local
  revalidation.
- Blind trust with audit-after: rejected categorically; audit is how
  you learn, not how you prevent.

## Tradeoffs
(+) "Who authorized this foreign capability, and what did it survive
  locally?" — answerable from two files, always.
(−) Revalidation cost per import; amortized by the fact that
  capabilities are imported rarely and run forever.

## Consequences
`test_quarantined_install_refused_even_with_token`,
`test_tampered_foreign_unit_never_enters`,
`test_revalidate_promotes_and_install_succeeds`; demo evidence in
`evidence/v10-federation-run.json`.
