"""v14.0 — The Dividend: memory that measurably pays for itself.

ClaudeMem proved the economics in the field: capture raw context,
distill it into typed ~500-token observations, retrieve layers instead
of transcripts — ~10x token efficiency. v14 brings the same economics
into the OS as law and ledger:

  MemoryDistiller   episodic records -> ONE compact semantic record
                    per (task, outcome): the tightest phrasing kept,
                    provenance counts attached; compression MEASURED
  stable_prefix()   canonical-JSON (sorted keys, tight separators)
                    stable-first assembly: byte-identical prefixes
                    across runs -> provider prompt-cache eligible;
                    volatile tails ride last
  TokenLedger       per task-class curve: baseline (naive) vs actual
                    (memory+overhead). NEGATIVE MARGINAL CONSUMPTION
                    is when the memory-inclusive cost of run N is
                    BELOW the no-memory baseline — the dividend
  rent()            MEMORY MUST PAY RENT: a record never recalled is
                    token-weight you carry forever — flagged, not
                    forgiven (ADR-023)

Deterministic throughout: the dividend is computed, never vibed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from .context_os import approx_tokens
from .contracts import MemoryClass
from .memory import MemoryRecord, MemoryStore


# ------------------------------------------------------------- distiller

@dataclass
class DistillationReport:
    groups: int = 0
    episodes_in: int = 0
    tokens_in: int = 0
    tokens_out: int = 0

    @property
    def compression(self) -> float:
        return round(self.tokens_in / self.tokens_out, 2) if self.tokens_out else 0.0

    @property
    def projected_saving_per_recall(self) -> int:
        """Tokens a future run saves by recalling the distilled record
        instead of re-reading every episode."""
        return max(0, self.tokens_in - self.tokens_out)


def _episode_group_key(record: MemoryRecord) -> tuple[str, str] | None:
    """lesson::<task>::<n> -> (task, outcome-ish). None = not episodic
    lesson material."""
    if record.mclass is not MemoryClass.EPISODIC:
        return None
    parts = record.key.split("::")
    if len(parts) >= 2 and parts[0] == "lesson":
        return parts[1], record.value.split(":", 1)[0][:40]
    return None


class MemoryDistiller:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def distill_lessons(self, *, min_group: int = 2) -> DistillationReport:
        """Compress repeated episodic lessons into single semantic
        records. The tightest phrasing survives (shortest value);
        validation counts are attached as the record's evidence."""
        groups: dict[tuple[str, str], list[MemoryRecord]] = {}
        for r in list(self.store.records.values()):
            key = _episode_group_key(r)
            if key:
                groups.setdefault(key, []).append(r)

        report = DistillationReport()
        for (task, outcome), records in sorted(groups.items()):
            if len(records) < min_group:
                continue
            report.groups += 1
            report.episodes_in += len(records)
            values = [r.value for r in records]
            report.tokens_in += sum(approx_tokens(v) for v in values)
            tightest = min(values, key=len)
            wins = sum(1 for v in values if "SUCCEEDED" in v or "success" in v)
            distilled = (f"{task}: {tightest.split(':', 1)[-1].strip()} "
                         f"[validated {len(records)}x, "
                         f"{wins}/{len(records)} clean]")
            report.tokens_out += approx_tokens(distilled)
            self.store.write(MemoryRecord(
                key=f"semantic::{task}", value=distilled,
                mclass=MemoryClass.SEMANTIC, source="distiller",
                confidence=0.85,
                evidence=[f"distilled from {len(records)} episodic records",
                          f"win {wins}/{len(records)}"]), )
        return report


# -------------------------------------------------------- cache-stable

def canonical_json(payload) -> str:
    """Deterministic serialization: sorted keys, no whitespace — the
    same data ALWAYS yields the same bytes (JCS-style), which is what
    provider prompt caches need to hit."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass
class StableAssembly:
    prefix: str
    tail: str
    prefix_tokens: int
    total_tokens: int

    @property
    def cache_eligible_fraction(self) -> float:
        return round(self.prefix_tokens / self.total_tokens, 3) if self.total_tokens else 0.0


def stable_prefix(stable: dict, volatile: dict) -> StableAssembly:
    """Stable-first assembly: canonical JSON of the stable payload,
    then the volatile tail. Across runs with the same stable set the
    prefix is BYTE-IDENTICAL — cache-eligible — while the changing
    parts ride last where they invalidate nothing before them."""
    prefix = canonical_json(stable)
    tail = canonical_json(volatile)
    return StableAssembly(prefix=prefix, tail=tail,
                          prefix_tokens=approx_tokens(prefix),
                          total_tokens=approx_tokens(prefix + tail))


# ------------------------------------------------------------- ledger

@dataclass
class LedgerEntry:
    task_class: str
    run: int
    baseline_tokens: int      # naive: re-read everything, no memory
    actual_tokens: int        # what this run actually consumed
    memory_overhead_tokens: int = 0   # amortized share of storing memory


class TokenLedger:
    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def record(self, task_class: str, run: int, baseline_tokens: int,
               actual_tokens: int, memory_overhead_tokens: int = 0) -> None:
        self.entries.append(LedgerEntry(task_class, run, baseline_tokens,
                                        actual_tokens,
                                        memory_overhead_tokens))

    def curve(self, task_class: str) -> list[LedgerEntry]:
        return sorted((e for e in self.entries if e.task_class == task_class),
                      key=lambda e: e.run)

    def marginal(self, task_class: str) -> dict:
        """The marginal consumption picture for one task class."""
        entries = self.curve(task_class)
        if not entries:
            return {"task_class": task_class, "runs": 0}
        latest = entries[-1]
        all_in = latest.actual_tokens + latest.memory_overhead_tokens
        baseline = latest.baseline_tokens
        return {
            "task_class": task_class, "runs": len(entries),
            "baseline": baseline, "all_in": all_in,
            "delta": all_in - baseline,           # negative = the dividend
            "negative_marginal": all_in < baseline,
            "cumulative_saved": sum(e.baseline_tokens - (e.actual_tokens
                                                  + e.memory_overhead_tokens)
                                    for e in entries),
        }

    def dividend(self) -> dict:
        per_class = sorted({e.task_class for e in self.entries})
        return {"classes": {c: self.marginal(c) for c in per_class},
                "any_negative": any(self.marginal(c).get("negative_marginal")
                                    for c in per_class),
                "total_saved": sum(e.baseline_tokens - (e.actual_tokens
                                                 + e.memory_overhead_tokens)
                                   for e in self.entries)}


# --------------------------------------------------------------- rent

@dataclass
class RentFinding:
    key: str
    tokens: int
    recalls: int
    verdict: str                    # PAYS_RENT | SQUATTING


def rent(records: list[MemoryRecord], recalled_keys: set[str],
         *, min_recalls: int = 1) -> list[RentFinding]:
    """MEMORY MUST PAY RENT. Every stored byte is token-weight carried
    into every future assembly that might retrieve it. A record never
    recalled is squatting: flag it for the entropy scanner's REMOVE
    path — memory pollution is an economic crime, not just a
    confidence problem."""
    out = []
    for r in records:
        if r.mclass is MemoryClass.WORKING:
            continue                        # volatile by definition
        recalls = sum(1 for k in recalled_keys if k == r.key or r.key in k)
        cost = approx_tokens(r.value)
        out.append(RentFinding(
            r.key, cost, recalls,
            "PAYS_RENT" if recalls >= min_recalls else "SQUATTING"))
    return out


def squatters(findings: list[RentFinding]) -> list[RentFinding]:
    return [f for f in findings if f.verdict == "SQUATTING"]
