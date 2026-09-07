"""v37 The Ignition: one front door, staged boot, plain-language failure.

Feedback from the operator, kept verbatim in spirit: the system grew
35+ verbs and gave no single production door — and when a real
environment fails to load (permissions, disk, state from the future,
a missing key, a crashed previous boot), a stack trace is not help.
Production engines are judged at boot, in the dark, by someone in a
hurry.

The answer is an init system, not another feature. `aeos up` runs
four stages — PREFLIGHT (power-on self-test: python, disk, zero-dep
law, writable workspace, state schema, torn writes, locks, live-key
readiness), WORKSPACE (create/heal, upgrade old state in place),
WORK (the reference loop, evidence bundle), SHUTDOWN (a numbered
boot receipt, atomically written, so the NEXT boot can tell you how
the LAST one ended). Exit codes are the language scripts speak:
0 ok · 2 preflight · 3 workspace · 4 work · 5 shutdown.

THE PLAIN-LANGUAGE LAW: every FAIL names WHAT HAPPENED and WHAT TO
DO, in one breath each — never a traceback, never a secret (key
PRESENCE is checked, key VALUES never read into a receipt). A boot
that cannot proceed still leaves a receipt, so the system's own
history explains its own crashes. That is the whole point.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_PREFLIGHT = 2
EXIT_WORKSPACE = 3
EXIT_WORK = 4
EXIT_SHUTDOWN = 5

STAGES = ("preflight", "workspace", "work", "shutdown")

LIVE_KEY_ENVS = ("OPENROUTER_API_KEY", "ABACUS_API_KEY", "OPENAI_API_KEY")


class BootFailure(RuntimeError):
    """A named stage failure with a remedy — the only way boot dies."""

    def __init__(self, stage: str, what: str, remedy: str):
        super().__init__(f"{stage}: {what}")
        self.stage = stage
        self.what = what
        self.remedy = remedy


@dataclass
class Check:
    name: str
    verdict: str            # PASS / WARN / FAIL
    detail: str             # what happened
    remedy: str = ""        # what to do (required for FAIL)

    def as_row(self) -> dict:
        return {"name": self.name, "verdict": self.verdict,
                "detail": self.detail, "remedy": self.remedy}


# ------------------------------------------------------------ stage 1: POST

def post(ws: Path, *, live_requested: bool = False) -> list[Check]:
    """Power-on self-test. Read-only until the writable probe; every
    FAIL must carry a remedy — that is the plain-language law."""
    ws = Path(ws)
    checks: list[Check] = []

    v = sys.version_info
    checks.append(Check(
        "python", "PASS" if v >= (3, 10) else "FAIL",
        f"{v.major}.{v.minor}.{v.micro}",
        "" if v >= (3, 10) else "install Python 3.10 or newer and retry"))

    audit = None
    from .doctor import zero_dep_audit
    audit = zero_dep_audit()
    n_bad = len(audit["violations"])
    checks.append(Check(
        "zero dependencies (ADR-002)", "PASS" if not n_bad else "FAIL",
        f"{audit['modules']} modules scanned, {n_bad} violation(s)",
        "" if not n_bad else
        "a module imported something non-stdlib — report this; "
        "the tree is not the shipped tree"))

    try:
        import shutil
        du = shutil.disk_usage(ws if ws.exists() else ".")
        free_mb = round(du.free / 1_000_000)
    except OSError:
        free_mb = None
    if free_mb is None:
        checks.append(Check("disk", "WARN", "could not measure", ""))
    else:
        verdict = "PASS" if free_mb > 50 else ("WARN" if free_mb >= 10
                                               else "FAIL")
        checks.append(Check(
            "disk", verdict, f"{free_mb}MB free",
            "" if verdict == "PASS" else
            ("low disk — budgets will tighten; `aeos groom` frees run "
             "history" if verdict == "WARN" else
             "disk nearly full — free space or point --workspace "
             "elsewhere; `aeos groom` archives old runs")))

    try:
        ws.mkdir(parents=True, exist_ok=True)
        probe_dir = ws / ".aeos"
        probe_dir.mkdir(parents=True, exist_ok=True)
        # found by the v39.4 gauntlet re-run: a FIXED probe path let
        # two simultaneous boots unlink each other's probe and
        # misreport a writable workspace as unwritable (rc=2 in the
        # concurrent-boot race). Unique per call, cleaned on close.
        import tempfile
        with tempfile.NamedTemporaryFile(dir=probe_dir,
                                         prefix=".boot-probe-",
                                         delete=True) as fh:
            fh.write(b"probe")
        checks.append(Check("workspace writable", "PASS",
                            str(ws), ""))
    except OSError as exc:
        checks.append(Check(
            "workspace writable", "FAIL", f"{ws}: {exc.strerror or exc}",
            "check ownership/permissions of the workspace path, or "
            "point --workspace at a directory you own"))

    mem = ws / ".aeos" / "memory.jsonl"
    if mem.exists():
        from .vault import HEADER_KEY, STATE_SCHEMA, load_jsonl_tolerant
        good, _ = load_jsonl_tolerant(mem)
        hv = good[0].get(HEADER_KEY) if good and HEADER_KEY in good[0] \
            else 1
        if not isinstance(hv, int) or hv > STATE_SCHEMA:
            checks.append(Check(
                "state schema", "FAIL",
                f"memory.jsonl carries schema {hv} — state from the "
                f"future (this aeos supports {STATE_SCHEMA})",
                "upgrade aeos (pip install -U aeos) or point "
                "--workspace at a fresh directory"))
        else:
            checks.append(Check("state schema", "PASS",
                                f"schema {hv}", ""))

    torn = list(ws.glob("**/*.torn"))
    if torn:
        checks.append(Check(
            "torn writes", "WARN",
            f"{len(torn)} quarantined sidecar(s) from a hard cut",
            "already quarantined (the system continued); inspect or "
            "delete *.torn when convenient"))

    lock_path = ws / ".aeos" / "workspace.lock"
    if lock_path.exists():
        from .vault import WorkspaceLock
        lock = WorkspaceLock(lock_path)
        if lock.acquire(blocking=False):
            lock.release()
            checks.append(Check("workspace lock", "PASS",
                                "runnable (no holder)", ""))
        else:
            checks.append(Check(
                "workspace lock", "WARN", "held by a live run",
                "one run per workspace at a time; the lock is "
                "kernel-released, so a dead holder cannot strand you — "
                "wait for the holder or check for a live process"))

    ledger = _last_boot(ws)
    if ledger is not None and ledger.get("outcome") != "ok":
        prev_stage = ledger.get("failed_stage", "-")
        checks.append(Check(
            "previous boot", "WARN",
            f"boot #{ledger.get('boot_seq')} ended: "
            f"{ledger.get('outcome')} (stage: {prev_stage})",
            f"receipt: {ledger.get('receipt', '-')}; state writes are "
            "atomic, so a crashed boot leaves no torn state — this "
            "boot continues"))

    if live_requested:
        have = [e for e in LIVE_KEY_ENVS if os.environ.get(e)]
        if not have:
            checks.append(Check(
                "live key", "FAIL",
                "live mode requested but no provider key found",
                "export one of " + " / ".join(LIVE_KEY_ENVS) +
                " (and AEOS_LIVE=1); keys are never logged"))
        else:
            checks.append(Check("live key", "PASS",
                                f"{len(have)} provider key(s) present "
                                "(values never read into receipts)", ""))

    return checks


# ------------------------------------------------------------ stage 2: ready

def prepare(ws: Path) -> list[str]:
    """Create/heal the workspace. Returns notes — silence is health."""
    ws = Path(ws)
    notes: list[str] = []
    (ws / ".aeos").mkdir(parents=True, exist_ok=True)
    mem = ws / ".aeos" / "memory.jsonl"
    if mem.exists():
        from .groom import upgrade_state
        upgraded = upgrade_state(ws)      # returns the names it healed
        if upgraded:
            notes.append(f"state upgraded in place: "
                         f"{', '.join(sorted(upgraded))}")
    return notes


# ------------------------------------------------------------ the ledger

def _boot_dir(ws: Path) -> Path:
    return Path(ws) / ".aeos" / "boots"


def _last_boot(ws: Path) -> dict | None:
    d = _boot_dir(ws)
    boots = sorted(d.glob("boot-*.json")) if d.exists() else []
    if not boots:
        return None
    import json
    try:
        cert = json.loads(boots[-1].read_text(encoding="utf-8"))
        cert["receipt"] = boots[-1].name
        return cert
    except (OSError, ValueError):
        return None


def _write_receipt(ws: Path, payload: dict) -> Path:
    from .vault import durable_write
    import json
    d = _boot_dir(ws)
    seq = len(list(d.glob("boot-*.json"))) + 1 if d.exists() else 1
    payload["boot_seq"] = seq
    path = d / f"boot-{seq:04d}.json"
    durable_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


# ------------------------------------------------------------ the boot

def boot(ws: Path, intent: str = "Ship a verified seed module",
         *, live: bool = False, save_proof: bool = False,
         profile: str = "balanced") -> dict:
    """The front door. Returns a result dict with an exit_code — the
    CLI prints it, scripts consume it, the ledger remembers it."""
    ws = Path(ws)
    t0 = time.time()
    result = {"kind": "aeos-boot", "stages": [], "checks": [],
              "notes": [], "outcome": "ok", "failed_stage": None,
              "exit_code": EXIT_OK}
    checks: list[Check] = []
    notes: list[str] = []

    def fail(stage: str, exc: BootFailure, code: int) -> dict:
        result.update(outcome=f"{stage}-failed", failed_stage=stage,
                      exit_code=code, what=exc.what, remedy=exc.remedy)
        return result

    # -- stage 1: preflight ------------------------------------------
    try:
        checks = post(ws, live_requested=live)
    except OSError as exc:                       # preflight itself broke
        b = BootFailure("preflight", f"self-test would not run: {exc}",
                        "check the workspace path and retry")
        fail("preflight", b, EXIT_PREFLIGHT)
    else:
        result["checks"] = [c.as_row() for c in checks]
        bad = [c for c in checks if c.verdict == "FAIL"]
        if bad:
            b = BootFailure(
                "preflight",
                "; ".join(f"{c.name}: {c.detail}" for c in bad),
                "; ".join(c.remedy for c in bad if c.remedy))
            fail("preflight", b, EXIT_PREFLIGHT)
        else:
            result["stages"].append("preflight")

            # -- stage 2: workspace ----------------------------------
            try:
                notes = prepare(ws)
                result["notes"] = notes
                result["stages"].append("workspace")
            except OSError as exc:
                fail("workspace",
                     BootFailure("workspace",
                                 f"could not prepare {ws}: "
                                 f"{exc.strerror or exc}",
                                 "check permissions/disk and retry"),
                     EXIT_WORKSPACE)
            else:
                # -- stage 3: work -----------------------------------
                try:
                    from .pipeline import reference_run
                    run = reference_run(ws, intent=intent,
                                        profile=profile)
                    if run.get("accepted") is False:
                        # found by the v39.2 production gauntlet: a
                        # refused run (e.g. the workspace lock is
                        # held) surfaced as an opaque KeyError instead
                        # of the refusal's own plain-language reason
                        raise RuntimeError(
                            run.get("reason", "the run was refused"))
                    result["run"] = {"accepted": run["accepted"],
                                     "leverage": run["leverage"],
                                     "evidence": run["evidence_file"],
                                     "events": run["events_file"]}
                    result["stages"].append("work")
                except Exception as exc:        # named, never traceback
                    fail("work",
                         BootFailure("work",
                                     f"{type(exc).__name__}: {exc}",
                                     "the run left partial evidence in "
                                     f"{ws / '.aeos'}; inspect it, fix "
                                     "the cause, run `aeos up` again — "
                                     "durable writes mean no torn "
                                     "state"),
                         EXIT_WORK)

    # -- stage 4: shutdown (always runs, even after failure) --------
    try:
        result["wall_s"] = round(time.time() - t0, 2)
        if result["outcome"] == "ok":
            result["stages"].append("shutdown")
        receipt = _write_receipt(ws, result)
        result["receipt"] = str(receipt)
        if save_proof:
            from .doctor import repo_root
            root = repo_root()
            if root is None:
                result["save_proof"] = ("skipped — no checkout context, "
                                        "not guessed (the boot itself "
                                        "was completed and receipted)")
            else:
                from .saveproof import (SaveProofError, run_notary,
                                        write)
                try:
                    cert = run_notary(root)
                    write(cert, root / "evidence" / "save-proofs")
                    result["save_proof"] = (f"{cert['outcome']} — "
                                            f"{cert['post_root'][:12]}")
                except SaveProofError as exc:
                    result["save_proof"] = f"skipped — {exc}"
    except OSError as exc:
        # the FIRST failure is the truth; a receipt that cannot write
        # is appended, never allowed to overwrite the original cause
        result["receipt_unwritten"] = f"{exc.strerror or exc}"
        if result["outcome"] == "ok":
            result["stages"] = [s for s in result["stages"]
                                if s != "shutdown"]
            result.update(
                outcome="shutdown-failed", failed_stage="shutdown",
                exit_code=EXIT_SHUTDOWN,
                what=f"receipt would not write: {exc}",
                remedy="check disk space and permissions on the "
                       "workspace — the work itself already finished")
    return result


# ------------------------------------------------------------ rendering

def render(result: dict) -> str:
    """Human speech: stages on the way up, remedy in one breath on
    the way down."""
    stages = result.get("stages", [])
    n_checks = len(result.get("checks", []))
    n_pass = sum(1 for c in result.get("checks", [])
                 if c["verdict"] == "PASS")
    n_warn = sum(1 for c in result.get("checks", [])
                 if c["verdict"] == "WARN")
    lines = ["IGNITION — 4 stages: preflight · workspace · work ·"
             " shutdown"]

    if result["outcome"] == "ok":
        w = f"{n_warn} warn — continuing" if n_warn else "all clear"
        lines.append(f"  [1/4] PREFLIGHT   {n_checks} check(s): "
                     f"{n_pass} pass, {w}")
        notes = result.get("notes") or []
        lines.append(f"  [2/4] WORKSPACE   ready"
                     + (f" ({'; '.join(notes)})" if notes else ""))
        run = result.get("run", {})
        lines.append(f"  [3/4] WORK        accepted — leverage "
                     f"{run.get('leverage')}, evidence bundle written")
        sp = result.get("save_proof")
        if sp:
            lines.append(f"        SAVE-PROOF  {sp}")
        lines.append(f"  [4/4] SHUTDOWN    boot receipt -> "
                     f"{result.get('receipt', '-')}")
        lines.append(f"BOOT — outcome: OK (wall {result.get('wall_s')}s)")
    else:
        stage = result.get("failed_stage", "?")
        idx = STAGES.index(stage) + 1 if stage in STAGES else "?"
        lines.append(f"IGNITION FAILED at stage {idx}/4 ({stage})")
        lines.append(f"  what happened: {result.get('what')}")
        lines.append(f"  what to do:    {result.get('remedy')}")
        lines.append(f"  boot receipt:  {result.get('receipt', '-')}")
        if result.get("receipt_unwritten"):
            lines.append(f"  receipt could not be written "
                         f"({result['receipt_unwritten']}) — this "
                         "screen is the record; fix disk/permissions")
        lines.append("  exit code "
                     f"{result.get('exit_code')} — scripts can branch "
                     "on the stage; the receipt carries the same words")
    return "\n".join(lines)
