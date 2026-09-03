"""v15 RecallFTS: layered retrieval over the memory store.

ClaudeMem's third leg (after distillation and economics): recall pays
in layers, not transcripts. Three layers, paid in order, measured:
  L0 keys        — exact/prefix key hits, ~1 token each
  L1 snippets    — FTS5 MATCH fragments, trimmed to remaining budget
  L2 full record — only the top hit, only if budget remains
A recall that stays in L0/L1 is the dividend compounding.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from .context_os import approx_tokens
from .memory import MemoryStore


@dataclass
class RecallLayer:
    layer: int
    items: list = field(default_factory=list)
    tokens: int = 0


@dataclass
class RecallReport:
    query: str
    layers: list = field(default_factory=list)
    full_scan_tokens: int = 0

    @property
    def recall_tokens(self) -> int:
        return sum(l.tokens for l in self.layers)

    @property
    def saving(self) -> int:
        return self.full_scan_tokens - self.recall_tokens


def _match_expr(query: str) -> str:
    """FTS5-safe OR of quoted words; never raises on punctuation."""
    words = [w for w in query.replace('"', " ").split() if w][:4]
    return " OR ".join(f'"{w}"' for w in words)


class RecallIndex:
    """FTS5 index over a MemoryStore; sqlite3 is stdlib, FTS5 compiled in."""

    def __init__(self, path: str, store: MemoryStore):
        self.store = store
        self.db = sqlite3.connect(path)
        self.db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS recall USING fts5(key, body)")

    def build(self) -> int:
        """(Re)index every record; returns record count."""
        self.db.execute("DELETE FROM recall")
        n = 0
        for rec in self.store.records.values():
            self.db.execute("INSERT INTO recall(key, body) VALUES (?, ?)",
                            (rec.key, rec.value))
            n += 1
        self.db.commit()
        return n

    def recall(self, query: str, budget: int = 120) -> RecallReport:
        rep = RecallReport(query=query, full_scan_tokens=sum(
            approx_tokens(r.value) for r in self.store.records.values()))
        words = [w.lower() for w in query.split() if w]

        # L0 — key hits: cheapest addressable layer
        keys = [k for k in self.store.records
                if any(w in k.lower() for w in words)][:8]
        rep.layers.append(RecallLayer(0, list(keys), len(keys)))

        # L1 — FTS snippets within remaining budget
        remaining = budget - rep.recall_tokens
        if remaining > 0 and _match_expr(query):
            try:
                rows = self.db.execute(
                    "SELECT key, snippet(recall, 1, '', '', ' … ', 10) "
                    "FROM recall WHERE recall MATCH ? ORDER BY rank LIMIT 3",
                    (_match_expr(query),)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            snips = [f"{k}: {s}" for k, s in rows]
            spent = 0
            kept = []
            for s in snips:
                t = approx_tokens(s)
                if spent + t > remaining:
                    break
                spent += t
                kept.append(s)
            if kept:
                rep.layers.append(RecallLayer(1, kept, spent))
                remaining = budget - rep.recall_tokens

                # L2 — the single top hit, only if L1 was affordable
                # and the budget still allows
                if rows and remaining > 0:
                    full = self.store.read(rows[0][0])
                    if full is not None:
                        t = approx_tokens(full.value)
                        if t <= remaining:
                            rep.layers.append(RecallLayer(2, [rows[0][0]], t))
        return rep

    def close(self) -> None:
        self.db.close()
