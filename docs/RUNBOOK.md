# Runbook — operating the OS

## Daily commands

```bash
python -m pytest                 # verify the whole system (~5s)
aeos run-demo --workspace ./demo # full reference loop
aeos run-demo --intent "..."     # custom intent
aeos selftest
```

## Reading a run

1. `demo/.aeos/evidence/bundle.json` — verdict first: `accepted` true?
2. `demo/.aeos/runs/*.jsonl` — every event, in order. Grepping:
   - `governor.checkpoint|governor.deny` — anything asking permission
   - `boundary.violation` — an agent wrote outside its fence
   - `task.failed` — failures with reasons
3. `demo/evaluation/report.json` — the independent verdict and its checks.
4. `demo/release/NOTES.md` — the shipped record.

## Failure playbook (spec §14: repair the correct layer)

| Symptom | Likely missing layer | Action |
|---|---|---|
| Task failed: `evaluation FAIL` | SPECIFICATION (acceptance unclear) | Tighten the task description; check artifacts expected |
| `boundary.violation` | PERMISSION | Fix the agent's `writes:` or the handler's target path |
| `claims_are_backed` FAIL | EVALUATION | Handler must attach Evidence, not prose |
| Task ESCALATED | ORCHESTRATION (class/level) | Raise autonomy with evidence, or approve explicitly |
| Model outage (EchoModel raise) | MODEL | Adapter resilience; repair cycle retries bounded |
| Looping repairs | ORCHESTRATION | `max_attempts` bounds it; find the systemic cause |

## Promoting autonomy

The governor moves itself on reliability. To operate at a higher level
deliberately: run more work, watch the event log, let the EMA promote —
or set the level explicitly in `reference_run` for a scoped
experiment. High-impact classes checkpoint forever regardless.

## Adding an agent (the only checklist

1. `AgentSpec` with all contract fields (no blanks — validation
   rejects empty success criteria).
2. A handler returning `Envelope` with evidence attached.
3. If it writes: declare `writes:` globs; wrap with `bounded()`.
4. A test in `tests/` that fails if the contract regresses.
5. One ADR if the decision is architectural.
