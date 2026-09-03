"""v29 tests: backup/restore drills + the soak."""

import json

import pytest

from aeos.backup import BackupError, create_backup, restore_backup
from aeos.contracts import MemoryClass
from aeos.memory import MemoryRecord, MemoryStore


def stateful_ws(tmp_path):
    from aeos.pipeline import reference_run
    ws = tmp_path / "ws"
    reference_run(ws, intent="Ship it per [STD-1]")
    return ws


class TestBackup:
    def test_roundtrip_restores_state_after_destruction(self, tmp_path):
        ws = stateful_ws(tmp_path)
        before = sorted(MemoryStore(ws / ".aeos" / "memory.jsonl").records)
        bak = create_backup(ws, tmp_path / "bak.tar")
        assert bak["files"] > 0 and len(bak["sha256"]) == 64

        import shutil as sh
        sh.rmtree(ws)                        # total destruction
        assert not (ws / ".aeos" / "memory.jsonl").exists()

        r = restore_backup(tmp_path / "bak.tar", ws)
        assert r["verified"] is True and r["recall_rebuilt"] is True
        after = sorted(MemoryStore(ws / ".aeos" / "memory.jsonl").records)
        assert after == before               # memory survived destruction

    def test_restored_workspace_still_runs(self, tmp_path):
        from aeos.pipeline import reference_run
        ws = stateful_ws(tmp_path)
        create_backup(ws, tmp_path / "bak.tar")
        import shutil as sh
        sh.rmtree(ws)
        restore_backup(tmp_path / "bak.tar", ws)
        b = reference_run(ws, intent="Ship it per [STD-1]")
        assert b["accepted"] is True

    def test_tampered_backup_refused_fail_closed(self, tmp_path):
        import io
        import tarfile as tf
        ws = stateful_ws(tmp_path)
        create_backup(ws, tmp_path / "bak.tar")
        # rewrite one member's bytes, keep the old manifest hash
        with tf.open(tmp_path / "bak.tar") as tar:
            members = {n: tar.extractfile(n).read()
                       for n in tar.getnames()}
        victim = next(n for n in members
                      if n.endswith("memory.jsonl"))
        members[victim] = members[victim] + b"tampered\n"
        with tf.open(tmp_path / "evil.tar", "w", format=tf.PAX_FORMAT) as tar:
            for n, data in members.items():
                info = tf.TarInfo(n)
                info.size = len(data)
                info.mtime = 0
                tar.addfile(info, io.BytesIO(data))
        with pytest.raises(BackupError, match="verification"):
            restore_backup(tmp_path / "evil.tar", tmp_path / "target")

    def test_backup_is_deterministic(self, tmp_path):
        ws = stateful_ws(tmp_path)
        a = create_backup(ws, tmp_path / "a.tar")
        b = create_backup(ws, tmp_path / "b.tar")
        assert a["sha256"] == b["sha256"]     # byte-stable evidence

    def test_locks_and_caches_never_carried(self, tmp_path):
        ws = stateful_ws(tmp_path)
        lock = ws / ".aeos" / "workspace.lock"
        lock.write_text("", encoding="utf-8")
        (ws / ".aeos" / "junk.tmp").write_text("x", encoding="utf-8")
        create_backup(ws, tmp_path / "bak.tar")
        import tarfile as tf
        names = tf.open(tmp_path / "bak.tar").getnames()
        assert not any(n.endswith("workspace.lock") for n in names)
        assert not any(n.endswith(".tmp") for n in names)
        assert not any(n.endswith("recall.sqlite") for n in names)

    def test_empty_workspace_refused(self, tmp_path):
        (tmp_path / "empty").mkdir()
        with pytest.raises(BackupError):
            create_backup(tmp_path / "empty", tmp_path / "bak.tar")


class TestSoak:
    def test_simulated_soak_passes_with_receipt(self, tmp_path):
        from aeos.soak import run_soak
        r = run_soak(tmp_path / "ws", runs=3)
        assert r["passed"] and r["accepted"] == 3
        assert r["memory_records"] > 0
        assert "simulation" in r["mode"]

    def test_live_soak_requires_opt_in(self, tmp_path):
        from aeos.soak import run_soak
        with pytest.raises(PermissionError, match="AEOS_LIVE=1"):
            run_soak(tmp_path / "ws", runs=1, live=True)


class TestStormScenario:
    def test_backup_restore_drill_in_the_storm(self, tmp_path):
        from aeos.storm import sc_backup_restore
        row = sc_backup_restore(tmp_path / "drill")
        assert row.passed, row.detail


class TestCLI:
    def test_backup_restore_commands(self, tmp_path, capsys):
        from aeos.cli import main
        ws = str(stateful_ws(tmp_path))
        assert main(["backup", "--workspace", ws,
                     "--out", str(tmp_path / "bak.tar")]) == 0
        out = capsys.readouterr().out
        assert "BACKUP" in out
        import shutil as sh
        sh.rmtree(tmp_path / "ws")
        assert main(["restore", "--backup", str(tmp_path / "bak.tar"),
                     "--workspace", ws]) == 0
        out = capsys.readouterr().out
        assert "RESTORE" in out and "verified" in out

    def test_soak_command_renders(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["soak", "--workspace", str(tmp_path / "ws"),
                   "--runs", "2"])
        out = capsys.readouterr().out
        assert rc == 0 and "SOAK" in out and "2/2" in out

    def test_soak_live_gate(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["soak", "--workspace", str(tmp_path / "ws"),
                   "--live"])
        out = capsys.readouterr().out
        assert rc == 1 and "AEOS_LIVE=1" in out
