"""aeos.cli_run — the RUN surface (ADR-057): plans that execute. Behavior moved verbatim from cli.py; the front door routes here."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _spine(workspace, intent=None, tasks=None, graph_file=None,
           style_file=None, profile="balanced") -> int:
    """v39.8 THE SPINE (ADR-055): one command, end to end. The
    reference objective — or an operator's compiled graph — executes
    on the REFERENCE pipeline: real roster, real handlers, real
    evidence law. The bundle, leverage, memory and learning are the
    product's, not a demo's; events stream LIVE into the runs dir
    (the one bus the shopfloor tails)."""
    from .graphlang import render_plan
    from .pipeline import reference_run

    if tasks is None and graph_file is not None:
        from .graphlang import GraphError, compile_graph
        style_text = None
        if style_file:
            sp = Path(style_file)
            if not sp.exists():
                print(f"RUN REFUSED — stylesheet not found: {sp}")
                return 2
            style_text = sp.read_text(encoding="utf-8")
        try:
            tasks = compile_graph(
                Path(graph_file).read_text(encoding="utf-8"),
                style=style_text)
        except GraphError as exc:
            print(f"RUN REFUSED — {exc}")
            return 2
    if tasks is not None:
        print(render_plan(tasks))
        routed = [(t.name, t.model) for t in tasks if t.model]
        if routed:
            print(f"  routing: {', '.join(f'{n}->{m}' for n, m in routed)}")
    if intent is None:
        intent = (f"Execute the workflow graph {Path(graph_file).name}"
                  if tasks is not None else
                  "Ship a verified seed module")
    try:
        bundle = reference_run(Path(workspace), intent, tasks=tasks,
                               live_events=True, profile=profile)
    except ValueError as exc:        # contract law: unknown agent/class
        print(f"RUN REFUSED — {exc}")
        return 2
    if not bundle.get("accepted"):
        print("SPINE RUN — REFUSED")
        if bundle.get("reason"):
            print(f"  reason: {bundle['reason']}")
        else:
            for d in bundle.get("states_detail", []):
                if d["state"] in ("FAILED", "ESCALATED"):
                    print(f"  {d['state'].lower()}: {d['name']} "
                          f"(agent {d['agent']}, {d['attempts']} attempt(s))")
            print(f"  summary: {bundle.get('summary')}")
            print(f"  why:     task.failed events in "
                  f"{bundle.get('events_file')}")
        return 1
    print("SPINE RUN — ACCEPTED")
    print(f"  plan:      {bundle.get('plan_origin')}")
    print(f"  summary:   {bundle.get('summary')}")
    mem = bundle.get("memory") or {}
    foreman_n = len(mem.get("foreman_lessons") or [])
    print(f"  memory:    {len(mem.get('recalled_lessons') or [])} lesson(s) "
          f"recalled from prior runs; "
          f"{len(mem.get('applied_to_spec') or [])} cited in the spec"
          + (f"; {foreman_n} foreman note(s)" if foreman_n else ""))
    print(f"  leverage:  {bundle.get('leverage')} | governor: "
          f"{bundle.get('governor_level')} "
          f"(reliability {bundle.get('governor_reliability')})")
    print(f"  lessons:   {bundle.get('learning_lessons')} | proposals: "
          f"{len(bundle.get('promotion_proposals') or [])}")
    print(f"  evidence:  {bundle.get('evidence_file')}")
    print(f"  events (live): {bundle.get('events_file')}")
    print(f"  shopfloor: aeos stream --workspace {workspace}")
    print(f"  holdout:   aeos holdout --run --workspace {workspace}")
    return 0


def dispatch(args) -> int:
    if args.cmd == "graph":
        from .graphlang import GraphError, compile_graph, render_plan
        if not args.file:
            print("GRAPH — no --file given. Try: aeos graph --file "
                  "examples/ship-graph.dot --style examples/routing.style")
            return 2
        f = Path(args.file)
        if not f.exists():
            print(f"GRAPH REFUSED — workflow file not found: {f}")
            return 2
        style_text = None
        if args.style:
            sp = Path(args.style)
            if not sp.exists():
                print(f"GRAPH REFUSED — stylesheet not found: {sp}")
                return 2
            style_text = sp.read_text(encoding="utf-8")
        try:
            tasks = compile_graph(f.read_text(encoding="utf-8"),
                                  style=style_text)
        except GraphError as exc:
            print(f"GRAPH REFUSED — {exc}")
            return 2
        if not args.run:
            print(render_plan(tasks))
            print("  (dry run — add --run to execute on the reference "
                  "pipeline: the spine, no demo path)")
            return 0
        # --run: THE SPINE (v39.8, ADR-055) — the compiled graph
        # executes on the REFERENCE pipeline: same roster, same
        # handlers, same evidence law. The demo roster is gone from
        # this path; the pipeline's own live sink feeds the shopfloor.
        return _spine(args.workspace, tasks=tasks, graph_file=f,
                      profile="balanced")
    if args.cmd == "up":
        from .ignition import boot, render
        r = boot(Path(args.workspace), args.intent,
                 save_proof=args.save_proof, profile=args.profile)
        print(render(r))
        return r["exit_code"]
    if args.cmd == "foreman":
        from .doctor import repo_root
        from .foreman import render, run
        r = run(Path(args.workspace), apply_mode=args.apply,
                repo=repo_root())
        print(render(r))
        if r["exit_code"] == 1:
            print("  exit 1 = attention (findings remain); "
                  "0 = clean; 2 = a remediation failed")
        return r["exit_code"]
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
    if args.cmd == "run":
        graph_file = None
        if args.graph:
            graph_file = Path(args.graph)
            if not graph_file.exists():
                print(f"RUN REFUSED — workflow file not found: {graph_file}")
                return 2
        return _spine(args.workspace, intent=args.intent,
                      graph_file=graph_file, style_file=args.style,
                      profile=args.profile)
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
    print(f"FRONT DOOR — no handler for {args.cmd!r}; this is a bug")
    return 2
