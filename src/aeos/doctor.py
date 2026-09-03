"""v32 The Physician: the system audits its own claims.

The oldest claim in the charter (ADR-002: zero runtime dependencies)
has always been verified by inspection — until now. `doctor` parses
every module's imports with ast and classifies them: stdlib, aeos,
or VIOLATION. The claim became a machine check. Plus workspace
health (schema versions, torn sidecars, stale locks, disk, groom
hint) and repo health (clean tree, tags). Verdicts are PASS/WARN/FAIL
with named detail; a FAIL fails the command — a doctor that flatters
is not a doctor.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path


# ------------------------------------------------------- the zero-dep audit

def scan_imports(root: Path) -> dict:
    """Every module under root -> its absolute imports (ast-based)."""
    root = Path(root)
    out = {}
    for py in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue                       # unreadable: named elsewhere
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.level and node.level > 0:
                    continue               # relative import: internal
                mods.add(node.module.split(".")[0])
        out[py.relative_to(root).as_posix()] = sorted(mods)
    return out


def classify_imports(imports: dict) -> dict:
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    internal = {"aeos"}
    clean, violations = {}, {}
    for mod, deps in imports.items():
        bad = [d for d in deps
               if d not in stdlib and d not in internal and d != "__future__"]
        if bad:
            violations[mod] = bad
        else:
            clean[mod] = deps
    return {"modules": len(imports), "clean": len(clean),
            "violations": violations}


def zero_dep_audit() -> dict:
    """ADR-002 machine-checked: no aeos module may import a non-stdlib,
    non-aeos absolute import. Ever."""
    pkg = Path(__file__).resolve().parent
    return classify_imports(scan_imports(pkg))


# ------------------------------------------------------- workspace checks

def check_workspace(ws: Path) -> list:
    from .vault import STATE_SCHEMA, WorkspaceLock
    ws = Path(ws)
    rows = []

    mem = ws / ".aeos" / "memory.jsonl"
    if mem.exists():
        from .vault import HEADER_KEY, load_jsonl_tolerant
        good, _ = load_jsonl_tolerant(mem)
        v = good[0].get(HEADER_KEY) if good and HEADER_KEY in good[0] else 1
        rows.append(("memory schema", "PASS" if v == STATE_SCHEMA else
                     ("WARN" if v == 1 else "FAIL"),
                     f"schema {v}"))
    ev = ws / ".aeos" / "events.jsonl"
    if ev.exists():
        from .vault import HEADER_KEY, load_jsonl_tolerant
        good, _ = load_jsonl_tolerant(ev)
        v = good[0].get(HEADER_KEY) if good and HEADER_KEY in good[0] else 1
        rows.append(("fleet schema", "PASS" if v == STATE_SCHEMA else
                     ("WARN" if v == 1 else "FAIL"), f"schema {v}"))

    torn = list(ws.glob("**/*.torn"))
    if torn:
        rows.append(("torn writes", "WARN",
                     f"{len(torn)} quarantined sidecar(s) — inspect or clear"))

    lock = WorkspaceLock(ws / ".aeos" / "workspace.lock")
    if ws / ".aeos" / "workspace.lock" in ws.glob("**/workspace.lock"):
        if lock.acquire(blocking=False):
            lock.release()
            rows.append(("workspace lock", "PASS", "runnable (no holder)"))
        else:
            rows.append(("workspace lock", "WARN",
                         "held by a live run (kernel releases on death)"))

    try:
        free = __import__("shutil").disk_usage(ws).free // 1_000_000
        rows.append(("disk", "PASS" if free > 50 else "WARN",
                     f"{free}MB free"))
    except OSError:
        pass

    runs = list((ws / ".aeos" / "runs").glob("*-events.jsonl")) \
        if (ws / ".aeos" / "runs").exists() else []
    if len(runs) > 10:
        rows.append(("retention", "WARN",
                     f"{len(runs)} run files kept — `aeos groom` would archive"))
    return rows


def check_repo(path: Path) -> list:
    rows = []
    git = Path(path) / ".git"
    if not git.exists():
        return [("version control", "WARN",
                 "not a git repository — history is not preserved")]
    import subprocess
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=path,
                           capture_output=True, text=True).stdout.strip()
    rows.append(("working tree", "PASS" if not dirty else "WARN",
                 "clean" if not dirty else f"{len(dirty.splitlines())} uncommitted change(s)"))
    tags = subprocess.run(["git", "tag"], cwd=path, capture_output=True,
                          text=True).stdout.split()
    rows.append(("tags", "PASS" if tags else "WARN",
                 f"{len(tags)} tag(s), latest {tags[-1] if tags else '-'}"))
    return rows


def charter_check(principles: Path, tests_root: Path) -> tuple:
    """The charter is load-bearing only if every test it cites exists
    in the suite. Machine-verified, like every other claim."""
    import re as _re
    if not principles.exists():
        return ("WARN", "charter not found (installed package?)")
    text = principles.read_text(encoding="utf-8")
    cited = sorted(set(_re.findall(r"\btest_[a-z0-9_]+\b", text)))
    if not cited:
        return ("WARN", "charter cites no tests — nothing is load-bearing")
    corpus = ""
    for t in sorted(Path(tests_root).glob("test_*.py")):
        try:
            corpus += t.read_text(encoding="utf-8")
        except OSError:
            pass
    missing = [c for c in cited if c not in corpus]
    if missing:
        return ("FAIL", f"cited but absent: {', '.join(missing[:3])}")
    return ("PASS", f"{len(cited)} cited test(s) all exist in the suite")


def doctor(ws: Path | None = None) -> dict:
    rows = []
    v = sys.version_info
    rows.append(("python", "PASS" if v >= (3, 10) else "FAIL",
                 f"{v.major}.{v.minor}.{v.micro}"))
    audit = zero_dep_audit()
    rows.append(("zero dependencies (ADR-002)",
                 "PASS" if not audit["violations"] else "FAIL",
                 f"{audit['modules']} modules scanned, "
                 f"{audit['clean']} clean, "
                 f"{len(audit['violations'])} violation(s)"))
    if ws:
        rows.extend(check_workspace(Path(ws)))
    here = Path(__file__).resolve()
    repo_root = next((parent for parent in here.parents
                      if (parent / ".git").exists()), here.parent.parent)
    verdict, detail = charter_check(repo_root / "docs" / "PRINCIPLES.md",
                                    repo_root / "tests")
    rows.append(("charter is load-bearing", verdict, detail))
    if (repo_root / "README.md").exists():
        from .scribe import audit as _audit
        srep = _audit(repo_root, ("README.md",))
        rows.append(("README tells the truth",
                     "PASS" if srep.passed else "FAIL",
                     f"{len(srep.claims)} claim(s), "
                     f"{len(srep.drift)} drift(s)"))
    rows.extend(check_repo(repo_root))
    report = {"rows": [{"area": a, "verdict": verdict, "detail": d}
                       for a, verdict, d in rows],
              "audit": audit}
    report["failed"] = sum(1 for r in report["rows"]
                           if r["verdict"] == "FAIL")
    report["warned"] = sum(1 for r in report["rows"]
                           if r["verdict"] == "WARN")
    return report


def render(rep: dict) -> str:
    ok = rep["failed"] == 0
    head = (f"DOCTOR — {len(rep['rows'])} check(s): "
            f"{rep['failed']} failed, {rep['warned']} warned "
            f"({'HEALTHY' if ok and rep['warned'] == 0 else 'ATTENTION' if ok else 'UNHEALTHY'})")
    lines = [head]
    for r in rep["rows"]:
        lines.append(f"  [{r['verdict']:<4}] {r['area']:<26} {r['detail']}")
    return "\n".join(lines)
