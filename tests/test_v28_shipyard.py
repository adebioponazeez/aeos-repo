"""v28 tests: the shipyard — schema law, migrations, retention."""

import json

import pytest

from aeos.contracts import MemoryClass
from aeos.fleet import EventBus
from aeos.groom import groom, render, upgrade_state
from aeos.memory import MemoryRecord, MemoryStore
from aeos.resume import PlanCheckpoint, PlanTask
from aeos.vault import STATE_SCHEMA, SchemaError


def legacy_memory(tmp_path, n=2):
    """A v27-era memory file: records, NO schema header."""
    p = tmp_path / "memory.jsonl"
    lines = []
    for i in range(n):
        lines.append(json.dumps({
            "key": f"semantic::k{i}", "value": f"lesson {i}",
            "mclass": "SEMANTIC", "source": "t", "confidence": 0.5,
            "created_at": 1.0, "expires_at": None,
            "evidence": ["e"]}, sort_keys=True))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


class TestSchemaMemory:
    def test_flush_writes_header(self, tmp_path):
        p = tmp_path / "m.jsonl"
        MemoryStore(p).write(MemoryRecord(
            key="semantic::x", value="v", mclass=MemoryClass.SEMANTIC,
            source="t", evidence=["e"]))
        first = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
        assert first["aeos_schema"] == STATE_SCHEMA

    def test_reload_skips_header_keeps_records(self, tmp_path):
        p = tmp_path / "m.jsonl"
        store = MemoryStore(p)
        store.write(MemoryRecord(key="semantic::x", value="v",
                                 mclass=MemoryClass.SEMANTIC, source="t",
                                 evidence=["e"]))
        again = MemoryStore(p)
        assert len(again.records) == 1
        assert again.read("semantic::x").value == "v"

    def test_legacy_v27_file_still_loads(self, tmp_path):
        p = legacy_memory(tmp_path)
        store = MemoryStore(p)
        assert len(store.records) == 2          # back-compat, no rewrite

    def test_future_schema_fails_closed(self, tmp_path):
        p = tmp_path / "m.jsonl"
        p.write_text(json.dumps({"aeos_schema": 99}) + "\n"
                     + json.dumps({"key": "k", "value": "v",
                                   "mclass": "SEMANTIC", "source": "t",
                                   "evidence": ["e"]}) + "\n",
                     encoding="utf-8")
        with pytest.raises(SchemaError):
            MemoryStore(p)


class TestSchemaFleet:
    def test_new_stream_carries_header_and_replays(self, tmp_path):
        bus = EventBus(tmp_path / "e.jsonl")
        bus.publish("AGENT_REGISTERED", "a")
        first = json.loads(bus.path.read_text(encoding="utf-8")
                           .splitlines()[0])
        assert first["aeos_schema"] == STATE_SCHEMA
        assert [e.kind for e in bus.replay()] == ["AGENT_REGISTERED"]

    def test_legacy_stream_replays(self, tmp_path):
        p = tmp_path / "e.jsonl"
        p.write_text(json.dumps({"ts": 1.0, "kind": "TICK",
                                 "agent": "x"}) + "\n", encoding="utf-8")
        assert len(EventBus(p).replay()) == 1

    def test_future_stream_fails_closed(self, tmp_path):
        p = tmp_path / "e.jsonl"
        p.write_text(json.dumps({"aeos_schema": 99}) + "\n",
                     encoding="utf-8")
        with pytest.raises(SchemaError):
            EventBus(p).replay()


class TestSchemaCheckpoint:
    def test_checkpoint_roundtrip_carries_schema(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        cp.save("p", [PlanTask("t0", "build")], [])
        assert cp.load()["aeos_schema"] == 1
        assert cp.state()["pending"] == ["t0"]

    def test_future_checkpoint_fails_closed(self, tmp_path):
        p = tmp_path / "cp.json"
        p.write_text(json.dumps({"aeos_schema": 99, "plan_id": "x",
                                 "tasks": [], "done": []}),
                     encoding="utf-8")
        with pytest.raises(SchemaError):
            PlanCheckpoint(p).load()


class TestGroom:
    def ws(self, tmp_path, runs=15):
        ws = tmp_path / "ws"
        ws.mkdir(parents=True, exist_ok=True)
        (ws / ".aeos").mkdir(parents=True, exist_ok=True)
        legacy_memory(ws / ".aeos")
        ev = ws / ".aeos" / "events.jsonl"
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps({"ts": 1.0, "kind": "TICK",
                                  "agent": "x"}) + "\n", encoding="utf-8")
        (ws / ".aeos" / "checkpoint.json").write_text(
            json.dumps({"plan_id": "p", "tasks": [], "done": []}),
            encoding="utf-8")
        runs_dir = ws / ".aeos" / "runs"
        runs_dir.mkdir(parents=True)
        for i in range(runs):
            f = runs_dir / f"{1700000000 + i}-events.jsonl"
            f.write_text('{"ts": 1.0, "kind": "TICK", "agent": "x"}\n'
                         * 3, encoding="utf-8")
        return ws

    def test_groom_upgrades_archives_receipts(self, tmp_path):
        ws = self.ws(tmp_path)
        r = groom(ws, keep_runs=10)
        assert sorted(r["upgraded"]) == ["checkpoint.json", "events.jsonl",
                                         "memory.jsonl"]
        assert r["runs_kept"] == 10 and r["runs_archived"] == 5
        arch = ws / ".aeos" / "archive" / "runs"
        assert len(list(arch.glob("*-events.jsonl"))) == 5   # not deleted
        assert len(MemoryStore(ws / ".aeos" / "memory.jsonl").records) == 2
        first = json.loads((ws / ".aeos" / "events.jsonl")
                           .read_text(encoding="utf-8").splitlines()[0])
        assert first["aeos_schema"] == 1

    def test_groom_is_idempotent(self, tmp_path):
        ws = self.ws(tmp_path)
        groom(ws, keep_runs=10)
        r2 = groom(ws, keep_runs=10)
        assert r2["upgraded"] == [] and r2["runs_archived"] == 0

    def test_render_is_the_receipt(self, tmp_path):
        r = groom(self.ws(tmp_path), keep_runs=10)
        text = render(r)
        assert "GROOM" in text and "archived 5" in text

    def test_groom_command(self, tmp_path, capsys):
        from aeos.cli import main
        ws = self.ws(tmp_path)
        rc = main(["groom", "--workspace", str(ws), "--keep-runs", "10"])
        out = capsys.readouterr().out
        assert rc == 0 and "GROOM" in out and "archived 5" in out
