"""aeos.cli_operate — the OPERATE surface (ADR-057): keep the machine running. Behavior moved verbatim from cli.py."""

from __future__ import annotations

import json
import os
import shlex
import time
from pathlib import Path


def dispatch(args) -> int:
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
        print("BACKUP — deterministic, manifest-verified")
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
    print(f"FRONT DOOR — no handler for {args.cmd!r}; this is a bug")
    return 2
