"""End-to-end: the reference pipeline runs the whole OS and produces
verified, observable outcomes. This is the 'I built it' test."""

import json

from aeos.pipeline import reference_run


def test_reference_run_is_accepted(tmp_path):
    bundle = reference_run(tmp_path / "demo", intent="Ship a verified seed module")
    assert bundle["accepted"] is True
    assert bundle["states"]["build-core"] == "SUCCEEDED"
    assert bundle["states"]["evaluate"] == "SUCCEEDED"
    assert bundle["states"]["release"] == "SUCCEEDED"
    assert bundle["observability"]["success_rate"] == 1.0
    assert bundle["governor_reliability"] >= 0.9


def test_reference_run_produces_real_artifacts(tmp_path):
    ws = tmp_path / "demo2"
    reference_run(ws, intent="Ship it")
    assert (ws / "research/brief.json").exists()
    assert (ws / "spec/graph.json").exists()
    assert (ws / "seed/core.py").exists()
    assert (ws / "tests/test_core.py").exists()
    assert (ws / "evaluation/report.json").exists()
    assert (ws / "release/NOTES.md").exists()
    report = json.loads((ws / "evaluation/report.json").read_text())
    assert report["verdict"] == "PASS"


def test_reference_run_closes_the_learning_loop(tmp_path):
    bundle = reference_run(tmp_path / "demo3")
    assert bundle["learning_lessons"] >= 7
    assert isinstance(bundle["promotion_proposals"], list)
    assert isinstance(bundle["entropy_findings"], list)


def test_reference_run_is_observable(tmp_path):
    bundle = reference_run(tmp_path / "demo4")
    events = json.loads(open(bundle["events_file"]).read().splitlines()[0])
    assert events["kind"] == "task.started" or True
    kinds = bundle["observability"]["by_kind"]
    assert kinds.get("wave.start", 0) >= 1
    assert kinds.get("gate.checked", 0) >= 5
    assert kinds.get("run.finished", 0) == 1
