"""aeos CLI — run the reference pipeline, inspect evidence."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aeos",
        description="AI Engineering OS — reference pipeline and inspection tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run-demo", help="Execute the reference pipeline")
    run_p.add_argument("--workspace", default="aeos-demo")
    run_p.add_argument("--intent", default="Ship a verified seed module")
    run_p.add_argument("--live", action="store_true",
                       help="v11: run on a real model (bring your own key)")
    run_p.add_argument("--provider", default=None,
                       help="openrouter | abacus | openai (default: AEOS_PROVIDER)")
    run_p.add_argument("--model", default=None, help="model id for live mode")
    run_p.add_argument("--profile", default="balanced",
                       choices=["control", "balanced", "speed", "cost"],
                       help="v13: the control-cost-speed stance for this run")

    sub.add_parser("companions", help="v12: Pi CLI / DeerFlow status + how to enable")

    stm_p = sub.add_parser("storm", help="v27: the nuclear test — kill storms, torn files, disk full, blackout")
    stm_p.add_argument("--workspace", default="aeos-demo")

    bak_p = sub.add_parser("backup", help="v29: deterministic workspace backup (sha256 manifest)")
    bak_p.add_argument("--workspace", default="aeos-demo")
    bak_p.add_argument("--out", default=None)

    res_p = sub.add_parser("restore", help="v29: verify + restore a backup (fails closed on corruption)")
    res_p.add_argument("--backup", required=True)
    res_p.add_argument("--workspace", default="aeos-demo")

    soa_p = sub.add_parser("soak", help="v29: sustained operation receipt — N runs, one workspace")
    soa_p.add_argument("--workspace", default="aeos-demo")
    soa_p.add_argument("--runs", type=int, default=5)
    soa_p.add_argument("--live", action="store_true",
                       help="live provider soak (requires AEOS_LIVE=1 + key)")
    soa_p.add_argument("--max-usd", type=float, default=1.0)

    gro_p = sub.add_parser("groom", help="v28: retention + schema migration — archive old runs, upgrade state")
    gro_p.add_argument("--workspace", default="aeos-demo")
    gro_p.add_argument("--keep-runs", type=int, default=10)

    vlt_p = sub.add_parser("vault", help="v26: fault tolerance — environment scan + self-proof")
    vlt_p.add_argument("--workspace", default="aeos-demo")

    evl_p = sub.add_parser("eval", help="v23: eval suite — the system grades its own laws")
    evl_p.add_argument("--workspace", default="aeos-demo")

    ote_p = sub.add_parser("otel", help="v24: export the fleet stream as OTel spans")
    ote_p.add_argument("--workspace", default="aeos-demo")

    mcp_p = sub.add_parser("mcp", help="v21: MCP client demo — handshake, tools, UNTRUSTED import")
    mcp_p.add_argument("--serve", action="store_true",
                       help="v24: serve AEOS read-only over MCP and roundtrip")

    col_p = sub.add_parser("colony", help="v25: explicit graph orchestration demo")
    tel_p = sub.add_parser("telemetry", help="v22: cache telemetry — hit rate and effective tokens")
    tel_p.add_argument("--live", action="store_true",
                       help="read a live provider response (requires AEOS_LIVE=1)")

    std_p = sub.add_parser("standards", help="v19: operator standards — the plan gate")
    std_p.add_argument("--workspace", default="aeos-demo")
    std_p.add_argument("--init", action="store_true",
                       help="write the STANDARDS.md template")

    res_p = sub.add_parser("resume", help="v17: durable plans — crash, resume, side effects once")
    res_p.add_argument("--workspace", default="aeos-demo")

    lev_p = sub.add_parser("leverage-audit", help="v18: the 12 leverage points audited against disk")
    lev_p.add_argument("--workspace", default="aeos-demo")

    rec_p = sub.add_parser("recall", help="v15: layered FTS recall — keys, snippets, full records")
    rec_p.add_argument("--workspace", default="aeos-demo")
    rec_p.add_argument("--query", default="deploy research")

    flt_p = sub.add_parser("fleet", help="v16: fleet CRUD + live event stream demo")
    flt_p.add_argument("--workspace", default="aeos-demo")

    div_p = sub.add_parser("dividend", help="v14: memory economics — distillation, negative marginal, rent")
    div_p.add_argument("--workspace", default="aeos-demo")

    tri_p = sub.add_parser("triangle", help="v13: measured control/cost/speed of the last run")
    tri_p.add_argument("--workspace", default="aeos-demo")

    lc_p = sub.add_parser("live-check",
                          help="v11: show resolved live config — zero spend")
    lc_p.add_argument("--provider", default=None,
                      help="openrouter | abacus | openai")

    sub.add_parser("selftest", help="Print system identity and exit 0")

    fac_p = sub.add_parser("factory-demo",
                           help="v7: run the capability factory over history")
    fac_p.add_argument("--workspace", default="aeos-factory")
    fac_p.add_argument("--token", default=None,
                       help="sponsorship token (omit to see proposals only)")

    dash_p = sub.add_parser("dashboard", help="render the static run dashboard")
    dash_p.add_argument("--live", action="store_true",
                        help="v16: tail the fleet event stream instead")
    dash_p.add_argument("--workspace", default="aeos-demo")

    con_p = sub.add_parser("console", help="v8: render the authority console")
    con_p.add_argument("--workspace", default="aeos-factory")

    spo_p = sub.add_parser("sponsor", help="v8: issue a persistent sponsorship token")
    spo_p.add_argument("--workspace", default="aeos-factory")
    spo_p.add_argument("--scope", required=True,
                       help="what this token authorizes, e.g. factory:install:NAME")
    spo_p.add_argument("--ttl", type=float, default=3600)

    fed_p = sub.add_parser("federation-demo",
                           help="v10: quarantine -> revalidate -> sponsored install")
    fed_p.add_argument("--workspace", default="aeos-federation")

    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        from . import __version__
        print(f"AEOS v{__version__} — harness is the product.")
        return 0

    if args.cmd == "storm":
        from .storm import run_storm
        t0 = time.time()
        rep = run_storm(Path(args.workspace))
        print(rep.render())
        print(f"  wall: {time.time() - t0:.1f}s — real subprocesses, "
              "real SIGKILLs, real fault injection")
        return 0 if rep.passed else 1

    if args.cmd == "backup":
        from .backup import create_backup
        out = args.out or str(Path(args.workspace) / ".aeos" / "backup.tar")
        r = create_backup(Path(args.workspace), Path(out))
        print(f"BACKUP — deterministic, manifest-verified")
        print(f"  {r['files']} file(s), {r['bytes'] // 1024} KB -> {r['path']}")
        print(f"  sha256: {r['sha256']}")
        print("  caches skipped (recall rebuilds); locks never carried")
        return 0

    if args.cmd == "restore":
        from .backup import BackupError, restore_backup
        try:
            r = restore_backup(Path(args.backup), Path(args.workspace))
        except BackupError as exc:
            print(f"RESTORE REFUSED: {exc}")
            return 1
        print("RESTORE — every member verified against the manifest")
        print(f"  {r['files']} file(s) -> {r['workspace']}")
        print(f"  recall cache rebuilt: {r['recall_rebuilt']}")
        print(f"  backup sha256: {r['sha256']}")
        return 0

    if args.cmd == "soak":
        from .soak import render, run_soak
        try:
            r = run_soak(Path(args.workspace), args.runs,
                         live=args.live, max_usd=args.max_usd)
        except PermissionError as exc:
            print(f"soak: {exc}")
            return 1
        print(render(r))
        return 0 if r["passed"] else 1

    if args.cmd == "groom":
        from .groom import groom as sweep, render
        print(render(sweep(Path(args.workspace), args.keep_runs)))
        return 0

    if args.cmd == "vault":
        from aeos import vault
        ws = Path(args.workspace)
        scan = vault.environment_scan(ws)
        print("VAULT — fault tolerance posture")
        print(f"  disk free: {scan['disk_free_mb']}MB | cpus: "
              f"{scan['cpu_count']} | mem: {scan['mem_total_mb']}MB "
              f"or unknown")
        print(f"  degraded: {scan['degraded'] or 'no'}")
        print("  every persistent write: atomic (tmp+fsync+rename)")
        print("  every load: tolerant (torn -> .torn quarantine)")
        print("  workspace: kernel-released lock (kill -9 cannot strand)")
        print("  network: offline by default, provable under blackout")
        print("  full chaos receipt: `aeos storm`")
        return 0

    if args.cmd == "eval":
        from .evals import run_self_eval
        rep = run_self_eval(Path(args.workspace))
        print(rep.render())
        print("  judges are predicates, not models — no charm, "
              "no self-report")
        return 0 if rep.passed else 1

    if args.cmd == "otel":
        from .fleet import EventBus
        from .otel import export
        bus = EventBus(Path(args.workspace) / ".aeos" / "events.jsonl")
        events = bus.replay()
        if not events:
            print("no events to export — run `aeos fleet --workspace "
                  f"{args.workspace}` first")
            return 1
        out = Path(args.workspace) / ".aeos" / "otel-spans.jsonl"
        n = export(bus, out)
        print(f"OTEL — {n} span(s) exported (byte-stable, "
              "content-addressed ids)")
        print(f"  {out}")
        print("  one trace per stream; FAILED events map to ERROR "
              "status; ingestible by any OTel collector")
        return 0

    if args.cmd == "colony":
        from .colony import Colony, Node
        c = Colony()
        c.add(Node("scout", lambda ctx: {"risk": "medium"}))
        c.add(Node("smith", lambda ctx: f"code against {ctx['scout']['risk']}",
                   requires=("scout",)))
        c.add(Node("scribe", lambda ctx: "docs drafted"))
        c.add(Node("deploy", lambda ctx: "shipped", requires=("smith",),
                   condition=lambda ctx: ctx["smith"].endswith("high")
                   is True))
        rep = c.run()
        print(rep.render())
        print("  nodes declare requires + conditions; failures block "
              "dependents; cycles BLOCK, never hang")
        return 0

    if args.cmd == "mcp" and getattr(args, "serve", False):
        import sys as _sys
        from .mcp_client import MCPClient
        c = MCPClient([_sys.executable, "-m", "aeos.mcp_server"],
                      timeout_s=15.0)
        c.start()
        try:
            info = c.initialize()
            tools = c.tools()
            res = c.call("leverage_audit",
                         {"workspace": str(Path.cwd() / "aeos-demo")})
        finally:
            c.close()
        print("MCP SERVE — roundtrip: our client, our server (ADR-033)")
        print(f"  handshake: {info['serverInfo']['name']} "
              f"v{info['serverInfo']['version']}")
        for t in tools:
            print(f"  tool: {t.name:<16} (read-only by law)")
        first = res.text.splitlines()[0] if res.text else ""
        print(f"  call leverage_audit -> {first}")
        return 0

    if args.cmd == "mcp":
        import sys as _sys
        from .mcp_client import MCPClient, import_tools
        c = MCPClient([_sys.executable, "-m", "aeos.mcp_demo_server"],
                      timeout_s=10.0)
        c.start()
        try:
            info = c.initialize()
            tools = c.tools()
            imported = import_tools(tools)
            res = c.call("echo", {"text": "the law travels with the protocol"})
        finally:
            c.close()
        print("MCP — stateless core, stdlib client (ADR-030)")
        print(f"  handshake: {info['serverInfo']['name']} "
              f"v{info['serverInfo']['version']}")
        for t in tools:
            trust = imported[t.name]["trust"]
            print(f"  tool: {t.name:<12} imported as {trust}")
        print(f"  call: {res.text!r} -> ok={res.ok}")
        print("  law: imported tools are UNTRUSTED until evidence "
              "promotes them")
        return 0

    if args.cmd == "telemetry":
        import os as _os
        from .telemetry import UsageSnapshot, effective_tokens, parse_usage
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

    if args.cmd == "standards":
        from .standards import check_plan, init_template, registered_ids
        ws = Path(args.workspace)
        if args.init:
            p_std = init_template(ws)
            print(f"STANDARDS — template written: {p_std}")
        path = ws / "STANDARDS.md"
        ids = registered_ids(path)
        if not ids:
            print("no STANDARDS.md — the gate is off (operator's choice);"
                  " `aeos standards --init` to register law")
            return 0
        print(f"STANDARDS — {len(ids)} registered: {', '.join(ids)}")
        demo = check_plan("example plan per [STD-1]", path)
        print(f"  plan citing {demo['cited']} -> "
              f"{'ACCEPTED' if demo['ok'] else 'REFUSED'}")
        return 0

    if args.cmd == "resume":
        from .resume import PlanCheckpoint, PlanTask, ResumeNeeded, execute_plan
        ws = Path(args.workspace)
        cp = PlanCheckpoint(ws / ".aeos" / "checkpoint.json")
        if cp.load():   # stale demo checkpoint — start the demo fresh
            cp.path.unlink()
        plan = [PlanTask(f"t{i}", "build", f"step {i}") for i in range(5)]
        calls = []
        try:
            execute_plan("demo", plan, lambda t: calls.append(t.id),
                         cp, fail_at="t2")
        except ResumeNeeded as e:
            print(f"RESUME — simulated crash: {e}")
        report = execute_plan("demo", plan, lambda t: calls.append(t.id), cp)
        print("RESUME — durable plans, idempotent restart")
        print(f"  executed after recovery: {report['executed']}")
        print(f"  call log: {calls} — every task ran exactly once")
        print(f"  checkpoint: {cp.path} ({len(report['done'])}/5 durable)")
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

    if args.cmd == "fleet":
        from .fleet import EventBus, FleetOrchestrator
        ws = Path(args.workspace)
        bus = EventBus(ws / ".aeos" / "events.jsonl")
        orch = FleetOrchestrator(bus)
        orch.register("scout", "research", skills=("brief", "cite"))
        orch.register("smith", "build", skills=("tests-first",))
        orch.register("warden", "governance", skills=("gates", "budget"))
        orch.dispatch("scout", "survey the landscape")
        orch.dispatch("smith", "ship the module with tests")
        orch.retire("smith")
        print("FLEET — one orchestrator, every mutation an event")
        for a in orch.roster():
            print(f"  {a['name']:<8} {a['role']:<12} skills={a['skills']}")
        print("  event stream (tail):")
        for ev in bus.tail(6):
            print(f"    {ev.kind:<18} {ev.agent:<8} {ev.detail[:48]}")
        print(f"  stream: {bus.path} — `aeos dashboard --live` to tail it")
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

    if args.cmd == "companions":
        from .companions import companion_status
        for st in companion_status():
            state = "READY" if st.available else "not installed"
            print(f"{st.name:10s} {state:15s} {st.path or '-'}")
            print(f"{'':10s} {st.hint}")
        return 0

    if args.cmd == "live-check":
        from .providers import PRESETS, live_budget
        import os
        provider = (args.provider or os.environ.get("AEOS_PROVIDER")
                    or "openrouter").lower()
        if provider not in PRESETS:
            print(f"unknown provider '{provider}' — known: {sorted(PRESETS)}")
            return 2
        preset = PRESETS[provider]
        model = os.environ.get("AEOS_MODEL") or preset["default_model"]
        print(json.dumps({
            "provider": provider, "model": model,
            "base_url": preset["base_url"],
            "key_env": preset["key_env"],
            "key_present": bool(os.environ.get(preset["key_env"])),
            "budget_usd": live_budget().max_cost,
            "spend": "0.00 — this command never calls the wire",
        }, indent=2))
        return 0

    if args.cmd == "run-demo":
        from .pipeline import reference_run
        model = None
        if args.live:
            from .providers import live_adapter
            try:
                model = live_adapter(args.provider, args.model)
            except PermissionError as exc:
                print(f"live mode: {exc}", file=sys.stderr)
                return 2
        bundle = reference_run(Path(args.workspace), args.intent, model=model,
                               profile=args.profile)
        print(json.dumps(bundle, indent=2, default=str))
        return 0 if bundle["accepted"] else 1

    if args.cmd == "factory-demo":
        from .pipeline import factory_demo
        summary = factory_demo(Path(args.workspace), token=args.token)
        print(json.dumps(summary, indent=2, default=str))
        return 0

    if args.cmd == "dashboard" and getattr(args, "live", False):
        from .fleet import EventBus
        bus = EventBus(Path(args.workspace) / ".aeos" / "events.jsonl")
        events = bus.tail(20)
        if not events:
            print("no events yet — run `aeos fleet --workspace "
                  f"{args.workspace}` first")
            return 1
        print("LIVE — fleet event stream (last "
              f"{len(events)})")
        for ev in events:
            print(f"  {ev.kind:<18} {ev.agent:<10} {ev.detail[:52]}")
        return 0

    if args.cmd == "dashboard":
        from .pipeline import render_last_dashboard
        out = render_last_dashboard(Path(args.workspace))
        print(f"dashboard: {out}")
        return 0

    if args.cmd == "console":
        from .console import render_console
        out = render_console(Path(args.workspace))
        print(f"console: {out}")
        return 0

    if args.cmd == "sponsor":
        from .sponsorship import SponsorshipGate
        ws = Path(args.workspace)
        gate = SponsorshipGate(ws / ".aeos" / "sponsorships.jsonl")
        s = gate.issue(args.scope, ttl_s=args.ttl)
        print(json.dumps({"token": s.token, "scope": s.scope,
                          "expires_at": s.expires_at,
                          "note": "one use, this scope only — spend it with "
                                  "--token"}, indent=2))
        return 0

    if args.cmd == "federation-demo":
        from .federation import federation_demo
        summary = federation_demo(Path(args.workspace))
        print(json.dumps(summary, indent=2, default=str))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
