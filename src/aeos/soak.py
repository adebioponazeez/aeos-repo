"""v29 Soak: sustained operation, seriously evidenced.

A soak is not a demo: it is N consecutive runs on ONE workspace
(state accumulating across runs), every run verdict-gated, with a
stability receipt — accepted count, wall-clock mean/max drift,
token/cost totals, disk delta, memory growth, groom behavior. Live
mode is opt-in only (AEOS_LIVE=1 + provider key) under a hard dollar
cap; the default is simulation, labeled as simulation.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path


def run_soak(workspace: Path, runs: int = 5, *, live: bool = False,
             max_usd: float = 1.0) -> dict:
    from .pipeline import reference_run
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)

    model = None
    mode = "simulation (honest default — no network, no spend)"
    if live:
        import os
        if os.environ.get("AEOS_LIVE") != "1":
            raise PermissionError(
                "live soak needs explicit opt-in: AEOS_LIVE=1 plus the "
                "provider key env — no silent spend, ever")
        from .providers import live_adapter
        model = live_adapter(None, None)      # raises without key
        mode = f"LIVE (hard cap ${max_usd:.2f}, inline cutoff armed)"

    disk_before = shutil.disk_usage(ws).free if ws.exists() else None
    durations, accepted, costs, tokens = [], 0, 0.0, 0
    failures = []
    for i in range(runs):
        t0 = time.time()
        try:
            bundle = reference_run(ws, intent="Ship it per [STD-1]",
                                   model=model,
                                   cost_budget=max_usd if live else None)
            ok = bundle.get("accepted") is True
            econ = bundle.get("economics", {})
            costs += float(econ.get("total_cost") or 0)
            tokens += int(econ.get("total_tokens") or 0)
            if not ok:
                failures.append(f"run {i + 1}: not accepted")
        except Exception as exc:
            failures.append(f"run {i + 1}: {type(exc).__name__}: {exc}")
            continue
        finally:
            durations.append(time.time() - t0)
        if ok:
            accepted += 1

    mem_records = 0
    mem_path = ws / ".aeos" / "memory.jsonl"
    if mem_path.exists():
        from .memory import MemoryStore
        mem_records = len(MemoryStore(mem_path).records)

    disk_after = shutil.disk_usage(ws).free
    receipt = {
        "mode": mode, "runs": runs, "accepted": accepted,
        "failures": failures,
        "wall_total_s": round(sum(durations), 2),
        "wall_mean_s": round(sum(durations) / len(durations), 3) if durations else None,
        "wall_max_s": round(max(durations), 3) if durations else None,
        "cost_total": round(costs, 4), "tokens_total": tokens,
        "memory_records": mem_records,
        "disk_delta_mb": round((disk_before - disk_after) / 1e6, 2)
                         if disk_before is not None else None,
        "passed": accepted == runs and not failures,
    }
    return receipt


def render(r: dict) -> str:
    head = (f"SOAK — {r['accepted']}/{r['runs']} accepted "
            f"({'PASS' if r['passed'] else 'FAIL'})")
    lines = [head, f"  mode: {r['mode']}"]
    lines.append(f"  wall: total {r['wall_total_s']}s | mean "
                 f"{r['wall_mean_s']}s | max {r['wall_max_s']}s")
    lines.append(f"  economics: {r['tokens_total']} tokens, "
                 f"${r['cost_total']} (metered by the run)")
    lines.append(f"  state: {r['memory_records']} memory records | "
                 f"disk delta {r['disk_delta_mb']}MB")
    if r["failures"]:
        lines.append(f"  FAILURES: {r['failures']}")
    return "\n".join(lines)
