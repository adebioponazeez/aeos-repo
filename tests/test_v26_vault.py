"""v26 tests: the vault — atomicity, quarantine, locks, blackout."""

import json

import pytest

from aeos.contracts import MemoryClass
from aeos.fleet import EventBus
from aeos.memory import MemoryRecord, MemoryStore
from aeos.vault import (BlackoutError, WorkspaceLock, durable_write,
                        environment_scan, load_jsonl_tolerant,
                        quarantine_torn, socket_blackout)


def sem_store(tmp_path, n=2):
    store = MemoryStore(tmp_path / "m.jsonl")
    for i in range(n):
        store.write(MemoryRecord(key=f"semantic::k{i}",
                                 mclass=MemoryClass.SEMANTIC,
                                 value=f"lesson {i}", source="t",
                                 evidence=["e"]))
    return store


class TestDurableWrite:
    def test_write_roundtrips_bytes(self, tmp_path):
        p = durable_write(tmp_path / "a" / "f.json", '{"x": 1}\n')
        assert p.read_text(encoding="utf-8") == '{"x": 1}\n'

    def test_no_tmp_left_behind(self, tmp_path):
        durable_write(tmp_path / "f.json", "data")
        leftovers = [q.name for q in tmp_path.iterdir()
                     if q.name.endswith(".tmp")]
        assert leftovers == []

    def test_failed_rename_leaves_original_intact(self, tmp_path,
                                                  monkeypatch):
        import os as _os
        p = tmp_path / "f.json"
        durable_write(p, "ORIGINAL")
        real = _os.replace

        def boom(*a, **k):
            raise OSError(28, "No space left on device")
        monkeypatch.setattr(_os, "replace", boom)
        with pytest.raises(OSError):
            durable_write(p, "SHOULD NEVER LAND")
        monkeypatch.setattr(_os, "replace", real)
        assert p.read_text(encoding="utf-8") == "ORIGINAL"


class TestTolerance:
    def test_torn_tail_quarantined_not_fatal(self, tmp_path):
        store = sem_store(tmp_path)
        path = tmp_path / "m.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write('{"key": "semantic::torn", "value": "halfw')  # cut
        reloaded = MemoryStore(path)
        assert len(reloaded.records) == 2          # survivors intact
        assert reloaded.torn_lines == 1
        assert (tmp_path / "m.jsonl.torn").exists()  # forensics kept

    def test_garbage_line_quarantined(self, tmp_path):
        store = sem_store(tmp_path, n=1)
        path = tmp_path / "m.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write("<<<disk garbage>>>\n")
        reloaded = MemoryStore(path)
        assert len(reloaded.records) == 1 and reloaded.torn_lines == 1

    def test_memory_flush_is_atomic_survivor(self, tmp_path):
        path = tmp_path / "m.jsonl"
        sem_store(tmp_path, n=3)
        good = path.read_text(encoding="utf-8")
        MemoryStore(path)._flush()            # reload + re-flush: identity
        assert path.read_text(encoding="utf-8") == good

    def test_fleet_replay_survives_torn_tail(self, tmp_path):
        bus = EventBus(tmp_path / "e.jsonl")
        bus.publish("AGENT_REGISTERED", "a")
        with bus.path.open("a", encoding="utf-8") as fh:
            fh.write('{"ts": 1.0, "kind": "TORN')     # power cut
        events = EventBus(tmp_path / "e.jsonl").replay()
        assert [e.kind for e in events] == ["AGENT_REGISTERED"]
        assert (tmp_path / "e.jsonl.torn").exists()

    def test_load_jsonl_tolerant_counts(self, tmp_path):
        p = tmp_path / "l.jsonl"
        p.write_text('{"a": 1}\nnot json\n{"b": 2}\n\n', encoding="utf-8")
        good, torn = load_jsonl_tolerant(p)
        assert good == [{"a": 1}, {"b": 2}] and len(torn) == 1
        assert quarantine_torn(p, torn) is not None


class TestWorkspaceLock:
    def test_second_acquire_is_refused(self, tmp_path):
        a = WorkspaceLock(tmp_path / "l.lock")
        b = WorkspaceLock(tmp_path / "l.lock")
        assert a.acquire() is True
        assert b.acquire() is False          # held: one run at a time
        a.release()
        assert b.acquire() is True           # released: runnable again
        b.release()

    def test_lock_context(self, tmp_path):
        with WorkspaceLock(tmp_path / "l.lock"):
            other = WorkspaceLock(tmp_path / "l.lock")
            assert other.acquire() is False
        other2 = WorkspaceLock(tmp_path / "l.lock")
        assert other2.acquire() is True
        other2.release()

    def test_locked_workspace_refuses_run(self, tmp_path):
        from aeos.pipeline import reference_run
        ws = tmp_path / "ws"
        ws.mkdir()
        with WorkspaceLock(ws / ".aeos" / "workspace.lock"):
            b = reference_run(ws, intent="Ship it")
        assert b["accepted"] is False
        assert "locked" in b["reason"]

    def test_killed_holder_cannot_strand_the_workspace(self, tmp_path):
        """The kernel releases flock on death — no stale locks, ever."""
        import subprocess
        import sys
        holder = subprocess.Popen([
            sys.executable, "-c",
            "import fcntl, sys, time\n"
            "fh = open(sys.argv[1], 'a+')\n"
            "fcntl.flock(fh.fileno(), fcntl.LOCK_EX)\n"
            "print('held', flush=True)\n"
            "time.sleep(30)\n", str(tmp_path / "l.lock")],
            stdout=subprocess.PIPE, text=True)
        holder.stdout.readline()               # wait for 'held'
        holder.kill()                          # SIGKILL, no cleanup ran
        holder.wait()
        fresh = WorkspaceLock(tmp_path / "l.lock")
        assert fresh.acquire() is True         # released by the kernel
        fresh.release()


class TestBlackoutAndEnvironment:
    def test_full_run_makes_zero_socket_calls(self, tmp_path):
        from aeos.pipeline import reference_run
        from aeos.recall import RecallIndex
        with socket_blackout():
            b = reference_run(tmp_path / "ws", intent="Ship it")
            assert b["accepted"] is True
            store = MemoryStore(tmp_path / "ws" / ".aeos" /
                                "memory.jsonl")
            idx = RecallIndex(str(tmp_path / "r.sqlite"), store)
            idx.build()
            assert idx.recall("deploy").layers
            idx.close()
            EventBus(tmp_path / "e.jsonl").publish("TICK", "x")

    def test_blackout_catches_network_use(self):
        with pytest.raises(BlackoutError):
            with socket_blackout():
                import socket
                socket.create_connection(("example.com", 80), 0.2)

    def test_environment_scan_never_raises_never_dials(self, tmp_path):
        scan = environment_scan(tmp_path)
        assert "disk_free_mb" in scan and "cpu_count" in scan
        assert scan["network"].startswith("not probed")

    def test_bundle_carries_environment_truth(self, tmp_path):
        from aeos.pipeline import reference_run
        b = reference_run(tmp_path / "ws", intent="Ship it")
        assert "disk_free_mb" in b["environment"]

    def test_rerun_on_same_workspace_is_safe(self, tmp_path):
        from aeos.pipeline import reference_run
        ws = tmp_path / "ws"
        first = reference_run(ws, intent="Ship it")
        second = reference_run(ws, intent="Ship it")
        assert first["accepted"] is True and second["accepted"] is True
