"""v5.0 — Operations: scheduled sweeps and the regression book.

Sweeps make entropy control continuous (cron-shaped, not
quarterly-archaeology-shaped). The regression book is the 2026
Braintrust pattern in miniature: a production failure, once recorded,
becomes a permanent gate — the same mistake cannot ship twice.
"""

from __future__ import annotations

import fnmatch
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class SweepJob:
    name: str
    interval_s: float
    fn: Callable[[], dict]
    last_run: float = 0.0
    runs: int = 0


class SweepScheduler:
    def __init__(self) -> None:
        self.jobs: dict[str, SweepJob] = {}

    def every(self, name: str, interval_s: float,
              fn: Callable[[], dict]) -> SweepJob:
        self.jobs[name] = SweepJob(name=name, interval_s=interval_s, fn=fn)
        return self.jobs[name]

    def run_due(self, now: float | None = None) -> list[tuple[str, dict]]:
        t = now if now is not None else time.time()
        results = []
        for job in self.jobs.values():
            if t - job.last_run >= job.interval_s:
                out = job.fn()
                job.last_run = t
                job.runs += 1
                results.append((job.name, out))
        return results

    def next_due(self, now: float | None = None) -> str | None:
        t = now if now is not None else time.time()
        due = [(job.last_run + job.interval_s, name)
               for name, job in self.jobs.items()]
        return min(due)[1] if due else None


class RegressionBook:
    """Record failure signatures; block envelopes that match them."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.signatures: list[dict] = []
        if path and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.signatures.append(json.loads(line))

    def record(self, signature: str, reason: str,
               patterns: list[str]) -> dict:
        entry = {"signature": signature, "reason": reason,
                 "patterns": patterns, "recorded_at": time.time()}
        self.signatures.append(entry)
        self._flush()
        return entry

    def check(self, changed_files: list[str]) -> list[str]:
        """Which recorded signatures do these changed files match?"""
        hits = []
        for entry in self.signatures:
            for pattern in entry["patterns"]:
                if any(fnmatch.fnmatch(f, pattern) for f in changed_files):
                    hits.append(entry["signature"])
                    break
        return hits

    def _flush(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "\n".join(json.dumps(s) for s in self.signatures) + "\n",
            encoding="utf-8")
