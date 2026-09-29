"""aeos CLI — the front door (ADR-057: the Front Door Diet).

The door is thin: it builds the parser, prints the grouped menu on
bare `aeos`, and routes to the four surface modules — cli_run,
cli_inspect, cli_operate, cli_extend — where the behavior lives.
One door, four rooms; no room knows about the door.
"""

from __future__ import annotations

import argparse
import sys


_RUN = ('run', 'up', 'run-demo', 'foreman', 'graph', 'factory-demo', 'colony', 'resume', 'soak')
_INSPECT = ('doctor', 'scribe', 'triangle', 'leverage-audit', 'dividend', 'recall', 'bench', 'telemetry', 'eval', 'selftest')
_OPERATE = ('backup', 'restore', 'groom', 'storm', 'vault', 'save-proof', 'outbox', 'dashboard', 'console', 'stream')
_EXTEND = ('sponsor', 'mcp', 'otel', 'companions', 'federation-demo', 'hooks', 'holdout', 'standards', 'fleet', 'live-check')
_SURFACES = (("RUN", _RUN), ("INSPECT", _INSPECT),
             ("OPERATE", _OPERATE), ("EXTEND", _EXTEND))


def _menu() -> None:
    """Bare `aeos` prints the grouped front door, not argparse noise."""
    from . import __version__
    print(f"AEOS — the AI Engineering OS (v{__version__})")
    print("  aeos COMMAND [options] — --help on any command")
    print()
    for label, cmds in _SURFACES:
        print(f"  {label:<9} " + "  ".join(cmds))
    print()
    print("  the spine: aeos run --graph plan.dot --style routing.style")


def _build_parser() -> argparse.ArgumentParser:
    """The whole front door, declaratively: 39 commands in four
    surfaces. Split out of main() so the diet's own tests can hold
    the registration honest (every command on the menu, every menu
    entry routed)."""
    parser = argparse.ArgumentParser(
        prog="aeos",
        description="AI Engineering OS — reference pipeline and inspection tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    parser = argparse.ArgumentParser(
        prog="aeos",
        description="AI Engineering OS — reference pipeline and inspection tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    spine_p = sub.add_parser(
        "run",
        help="v39.8: THE SPINE — one command end-to-end: the reference "
             "objective or --graph plan.dot on the REFERENCE pipeline "
             "(no demo path); events stream live to the shopfloor")
    spine_p.add_argument("--workspace", default="aeos-demo")
    spine_p.add_argument("--intent", default=None,
                         help="the operator's objective "
                              "(default: the reference objective)")
    spine_p.add_argument("--graph", default=None, metavar="DOT",
                         help="a DOT workflow (e.g. examples/ship-graph.dot)")
    spine_p.add_argument("--style", default=None,
                         help="routing stylesheet for --graph")
    spine_p.add_argument("--profile", default="balanced",
                         choices=["control", "balanced", "speed", "cost"],
                         help="the control-cost-speed stance for this run")

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
    obx_sub.add_parser("status", help="queue counts — no side effects")
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
    gr_p.add_argument("--workspace", default="aeos-demo")
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

    sub.add_parser("colony", help="v25: explicit graph orchestration demo")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        _menu()            # the front door, grouped (ADR-057)
        return 2
    args = _build_parser().parse_args(argv)

    # the diet: route to the surface that owns this command
    if args.cmd in _RUN:
        from .cli_run import dispatch
    elif args.cmd in _INSPECT:
        from .cli_inspect import dispatch
    elif args.cmd in _OPERATE:
        from .cli_operate import dispatch
    else:
        from .cli_extend import dispatch
    return dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
