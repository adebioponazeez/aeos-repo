"""v34 tests: the gauge — correctness at scale + the O(1) tail."""

import json

import pytest

from aeos.bench import BenchReport, envelope, _seed_memory
from aeos.fleet import EventBus


class TestFastTail:
    def test_tail_matches_replay_at_scale(self, tmp_path):
        bus = EventBus(tmp_path / "e.jsonl")
        bus.publish("HEADER_BYPASS", "x")     # header + 5000 events
        for i in range(5000):
            bus.publish("TICK", f"a{i}")
        fast = EventBus(tmp_path / "e.jsonl")
        assert fast.tail(20) == fast.replay()[-20:]

    def test_tail_drops_torn_fragment(self, tmp_path):
        bus = EventBus(tmp_path / "e.jsonl")
        bus.publish("ONE", "a")
        bus.publish("TWO", "b")
        with bus.path.open("a", encoding="utf-8") as fh:
            fh.write('{"ts": 1.0, "kind": "TOR')   # power-cut tail
        events = EventBus(tmp_path / "e.jsonl").tail(5)
        assert [e.kind for e in events] == ["ONE", "TWO"]

    def test_tail_beyond_block_boundary(self, tmp_path):
        bus = EventBus(tmp_path / "e.jsonl")
        bus.publish("SEED", "x")
        for i in range(3000):                    # > 64KB of lines
            bus.publish("TICK", "x" * 40)
        t = EventBus(tmp_path / "e.jsonl").tail(3)
        assert len(t) == 3 and t[-1].kind == "TICK"

    def test_tail_on_empty_and_header_only(self, tmp_path):
        assert EventBus(tmp_path / "none.jsonl").tail() == []
        bus = EventBus(tmp_path / "e.jsonl")
        bus.publish("FIRST", "a")                # file = header + 1
        t = EventBus(tmp_path / "e.jsonl").tail(10)
        assert [e.kind for e in t] == ["FIRST"]


class TestScaleCorrectness:
    def test_memory_roundtrip_at_1000(self, tmp_path):
        from aeos.memory import MemoryStore
        mem = _seed_memory(tmp_path, 1000)
        store = MemoryStore(mem)
        assert len(store.records) == 1000
        assert store.read("lesson::task-7::7") is not None

    def test_recall_budget_holds_at_1000(self, tmp_path):
        from aeos.memory import MemoryStore
        from aeos.recall import RecallIndex
        store = MemoryStore(_seed_memory(tmp_path, 1000))
        idx = RecallIndex(str(tmp_path / "r.sqlite"), store)
        idx.build()
        rep = idx.recall("task-7 tests", budget=120)
        idx.close()
        assert rep.recall_tokens <= 120
        assert rep.saving > 1000            # the dividend at scale

    def test_colony_hundred_nodes(self):
        from aeos.colony import Colony, Node
        c = Colony()
        for i in range(60):
            c.add(Node(f"chain-{i}", lambda ctx, i=i: i,
                       requires=(f"chain-{i - 1}",) if i else ()))
        for i in range(40):
            c.add(Node(f"free-{i}", lambda ctx: i))
        rep = c.run()
        assert rep.ok and len(rep.executed) == 100
        assert rep.waves == 60               # chain depth = width


class TestGauge:
    def test_quick_envelope_within_budget(self, tmp_path):
        rep = envelope(tmp_path / "ws", full=False)
        assert rep.passed, rep.render()
        names = [r.name for r in rep.rows]
        assert "memory load" in names and "fleet tail(20)" in names

    def test_report_render_names_rows(self):
        rep = BenchReport(rows=[])
        assert "GAUGE" in rep.render()

    def test_bench_command(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["bench", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0 and "GAUGE" in out and "fleet tail" in out
