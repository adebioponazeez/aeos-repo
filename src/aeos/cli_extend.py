"""aeos.cli_extend — the EXTEND surface (ADR-057): protocols, hooks, federation. Behavior moved verbatim from cli.py."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _demo_orchestrator(workspace, log=None, hooks=None):
    """One demo factory for every surface that executes a plan live
    (graph --run, hooks --register-demo). The audit's first
    de-disjointing law: the demo path is a product path or it is
    a lie — ONE roster, ONE handler shape, ONE wiring."""
    from .contracts import (ActionClass, AgentSpec, Envelope, Evidence,
                            Verdict)
    from .evaluation import Evaluator
    from .governor import Governor
    from .hooks import BUS
    from .models import EchoModel
    from .observability import EventLog
    from .orchestrator import Orchestrator

    def spec(name, *classes):
        return AgentSpec(name=name, mission=f"m-{name}", inputs=["i"],
                         outputs=["o"], tools=["t"], constraints=["c"],
                         success_criteria=["s"], evaluation_criteria=["e"],
                         escalation_conditions=["x"],
                         termination_conditions=["t"], writes=[],
                         action_classes=list(classes) or [ActionClass.READ])

    roster = {"executive": spec("executive", ActionClass.READ,
                                ActionClass.WRITE),
              "researcher": spec("researcher", ActionClass.NETWORK),
              "builder": spec("builder", ActionClass.WRITE),
              "evaluator": spec("evaluator")}

    def handler(agent):
        def h(task, orch):
            return Envelope(
                agent=agent, objective=task.description,
                claims=[f"{agent} handled {task.name}"],
                evidence=[Evidence(kind="gate", detail=f"{task.name} ran",
                                   verdict=Verdict.PASS)])
        return h

    log = log if log is not None else EventLog()
    return Orchestrator(agents=roster,
                        handlers={n: handler(n) for n in roster},
                        model=EchoModel(), governor=Governor(log=log),
                        evaluator=Evaluator(), log=log,
                        workspace=Path(workspace),
                        hooks=hooks if hooks is not None else BUS)


def dispatch(args) -> int:
    if args.cmd == "hooks":
        from .hooks import BUS
        if args.register_demo:
            from .hooks import HookVeto

            def guard(payload):
                if payload.get("action_class") == "DESTRUCTIVE":
                    raise HookVeto(
                        "demo guardrail: destructive work needs a human")
                return payload

            BUS.register("task.pre", guard, name="demo-guardrail")
            from .contracts import ActionClass, TaskSpec
            import tempfile
            orch = _demo_orchestrator(tempfile.mkdtemp())
            orch.run("demo", [
                TaskSpec(name="safe", description="d", agent="executive"),
                TaskSpec(name="danger", description="d", agent="executive",
                         action_class=ActionClass.DESTRUCTIVE)])
            states = orch.runs[0].states
            print("HOOKS DEMO — one plan, one guardrail hook:")
            print(f"  safe task   -> {states['safe'].value}")
            print(f"  destructive -> {states['danger'].value} "
                  "(vetoed NAMED by the hook)")
            print(BUS.describe())
            for r in BUS.registered():
                BUS.unregister(r)
            return 0
        print(BUS.describe())
        return 0
    if args.cmd == "holdout":
        import sys
        from .holdout import HoldoutVault, run_holdout
        vroot = (Path(args.vault) if args.vault
                 else Path.home() / ".aeos" / "holdout")
        vault = HoldoutVault(vroot)
        if args.init:
            vault.init()
            v = vault.verify()
            print(f"HOLDOUT VAULT — {vroot}")
            print(f"  sealed: {v.get('families', 0) if v['ok'] else 0} "
                  "scenario families; per-install nonce (0600)")
            print(f"  integrity: {'OK' if v['ok'] else 'REFUSED — ' + v['reason']}")
            return 0 if v["ok"] else 2
        if args.run:
            r = run_holdout(Path(args.workspace), vault)
            print(r.render())
            print(f"  vault: {vroot} (outside the workspace; instances "
                  "sealed — verdicts only)")
            return 0 if r.passed else 1
        v = vault.verify() if vault.initialized() else {"ok": False,
               "reason": "vault not initialized — `aeos holdout --init`"}
        print(f"HOLDOUT — {v['reason'] if not v['ok'] else 'vault verified'}")
        return 0 if v["ok"] else 2
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
        if args.push:
            from .otlp import push_file
            r = push_file(args.push, out)
            verdict = "PUSHED" if r["ok"] else "PUSH REFUSED by the wire"
            print(f"  PUSH {verdict}: {r['pushed']} span(s), "
                  f"{r['attempts']} attempt(s), status={r['status']}")
            if not r["ok"]:
                print(f"  {r['note']}")
        return 0
    if args.cmd == "mcp" and getattr(args, "serve_http", False):
        from .mcp_http import MCPHTTPClient
        from .mcp_http_server import Consulate
        with Consulate(args.bind, args.port) as c:
            print("CONSULATE — AEOS over HTTP, read-only by law "
                  "(ADR-040)")
            print(f"  listening: {c.url} (bind {c.bind})"
                  f"{' — LOOPBACK ONLY' if c.bind == '127.0.0.1' else ''}")
            if not args.roundtrip:
                try:
                    import time as _t
                    while True:
                        _t.sleep(3600)
                except KeyboardInterrupt:
                    print("\nconsulate closed cleanly")
                return 0
            cli = MCPHTTPClient(c.url, timeout_s=5)
            info = cli.initialize()
            tools = cli.tools()
            res = cli.call("leverage_audit",
                           {"workspace": args.workspace})
            print(f"  roundtrip handshake: {info['serverInfo']['name']}")
            for t in tools:
                print(f"  tool: {t.name:<16} (read-only by law)")
            print(f"  roundtrip call -> {res.text.splitlines()[0]}")
        print("  consulate closed; the door is shut by default")
        return 0
    if args.cmd == "mcp" and getattr(args, "http_url", None):
        from .mcp_http import MCPHTTPClient
        c = MCPHTTPClient(args.http_url, timeout_s=10.0)
        info = c.initialize()
        tools = c.tools()
        print("MCP HTTP — streamable transport, same law (ADR-039)")
        print(f"  endpoint: {args.http_url}")
        print(f"  handshake: {info['serverInfo']['name']}")
        for t in tools[:6]:
            print(f"  tool: {t.name}")
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
    if args.cmd == "companions":
        from .companions import companion_status
        for st in companion_status():
            state = "READY" if st.available else "not installed"
            print(f"{st.name:10s} {state:15s} {st.path or '-'}")
            print(f"{'':10s} {st.hint}")
        return 0
    if args.cmd == "live-check":
        from .providers import PRESETS, live_budget
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
    print(f"FRONT DOOR — no handler for {args.cmd!r}; this is a bug")
    return 2
