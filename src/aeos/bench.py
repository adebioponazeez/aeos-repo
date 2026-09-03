"""v34 The Gauge: the performance envelope, measured — not vibes.

Every proof so far is correctness at toy scale; this measures the
system against size: memory load at N records, recall build+query,
fleet tail, backup, groom, doctor, colony width. Receipts carry
numbers and optional budgets; a budget blown is a FAIL row. The
envelope doc (docs/ENVELOPE.md) records where the system bends and
which bends are accepted limits vs fixed.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BenchRow:
    name: str
    n: int
    seconds: float
    budget_s: float | None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.budget_s is None or self.seconds <= self.budget_s


@dataclass
class BenchReport:
    rows: list = field(default_factory=list)
    scale: str = "quick"

    @property
    def passed(self) -> bool:
        return bool(self.rows) and all(r.ok for r in self.rows)

    def render(self) -> str:
        head = (f"GAUGE — {self.scale} scale, {len(self.rows)} case(s) "
                f"({'ALL WITHIN BUDGET' if self.passed else 'BUDGET BLOWN'})")
        lines = [head]
        for r in self.rows:
            bud = (f"/{r.budget_s:g}s" if r.budget_s else "")
            mark = "." if r.ok else "X"
            lines.append(f"  [{mark}] {r.name:<24} n={r.n:<7} "
                         f"{r.seconds:.3f}s{bud} {r.detail}")
        return "\n".join(lines)


def _seed_memory(ws: Path, n: int) -> Path:
    """N records straight to disk (fast, deterministic)."""
    from .vault import durable_write
    ws = Path(ws)
    ws.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"aeos_schema": 1})]
    for i in range(n):
        lines.append(json.dumps({
            "key": f"lesson::task-{i % 50}::{i}",
            "value": f"task-{i % 50}: SUCCEEDED via the tests-first "
                     f"sequence, padding to a realistic lesson length "
                     f"for record number {i}",
            "mclass": "EPISODIC", "source": "bench",
            "confidence": 0.6, "created_at": 1780000000.0 + i,
            "expires_at": None, "evidence": []}, sort_keys=True))
    mem = ws / ".aeos" / "memory.jsonl"
    durable_write(mem, "\n".join(lines) + "\n")
    return mem


def _seed_runs(ws: Path, n: int) -> None:
    runs = Path(ws) / ".aeos" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    body = '{"ts": 1.0, "kind": "TICK", "agent": "bench"}\n' * 5
    for i in range(n):
        (runs / f"{1780000000 + i}-events.jsonl").write_text(
            body, encoding="utf-8")


def envelope(ws: Path, *, full: bool = False) -> BenchReport:
    """The standard gauge: quick (1k) or full (10k) scale."""
    ws = Path(ws)
    n = 10_000 if full else 1_000
    rep = BenchReport(scale="full" if full else "quick")
    ws.mkdir(parents=True, exist_ok=True)

    # 1) memory load at N
    mem = _seed_memory(ws, n)
    from aeos.memory import MemoryStore
    t0 = time.perf_counter()
    store = MemoryStore(mem)
    dt = time.perf_counter() - t0
    rep.rows.append(BenchRow("memory load", n, dt,
                             10.0 if full else 2.0,
                             f"{len(store.records)} records"))

    # 2) recall build + query at N
    from aeos.recall import RecallIndex
    t0 = time.perf_counter()
    idx = RecallIndex(str(ws / ".aeos" / "bench-recall.sqlite"), store)
    idx.build()
    rrep = idx.recall("task-7 tests", budget=120)
    dt = time.perf_counter() - t0
    idx.close()
    rep.rows.append(BenchRow("recall build+query", n, dt,
                             10.0 if full else 3.0,
                             f"paid {rrep.recall_tokens} tokens"))

    # 3) fleet publish N + tail(20)
    from aeos.fleet import EventBus
    bus = EventBus(ws / ".aeos" / "bench-events.jsonl")
    bus.publish("BENCH_START", "gauge")          # header lands first
    for i in range(n):
        bus.publish("TICK", f"a{i % 97}")
    t0 = time.perf_counter()
    last = bus.tail(20)
    dt = time.perf_counter() - t0
    rep.rows.append(BenchRow("fleet tail(20)", n, dt,
                             0.05 if full else 0.02,
                             f"{len(last)} events, newest {last[-1].agent}"))

    # 4) backup at N-state
    from aeos.backup import create_backup
    t0 = time.perf_counter()
    bak = create_backup(ws, ws / ".aeos" / "bench-backup.tar")
    dt = time.perf_counter() - t0
    rep.rows.append(BenchRow("backup create", n, dt,
                             20.0 if full else 5.0,
                             f"{bak['files']} files, "
                             f"{bak['bytes'] // 1024} KB"))

    # 5) groom with N run files
    _seed_runs(ws, n)
    from aeos.groom import groom
    t0 = time.perf_counter()
    g = groom(ws, keep_runs=10)
    dt = time.perf_counter() - t0
    rep.rows.append(BenchRow("groom archive", n, dt,
                             30.0 if full else 8.0,
                             f"archived {g['runs_archived']}"))

    # 6) doctor on the whole thing
    from aeos.doctor import doctor
    t0 = time.perf_counter()
    drep = doctor(ws)
    dt = time.perf_counter() - t0
    rep.rows.append(BenchRow("doctor sweep", n, dt,
                             10.0 if full else 3.0,
                             f"{drep['failed']} failed, "
                             f"{drep['warned']} warned"))

    # 7) colony: 60 independents + one 59-fan-in dependent + 40 frees
    from aeos.colony import Colony, Node
    t0 = time.perf_counter()
    c = Colony()
    for i in range(60):
        c.add(Node(f"chain-{i}", (lambda ctx, i=i: i),))
    prev = tuple(f"chain-{i}" for i in range(59))
    c.nodes["chain-59"].requires = prev
    for i in range(40):
        c.add(Node(f"free-{i}", lambda ctx: i))
    crep = c.run()
    dt = time.perf_counter() - t0
    rep.rows.append(BenchRow("colony 100 nodes", 100, dt,
                             5.0 if full else 2.0,
                             f"{len(crep.executed)} ran, "
                             f"{crep.waves} waves"))
    return rep
