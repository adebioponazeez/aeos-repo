"""v19 Standards: success is planned — operator law cited up front.

The course's 80-20: encode engineering standards BEFORE the build, as
templates the plan must cite — not lessons memory discovers after.
Gate law: if the operator registered standards (STANDARDS.md), a plan
that cites none is refused; a citation that is not registered is
refused. No file, no gate (standards are the operator's choice).
"""
from __future__ import annotations

import re
from pathlib import Path

STANDARDS_TEMPLATE = """# STANDARDS — the operator's engineering law

Plans MUST cite the standards they honor, as `[STD-n]`. A plan that
cites nothing is refused; a citation that is not registered is refused.

- [STD-1] Tests precede claims — no verdict without a proof artifact.
- [STD-2] Evidence or silence — unsourced facts do not enter memory.
- [STD-3] Boundaries, not promises — declared writes only, enforced.
- [STD-4] Fail closed — uncertainty denies, never assumes success.
- [STD-5] Small, checked steps — every step leaves a verifiable seam.
"""

_ID = re.compile(r"\[STD-(\d+)\]")


def registered_ids(path: Path) -> list:
    """Sorted registered standard ids, e.g. ['STD-1', 'STD-2', ...]."""
    p = Path(path)
    if not p.exists():
        return []
    found = {f"STD-{m}" for m in _ID.findall(p.read_text(encoding="utf-8"))}
    return sorted(found, key=lambda s: int(s.split("-")[1]))


def cited_ids(text: str) -> list:
    seen = {f"STD-{m}" for m in _ID.findall(text or "")}
    return sorted(seen, key=lambda s: int(s.split("-")[1]))


def check_plan(plan_text: str, standards_path: Path) -> dict:
    """Gate: cited ids must exist and be registered; >=1 required."""
    registered = registered_ids(standards_path)
    gated = bool(registered)
    cited = cited_ids(plan_text)
    missing = [c for c in cited if c not in registered]
    ok = (not gated) or (bool(cited) and not missing)
    return {"gated": gated, "registered": registered, "cited": cited,
            "missing": missing, "ok": ok}


def init_template(workspace: Path) -> Path:
    p = Path(workspace) / "STANDARDS.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(STANDARDS_TEMPLATE, encoding="utf-8")
    return p
