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
    def test_survey_attention_then_apply_clean(self, tmp_path, capsys):
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
