"""v39 The Foreman: the shop runs itself between visits.

The operator's direction, kept verbatim in spirit: stop shipping
paper — produce a production-grade autonomous agentic system, in the
Omarchy tradition: one command, opinionated defaults, curated whole.
The harness already had every muscle (audits, groom, backup drills,
the notary, the boot ledger); what it lacked was the agent that
USES them. This is that agent.

THE LOOP (perceive -> plan -> act -> verify -> remember):
  perceive — survey the workspace: torn writes, old schema, run
             retention, backup posture, the boot ledger, the
             machine outbox, and (in a checkout) README drift and
             the save-proof ledger. Findings are facts, not vibes.
  plan     — every finding becomes a task, classified HONESTLY:
             MECHANICAL (safe, deterministic, reversible — the
             foreman may do it) or PROPOSAL (needs a human — filed,
             never silently attempted).
  act      — only with --apply, only the mechanical class, in a
             fixed dependency order (schema -> torn -> groom ->
             backup-drill: heal first, then capture the healed
             state). Safe by default: survey is the mode.
  verify   — re-survey after acting; findings that survive their
             own remedy are named. The receipt carries pre/post
             Merkle roots of the workspace — what the foreman did
             to your state is cryptographically visible.
  remember — an append-only history ledger, deduped by finding
             signature, so recurring findings are a pattern, not a
             surprise. No clocks in artifacts (determinism law):
             sequence numbers are time.

BOUNDARIES: the foreman writes ONLY inside the workspace (and its
own receipts); every write is atomic; an action that fails stops
the run with a named receipt — never a partial silence. Exit codes:
0 clean/resolved · 1 attention (findings remain) · 2 hard failure.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .backup import BackupError, create_backup, restore_backup
from .groom import groom as groom_sweep
from .groom import upgrade_state
from .merkle import snapshot
from .vault import durable_write, load_jsonl_tolerant

EXIT_CLEAN = 0
EXIT_ATTENTION = 1
EXIT_FAILED = 2

KEEP_RUNS = 10                      # convention over configuration
APPLY_ORDER = ("schema-upgrade", "torn-archive", "groom",
               "backup-drill")      # heal first, then capture


class Finding:
    def __init__(self, kind, detail, remedy, klass, name=None,
                 severity="work"):
        self.kind = kind            # machine id, stable
        self.detail = detail
        self.remedy = remedy
        self.klass = klass          # "mechanical" | "proposal"
        self.name = name or kind
        self.severity = severity    # "work" | "attention"

    def signature(self) -> str:
        return hashlib.sha256(
            f"{self.kind}\x00{self.klass}".encode("utf-8")).hexdigest()

    def as_row(self) -> dict:
        return {"kind": self.kind, "name": self.name,
                "detail": self.detail, "remedy": self.remedy,
                "class": self.klass, "severity": self.severity}


# ------------------------------------------------------------ perceive

def _last_boot(ws: Path) -> dict | None:
    d = ws / ".aeos" / "boots"
    boots = sorted(d.glob("boot-*.json")) if d.exists() else []
    if not boots:
        return None
    try:
        return json.loads(boots[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def survey(ws: Path, *, repo: Path | None = None) -> list[Finding]:
    """The perception pass — findings are facts with remedies."""
    ws = Path(ws)
    out: list[Finding] = []

    mem = ws / ".aeos" / "memory.jsonl"
    if mem.exists():
        good, _ = load_jsonl_tolerant(mem)
        from .vault import HEADER_KEY, STATE_SCHEMA
        hv = good[0].get(HEADER_KEY) if good and HEADER_KEY in good[0] \
            else None
        if hv != STATE_SCHEMA:
            out.append(Finding(
                "state-schema",
                f"state carries schema {hv} (current: {STATE_SCHEMA})",
                "upgrade in place (headers rewritten, content kept)",
                "mechanical", "state schema"))

    torn = sorted(t for t in ws.glob("**/*.torn")
                  if "torn-archive" not in t.relative_to(ws).parts)
    if torn:
        out.append(Finding(
            "torn-writes",
            f"{len(torn)} quarantined sidecar(s) from hard cuts",
            "archive into .aeos/torn-archive (content-hashed names)",
            "mechanical", "torn writes"))

    runs = ws / ".aeos" / "runs"
    n_runs = len(list(runs.glob("*-events.jsonl"))) if runs.exists() else 0
    if n_runs > KEEP_RUNS:
        out.append(Finding(
            "retention",
            f"{n_runs} run files kept (convention: {KEEP_RUNS})",
            f"groom archives {n_runs - KEEP_RUNS} (archives, never deletes)",
            "mechanical", "retention"))

    has_state = mem.exists() or (ws / ".aeos" / "events.jsonl").exists()
    backups = ws / ".aeos" / "backups"
    n_backups = len(list(backups.glob("*.tar"))) if backups.exists() else 0
    if has_state and n_backups == 0:
        out.append(Finding(
            "backup-posture",
            "state exists but no backup on record",
            "deterministic backup + restore drill (verify, then keep)",
            "mechanical", "backup"))

    boot = _last_boot(ws)
    if boot is not None and boot.get("outcome") != "ok":
        stage = boot.get("failed_stage", "-")
        out.append(Finding(
            "boot-ledger",
            f"boot #{boot.get('boot_seq')} ended "
            f"{boot.get('outcome')} (stage {stage})",
            "inspect the receipt; atomic writes left nothing torn — "
            "this is attention, not damage",
            "proposal", "previous boot", severity="attention"))

    from .outbox import health as outbox_health
    verdict, detail = outbox_health()
    if verdict != "PASS":
        out.append(Finding(
            "outbox", detail,
            "dead letters want a human; inspect before any flush",
            "proposal", "edge outbox", severity="attention"))

    if repo is not None:
        from .scribe import audit as scribe_audit
        rep = scribe_audit(repo, ("README.md",))
        if rep.drift:
            out.append(Finding(
                "readme-drift",
                f"{len(rep.drift)} README claim(s) drifted",
                "documentation is the author's craft — filed, not "
                "auto-edited",
                "proposal", "README drift", severity="attention"))
        sp = repo / "evidence" / "save-proofs"
        certs = sorted(sp.glob("save-proof-*.json")) if sp.exists() else []
        from .saveproof import verify as sp_verify
        bad = 0
        for c in certs:
            try:
                ok, _ = sp_verify(json.loads(c.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                ok = False
            bad += 0 if ok else 1
        if bad:
            out.append(Finding(
                "proof-ledger", f"{bad}/{len(certs)} certificate(s) "
                "fail verification",
                "a tampered receipt is grave — investigate immediately",
                "proposal", "save-proof ledger", severity="attention"))

    out.sort(key=lambda f: (f.klass != "mechanical", f.kind))
    return out


# ------------------------------------------------------------ act

ACTION_FOR = {"state-schema": "schema-upgrade",
              "torn-writes": "torn-archive",
              "retention": "groom",
              "backup-posture": "backup-drill"}


def _append_durable(path: Path, text: str) -> None:
    """Append + fsync: one write, one flush. A crash mid-append
    leaves a torn tail — which load_jsonl_tolerant quarantines by
    design; the history is a log, not a ledger of record."""
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())


def _torn_archive(ws: Path) -> dict:
    dest = ws / ".aeos" / "torn-archive"
    dest.mkdir(parents=True, exist_ok=True)
    moved = []
    for t in sorted(ws.glob("**/*.torn")):
        if dest in t.parents:
            continue
        digest = hashlib.sha256(t.read_bytes()).hexdigest()[:12]
        target = dest / f"{t.stem}-{digest}.torn"
        t.rename(target)
        moved.append(target.name)
    return {"ok": True, "detail": f"{len(moved)} archived -> "
            f".aeos/torn-archive"}


def _backup_drill(ws: Path) -> dict:
    backups = ws / ".aeos" / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    seq = len(list(backups.glob("*.tar"))) + 1
    out = backups / f"foreman-{seq:04d}.tar"
    created = create_backup(ws, out)
    drill_dir = tempfile.mkdtemp(prefix="foreman-drill-")
    try:
        restored = restore_backup(out, Path(drill_dir) / "ws")
        ok = restored["sha256"] == created["sha256"]
        return {"ok": ok, "detail": (
            f"backup {created['sha256'][:12]}… — restore drill "
            f"verified {restored['files']} member(s)"
            if ok else
            f"DRILL FAILED: restore sha mismatch on {out.name}")}
    except BackupError as exc:
        return {"ok": False, "detail": f"DRILL FAILED: {exc}"}
    finally:
        shutil.rmtree(drill_dir, ignore_errors=True)


ACTIONS = {
    "schema-upgrade": lambda ws: {
        "ok": True,
        "detail": (", ".join(upgrade_state(ws)) or
                   "nothing to upgrade")},
    "torn-archive": lambda ws: _torn_archive(ws),
    "groom": lambda ws: {
        "ok": True,
        "detail": (
            lambda r: f"{r['runs_archived']} run(s) archived, "
            f"{r['runs_kept']} kept" if r.get("runs_archived")
            else "nothing to archive")(groom_sweep(ws, KEEP_RUNS))},
    "backup-drill": lambda ws: _backup_drill(ws),
}


def apply(ws: Path, findings: list[Finding]) -> list[dict]:
    """Execute the MECHANICAL class in fixed order. A failure stops
    the run — the foreman never continues past a broken action."""
    ws = Path(ws)
    wanted = {ACTION_FOR[f.kind] for f in findings
              if f.klass == "mechanical" and f.kind in ACTION_FOR}
    acted = []
    for name in APPLY_ORDER:
        if name not in wanted:
            continue
        try:
            result = ACTIONS[name](ws)
        except OSError as exc:
            # found by the v39.2 production gauntlet: file-size
            # starvation escaped as a raw traceback. The plain-
            # language law applies to the agent too — name it, stop.
            result = {"ok": False,
                      "detail": f"{name} failed: "
                                f"{exc.strerror or exc}"}
        acted.append({"action": name, **result})
        if not result["ok"]:
            break
    return acted


# ------------------------------------------------------------ remember

def _history_path(ws: Path) -> Path:
    return ws / ".aeos" / "foreman" / "history.jsonl"


def remember(ws: Path, findings: list[Finding], status: str) -> dict:
    """Append-only, signature-deduped memory: recurring findings are
    a pattern. Returns the count for the most recent signature."""
    p = _history_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    entries, _ = load_jsonl_tolerant(p)
    counts = {}
    for e in entries:
        counts[(e.get("sig"), e.get("status"))] = e.get("count", 1)
    last = None
    for f in sorted(findings, key=lambda x: x.kind):
        key = (f.signature(), status)
        n = counts.get(key, 0) + 1
        counts[key] = n
        entry = {"kind": f.kind, "sig": f.signature(), "status": status,
                 "count": n}
        _append_durable(p, json.dumps(entry, sort_keys=True) + "\n")
        last = entry
    return last or {}


def run(ws: Path, *, apply_mode: bool = False,
        repo: Path | None = None) -> dict:
    """The whole loop, receipted. Exit codes are a contract."""
    ws = Path(ws)
    from .vault import WorkspaceLock
    lock = WorkspaceLock(ws / ".aeos" / "workspace.lock")
    if not lock.acquire(blocking=False):
        # found by the v39.2 production gauntlet: two foremen could
        # race on the same workspace. One operator at a time — the
        # lock is kernel-released, a dead holder cannot strand you.
        return {"kind": "aeos-foreman", "mode": "survey",
                "findings": [], "actions": [], "resolved": 0,
                "remaining": 0, "pre_root": None, "post_root": None,
                "exit_code": EXIT_FAILED,
                "failure": "workspace is locked by a live run "
                           "(kernel-released; a dead holder cannot "
                           "strand you)",
                "seq": len(list((ws / ".aeos" / "foreman")
                                .glob("foreman-*.json"))) + 1
                if (ws / ".aeos" / "foreman").exists() else 1}
    try:
        return _run_locked(ws, apply_mode=apply_mode, repo=repo)
    finally:
        lock.release()


def _run_locked(ws: Path, *, apply_mode: bool = False,
                repo: Path | None = None) -> dict:
    pre = survey(ws, repo=repo)
    result = {"kind": "aeos-foreman", "mode": ("apply" if apply_mode
                                               else "survey"),
              "findings": [f.as_row() for f in pre],
              "actions": [], "resolved": 0, "remaining": len(pre),
              "pre_root": snapshot(ws)["root"], "post_root": None,
              "exit_code": EXIT_CLEAN}

    if apply_mode and any(f.klass == "mechanical" for f in pre):
        result["actions"] = apply(ws, pre)
        if any(not a["ok"] for a in result["actions"]):
            result.update(exit_code=EXIT_FAILED,
                          failure="an action failed — stopped, "
                                  "receipted, nothing hidden")
        post = survey(ws, repo=repo)
        fixed = {f.kind for f in pre if f.klass == "mechanical"}
        result["resolved"] = sum(1 for k in fixed if k not in
                                 {g.kind for g in post})
        result["remaining"] = len(post)
        result["post_root"] = snapshot(ws)["root"]
    if result["post_root"] is None:
        # no actions ran: the receipt still carries both roots —
        # pre and post of the SAME state, evidence nothing moved
        result["post_root"] = snapshot(ws)["root"]

    if result["exit_code"] == EXIT_CLEAN and result["remaining"]:
        result["exit_code"] = EXIT_ATTENTION

    status = ("resolved" if result["resolved"] and
              not result["remaining"] else
              "clean" if not result["remaining"] else "open")
    remember(ws, pre, status)
    d = ws / ".aeos" / "foreman"
    d.mkdir(parents=True, exist_ok=True)
    seq = len(list(d.glob("foreman-*.json"))) + 1
    result["seq"] = seq
    durable_write(d / f"foreman-{seq:04d}.json",
                  json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


# ------------------------------------------------------------ render

def render(result: dict) -> str:
    if result.get("pre_root") is None and result.get("failure"):
        # the busy refusal: no findings, no receipt (the lock holder
        # owns the workspace) — named, one breath, done
        return ("FOREMAN — refused: " + result["failure"] +
                "\n  wait for the holder or check for a live process; "
                "exit code " + str(result["exit_code"]))
    rows = result["findings"]
    mech = [r for r in rows if r["class"] == "mechanical"]
    prop = [r for r in rows if r["class"] == "proposal"]
    lines = [f"FOREMAN — {result['mode']}: {len(rows)} finding(s) — "
             f"{len(mech)} mechanical, {len(prop)} proposal"]
    for r in rows:
        tag = "mech" if r["class"] == "mechanical" else "prop"
        lines.append(f"  [{tag}] {r['name']:<16} {r['detail']}")
        if r["class"] == "proposal":
            lines.append(f"        what to do: {r['remedy']}")
    if result["mode"] == "survey" and mech:
        lines.append("  apply order: " + " -> ".join(APPLY_ORDER))
        lines.append("  run `aeos foreman --apply` to execute the "
                     "mechanical class; proposals stay human")
    for a in result["actions"]:
        mark = "ok" if a["ok"] else "FAILED"
        lines.append(f"  [{mark}] {a['action']:<14} {a['detail']}")
    if result["actions"]:
        lines.append(f"  verification: {result['resolved']} finding(s) "
                     f"resolved, {result['remaining']} remain")
        pre, post = result["pre_root"], result["post_root"]
        if post:
            lines.append(f"  workspace root {pre[:12]} -> {post[:12]}"
                         + (" (unchanged)" if pre == post else ""))
    lines.append(f"  receipt: .aeos/foreman/foreman-"
                 f"{result['seq']:04d}.json")
    verdict = {EXIT_CLEAN: "CLEAN", EXIT_ATTENTION: "ATTENTION",
               EXIT_FAILED: "FAILED"}[result["exit_code"]]
    lines.append(f"FOREMAN — outcome: {verdict} (exit "
                 f"{result['exit_code']})")
    return "\n".join(lines)
