"""v39.8 — THE SPINE (ADR-055): an operator's graph executes on the
REFERENCE pipeline.

Before this, `graph --run` wired a demo roster whose handlers
fabricated PASS evidence, while the reference pipeline ran its own
hardcoded 7 tasks — two planners that never met (the audit's step-2
verdict in docs/STATE-OF-AEOS.md). These tests pin the composition
as law: same roster, same handlers, same evidence law, real
artifacts, live events, memory that accumulates — and the refusals
that keep contract law intact at the spine's door.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aeos.contracts import ActionClass
from aeos.graphlang import compile_graph
from aeos.pipeline import build_roster, reference_run

_REPO = Path(__file__).resolve().parent.parent
_SHIP = (_REPO / "examples" / "ship-graph.dot").read_text(encoding="utf-8")
_STYLE = (_REPO / "examples" / "routing.style").read_text(encoding="utf-8")


def _graph_tasks() -> list:
    return compile_graph(_SHIP, style=_STYLE)


class TestTheSpine:
    def test_operators_graph_executes_on_the_reference_pipeline(
            self, tmp_path):
        ws = tmp_path / "ws"
        bundle = reference_run(ws, "spine test", tasks=_graph_tasks(),
                               live_events=True)
        assert bundle["accepted"] is True
        assert bundle["plan_origin"] == "operator-graph"
        assert bundle["live_events"] is True
        # every task — including the nested harness — is in the bundle
        names = {d["name"] for d in bundle["states_detail"]}
        assert {"define", "research", "build", "core", "cli",
                "evaluate", "release"} <= names
        # every agent is a real contract from the reference roster
        roster = build_roster()
        assert all(d["agent"] in roster
                   for d in bundle["states_detail"])
        # REAL artifacts, not fabricated-PASS envelopes: the demo
        # roster never wrote a file in its life
        assert (ws / "seed" / "core.py").exists()
        assert (ws / "tests" / "test_core.py").exists()
        assert (ws / "evaluation" / "report.json").exists()
        verdict = json.loads(
            (ws / "evaluation" / "report.json").read_text())["verdict"]
        assert verdict == "PASS"
        # the founding metric and the governor, on the graph run
        assert bundle["leverage"] >= 1
        assert bundle["governor_reliability"] == 1.0
        # events streamed LIVE (the shopfloor's bus), not dumped after
        assert str(bundle["events_file"]).endswith("-events.jsonl")
        kinds = {json.loads(l)["kind"] for l in
                 Path(bundle["events_file"]).read_text().splitlines() if l}
        assert "task.started" in kinds and "subplan.start" in kinds

    def test_the_reference_objective_still_composes(self, tmp_path):
        bundle = reference_run(tmp_path / "ws")
        assert bundle["accepted"] is True
        assert bundle["plan_origin"] == "reference"
        assert bundle["live_events"] is False
        names = [d["name"] for d in bundle["states_detail"]]
        assert names == ["define-objective", "research", "architect",
                         "build-core", "build-cli", "evaluate", "release"]

    def test_memory_accumulates_the_graphs_own_lessons(self, tmp_path):
        ws = tmp_path / "ws"
        reference_run(ws, "spine memory test", tasks=_graph_tasks(),
                      live_events=True)
        keys = set((ws / ".aeos" / "memory.jsonl").read_text().split())
        assert any("lesson::core" in k for k in keys)
        assert any("lesson::define" in k for k in keys)


class TestContractLawAtTheDoor:
    def test_unknown_agent_is_a_named_refusal(self, tmp_path):
        bad = 'digraph bad { a [label="x", agent="stranger"]; }'
        tasks = compile_graph(bad)
        with pytest.raises(ValueError, match="not a registered contract"):
            reference_run(tmp_path / "ws", tasks=tasks)

    def test_class_outside_the_contract_is_refused(self, tmp_path):
        bad = ('digraph bad { a [label="x", agent="executive", '
               'class="WRITE"]; }')
        tasks = compile_graph(bad)
        with pytest.raises(ValueError, match="contracted for READ"):
            reference_run(tmp_path / "ws", tasks=tasks)

    def test_unknown_builder_capability_refuses_not_misbuilds(
            self, tmp_path):
        # before the spine, an unknown builder task silently fell into
        # the CLI branch and built the WRONG artifact
        bad = ('digraph bad { a [label="build a rocket", '
               'agent="builder", class="WRITE"]; }')
        tasks = compile_graph(bad)
        ws = tmp_path / "ws"
        bundle = reference_run(ws, tasks=tasks)
        assert bundle["accepted"] is False
        assert bundle["states_detail"][0]["state"] == "FAILED"
        assert not (ws / "seed" / "cli.py").exists(), \
            "unknown capability must refuse, never mis-build"


class TestTheFrontDoor:
    def test_run_command_streams_live(self, tmp_path, monkeypatch, capsys):
        from aeos.cli import main
        from aeos.stream import newest_events_file
        ws = tmp_path / "ws"
        monkeypatch.setattr(
            "sys.argv", ["aeos", "run", "--graph",
                         str(_REPO / "examples" / "ship-graph.dot"),
                         "--style", str(_REPO / "examples" / "routing.style"),
                         "--workspace", str(ws)])
        assert main() == 0
        out = capsys.readouterr().out
        assert "SPINE RUN — ACCEPTED" in out
        assert "plan:      operator-graph" in out
        assert "events (live):" in out and "shopfloor:" in out
        ev = newest_events_file(ws)
        assert ev is not None
        kinds = {json.loads(l)["kind"] for l in
                 ev.read_text().splitlines() if l}
        assert "task.started" in kinds and "subplan.start" in kinds

    def test_graph_run_uses_the_spine_no_demo_roster(
            self, tmp_path, monkeypatch, capsys):
        from aeos.cli import main
        ws = tmp_path / "ws"
        monkeypatch.setattr(
            "sys.argv", ["aeos", "graph", "--file",
                         str(_REPO / "examples" / "ship-graph.dot"),
                         "--run", "--workspace", str(ws)])
        assert main() == 0
        out = capsys.readouterr().out
        assert "SPINE RUN — ACCEPTED" in out    # the demo roster is gone
        assert "plan:      operator-graph" in out
        assert (ws / "seed" / "core.py").exists(), \
            "graph --run must leave real artifacts (product path)"

    def test_run_refuses_missing_graph_named(self, tmp_path, monkeypatch,
                                             capsys):
        from aeos.cli import main
        monkeypatch.setattr(
            "sys.argv", ["aeos", "run", "--graph", "/nope/none.dot",
                         "--workspace", str(tmp_path)])
        assert main() == 2
        assert "RUN REFUSED" in capsys.readouterr().out
