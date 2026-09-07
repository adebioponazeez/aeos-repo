"""v36 The Notary, part 1: the tree has a cryptographic identity.

SEF-X handover 6.4 (adopted): every completion claim is anchored to a
Merkle root of the tree it speaks about. This is the stdlib-only
implementation — sha256 leaves that bind the path to the content (a
rename is not free), pairwise internal nodes, the odd node promoted
unchanged. Deterministic by construction: sorted paths only; no
clocks, no locales, no filesystem order, no metadata (permissions and
mtimes are not truth). The exclusion set is fixed and documented so
two snapshots of the same tree agree everywhere, forever.

Algorithm (one sentence, auditable): leaf_i = H("aeos-merkle-leaf\\0"
+ path_i + "\\0" + sha256(bytes_i)); node = H("aeos-merkle-node\\0" +
left + right); an odd trailing node is promoted unchanged; the empty
tree has the constant EMPTY_ROOT.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

LEAF_PREFIX = b"aeos-merkle-leaf\x00"
NODE_PREFIX = b"aeos-merkle-node\x00"
EMPTY_ROOT = hashlib.sha256(b"aeos-merkle-empty").hexdigest()

# Volatile / derived / foreign trees never count toward identity.
# "save-proofs" is excluded BY LAW: the receipt about a tree is not
# part of the tree — otherwise every certificate would shift the root
# it certifies (the observer effect, removed by rule, on the record).
EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache",
                ".ruff_cache", ".tox", ".nox", ".venv", "node_modules",
                "dist", "build", "out", "aeos-demo", ".aeos-demo",
                "save-proofs"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".tmp", ".lock", ".torn")
EXCLUDE_NAMES = {"workspace.lock", ".coverage", "recall.sqlite"}


def file_digest(path: Path) -> str:
    """sha256 of a file's bytes — chunked, never loading it whole."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(root: Path,
            exclude_dirs: frozenset | set = EXCLUDE_DIRS,
            exclude_suffixes: tuple = EXCLUDE_SUFFIXES,
            exclude_names: frozenset | set = EXCLUDE_NAMES) -> list[Path]:
    """The deterministic member list: every kept file, sorted by
    posix relative path — the only ordering that means anything."""
    root = Path(root)
    members = []
    for p in root.rglob("*"):
        if not p.is_file() and not p.is_symlink():
            continue
        rel = p.relative_to(root)
        if any(part in exclude_dirs for part in rel.parts[:-1]):
            continue
        name = rel.parts[-1]
        if name in exclude_names or name.endswith(exclude_suffixes):
            continue
        if p.is_symlink():
            continue                       # a link is a claim, not content
        members.append(p)
    return sorted(members, key=lambda p: p.relative_to(root).as_posix())


def _leaf(relpath: str, file_sha: str) -> bytes:
    return hashlib.sha256(
        LEAF_PREFIX + relpath.encode("utf-8") + b"\x00"
        + file_sha.encode("ascii")).digest()


def _root_of(leaves: list[bytes]) -> str:
    if not leaves:
        return EMPTY_ROOT
    level = leaves
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level) - 1, 2):
            nxt.append(hashlib.sha256(
                NODE_PREFIX + level[i] + level[i + 1]).digest())
        if len(level) % 2:
            nxt.append(level[-1])         # odd node promoted unchanged
        level = nxt
    return level[0].hex()


def snapshot(root: Path, **exclude) -> dict:
    """The tree's identity card: merkle root, file count, byte count,
    and the per-file sha256 map (for naming drift, not for hashing)."""
    root = Path(root)
    files = collect(root, **exclude) if exclude else collect(root)
    leaves, shas, total = [], {}, 0
    for p in files:
        rel = p.relative_to(root).as_posix()
        sha = file_digest(p)
        shas[rel] = sha
        total += p.stat().st_size
        leaves.append(_leaf(rel, sha))
    return {"root": _root_of(leaves), "files": len(files),
            "bytes": total, "shas": shas}


def diff(pre: dict, post: dict, *, cap: int = 16) -> dict:
    """Name what changed between two snapshots — added, removed,
    modified — capped, with the full counts. Never a narrative."""
    pre_shas, post_shas = pre.get("shas", {}), post.get("shas", {})
    added = sorted(set(post_shas) - set(pre_shas))
    removed = sorted(set(pre_shas) - set(post_shas))
    modified = sorted(k for k in set(pre_shas) & set(post_shas)
                      if pre_shas[k] != post_shas[k])
    events = ([{"path": p, "change": "added"} for p in added]
              + [{"path": p, "change": "removed"} for p in removed]
              + [{"path": p, "change": "modified"} for p in modified])
    return {"events": events[:cap],
            "total": len(events),
            "truncated": len(events) > cap}
