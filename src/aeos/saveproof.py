"""v36 The Notary, part 2: "done" is a certificate, not a sentence.

SEF-X handover Law 5 / Tier 4 / FR-04 (adopted, honestly scoped): no
task completes on conversational confirmation. `save-proof` captures
the pre-state Merkle root, runs the proof command, captures the
post-state root, and emits a certificate into the ledger
(evidence/save-proofs/). VERIFIED means both roots are equal AND the
command exited 0 — the proof ran clean and left no unproven state
behind. Anything else is NAMED, never narrated: "drifted" lists the
files, "tests-failed" carries the exit code, "timed-out" says so.

Honest scope (ADR-045): the stdlib ceiling is sha256, so the default
auth is a self-digest — tamper-EVIDENT, not origin-authentic; set
AEOS_PROOF_KEY and it upgrades to HMAC-SHA256 between parties who
share the key (asymmetric signatures need a dependency: rejected).
The certificate carries NO timestamps — determinism is law; time
lives in the receipt around the artifact, never inside it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from .merkle import diff, snapshot
from .vault import durable_write

SCHEMA = 1
PROOF_COMMAND = ["python", "-m", "pytest", "tests/", "-q"]   # as recorded
COMMAND_TIMEOUT_S = 1800


class SaveProofError(RuntimeError):
    """The certificate is malformed or the ledger is unwritable."""


def capture(root: Path) -> dict:
    return snapshot(root)


def _canonical(cert: dict) -> bytes:
    return json.dumps(cert, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def authenticate(cert: dict, key: str | None = None) -> dict:
    """Bind the certificate to its own bytes. sha256 (default) makes
    any later edit detectable; HMAC-SHA256 (key) additionally proves
    WHO signed it — to everyone else the digest is noise."""
    body = {k: v for k, v in cert.items() if k != "auth"}
    if key:
        digest = hmac.new(key.encode("utf-8"), _canonical(body),
                          hashlib.sha256).hexdigest()
        scheme = "hmac-sha256"
    else:
        digest = hashlib.sha256(_canonical(body)).hexdigest()
        scheme = "sha256"
    cert["auth"] = {"scheme": scheme, "digest": digest}
    return cert


def _outcome(exit_code: int | None, drift_total: int,
             timed_out: bool) -> str:
    if timed_out:
        return "timed-out"
    failed = exit_code != 0
    drifted = drift_total > 0
    if failed and drifted:
        return "drifted-and-failed"
    if failed:
        return "tests-failed"
    if drifted:
        return "drifted"
    return "verified"


def run_notary(root: Path, command: list[str] | None = None,
               *, key: str | None = None) -> dict:
    """Pre-root, proof command, post-root, certificate. The command
    runs without a shell, bounded in time, from the tree it proves."""
    root = Path(root)
    from . import __version__
    cmd = list(command) if command is not None else list(PROOF_COMMAND)
    exec_cmd = cmd
    if cmd == PROOF_COMMAND:               # run the suite with THIS python
        exec_cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]

    pre = capture(root)
    timed_out, exit_code = False, None
    env = dict(os.environ, PYTEST_ADDOPTS="")   # mirror CI: no -qq surprise
    try:
        proc = subprocess.run(exec_cmd, cwd=str(root), env=env,
                              capture_output=True, text=True,
                              timeout=COMMAND_TIMEOUT_S)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    except OSError as exc:
        raise SaveProofError(f"proof command would not run: {exc}") from exc
    post = capture(root)

    drift = diff(pre, post)
    cert = {
        "schema": SCHEMA,
        "kind": "aeos-save-proof",
        "aeos_version": __version__,
        "command": cmd,
        "test_exit": exit_code,
        "outcome": _outcome(exit_code, drift["total"], timed_out),
        "pre_root": pre["root"],
        "post_root": post["root"],
        "files": post["files"],
        "bytes": post["bytes"],
        "drift": drift,
        "merkle": ("sha256; path-bound leaves; pairwise nodes; "
                   "odd promoted; volatile trees excluded"),
    }
    return authenticate(cert, key)


def write(cert: dict, dest_dir: Path) -> Path:
    """Append to the ledger, atomically (tmp + fsync + rename)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"save-proof-{cert['post_root'][:12]}-{cert['outcome']}.json"
    text = json.dumps(cert, indent=2, sort_keys=True) + "\n"
    return durable_write(dest_dir / name, text)


def verify(cert: dict, *, root: Path | None = None,
           key: str | None = None) -> tuple[bool, str]:
    """A certificate is believed only when its bytes, its arithmetic,
    and (optionally) the live tree agree. Anything else: refused."""
    if not isinstance(cert, dict) or cert.get("kind") != "aeos-save-proof":
        return False, "not an aeos save-proof certificate"
    auth = cert.get("auth")
    if not isinstance(auth, dict) or "digest" not in auth:
        return False, "certificate carries no authentication"
    body = {k: v for k, v in cert.items() if k != "auth"}
    if auth.get("scheme") == "hmac-sha256":
        if not key:
            return False, "hmac certificate but no key provided"
        expect = hmac.new(key.encode("utf-8"), _canonical(body),
                          hashlib.sha256).hexdigest()
    else:
        expect = hashlib.sha256(_canonical(body)).hexdigest()
    if not hmac.compare_digest(expect, auth["digest"]):
        return False, "digest mismatch — the certificate was edited"
    if cert.get("outcome") == "verified":
        if cert.get("test_exit") != 0 or cert["pre_root"] != cert["post_root"]:
            return False, "claims verified but the arithmetic disagrees"
    if root is not None:
        live = snapshot(Path(root))["root"]
        if live != cert.get("post_root"):
            return False, "the tree no longer matches the certificate"
    return True, "bytes, arithmetic, and tree agree"
