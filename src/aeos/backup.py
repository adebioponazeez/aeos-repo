"""v29 Backup/Restore: backups are drilled, not assumed.

A backup that was never restored is a hope. Law: a backup is a
deterministic tar (sorted members, fixed metadata) carrying a sha256
manifest; a restore verifies EVERY member against the manifest and
REFUSES on any mismatch (fail closed — a corrupt backup restores
nothing, never something wrong); caches are skipped (the recall index
is REBUILT on restore, proving it is rebuildable); locks are never
carried (a restored lock would be stale by definition).
"""
from __future__ import annotations

import hashlib
import json
import tarfile
import time
from pathlib import Path

from .vault import STATE_SCHEMA, SchemaError

EXCLUDE_NAMES = {"workspace.lock"}
EXCLUDE_SUFFIXES = (".tmp", ".lock")
CACHE_NAMES = {"recall.sqlite"}          # rebuilt on restore, never carried


class BackupError(RuntimeError):
    """Backup corrupt or incompatible — restore refuses, fail closed."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _collect(ws: Path) -> list:
    """Deterministic member list: workspace files worth keeping."""
    members = []
    std = ws / "STANDARDS.md"
    if std.exists():
        members.append(std)
    aeos = ws / ".aeos"
    if aeos.exists():
        for p in sorted(aeos.rglob("*")):
            if not p.is_file():
                continue
            if p.name in EXCLUDE_NAMES or p.name.endswith(EXCLUDE_SUFFIXES):
                continue
            if p.name in CACHE_NAMES:
                continue
            members.append(p)
    return members


def create_backup(ws: Path, out: Path) -> dict:
    ws = Path(ws)
    out = Path(out)
    members = _collect(ws)
    if not members:
        raise BackupError("nothing to back up: no .aeos state, no STANDARDS.md")

    # the artifact carries ONLY what verification needs — no clocks, no
    # paths — so identical state yields byte-identical backups
    manifest = {"aeos_schema": STATE_SCHEMA, "kind": "aeos-backup",
                "files": {}}
    blobs = {}
    for p in members:
        data = p.read_bytes()
        rel = p.relative_to(ws).as_posix()
        manifest["files"][rel] = _sha256_bytes(data)
        blobs[rel] = data

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    with tarfile.open(tmp, "w", format=tarfile.PAX_FORMAT) as tar:
        for rel in sorted(blobs):          # sorted + fixed meta = deterministic
            data = blobs[rel]
            info = tarfile.TarInfo(rel)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, __import__("io").BytesIO(data))
        mdata = json.dumps(manifest, sort_keys=True).encode("utf-8")
        minfo = tarfile.TarInfo("manifest.json")
        minfo.size = len(mdata)
        minfo.mtime = 0
        minfo.mode = 0o644
        tar.addfile(minfo, __import__("io").BytesIO(mdata))
    tmp.replace(out)                        # atomic: no half-written backups

    return {"path": str(out), "files": len(members),
            "bytes": sum(len(b) for b in blobs.values()),
            "sha256": _sha256_bytes(out.read_bytes())}


def restore_backup(backup: Path, ws: Path) -> dict:
    backup = Path(backup)
    ws = Path(ws)
    if not backup.exists():
        raise BackupError(f"no backup at {backup}")

    lock = ws / ".aeos" / "workspace.lock"
    if lock.exists():
        from .vault import WorkspaceLock
        probe = WorkspaceLock(lock)
        if not probe.acquire(blocking=False):
            raise BackupError("workspace is locked by a live run; "
                              "restore refuses")
        probe.release()

    with tarfile.open(backup, "r:") as tar:
        names = tar.getnames()
        if "manifest.json" not in names:
            raise BackupError("no manifest in backup — not an aeos backup")
        manifest = json.loads(
            tar.extractfile("manifest.json").read().decode("utf-8"))
        v = manifest.get("aeos_schema", 1)
        if not isinstance(v, int) or v > STATE_SCHEMA:
            raise SchemaError(f"backup schema {v!r} newer than this aeos; "
                              "upgrade first")

        # verify EVERY member before touching the workspace
        mismatched = []
        payloads = {}
        for rel, want in manifest["files"].items():
            if rel not in names:
                mismatched.append(f"{rel}: missing")
                continue
            data = tar.extractfile(rel).read()
            if _sha256_bytes(data) != want:
                mismatched.append(f"{rel}: checksum mismatch")
            payloads[rel] = data
        if mismatched:
            raise BackupError("backup fails verification, restore refused: "
                              + "; ".join(mismatched[:4]))

        ws.mkdir(parents=True, exist_ok=True)
        for rel in sorted(payloads):
            dest = ws / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payloads[rel])

    # rebuild the recall cache — proving it is a cache
    recall_built = False
    mem = ws / ".aeos" / "memory.jsonl"
    if mem.exists():
        from .memory import MemoryStore
        from .recall import RecallIndex
        idx = RecallIndex(str(ws / ".aeos" / "recall.sqlite"),
                          MemoryStore(mem))
        idx.build()
        idx.close()
        recall_built = True

    return {"workspace": str(ws), "files": len(payloads),
            "verified": True, "recall_rebuilt": recall_built,
            "sha256": _sha256_bytes(backup.read_bytes())}
