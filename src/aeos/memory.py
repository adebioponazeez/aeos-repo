"""Memory OS: six memory classes, freshness-aware and evaluable (spec §21).

Do not store everything. Store what improves future outcomes. Each
memory carries provenance, confidence and expiry; the learning loop
may only write PROCEDURAL/SEMANTIC entries that carry validated
evidence — failed experiments are recorded as EPISODIC lessons, never
promoted into canonical knowledge.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .contracts import MemoryClass


@dataclass
class MemoryRecord:
    key: str
    value: str
    mclass: MemoryClass
    source: str                      # provenance: agent, human, system
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    evidence: list[str] = field(default_factory=list)

    def fresh(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return True
        return (now or time.time()) <= self.expires_at


class MemoryStore:
    """Attributable, searchable, updateable, freshness-aware, permission-aware."""

    WRITE_SAFE = {MemoryClass.WORKING, MemoryClass.TASK, MemoryClass.EPISODIC}
    CANONICAL = {MemoryClass.SEMANTIC, MemoryClass.PROCEDURAL, MemoryClass.ORGANIZATIONAL}

    def __init__(self, path: Path | None = None) -> None:
        from .vault import load_jsonl_tolerant, quarantine_torn
        self.records: dict[str, MemoryRecord] = {}
        self.path = path
        self.torn_lines = 0
        if path and path.exists():
            from .vault import check_schema, is_header
            good, torn = load_jsonl_tolerant(path)
            if good and is_header(good[0]):
                check_schema(good[0])       # future state fails closed
                good = good[1:]             # legacy v27 files: no header,
            for d in good:                  # treated as schema 1
                try:
                    d["mclass"] = MemoryClass(d["mclass"])
                    self.records[d["key"]] = MemoryRecord(**d)
                except (KeyError, ValueError, TypeError):
                    torn.append("unrecoverable-record")
            if torn:
                quarantine_torn(path, torn)
                self.torn_lines = len(torn)   # survived, not silenced

    def write(self, record: MemoryRecord, *, canonical_requires_evidence: bool = True) -> MemoryRecord:
        if (canonical_requires_evidence and record.mclass in self.CANONICAL
                and not record.evidence):
            raise ValueError(
                f"refusing canonical write '{record.key}': no evidence attached. "
                "Unvalidated knowledge may not become organizational memory.")
        self.records[record.key] = record
        self._flush()
        return record

    def read(self, key: str) -> MemoryRecord | None:
        return self.records.get(key)

    def search(self, needle: str, *, mclass: MemoryClass | None = None,
               fresh_only: bool = True) -> list[MemoryRecord]:
        now = time.time()
        hits = []
        for r in self.records.values():
            if mclass and r.mclass is not mclass:
                continue
            if fresh_only and not r.fresh(now):
                continue
            if needle.lower() in r.key.lower() or needle.lower() in r.value.lower():
                hits.append(r)
        return hits

    def expire_stale(self) -> list[str]:
        now = time.time()
        dead = [k for k, r in self.records.items() if not r.fresh(now)]
        for k in dead:
            del self.records[k]
        self._flush()
        return dead

    def classes_in_use(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.records.values():
            out[r.mclass.value] = out.get(r.mclass.value, 0) + 1
        return out

    def _flush(self) -> None:
        if not self.path:
            return
        from .vault import durable_write, schema_header
        lines = [json.dumps(schema_header("memory"))]
        for r in self.records.values():
            d = asdict(r)
            d["mclass"] = r.mclass.value
            lines.append(json.dumps(d, sort_keys=True))
        durable_write(self.path, "\n".join(lines) + "\n")
