"""Harness: the execution environment agents run inside (spec §14, §21).

Repository-native: the filesystem is the working memory (artifact-first,
2026 blueprint rule), the harness owns checkpoints (copy-on-write
snapshots of everything an agent may touch), and enforces the writes:
boundary AFTER every agent call — unauthorized changes are rolled back
and the phase dies. A tool list says what an agent CAN do; the writes:
boundary is what the harness will LET SURVIVE.
"""

from __future__ import annotations

import fnmatch
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Checkpoint:
    uid: str
    label: str
    created_at: float = field(default_factory=time.time)
    files: dict[str, str] = field(default_factory=dict)   # relpath -> content snapshot


class Harness:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        workspace.mkdir(parents=True, exist_ok=True)
        self.checkpoints: list[Checkpoint] = []
        self.violations: list[dict] = []

    # ------------------------------------------------------------ writes
    def path_allowed(self, relpath: str, patterns: list[str]) -> bool:
        if not patterns:
            return False  # no boundary declared -> write nothing
        return any(fnmatch.fnmatch(relpath, p) or fnmatch.fnmatch("/" + relpath, p)
                   for p in patterns)

    def snapshot(self, label: str, patterns: list[str] | None = None) -> Checkpoint:
        """Copy-on-write snapshot of files matching the boundary (or all)."""
        cp = Checkpoint(uid=f"cp-{int(time.time()*1000)}", label=label)
        for p in sorted(self.workspace.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.workspace).as_posix()
                if patterns is None or any(fnmatch.fnmatch(rel, pat) for pat in patterns):
                    try:
                        cp.files[rel] = p.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        cp.files[rel] = ""  # binary: content not snapshotted, presence is
        self.checkpoints.append(cp)
        return cp

    def enforce_boundary(self, cp: Checkpoint, agent: str,
                         patterns: list[str]) -> list[str]:
        """Diff workspace vs checkpoint; roll back unauthorized writes.

        Returns the list of reverted paths. Authorized changes survive.
        Deleted files within the boundary are restored."""
        reverted: list[str] = []
        for p in sorted(self.workspace.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.workspace).as_posix()
            if rel.startswith(".aeos/") or "/.aeos/" in rel:
                continue  # the OS's own state directory is always inside the fence
            if rel in cp.files:
                try:
                    current = p.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    current = ""
                if current != cp.files[rel] and not self.path_allowed(rel, patterns):
                    p.write_text(cp.files[rel], encoding="utf-8")
                    reverted.append(rel)
            else:
                if not self.path_allowed(rel, patterns):
                    p.unlink()
                    reverted.append(rel)
        for rel, content in cp.files.items():
            if not (self.workspace / rel).exists():
                (self.workspace / rel).parent.mkdir(parents=True, exist_ok=True)
                (self.workspace / rel).write_text(content, encoding="utf-8")
                reverted.append(rel)
        if reverted:
            self.violations.append({"agent": agent, "reverted": reverted,
                                    "checkpoint": cp.uid})
        return reverted

    def rollback(self, cp: Checkpoint) -> int:
        """Full rollback to a checkpoint (destructive recovery path)."""
        restored = 0
        for p in sorted(self.workspace.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.workspace).as_posix()
                if rel not in cp.files and not rel.startswith(".aeos/"):
                    p.unlink()
        for rel, content in cp.files.items():
            target = self.workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            restored += 1
        return restored

    # ------------------------------------------------------------ helpers
    def write(self, relpath: str, content: str) -> Path:
        target = self.workspace / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read(self, relpath: str) -> str:
        return (self.workspace / relpath).read_text(encoding="utf-8")

    def exists(self, relpath: str) -> bool:
        return (self.workspace / relpath).exists()

    def state_dir(self, name: str) -> Path:
        d = self.workspace / ".aeos" / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def dump_events(self, log, name: str = "events.jsonl") -> Path:
        out = self.state_dir("runs") / f"{int(time.time())}-{name}"
        lines = [json.dumps({"kind": e.kind, "ts": e.ts, "detail": e.detail},
                            default=str) for e in log.events()]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out
