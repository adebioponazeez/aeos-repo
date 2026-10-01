"""v40.4.0 — TEST-QUALITY AUDIT (ADR-061): the suite must BITE.

Method (mechanical, not narrative): four one-line mutations neutered
real product laws and the full suite counted the failures:

    M1  evidence gates off (evaluator runs no gates)      -> 69 fail
    M2  autonomy level-gates off                          -> 11 fail
    M3  write-boundary wiring off (pipeline.bounded)      ->  0 fail  HOLE
    M4  secret redaction off (EventLog.redact)            ->  2 fail  thin

This file pins the hole (M3) and thickens the thin spot (M4): the
boundary law was tested at the mechanism level (harness.enforce_
boundary) and in the companions' wiring, but NOT through the
reference pipeline's bounded() wrapper — a regression that
disconnected the wrapper would have shipped silently. Found by the
audit, fixed here, and the audit doc records the method.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from aeos.contracts import ActionClass, TaskSpec


class TestMutationSensitivityPins:
    def test_m3_the_pipelines_boundary_wiring_bites(self, tmp_path):
        # M3 regression: drive the REAL pipeline wiring with a roster
        # whose builder is contracted for nowhere/* — the real builder
        # writes seed/*, bounded() must revert it, name it, and the
        # run must refuse. Before this test, disconnecting bounded()
        # from enforce_boundary shipped silently (0 failures).
        import aeos.pipeline as pipeline
        roster = pipeline.build_roster()
        roster["builder"] = dataclasses.replace(
            roster["builder"], writes=["nowhere/*"])
        orig = pipeline.build_roster
        pipeline.build_roster = lambda: roster
        try:
            tasks = [TaskSpec(
                name="build-core",
                description="Implement the core module plus its tests",
                agent="builder", action_class=ActionClass.WRITE)]
            b = pipeline.reference_run(tmp_path / "ws", tasks=tasks)
        finally:
            pipeline.build_roster = orig
        assert b["accepted"] is False
        assert b["states_detail"][0]["state"] == "FAILED"
        events = Path(b["events_file"]).read_text(encoding="utf-8")
        assert "boundary.violation" in events, \
            "the violation must be NAMED on the event log"
        assert not (tmp_path / "ws" / "seed" / "core.py").exists(), \
            "the out-of-boundary write must be reverted"

    def test_m3_the_law_applies_at_the_real_boundary_too(self, tmp_path):
        # the honest control: with the REAL roster (writes=seed/*),
        # the same run succeeds — the pin above bites on the WIRING,
        # not on the builder's legitimate work
        import aeos.pipeline as pipeline
        tasks = [TaskSpec(
            name="build-core",
            description="Implement the core module plus its tests",
            agent="builder", action_class=ActionClass.WRITE)]
        b = pipeline.reference_run(tmp_path / "ws2", tasks=tasks)
        assert b["accepted"] is True
        assert (tmp_path / "ws2" / "seed" / "core.py").exists()

    def test_m4_secret_redaction_pinned_through_the_bus(self, tmp_path):
        # M4 thickening: redaction pinned at the BUS surface — the
        # file the shopfloor streams must never carry a secret
        from aeos.observability import EventLog
        sink = tmp_path / "bus-events.jsonl"
        log = EventLog(sink=sink)
        log.emit("probe", api_key="sk-super-secret-value",
                 authorization="Bearer nope", task="t")
        text = sink.read_text(encoding="utf-8")
        assert "sk-super-secret-value" not in text
        assert "Bearer nope" not in text
        assert "[REDACTED]" in text
