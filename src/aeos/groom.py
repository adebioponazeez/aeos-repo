"""v28 Groom: retention + schema migration — state that pays its keep.

Long-lived state (memory, fleet stream, checkpoints) is schema-
versioned (ADR-037); run artifacts accumulate without bound unless
someone sweeps. `groom` is that sweep: upgrade legacy files to the
current schema header (in place, atomically), archive all but the
newest N run event files, and return a receipt. Nothing is ever
deleted — archived, retrievable, auditable.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .vault import (HEADER_KEY, STATE_SCHEMA, durable_write,
                    load_jsonl_tolerant, schema_header)


def _first_header(path: Path) -> dict | None:
    if not path.exists():
        return None
    good, _ = load_jsonl_tolerant(path)
    if good and HEADER_KEY in good[0]:
        return good[0]
    return None


def upgrade_state(ws: Path) -> list:
    """Bring legacy (unversioned) long-lived state to schema 1."""
    ws = Path(ws)
    upgraded = []

    mem = ws / ".aeos" / "memory.jsonl"
    if mem.exists() and _first_header(mem) is None:
        from .memory import MemoryStore
        store = MemoryStore(mem)          # legacy load, tolerant
        lines = [json.dumps(schema_header("memory"))]
        for r in store.records.values():
            from dataclasses import asdict
            d = asdict(r)
            d["mclass"] = r.mclass.value
            lines.append(json.dumps(d, sort_keys=True))
        durable_write(mem, "\n".join(lines) + "\n")
        upgraded.append("memory.jsonl")

    ev = ws / ".aeos" / "events.jsonl"
    if ev.exists() and _first_header(ev) is None:
        good, torn = load_jsonl_tolerant(ev)
        body = [json.dumps(d, sort_keys=True) for d in good]
        durable_write(ev, "\n".join(
            [json.dumps(schema_header("fleet"))] + body) + "\n")
        upgraded.append("events.jsonl")

    cp = ws / ".aeos" / "checkpoint.json"
    if cp.exists():
        try:
            data = json.loads(cp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and HEADER_KEY not in data:
            data[HEADER_KEY] = STATE_SCHEMA
            durable_write(cp, json.dumps(data, sort_keys=True))
            upgraded.append("checkpoint.json")

    return upgraded


def groom(ws: Path, keep_runs: int = 10) -> dict:
    ws = Path(ws)
    upgraded = upgrade_state(ws)

    runs_dir = ws / ".aeos" / "runs"
    archived, kept = 0, 0
    archived_bytes = 0
    if runs_dir.exists():
        run_files = sorted(runs_dir.glob("*-events.jsonl"),
                           key=lambda p: p.stat().st_mtime, reverse=True)
        kept = len(run_files[:keep_runs])
        archive_dir = ws / ".aeos" / "archive" / "runs"
        for old in run_files[keep_runs:]:
            archive_dir.mkdir(parents=True, exist_ok=True)
            archived_bytes += old.stat().st_size
            shutil.move(str(old), archive_dir / old.name)
            archived += 1

    return {"schema": STATE_SCHEMA, "upgraded": upgraded,
            "runs_kept": kept, "runs_archived": archived,
            "archived_bytes": archived_bytes,
            "archive": str(ws / ".aeos" / "archive" / "runs")}


def render(receipt: dict) -> str:
    lines = ["GROOM — retention + schema migration receipt"]
    up = receipt["upgraded"]
    lines.append(f"  schema {receipt['schema']} | upgraded: "
                 f"{', '.join(up) if up else 'none (already current)'}")
    lines.append(f"  runs: kept {receipt['runs_kept']}, archived "
                 f"{receipt['runs_archived']} "
                 f"({receipt['archived_bytes'] // 1024} KB) -> "
                 f"{receipt['archive']}")
    lines.append("  nothing deleted — archived, retrievable, auditable")
    return "\n".join(lines)
