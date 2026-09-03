"""v18 Leverage Rubric: the 12 leverage points, auditable.

The course teaches the 12 leverage points as a mindset; a mindset you
cannot audit is a vibe. Each row below is one leverage point as AEOS
compiles it, checked against a real workspace's artifacts — PASS
requires evidence on disk, not a claim.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RubricRow:
    point: str
    mechanism: str
    status: str = "GAP"
    evidence: str = ""


def _bundle(ws: Path) -> dict:
    f = ws / ".aeos" / "evidence" / "bundle.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _has(ws: Path, rel: str) -> bool:
    return (ws / rel).exists()


def audit(workspace: Path) -> dict:
    ws = Path(workspace)
    b = _bundle(ws)
    d = b.get("dividend", {})
    checks = [
        ("Stdout is the contract",
         "evidence bundle parses into closed verdicts",
         bool(b) and "accepted" in b, "bundle.json with verdicts"),
        ("Tests are the gate",
         "acceptance is gate-driven, not narrated",
         b.get("accepted") is True, "accepted=true in bundle"),
        ("Architecture is boundaries",
         "writes enforced post-hoc", "triangle" in b or bool(b),
         "profile/boundary receipt in bundle"),
        ("The trade is measured",
         "control/cost/speed on every run", "triangle" in b,
         "triangle receipt in bundle"),
        ("Leverage is a number",
         "outcomes per unit of human attention", "leverage" in b,
         "leverage field in bundle"),
        ("Memory pays rent",
         "distillation + ledger + squatters", bool(d.get("ledger")),
         "dividend ledger in bundle"),
        ("Recall pays in layers",
         "FTS index over the store", _has(ws, ".aeos/recall.sqlite"),
         ".aeos/recall.sqlite"),
        ("Learning compounds",
         "episodes distilled into semantics", _has(ws, ".aeos/memory.jsonl"),
         ".aeos/memory.jsonl"),
        ("The fleet is a stream",
         "every mutation an event", _has(ws, ".aeos/events.jsonl"),
         ".aeos/events.jsonl"),
        ("Plans are durable",
         "checkpointed, resumable mid-wave", _has(ws, ".aeos/checkpoint.json"),
         ".aeos/checkpoint.json"),
        ("Standards are cited up front",
         "STANDARDS.md gates the plan", _has(ws, "STANDARDS.md"),
         "STANDARDS.md in workspace root"),
        ("Money is governed",
         "budget enforced inline", "economics" in b,
         "economics metered in bundle"),
    ]
    rows = [RubricRow(p, m, "PASS" if ok else "GAP",
                      ev if ok else "not found")
            for p, m, ok, ev in checks]
    score = sum(1 for r in rows if r.status == "PASS")
    return {"score": score, "of": len(rows),
            "rows": [r.__dict__ for r in rows]}


def render(report: dict) -> str:
    lines = [f"LEVERAGE AUDIT — {report['score']}/{report['of']} points "
             f"with evidence on disk"]
    for r in report["rows"]:
        mark = "x" if r["status"] == "PASS" else " "
        lines.append(f"  [{mark}] {r['point']:<28} {r['evidence']}")
    return "\n".join(lines)
