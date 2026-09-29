"""v39.9 — THE LOOP CLOSES (ADR-056): this run's lessons reach the
next run's plan.

The audit's spine step 9 verdict: "foreman heals workspaces, but
nothing it learns changes the next plan." These tests pin the
closure: before a plan executes, lesson/proven/semantic records
whose keys name the plan's tasks or agents are recalled into the
context OS (memory authority, capped at 8, confidence-ordered);
the architect CITES what it applied in the spec artifact; the
bundle records both. What this does NOT claim: behavioral change
— under the EchoModel, applying a lesson means citing it in the
plan's context and spec. A real model acting on lessons is First
Light (operator opt-in), still open.
"""

from __future__ import annotations

import json
from pathlib import Path

from aeos.graphlang import compile_graph
from aeos.pipeline import reference_run

_REPO = Path(__file__).resolve().parent.parent
_SHIP = (_REPO / "examples" / "ship-graph.dot").read_text(encoding="utf-8")
_STYLE = (_REPO / "examples" / "routing.style").read_text(encoding="utf-8")


class TestTheLoopCloses:
    def test_the_second_plan_inherits_the_firsts_lessons(self, tmp_path):
        ws = tmp_path / "ws"
        run1 = reference_run(ws)
        assert run1["accepted"] is True
        # a fresh workspace recalls the DISCLOSED prior-run seeds
        assert run1["memory"]["recalled_lessons"]
        assert all(k.startswith(("lesson::", "proven::", "semantic::"))
                   for k in run1["memory"]["recalled_lessons"])

        run2 = reference_run(ws)
        assert run2["accepted"] is True
        # the honest compounding proof: run 2 recalls records that
        # DID NOT EXIST at run 1's recall time — run 1's own
        # evidence-validated lessons (proven::, written post-run)
        new = (set(run2["memory"]["recalled_lessons"])
               - set(run1["memory"]["recalled_lessons"]))
        assert new, "run 2 must recall lessons run 1 wrote"
        assert any(k.startswith("proven::") for k in new)
        # the planner cites what it applied — in the bundle AND in
        # the spec artifact on disk
        assert run2["memory"]["applied_to_spec"]
        spec = json.loads((ws / "spec" / "graph.json").read_text())
        assert spec["prior_lessons"] == run2["memory"]["applied_to_spec"]

    def test_graph_runs_share_the_loop(self, tmp_path):
        ws = tmp_path / "ws"
        tasks = compile_graph(_SHIP, style=_STYLE)
        run1 = reference_run(ws, "graph loop", tasks=tasks)
        assert run1["accepted"] is True
        run2 = reference_run(ws, "graph loop", tasks=tasks)
        assert run2["accepted"] is True
        # run 2 recalls run 1's nested-harness lessons (core/cli)
        assert any(("core" in k or "cli" in k)
                   for k in run2["memory"]["recalled_lessons"])
        # graph plans have no architect node: lessons enter context;
        # only the reference plan's architect cites (disclosed in ADR)

    def test_recall_is_scoped_and_capped(self, tmp_path):
        ws = tmp_path / "ws"
        b = reference_run(ws)
        assert b["accepted"] is True
        assert len(b["memory"]["recalled_lessons"]) <= 8
        assert all(k.startswith(("lesson::", "proven::", "semantic::"))
                   for k in b["memory"]["recalled_lessons"])

    def test_the_front_door_prints_the_loop(self, tmp_path, monkeypatch,
                                            capsys):
        from aeos.cli import main
        ws = tmp_path / "ws"
        for _ in range(2):
            monkeypatch.setattr("sys.argv",
                                ["aeos", "run", "--workspace", str(ws)])
            assert main() == 0
        out = capsys.readouterr().out
        assert "memory:" in out
        assert "recalled from prior runs" in out
        assert "cited in the spec" in out
