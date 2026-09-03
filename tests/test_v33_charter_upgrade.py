"""v33 tests: the charter machine-checked + the cross-version upgrade
drill — a genuine v27-era workspace must serve at v33."""

import json

import pytest

from aeos.doctor import charter_check, doctor


REPO = pytest.fixture(lambda: __import__("pathlib").Path(__file__).resolve().parents[1])


class TestCharterCheck:
    def test_charter_is_load_bearing(self, REPO):
        verdict, detail = charter_check(REPO / "docs" / "PRINCIPLES.md",
                                        REPO / "tests")
        assert verdict == "PASS", detail
        assert "cited test" in detail

    def test_missing_cited_test_fails(self, tmp_path):
        (tmp_path / "P.md").write_text(
            "| 1 | Law | mechanism | `test_never_written_anywhere` |",
            encoding="utf-8")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_x.py").write_text("def test_ok(): pass\n",
                                                      encoding="utf-8")
        verdict, detail = charter_check(tmp_path / "P.md",
                                        tmp_path / "tests")
        assert verdict == "FAIL" and "test_never_written_anywhere" in detail

    def test_absent_charter_warns_not_fails(self, tmp_path):
        verdict, _ = charter_check(tmp_path / "nope.md", tmp_path)
        assert verdict == "WARN"

    def test_doctor_includes_the_charter_row(self):
        rep = doctor()
        areas = [r["area"] for r in rep["rows"]]
        assert "charter is load-bearing" in areas
        row = next(r for r in rep["rows"]
                   if r["area"] == "charter is load-bearing")
        assert row["verdict"] == "PASS"


def legacy_v27_workspace(ws):
    """A genuine v27-era workspace: no schema headers anywhere."""
    aeos = ws / ".aeos"
    aeos.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({
        "key": f"lesson::research::{i}", "value": "research: SUCCEEDED "
        "via sourced brief", "mclass": "EPISODIC", "source": "prior-run",
        "confidence": 0.6, "created_at": 1780000000.0,
        "expires_at": None, "evidence": []}, sort_keys=True)
        for i in range(4)]
    lines.append(json.dumps({
        "key": "semantic::research", "value": "research: sourced brief; "
        "validated 4x", "mclass": "SEMANTIC", "source": "distiller",
        "confidence": 0.8, "created_at": 1780000001.0, "expires_at": None,
        "evidence": ["distilled from 4 episodes"]}, sort_keys=True))
    (aeos / "memory.jsonl").write_text("\n".join(lines) + "\n",
                                       encoding="utf-8")
    (aeos / "events.jsonl").write_text(json.dumps(
        {"ts": 1780000002.0, "kind": "AGENT_REGISTERED", "agent": "scout",
         "detail": "role=research"}) + "\n", encoding="utf-8")
    (aeos / "checkpoint.json").write_text(json.dumps(
        {"plan_id": "old", "tasks": [{"id": "t0", "kind": "build",
                                      "detail": ""}], "done": ["t0"]}),
        encoding="utf-8")
    runs = aeos / "runs"
    runs.mkdir(exist_ok=True)
    for i in range(12):
        (runs / f"{1780000000 + i}-events.jsonl").write_text(
            '{"ts": 1.0, "kind": "TICK", "agent": "x"}\n', encoding="utf-8")
    return ws


class TestUpgradeDrill:
    def test_v27_state_serves_at_v33(self, tmp_path):
        """Load -> groom -> run -> doctor: the whole upgrade path."""
        from aeos.groom import groom
        ws = legacy_v27_workspace(tmp_path / "ancient")

        # legacy loads (back-compat, no rewrite on read)
        from aeos.fleet import EventBus
        from aeos.memory import MemoryStore
        assert len(MemoryStore(ws / ".aeos" / "memory.jsonl").records) == 5
        assert len(EventBus(ws / ".aeos" / "events.jsonl").replay()) == 1

        # groom upgrades in place + archives beyond 10 runs
        r = groom(ws, keep_runs=10)
        assert sorted(r["upgraded"]) == ["checkpoint.json", "events.jsonl",
                                         "memory.jsonl"]
        assert r["runs_archived"] == 2 and r["runs_kept"] == 10

        # the upgraded store still serves, with its header
        first = json.loads((ws / ".aeos" / "memory.jsonl")
                           .read_text(encoding="utf-8").splitlines()[0])
        assert first["aeos_schema"] == 1

        # a fresh run on the upgraded workspace is accepted
        from aeos.pipeline import reference_run
        b = reference_run(ws, intent="Ship it per [STD-1]")
        assert b["accepted"] is True

        # doctor: zero failures on the ancient-healed workspace
        rep = doctor(ws)
        assert rep["failed"] == 0, rep["rows"]

    def test_healed_workspace_backs_up_and_restores(self, tmp_path):
        from aeos.backup import create_backup, restore_backup
        from aeos.groom import groom
        from aeos.memory import MemoryStore
        ws = legacy_v27_workspace(tmp_path / "old2")
        groom(ws, keep_runs=10)
        before = sorted(MemoryStore(ws / ".aeos" / "memory.jsonl").records)
        create_backup(ws, tmp_path / "ancient.tar")
        import shutil as sh
        sh.rmtree(ws)
        restore_backup(tmp_path / "ancient.tar", ws)
        after = sorted(MemoryStore(ws / ".aeos" / "memory.jsonl").records)
        assert after == before

    def test_future_state_still_fails_closed(self, tmp_path):
        ws = tmp_path / "future"
        (ws / ".aeos").mkdir(parents=True)
        (ws / ".aeos" / "memory.jsonl").write_text(
            json.dumps({"aeos_schema": 99}) + "\n", encoding="utf-8")
        rep = doctor(ws)
        row = next(r for r in rep["rows"] if r["area"] == "memory schema")
        assert row["verdict"] == "FAIL"
