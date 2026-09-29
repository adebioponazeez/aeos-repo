"""v40.1.0 — THE FOREMAN JOINS THE LOOP (ADR-058): repairs feed the
next plan.

The audit's last named loop gap: "the foreman heals workspaces, but
nothing it learns changes the next plan." The foreman's history was
a private ledger (.aeos/foreman/history.jsonl) the pipeline never
read. Now an APPLY-mode foreman writes its outcomes into the SAME
workspace memory the pipeline recalls (lesson::foreman::* — one
record per finding kind, newest outcome wins), the pipeline recalls
the most recent three as foreman-authority context units, and the
architect discloses them in the spec's workspace_notes. Survey mode
still writes nothing to memory: a foreman that only LOOKED learned
nothing; a foreman that ACTED owes the workspace its lesson.
"""

from __future__ import annotations

import json
from pathlib import Path

from aeos.foreman import run as foreman_run
from aeos.pipeline import reference_run


def _ws_with_runs(tmp_path: Path, n: int = 15) -> Path:
    ws = tmp_path / "ws"
    runs = ws / ".aeos" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (runs / f"{1000 + i}-events.jsonl").write_text(
            '{"kind": "x", "ts": 1.0, "detail": {}}\n', encoding="utf-8")
    return ws


def _foreman_keys(ws: Path) -> list[str]:
    mem = ws / ".aeos" / "memory.jsonl"
    if not mem.exists():
        return []
    return [json.loads(l)["key"] for l in
            mem.read_text().splitlines()
            if l and "lesson::foreman::" in l]


class TestTheForemanWritesLessons:
    def test_apply_writes_resolved_lessons_to_memory(self, tmp_path):
        ws = _ws_with_runs(tmp_path)          # 15 run files > KEEP_RUNS
        r = foreman_run(ws, apply_mode=True)
        assert r["exit_code"] == 0
        assert r["resolved"] == 1             # retention groomed
        keys = _foreman_keys(ws)
        assert keys == ["lesson::foreman::retention"]
        rec = [json.loads(l) for l in
               (ws / ".aeos" / "memory.jsonl").read_text().splitlines()
               if l and "lesson::foreman::retention" in l][0]
        assert "resolved retention" in rec["value"]
        assert rec["source"] == "foreman"

    def test_survey_never_writes_memory_lessons(self, tmp_path):
        ws = _ws_with_runs(tmp_path)
        r = foreman_run(ws, apply_mode=False)  # look, don't act
        assert r["findings"], "fixture must have findings"
        assert _foreman_keys(ws) == []
        assert not (ws / ".aeos" / "memory.jsonl").exists()

    def test_the_newest_outcome_replaces_the_stale_one(self, tmp_path):
        ws = _ws_with_runs(tmp_path)
        foreman_run(ws, apply_mode=True)       # resolves retention
        _ws_with_runs(tmp_path, 15)            # 15 more run files
        foreman_run(ws, apply_mode=True)       # resolves retention again
        keys = _foreman_keys(ws)
        assert keys.count("lesson::foreman::retention") == 1, \
            "one record per finding kind — updated, never duplicated"


class TestThePlannerReadsThem:
    def test_the_next_plan_recalls_and_discloses(self, tmp_path):
        ws = _ws_with_runs(tmp_path)
        r = foreman_run(ws, apply_mode=True)
        assert r["resolved"] == 1
        b = reference_run(ws, "foreman loop test")
        assert b["accepted"] is True
        m = b["memory"]
        assert m["foreman_lessons"] == ["lesson::foreman::retention"]
        assert m["foreman_notes_in_spec"], \
            "the architect must disclose the foreman's notes"
        spec = json.loads((ws / "spec" / "graph.json").read_text())
        assert spec["workspace_notes"] == m["foreman_notes_in_spec"]
        assert any("retention" in n for n in spec["workspace_notes"])

    def test_a_workspace_without_foreman_acts_has_no_notes(self, tmp_path):
        ws = tmp_path / "fresh"
        b = reference_run(ws)
        assert b["accepted"] is True
        assert b["memory"]["foreman_lessons"] == []
        assert b["memory"]["foreman_notes_in_spec"] == []
        spec = json.loads((ws / "spec" / "graph.json").read_text())
        assert spec["workspace_notes"] == []
