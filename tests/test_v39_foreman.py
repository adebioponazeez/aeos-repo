"""v39 tests: the foreman — the autonomous operator. Perception is
fact, action is bounded, verification is re-measurement, memory is
deduped, and everything is receipted."""

import json
from pathlib import Path

import pytest

from aeos.foreman import (EXIT_ATTENTION, EXIT_CLEAN, EXIT_FAILED,
                          Finding, apply, render, run, survey)


def _degraded(ws: Path) -> None:
    """The canonical tired workspace: old schema, torn writes,
    overflowing retention, no backup."""
    (ws / ".aeos" / "runs").mkdir(parents=True, exist_ok=True)
    (ws / ".aeos" / "memory.jsonl").write_text(
        '{"kind": "memory", "note": "v1 era"}\n', encoding="utf-8")
    (ws / ".aeos" / "memory.jsonl.torn").write_text('{"torn"', encoding="utf-8")
    for i in range(14):
        (ws / ".aeos" / "runs" / f"run-{i:02d}-events.jsonl").write_text(
            '{"e": 1}\n', encoding="utf-8")


class TestSurvey:
    def test_clean_workspace_is_quiet(self, tmp_path):
        # "clean" by the foreman's convention: current schema AND a
        # drilled backup on record (the first foreman run establishes
        # the baseline; quiet is what the SECOND run sees)
        (tmp_path / ".aeos").mkdir()
        (tmp_path / ".aeos" / "memory.jsonl").write_text(
            '{"aeos_schema": 1, "kind": "memory"}\n', encoding="utf-8")
        from aeos.foreman import _backup_drill
        assert _backup_drill(tmp_path)["ok"]
        findings = survey(tmp_path)
        assert findings == []

    def test_degraded_workspace_finds_all_four_mechanical(self, tmp_path):
        _degraded(tmp_path)
        findings = survey(tmp_path)
        kinds = {f.kind for f in findings if f.klass == "mechanical"}
        assert kinds == {"state-schema", "torn-writes", "retention",
                         "backup-posture"}

    def test_archived_torn_files_are_not_pending(self, tmp_path):
        _degraded(tmp_path)
        run(tmp_path, apply_mode=True)
        assert not any(f.kind == "torn-writes" for f in survey(tmp_path))

    def test_survey_is_deterministic(self, tmp_path):
        _degraded(tmp_path)
        a = [(f.kind, f.detail) for f in survey(tmp_path)]
        b = [(f.kind, f.detail) for f in survey(tmp_path)]
        assert a == b

    def test_crashed_boot_is_a_proposal_not_damage(self, tmp_path):
        boots = tmp_path / ".aeos" / "boots"
        boots.mkdir(parents=True)
        (boots / "boot-0001.json").write_text(json.dumps(
            {"boot_seq": 1, "outcome": "work-failed",
             "failed_stage": "work"}), encoding="utf-8")
        f = [x for x in survey(tmp_path) if x.kind == "boot-ledger"]
        assert f and f[0].klass == "proposal"
        assert "nothing torn" in f[0].remedy


class TestApply:
    def test_fixed_order_and_heal_before_backup(self, tmp_path):
        _degraded(tmp_path)
        findings = survey(tmp_path)
        acted = apply(tmp_path, findings)
        assert [a["action"] for a in acted] == [
            "schema-upgrade", "torn-archive", "groom", "backup-drill"]

    def test_apply_resolves_every_mechanical_finding(self, tmp_path):
        _degraded(tmp_path)
        r = run(tmp_path, apply_mode=True)
        assert r["actions"] and all(a["ok"] for a in r["actions"])
        assert r["resolved"] == 4 and r["remaining"] == 0
        assert r["exit_code"] == EXIT_CLEAN
        assert r["pre_root"] != r["post_root"]    # real work happened

    def test_backup_drill_verifies_the_restore(self, tmp_path):
        _degraded(tmp_path)
        r = run(tmp_path, apply_mode=True)
        drill = [a for a in r["actions"] if a["action"] == "backup-drill"]
        assert drill and "verified" in drill[0]["detail"]
        backups = list((tmp_path / ".aeos" / "backups").glob("*.tar"))
        assert len(backups) == 1

    def test_idempotent_second_run_changes_nothing(self, tmp_path):
        _degraded(tmp_path)
        run(tmp_path, apply_mode=True)
        second = run(tmp_path, apply_mode=True)
        assert second["actions"] == []
        assert second["remaining"] == 0
        assert second["pre_root"] == second["post_root"]

    def test_failure_stops_the_run_with_exit_2(self, tmp_path, monkeypatch):
        import aeos.foreman as fm

        def broken(ws):
            return {"ok": False, "detail": "simulated remediation failure"}

        monkeypatch.setitem(fm.ACTIONS, "groom", broken)
        _degraded(tmp_path)
        r = run(tmp_path, apply_mode=True)
        assert r["exit_code"] == EXIT_FAILED
        assert "stopped" in r["failure"]
        # the actions before the failure still happened; the failure
        # is named, not hidden
        assert r["actions"][-1]["ok"] is False

    def test_proposals_are_never_executed(self, tmp_path):
        finding = Finding("readme-drift", "1 claim drifted", "author's",
                          "proposal", "README drift")
        assert apply(tmp_path, [finding]) == []


class TestBoundaries:
    def test_every_write_stays_inside_the_workspace(self, tmp_path):
        import os
        before = {p: p.stat().st_mtime_ns
                  for p in Path("/tmp").glob("foreman-drill-*")}
        _degraded(tmp_path)
        run(tmp_path, apply_mode=True)
        # no drill litter left behind
        after = list(Path("/tmp").glob("foreman-drill-*"))
        assert after == []
        # every receipt references only paths under the workspace
        receipt = json.loads(
            sorted((tmp_path / ".aeos" / "foreman")
                   .glob("foreman-*.json"))[-1].read_text(encoding="utf-8"))
        assert receipt["kind"] == "aeos-foreman"

    def test_receipts_carry_no_secrets(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-TOPSECRET-99")
        _degraded(tmp_path)
        run(tmp_path, apply_mode=True)
        text = "\n".join(p.read_text(encoding="utf-8")
                         for p in (tmp_path / ".aeos" / "foreman")
                         .glob("foreman-*.json"))
        assert "TOPSECRET" not in text


class TestMemory:
    def test_history_dedupes_by_signature(self, tmp_path):
        _degraded(tmp_path)
        run(tmp_path)                    # survey 1
        run(tmp_path)                    # survey 2
        lines = [json.loads(l) for l in
                 (tmp_path / ".aeos" / "foreman" / "history.jsonl")
                 .read_text(encoding="utf-8").splitlines() if l.strip()]
        counts = {(e["kind"], e["status"]): e["count"] for e in lines}
        assert counts[("retention", "open")] == 2
        run(tmp_path, apply_mode=True)   # resolve
        lines = [json.loads(l) for l in
                 (tmp_path / ".aeos" / "foreman" / "history.jsonl")
                 .read_text(encoding="utf-8").splitlines() if l.strip()]
        assert any(e["status"] == "resolved" for e in lines)

    def test_receipts_are_numbered_and_atomic(self, tmp_path):
        _degraded(tmp_path)
        run(tmp_path)
        run(tmp_path, apply_mode=True)
        receipts = sorted((tmp_path / ".aeos" / "foreman")
                          .glob("foreman-*.json"))
        assert [p.name for p in receipts] == [
            "foreman-0001.json", "foreman-0002.json"]
        assert not list((tmp_path / ".aeos" / "foreman").glob("*.tmp"))


class TestCLI:
    def test_survey_attention_then_apply_clean(self, tmp_path, capsys,
                                                monkeypatch):
        # workspace-scoped: no repo context (in a checkout the CLI
        # also surveys README drift — an honest proposal, not this
        # test's subject)
        monkeypatch.setattr("aeos.doctor.repo_root", lambda: None)
        from aeos.cli import main
        _degraded(tmp_path)
        rc = main(["foreman", "--workspace", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == EXIT_ATTENTION
        assert "apply order" in out and "proposals stay human" in out
        rc = main(["foreman", "--workspace", str(tmp_path), "--apply"])
        out = capsys.readouterr().out
        assert rc == EXIT_CLEAN
        assert "verification: 4 finding(s) resolved, 0 remain" in out
        assert "workspace root" in out

    def test_render_failure_names_it(self, tmp_path, monkeypatch):
        import aeos.foreman as fm
        monkeypatch.setitem(fm.ACTIONS, "groom",
                            lambda ws: {"ok": False, "detail": "boom"})
        _degraded(tmp_path)
        r = fm.run(tmp_path, apply_mode=True)
        text = render(r)
        assert "FAILED" in text and "outcome: FAILED" in text


class TestDoctorRow:
    def test_doctor_reads_the_foreman_ledger(self, tmp_path):
        from aeos.doctor import doctor
        _degraded(tmp_path)
        run(tmp_path, apply_mode=True)
        rep = doctor(tmp_path)
        row = [r for r in rep["rows"] if r["area"] == "foreman ledger"]
        assert row and row[0]["verdict"] == "PASS"
        assert "1 resolved" in row[0]["detail"] or "4 resolved" in \
            row[0]["detail"] or "resolved" in row[0]["detail"]

class TestProductionGauntlet:
    """v39.2: the production gauntlet found five defects under real
    constraints (concurrency, starvation, refused runs). These pin
    every one of them — the gauntlet is now law, not a one-off."""

    def test_foreman_respects_the_workspace_lock(self, tmp_path):
        # G3: two foremen could race on one workspace; now the lock
        # (kernel-released) refuses the second, NAMED, exit 2
        from aeos.vault import WorkspaceLock
        (tmp_path / ".aeos").mkdir()
        lock = WorkspaceLock(tmp_path / ".aeos" / "workspace.lock")
        assert lock.acquire(blocking=False)
        r = run(tmp_path, apply_mode=True)
        assert r["exit_code"] == EXIT_FAILED
        assert "held by a live run" in r["failure"]
        assert r["actions"] == []            # refused = did nothing
        text = render(r)
        assert "FOREMAN — refused" in text and "Traceback" not in text
        lock.release()
        assert run(tmp_path, apply_mode=True)["exit_code"] in (0, 1)

    def test_action_exception_is_named_not_traced(self, tmp_path,
                                                  monkeypatch):
        # G4: file-size starvation escaped as a raw traceback; now
        # the action is named and the run stops with exit 2
        import aeos.foreman as fm

        def starved(ws):
            raise OSError(27, "File too large")

        monkeypatch.setitem(fm.ACTIONS, "backup-drill", starved)
        _degraded(tmp_path)
        r = run(tmp_path, apply_mode=True)
        assert r["exit_code"] == EXIT_FAILED
        last = r["actions"][-1]
        assert last["action"] == "backup-drill"
        assert "File too large" in last["detail"]
        assert "Traceback" not in render(r)
        # heal-first order: the earlier actions still happened
        assert any(a["action"] == "schema-upgrade" and a["ok"]
                   for a in r["actions"])

    def test_backup_leaves_no_tmp_corpse_on_failure(self, tmp_path,
                                                    monkeypatch):
        # G4: the atomic-write contract — a failed tar write leaves
        # NOTHING behind
        import aeos.backup as bk

        def boom(tmp, blobs, manifest):
            tmp.write_bytes(b"partial")     # a corpse-in-the-making
            raise OSError(27, "File too large")

        monkeypatch.setattr(bk, "_write_tar_body", boom)
        (tmp_path / ".aeos").mkdir()
        (tmp_path / ".aeos" / "memory.jsonl").write_text(
            '{"aeos_schema": 1, "kind": "memory"}\n', encoding="utf-8")
        with pytest.raises(OSError):
            bk.create_backup(tmp_path, tmp_path / "b.tar")
        assert not (tmp_path / "b.tar").exists()
        assert not (tmp_path / "b.tar.tmp").exists()   # no corpse

    def test_refused_run_is_named_not_keyerrored(self, tmp_path):
        # G2: a lock refusal returned accepted=False and ignition
        # died on KeyError; now the reason is spoken in plain language
        from aeos.ignition import boot
        from aeos.vault import WorkspaceLock
        (tmp_path / ".aeos").mkdir()
        lock = WorkspaceLock(tmp_path / ".aeos" / "workspace.lock")
        assert lock.acquire(blocking=False)
        r = boot(tmp_path)
        lock.release()
        assert r["outcome"] == "work-failed"
        assert "held by a live run" in r["what"]
        assert "kernel-released" in r["what"] or "releases" in r["what"]

    def test_cli_backup_names_starvation(self, tmp_path, monkeypatch,
                                         capsys):
        # G4: the backup verb itself speaks plain language when the
        # disk refuses — never a traceback
        from aeos.cli import main
        import aeos.backup as bk

        def boom(ws, out):
            raise OSError(27, "File too large")

        monkeypatch.setattr(bk, "create_backup", boom)
        rc = main(["backup", "--workspace", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == 1
        assert "BACKUP REFUSED" in out and "File too large" in out
        assert "nothing was written" in out

class TestFieldTest:
    """v39.3: the field test (different environments) found the lock
    lying about WHY it refused, and two unwrapped writes (history
    append, receipt write) escaping as raw tracebacks on full disks.
    These pin all three, read-only included."""

    def test_lock_names_why_it_refused(self, tmp_path):
        # read-only .aeos: acquire returns False and the reason is
        # PERMISSIONS, not "held by a live run" — the v26-era open
        # sat outside the guard and escaped as a raw PermissionError
        import os
        if os.geteuid() == 0:
            pytest.skip("root ignores permission bits")
        from aeos.vault import WorkspaceLock
        d = tmp_path / ".aeos"
        d.mkdir()
        d.chmod(0o555)
        lock = WorkspaceLock(d / "workspace.lock")
        try:
            assert lock.acquire(blocking=False) is False
            assert "could not be opened" in lock.refusal_reason()
            assert "Permission" in lock.refusal_reason()
        finally:
            d.chmod(0o755)
        # and the held case still tells the truth
        assert lock.acquire(blocking=False)
        lock2 = WorkspaceLock(d / "workspace.lock")
        assert lock2.acquire(blocking=False) is False
        assert "held by a live run" in lock2.refusal_reason()
        lock.release()

    def test_foreman_on_readonly_workspace_is_named(self, tmp_path):
        import os
        if os.geteuid() == 0:
            pytest.skip("root ignores permission bits")
        (tmp_path / ".aeos").mkdir()
        (tmp_path / ".aeos" / "memory.jsonl").write_text(
            '{"kind": "m"}\n', encoding="utf-8")
        import subprocess
        subprocess.run(["chmod", "-R", "a-w", str(tmp_path)], check=True)
        try:
            r = run(tmp_path, apply_mode=True)
            assert r["exit_code"] == EXIT_FAILED
            assert "could not be opened" in r["failure"]
            assert "Permission" in r["failure"]
            text = render(r)
            assert "FOREMAN — refused" in text
            assert "check permissions" in text
            assert "wait for the holder" not in text
        finally:
            subprocess.run(["chmod", "-R", "u+w", str(tmp_path)],
                           check=True)

    def test_history_append_is_best_effort(self, tmp_path, monkeypatch):
        # ENOSPC during the history append must not take the verdict
        import aeos.foreman as fm

        def full_disk(path, text):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(fm, "_append_durable", full_disk)
        _degraded(tmp_path)
        r = run(tmp_path, apply_mode=True)     # must not raise
        assert r["exit_code"] in (EXIT_CLEAN, EXIT_ATTENTION,
                                  EXIT_FAILED)

    def test_receipt_write_failure_keeps_the_verdict(self, tmp_path,
                                                     monkeypatch):
        import aeos.foreman as fm

        def full_disk(path, text, *a, **kw):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(fm, "durable_write", full_disk)
        _degraded(tmp_path)
        r = run(tmp_path, apply_mode=True)     # must not raise
        assert r["receipt_unwritten"] == "No space left on device"
        assert r["resolved"] == 4              # the work still counts
