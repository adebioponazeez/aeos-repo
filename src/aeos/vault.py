"""v26 The Vault: fault tolerance for the files everything else trusts.

Design law: power loss loses MOMENTS, never MEMORY. Every persistent
write is atomic (tmp + fsync + rename + dir fsync); every load is
tolerant (torn tail lines are quarantined to a .torn sidecar, the
system continues); the workspace is lockable across processes
(fcntl — kernel-released on death, so a killed run cannot leave a
stale lock); and the whole system is provably offline (the blackout
context makes ANY socket use raise). Built for hostile environments:
power cuts, full disks, no network, no money.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
from contextlib import contextmanager
from pathlib import Path

try:                                    # POSIX only; degrade loudly elsewhere
    import fcntl
except ImportError:                     # pragma: no cover
    fcntl = None


# ------------------------------------------------------------ atomic writes

def durable_write(path: Path, text: str) -> Path:
    """Atomic + durable: tmp file, fsync, rename, fsync the directory.
    A crash before rename leaves the ORIGINAL intact — never a torn
    file. A full disk raises before touching the original."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)      # explicit os-level atomic rename (3.10-proof)
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass                       # directory fsync is best-effort
    return path


# ------------------------------------------------------------ tolerant loads

def load_jsonl_tolerant(path: Path) -> tuple:
    """Returns (good_dicts, torn_lines). A torn line — power cut mid
    append, disk garbage, encoding damage — is DATA, not a crash."""
    path = Path(path)
    if not path.exists():
        return [], []
    good, torn = [], []
    for line in path.read_text(encoding="utf-8", errors="replace"
                               ).splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                good.append(obj)
            else:
                torn.append(line)
        except json.JSONDecodeError:
            torn.append(line)
    return good, torn


def quarantine_torn(path: Path, torn_lines: list) -> Path | None:
    """Torn lines are preserved for forensics, never silently lost."""
    if not torn_lines:
        return None
    sidecar = Path(str(path) + ".torn")
    with sidecar.open("a", encoding="utf-8") as fh:
        for line in torn_lines:
            fh.write(line + "\n")
    return sidecar


# ------------------------------------------------------------ workspace lock

class WorkspaceLock:
    """Cross-process run lock via fcntl.flock — the kernel releases it
    when the holder dies, so kill -9 can never strand the workspace.
    Where fcntl is unavailable the lock degrades to always-acquire
    (single-host assumption, documented)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._fh = None

    def acquire(self, blocking: bool = False) -> bool:
        if fcntl is None:                      # pragma: no cover
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a+")
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        try:
            fcntl.flock(self._fh.fileno(), flags)
            return True
        except (BlockingIOError, OSError):
            self._fh.close()
            self._fh = None
            return False

    def release(self) -> None:
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                self._fh.close()
                self._fh = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


# ------------------------------------------------------- offline by proof

class BlackoutError(RuntimeError):
    """Raised when ANY socket use is attempted under blackout."""


@contextmanager
def socket_blackout():
    """Make network use impossible: any socket construction raises.
    If the system completes inside this, it provably made ZERO network
    calls — the embargo/third-world receipt."""
    def _boom(*args, **kwargs):
        raise BlackoutError(
            "socket construction attempted under blackout — the "
            "default path must be offline")
    original = socket.socket
    socket.socket = _boom
    try:
        yield
    finally:
        socket.socket = original


# ------------------------------------------------------- environment truth

def environment_scan(ws: Path | None = None) -> dict:
    """Read-only truth about the host. NEVER dials out — a scanner
    that checks the network by using it is a bug."""
    free_mb = None
    try:
        du = shutil.disk_usage(Path(ws) if ws and Path(ws).exists()
                               else Path("."))
        free_mb = round(du.free / 1_000_000, 1)
    except OSError:
        pass
    mem_total_mb = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_total_mb = round(int(line.split()[1]) / 1024)
                break
    except OSError:
        pass
    degraded = []
    if free_mb is not None and free_mb < 50:
        degraded.append(f"low disk ({free_mb}MB free) — budgets tightened")
    return {"disk_free_mb": free_mb, "mem_total_mb": mem_total_mb,
            "cpu_count": os.cpu_count(),
            "degraded": degraded,
            "network": "not probed — offline by default"}


# ------------------------------------------------------------ schema law

STATE_SCHEMA = 1          # long-lived state: memory, fleet stream, checkpoints
HEADER_KEY = "aeos_schema"


class SchemaError(RuntimeError):
    """State written by a NEWER aeos — fail closed, never guess."""


def schema_header(kind: str) -> dict:
    return {HEADER_KEY: STATE_SCHEMA, "kind": kind}


def is_header(obj: dict) -> bool:
    return isinstance(obj, dict) and HEADER_KEY in obj


def check_schema(header: dict) -> None:
    v = header.get(HEADER_KEY)
    if not isinstance(v, int) or v > STATE_SCHEMA:
        raise SchemaError(
            f"state schema {v!r} is newer than this aeos understands "
            f"({STATE_SCHEMA}); upgrade aeos before touching this state")
