# Runbook — operating AEOS at v32

*The operator's journey, current as of v35.0.0 (59 modules, 426 tests,
zero dependencies). If this file and reality disagree, `aeos doctor`
is the tiebreaker.*

## 1. Install and first contact

```bash
git clone https://github.com/adebioponazeez/aeos-repo && cd aeos-repo
pip install -e .[dev]        # installs nothing but aeos (ADR-002)
aeos selftest                # identity receipt
aeos doctor                  # the system audits its own claims
python -m pytest tests/ -q   # every proof, chaos storm included
```

## 2. Daily commands

```bash
aeos run-demo --workspace ./demo            # the full reference loop
aeos run-demo --intent "Ship it per [STD-1]"  # cite your standards
aeos triangle --workspace ./demo            # control/cost/speed receipt
aeos dividend --workspace ./demo            # memory economics receipt
aeos recall --query deploy --workspace ./demo
```

## 3. Serious operation

```bash
aeos storm --workspace ./ws       # 9 chaos scenarios, end to end
aeos soak --runs 5 --workspace ./ws   # sustained-operation receipt
aeos backup --workspace ./ws --out ws.tar
rm -rf ./ws && aeos restore --backup ws.tar --workspace ./ws
aeos groom --keep-runs 10 --workspace ./ws   # archive, never delete
aeos leverage-audit --workspace ./ws         # 12 points, evidence on disk
```

Live mode is opt-in only: `AEOS_LIVE=1` plus a provider key env
(`aeos live-check` shows the resolved config, zero spend), capped by
`AEOS_MAX_COST` with an inline cutoff.

## 4. Serving and pushing (endpoint-explicit, never ambient)

```bash
aeos mcp --serve-http --roundtrip   # read-only consulate, loopback bind
aeos mcp --http-url https://host/mcp
aeos otel --push https://collector/v1/traces --workspace ./ws
```

## 5. Reading a run

The bundle at `.aeos/evidence/bundle.json` is the truth: `accepted`,
task states with attempts, economics (metered), leverage, standards
gate verdict, dividend (distillation/ledger/rent/recall), triangle
receipt, environment. Verdicts come from a closed vocabulary;
UNVERIFIED is a first-class answer.

## 6. Troubleshooting

| Symptom | Meaning | Move |
|---|---|---|
| `workspace locked` refusal | a run holds it | the kernel releases on death; or wait |
| `.torn` sidecars appear | power-cut writes | quarantined forensics; doctor reports them |
| `SchemaError` | state from a NEWER aeos | upgrade aeos before touching that state |
| doctor FAIL (dependencies) | a non-stdlib import crept in | remove it — ADR-002 is law |
| CI leg red once | shared-runner wall clock | the disclosed retry exists; twice red = real |

## 7. Shipping changes

Commit, tag (`vX.Y.Z`), push — CI must prove the matrix (3.10–3.13,
storm included) before anything counts. Release assets: the Codex
PDFs from `book/print/` via `python book/build_pdf.py`. Publishing
to PyPI: `docs/PUBLISHING.md`.
