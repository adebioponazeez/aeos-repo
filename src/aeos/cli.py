"""aeos CLI — run the reference pipeline, inspect evidence."""

from __future__ import annotations

import argparse
import json
import os
import shlex
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

    up_p = sub.add_parser("up",
                          help="v37: THE FRONT DOOR — staged boot: preflight, workspace, work, shutdown; failures speak plain language")
    up_p.add_argument("--workspace", default="aeos-demo")
    up_p.add_argument("--intent", default="Ship a verified seed module")
    up_p.add_argument("--profile", default="balanced",
                      choices=["control", "balanced", "speed", "cost"],
                      help="control-cost-speed stance for the work stage")
    up_p.add_argument("--save-proof", action="store_true",
                      help="notarize the repo tree after the work stage "
                           "(needs a checkout context; honest skip otherwise)")
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

    scr_p = sub.add_parser("scribe", help="v35: documentation that cannot drift — README claims vs live reality")
    scr_p.add_argument("--doc", action="append", default=None,
                       help="extra doc to audit (repeatable); default README.md")

    sfp_p = sub.add_parser("save-proof",
                           help="v36: the notary — pre/post Merkle roots + a green command = a completion certificate")
    sfp_p.add_argument("--command", default=None, metavar="CMD",
                       help="proof command as a quoted string (default: the test suite); shlex-split, never a shell")
    sfp_p.add_argument("--out", default=None, metavar="DIR",
                       help="certificate directory (default: evidence/save-proofs in the repo)")
    sfp_p.add_argument("--verify", default=None, metavar="CERT",
                       help="verify a saved certificate instead of running one")
    sfp_p.add_argument("--against-tree", action="store_true",
                       help="with --verify: also re-check the live tree against the certificate")

    obx_p = sub.add_parser("outbox",
                           help="v36: the edge outbox — a local WAL queue; the wire stays explicit")
    obx_sub = obx_p.add_subparsers(dest="outbox_cmd", required=True)
    obx_e = obx_sub.add_parser("enqueue",
                               help="buffer a record locally (offline-safe; nothing leaves the machine)")
    obx_e.add_argument("--endpoint", required=True,
                       help="explicit http(s) destination for a later flush")
    obx_e.add_argument("--payload", required=True, help="the record (text/JSON)")
    obx_e.add_argument("--key", default=None,
                       help="idempotency key (default: sha256 of endpoint+payload)")
    obx_s = obx_sub.add_parser("status", help="queue counts — no side effects")
    obx_f = obx_sub.add_parser("flush",
                               help="replay pending rows to ONE explicit endpoint")
    obx_f.add_argument("--endpoint", required=True,
                       help="the endpoint rows must already name — flush never guesses")
    obx_f.add_argument("--limit", type=int, default=100)
    obx_f.add_argument("--dry", action="store_true",
                       help="rehearse: report what would leave, deliver nothing")

    ben_p = sub.add_parser("bench", help="v34: the performance envelope — measured, budgeted receipts")
    ben_p.add_argument("--workspace", default="aeos-demo")
    st_p = sub.add_parser("stream",
                          help="v39.7: the live shopfloor — SSE event stream + console, read-only, loopback by default")
    st_p.add_argument("--workspace", default="aeos-demo")
    st_p.add_argument("--bind", default="127.0.0.1",
                      help="default 127.0.0.1 (loopback law); widen explicitly at your own risk")
    st_p.add_argument("--port", type=int, default=8787)

    gr_p = sub.add_parser("graph",
                          help="v39.6: workflows as declarative DOT — clusters compile to nested harnesses; stylesheets route, never declassify")
    gr_p.add_argument("--file", default=None,
                      help="workflow file (DOT subset: digraph, nodes with [attrs], -> edges, subgraph cluster_*)")
    gr_p.add_argument("--style", default=None,
                      help="routing stylesheet (INI [fnmatch-pattern] sections: model=, agent=, max_attempts=)")
    gr_p.add_argument("--workspace", default="aeos-graph-demo")
    gr_p.add_argument("--run", action="store_true",
                      help="execute the compiled plan (demo roster; the same governor/hooks/gates as every run)")

    hk_p = sub.add_parser("hooks",
                          help="v39.5: the hook surface — named lifecycle points, ordered registrations, veto/redirect semantics")
    hk_p.add_argument("--register-demo", action="store_true",
                      help="register a demo guardrail hook and run a tiny plan to show veto/redirect in action")

    ho_p = sub.add_parser("holdout",
                          help="v39.4: sealed holdout scenarios vs a digital twin — evaluation the agent cannot overfit to")
    ho_p.add_argument("--init", action="store_true",
                      help="create/verify the sealed vault (per-install nonce; scenarios never plaintext)")
    ho_p.add_argument("--run", action="store_true",
                      help="unseal against a twin of --workspace; verdict-only report")
    ho_p.add_argument("--workspace", default="aeos-demo")
    ho_p.add_argument("--vault", default=None,
                      help="vault dir (default: ~/.aeos/holdout — outside every repo and workspace)")
    ben_p.add_argument("--full", action="store_true",
                       help="10k scale (default: quick 1k)")

    doc_p = sub.add_parser("doctor", help="v32: the system audits its own claims — zero-dep scan, workspace + repo health")
    doc_p.add_argument("--workspace", default=None)

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

    ote_p = sub.add_parser("otel", help="v24: export the fleet stream as OTel spans; v30: --push to a collector")
    ote_p.add_argument("--workspace", default="aeos-demo")
    ote_p.add_argument("--push", default=None, metavar="URL",
                       help="v30: push spans to an OTLP/HTTP collector (explicit endpoint)")

    mcp_p = sub.add_parser("mcp", help="v21: MCP client demo — handshake, tools, UNTRUSTED import")
    mcp_p.add_argument("--serve", action="store_true",
                       help="v24: serve AEOS read-only over MCP and roundtrip")
    mcp_p.add_argument("--http-url", default=None, metavar="URL",
                       help="v30: talk to a streamable-HTTP MCP endpoint instead of stdio")
    mcp_p.add_argument("--serve-http", action="store_true",
                       help="v31: serve AEOS read-only over HTTP (bind 127.0.0.1 unless --bind)")
    mcp_p.add_argument("--bind", default="127.0.0.1",
                       help="v31: bind address for --serve-http (0.0.0.0 must be explicit)")
    mcp_p.add_argument("--port", type=int, default=0,
                       help="v31: port for --serve-http (0 = ephemeral)")
    mcp_p.add_argument("--roundtrip", action="store_true",
                       help="v31: prove the consulate with our own HTTP client, then exit")
    mcp_p.add_argument("--workspace", default="aeos-demo",
                       help="v31: workspace for --serve-http --roundtrip calls")

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

    frm_p = sub.add_parser("foreman",
                           help="v39: THE AUTONOMOUS OPERATOR — survey the workspace, fix the mechanical class, file the rest; receipts for everything")
    frm_p.add_argument("--workspace", default="aeos-demo")
    frm_p.add_argument("--apply", action="store_true",
                       help="execute the mechanical remediations "
                            "(default: survey only — safe by design")

    fed_p = sub.add_parser("federation-demo",
                           help="v10: quarantine -> revalidate -> sponsored install")
    fed_p.add_argument("--workspace", default="aeos-federation")

    args = parser.parse_args(argv)

    if args.cmd == "stream":
        from .stream import ShopfloorServer
        ws = Path(args.workspace)
        if not (ws / ".aeos").exists():
            print(f"SHOPFLOOR REFUSED — no .aeos in {ws}: the shopfloor "
                  "attaches to REAL run history; run `aeos up --workspace "
                  f"{ws}` first")
            return 2
        return ShopfloorServer(ws, bind=args.bind,
                               port=args.port).start()

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
        print(render_plan(tasks))
        if not args.run:
            print("  (dry run — add --run to execute under the governor,"
                  "  hooks and gates like every plan)")
            return 0
        # --run: the demo roster (deterministic engines; the same
        # kernel path every plan takes)
        from .contracts import (ActionClass, AgentSpec, Envelope, Evidence,
                                Verdict)
        from .evaluation import Evaluator
        from .governor import Governor
        from .hooks import BUS
        from .models import EchoModel
        from .observability import EventLog
        from .orchestrator import Orchestrator
        import tempfile

        def spec(name, *classes):
            return AgentSpec(name=name, mission=f"m-{name}", inputs=["i"],
                             outputs=["o"], tools=["t"], constraints=["c"],
                             success_criteria=["s"],
                             evaluation_criteria=["e"],
                             escalation_conditions=["x"],
                             termination_conditions=["t"], writes=[],
                             action_classes=list(classes) or
                             [ActionClass.READ])
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

        log = EventLog()
        orch = Orchestrator(
            agents=roster,
            handlers={n: handler(n) for n in roster},
            model=EchoModel(), governor=Governor(log=log),
            evaluator=Evaluator(), log=log,
            workspace=Path(args.workspace), hooks=BUS)
        rep = orch.run("graph", tasks)
        print(rep.summary_line())
        routed = [(t.name, t.model) for t in tasks if t.model]
        if routed:
            print(f"  routing: {', '.join(f'{n}->{m}' for n, m in routed)}")
        sub_events = [e for e in log.events()
                      if e.kind in ("subplan.start", "subplan.end")]
        for e in sub_events:
            print(f"  {e.kind}: {e.detail}")
        print("GRAPH RUN — " + ("ACCEPTED" if rep.accepted else "REFUSED"))
        return 0 if rep.accepted else 1

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
            from .contracts import (ActionClass, AgentSpec, Envelope,
                                    Evidence, TaskSpec, Verdict)
            from .evaluation import Evaluator
            from .governor import Governor
            from .models import EchoModel
            from .observability import EventLog
            from .orchestrator import Orchestrator
            import tempfile
            ag = AgentSpec(name="a", mission="m", inputs=["i"],
                           outputs=["o"], tools=["t"], constraints=["c"],
                           success_criteria=["s"], evaluation_criteria=["e"],
                           escalation_conditions=["x"],
                           termination_conditions=["t"], writes=[])
            orch = Orchestrator(
                agents={"a": ag},
                handlers={"a": lambda t, o: Envelope(
                    agent="a", objective=t.description, claims=["ran"],
                    evidence=[Evidence(kind="gate", detail="ran",
                                       verdict=Verdict.PASS)])},
                model=EchoModel(), governor=Governor(log=EventLog()),
                evaluator=Evaluator(), log=EventLog(),
                workspace=Path(tempfile.mkdtemp()))
            orch.run("demo", [
                TaskSpec(name="safe", description="d", agent="a"),
                TaskSpec(name="danger", description="d", agent="a",
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
            m = vault.init()
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

    if args.cmd == "selftest":
        from . import __version__
        print(f"AEOS v{__version__} — harness is the product.")
        return 0

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

    if args.cmd == "save-proof":
        from . import saveproof
        from .doctor import repo_root
        if args.verify:
            try:
                cert = json.loads(
                    Path(args.verify).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"SAVE-PROOF — cannot read certificate: {exc}")
                return 1
            ok, why = saveproof.verify(
                cert,
                root=repo_root() if args.against_tree else None,
                key=os.environ.get("AEOS_PROOF_KEY"))
            print(f"SAVE-PROOF — {'VERIFIED' if ok else 'REFUSED'}: {why}")
            if ok:
                print(f"  outcome {cert['outcome']}; "
                      f"pre {cert['pre_root'][:12]} -> "
                      f"post {cert['post_root'][:12]}; "
                      f"auth {cert['auth']['scheme']}")
            return 0 if ok else 1
        root = repo_root()
        if root is None:
            print("SAVE-PROOF — no repository context: run from a checkout "
                  "(any install kind); refusing to guess")
            return 1
        try:
            command = shlex.split(args.command) if args.command else None
            cert = saveproof.run_notary(
                root, command, key=os.environ.get("AEOS_PROOF_KEY"))
            path = saveproof.write(
                cert, Path(args.out) if args.out
                else root / "evidence" / "save-proofs")
        except (saveproof.SaveProofError, ValueError, OSError) as exc:
            print(f"SAVE-PROOF — refused: {exc}")
            return 1
        print(f"SAVE-PROOF — outcome: {cert['outcome'].upper()}")
        print(f"  command: {' '.join(cert['command'])}")
        print(f"  pre-root  {cert['pre_root'][:16]}…")
        print(f"  post-root {cert['post_root'][:16]}…")
        print(f"  {cert['files']} file(s), {cert['bytes'] // 1024} KB "
              f"in the proven tree")
        for ev in cert["drift"]["events"]:
            print(f"  DRIFT {ev['change']:<9} {ev['path']}")
        if cert["drift"]["truncated"]:
            print(f"  … and {cert['drift']['total'] - len(cert['drift']['events'])}"
                  " more")
        print(f"  auth: {cert['auth']['scheme']} | certificate: {path}")
        if cert["outcome"] != "verified":
            print("  done is a certificate, not a sentence —"
                  " this one is not done")
        return 0 if cert["outcome"] == "verified" else 1

    if args.cmd == "outbox":
        import sqlite3
        from . import outbox as obx
        if args.outbox_cmd == "enqueue":
            try:
                conn = obx.connect()
                try:
                    r = obx.enqueue(conn, args.endpoint, args.payload,
                                    args.key)
                finally:
                    conn.close()
            except (ValueError, sqlite3.Error, OSError) as exc:
                print(f"OUTBOX — enqueue refused: {exc}")
                return 1
            note = "" if r["created"] else " (already queued — idempotent)"
            print("OUTBOX — buffered locally (offline-safe; nothing left"
                  " the machine)")
            print(f"  record #{r['id']} for {args.endpoint} —"
                  f" {r['status']}{note}")
            print(f"  db: {obx.db_path()}")
            print("  flush later: aeos outbox flush --endpoint URL")
            return 0
        if args.outbox_cmd == "status":
            p = obx.db_path()
            if not p.exists():
                print(f"OUTBOX — no queue at {p} (nothing ever enqueued)")
                return 0
            conn = obx.connect(p)
            try:
                c = obx.counts(conn)
            finally:
                conn.close()
            print(f"OUTBOX — {p}")
            print(f"  pending {c['pending']} | sent {c['sent']} |"
                  f" dead {c['dead']}")
            for ep, n in sorted(c["endpoints"].items()):
                print(f"    {n} pending -> {ep}")
            if c["dead"]:
                print("  dead letters want a human — inspect before flush")
            return 0
        if args.outbox_cmd == "flush":
            try:
                conn = obx.connect()
            except (sqlite3.Error, OSError) as exc:
                print(f"OUTBOX — flush refused: {exc}")
                return 1
            try:
                if args.dry:
                    n = conn.execute(
                        "SELECT COUNT(*) FROM outbox WHERE status ="
                        " 'pending' AND endpoint = ?",
                        (args.endpoint,)).fetchone()[0]
                    print(f"OUTBOX FLUSH (DRY) — {n} row(s) would be POSTed"
                          f" to {args.endpoint}; nothing delivered")
                    return 0
                receipt = obx.drain(conn, obx.deliver_http,
                                    endpoint=args.endpoint,
                                    limit=args.limit)
            finally:
                conn.close()
            print(f"OUTBOX FLUSH — endpoint: {args.endpoint}")
            print(f"  considered {receipt['considered']} | delivered"
                  f" {receipt['delivered']} | failed {receipt['failed']}"
                  f" | dead {receipt['dead']}")
            print(f"  pending remaining: {receipt['remaining_pending']}")
            print("  at-least-once toward the endpoint; exactly-once"
                  " locally; the consumer dedupes on the idem key")
            return 0 if receipt["failed"] == 0 else 1

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
        try:
            r = create_backup(Path(args.workspace), Path(out))
        except OSError as exc:
            print(f"BACKUP REFUSED — the disk would not take it: "
                  f"{exc.strerror or exc}")
            print("  free space or point --out elsewhere; nothing "
                  "was written (atomic contract)")
            return 1
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
        if args.push:
            from .otlp import push_file
            r = push_file(args.push, out)
            verdict = "PUSHED" if r["ok"] else "PUSH REFUSED by the wire"
            print(f"  PUSH {verdict}: {r['pushed']} span(s), "
                  f"{r['attempts']} attempt(s), status={r['status']}")
            if not r["ok"]:
                print(f"  {r['note']}")
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

    if args.cmd == "mcp" and getattr(args, "serve_http", False):
        from .mcp_http import MCPHTTPClient
        from .mcp_http_server import Consulate
        with Consulate(args.bind, args.port) as c:
            print(f"CONSULATE — AEOS over HTTP, read-only by law "
                  f"(ADR-040)")
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
