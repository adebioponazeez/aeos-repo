"""aeos.cli_inspect — the INSPECT surface (ADR-057): read the system's truth. Behavior moved verbatim from cli.py."""

from __future__ import annotations

import json
import time
from pathlib import Path


def dispatch(args) -> int:
    if args.cmd == "selftest":
        from . import __version__
        print(f"AEOS v{__version__} — harness is the product.")
        return 0
    if args.cmd == "scribe":
        from .doctor import repo_root
        from .scribe import audit
        repo = repo_root()
        if repo is None:
            print("SCRIBE — no repository context: run from a checkout "
                  "(any install kind); refusing to guess")
            return 1
        docs = tuple(args.doc) if args.doc else ("README.md",)
        rep = audit(repo, docs)
        print(rep.render())
        print("  history is exempt (CHANGELOG/ADR/book count at tag time);"
              " the README is the storefront contract")
        return 0 if rep.passed else 1
    if args.cmd == "bench":
        from .bench import envelope
        t0 = time.time()
        rep = envelope(Path(args.workspace), full=args.full)
        print(rep.render())
        print(f"  wall: {time.time() - t0:.1f}s — budgets are law; "
              "see docs/ENVELOPE.md for the accepted limits")
        return 0 if rep.passed else 1
    if args.cmd == "doctor":
        from .doctor import doctor, render
        rep = doctor(Path(args.workspace) if args.workspace else None)
        print(render(rep))
        if rep["failed"] == 0 and rep["warned"] > 0:
            print("  (warnings are advice; failures are law)")
        return 0 if rep["failed"] == 0 else 1
    if args.cmd == "eval":
        from .evals import run_self_eval
        rep = run_self_eval(Path(args.workspace))
        print(rep.render())
        print("  judges are predicates, not models — no charm, "
              "no self-report")
        return 0 if rep.passed else 1
    if args.cmd == "telemetry":
        import os as _os
        from .telemetry import effective_tokens, parse_usage
        if args.live:
            if _os.environ.get("AEOS_LIVE") != "1":
                print("live telemetry needs explicit opt-in: AEOS_LIVE=1 "
                      "(and a real provider key in env) — no silent spend")
                return 1
            print("live telemetry reads the provider's own usage block; "
                  "point it at a live run's response log")
            return 0
        snap = parse_usage({"usage": {
            "input_tokens": 120, "output_tokens": 80,
            "cache_read_input_tokens": 4000,
            "cache_creation_input_tokens": 200}})
        naive = snap.input_tokens + snap.cache_read_tokens \
            + snap.cache_creation_tokens
        print("TELEMETRY — cache hits are money (fixture, honestly labeled)")
        print(f"  naive input tokens:      {naive}")
        print(f"  cache hit rate:          {snap.cache_hit_rate:.1%}")
        print(f"  effective after discount:{snap.effective_input_tokens}")
        print(f"  saving on this call:     "
              f"{effective_tokens(naive, snap)} felt vs {naive} billed-naive")
        print("  v14 made prefixes byte-stable; this reads the payoff")
        return 0
    if args.cmd == "leverage-audit":
        from .leverage import audit, render
        print(render(audit(Path(args.workspace))))
        return 0
    if args.cmd == "recall":
        ws = Path(args.workspace)
        mem_path = ws / ".aeos" / "memory.jsonl"
        if not mem_path.exists():
            print(f"no memory at {mem_path} — run `aeos run-demo "
                  f"--workspace {ws}` first")
            return 1
        from .memory import MemoryStore
        from .recall import RecallIndex
        idx = RecallIndex(str(ws / ".aeos" / "recall.sqlite"),
                          MemoryStore(mem_path))
        idx.build()
        rep = idx.recall(args.query, budget=120)
        idx.close()
        print(f"RECALL — layered, budgeted (query: {args.query!r})")
        for lay in rep.layers:
            names = ", ".join(str(i)[:60] for i in lay.items[:3]) or "-"
            print(f"  L{lay.layer}: {len(lay.items)} item(s), "
                  f"{lay.tokens} tokens — {names}")
        print(f"  paid {rep.recall_tokens} vs full-scan {rep.full_scan_tokens}"
              f" — saved {rep.saving}")
        return 0
    if args.cmd == "dividend":
        ws = Path(args.workspace)
        bundle_file = ws / ".aeos" / "evidence" / "bundle.json"
        if not bundle_file.exists():
            print(f"no run found at {bundle_file} — run `aeos run-demo "
                  f"--workspace {ws}` first")
            return 1
        b = json.loads(bundle_file.read_text(encoding="utf-8"))
        d = b.get("dividend")
        if not d:
            print("this run predates v14 — re-run to measure the dividend")
            return 1
        dis = d["distillation"]
        print("DIVIDEND — memory economics (measured, not asserted)")
        print(f"  distillation: {dis['groups']} group(s), "
              f"{dis['episodes_in']} episodes -> {dis['tokens_out']} tokens "
              f"(compression x{dis['compression']})")
        print(f"  projected saving per future recall: "
              f"{dis['projected_saving_per_recall']} tokens")
        for cls, m in d["ledger"]["classes"].items():
            verdict = ("NEGATIVE MARGINAL ✓"
                       if m.get("negative_marginal") else "no dividend yet")
            print(f"  {cls}: baseline {m.get('baseline')} -> all-in "
                  f"{m.get('all_in')} tokens/run — {verdict} "
                  f"(cumulative saved {m.get('cumulative_saved')})")
        print(f"  rent: {d['rent']['pays']} record(s) pay rent; "
              f"{d['rent']['squatters']} squatting "
              f"({d['rent']['squat_tokens']} tokens drag)")
        return 0
    if args.cmd == "triangle":
        from .triangle import RunProfile, TriangleReport
        ws = Path(args.workspace)
        bundle_file = ws / ".aeos" / "evidence" / "bundle.json"
        if not bundle_file.exists():
            print(f"no run found at {bundle_file} — run `aeos run-demo "
                  f"--workspace {ws}` first")
            return 1
        b = json.loads(bundle_file.read_text(encoding="utf-8"))
        t = b.get("triangle")
        if not t:
            print("this run predates v13 — re-run with --profile")
            return 1
        prof = RunProfile.preset(t["profile"])
        report = TriangleReport(
            profile=t["profile"], control=t["control"],
            cost_usd=t["cost_usd"],
            speed_tasks_per_s=t["speed_tasks_per_s"],
            duration_s=t["duration_s"], components=t["components"])
        print(report.render())
        print(f"\n  stance: {prof.label}")
        return 0
    print(f"FRONT DOOR — no handler for {args.cmd!r}; this is a bug")
    return 2
