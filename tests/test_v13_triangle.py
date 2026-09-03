"""v13 tests: the Control–Cost–Speed triangle — dials, floors, measurement."""

import json
import pytest
from pathlib import Path

from aeos.contracts import AutonomyLevel
from aeos.observability import EventLog
from aeos.triangle import (FLOOR_GATES, PROFILE_PRESETS, RunProfile,
                           TriangleReport, measure_triangle)


class TestProfiles:
    def test_four_stances_exist(self):
        assert sorted(PROFILE_PRESETS) == ["balanced", "control", "cost", "speed"]

    def test_control_is_the_slow_checked_stance(self):
        p = RunProfile.preset("control")
        assert p.autonomy_ceiling is AutonomyLevel.L3_CHECKPOINTED_AUTONOMY
        assert p.strict_gates and p.isolation == "process" and p.fusion
        assert p.max_workers <= 2                      # serialized on purpose

    def test_speed_is_wide_and_lean(self):
        p = RunProfile.preset("speed")
        assert p.max_workers >= 8
        assert p.autonomy_ceiling is AutonomyLevel.L5_CONTINUOUS_AUTONOMY
        assert not p.strict_gates

    def test_cost_tightens_the_purse(self):
        assert RunProfile.preset("cost").budget_usd == 0.25

    def test_unknown_profile_rejected(self):
        with pytest.raises(ValueError, match="unknown profile"):
            RunProfile.preset("yolo")

    def test_no_profile_starts_above_l5(self):
        with pytest.raises(ValueError, match="earned by evidence"):
            RunProfile.preset("balanced",
                              autonomy_ceiling=AutonomyLevel.L7_CAPABILITY_DISCOVERY)

    def test_bad_knobs_rejected(self):
        with pytest.raises(ValueError, match="max_workers"):
            RunProfile.preset("speed", max_workers=99)
        with pytest.raises(ValueError, match="budget must be positive"):
            RunProfile.preset("cost", budget_usd=0.0)


class TestFloors:
    def test_floor_gates_survive_every_stance(self):
        for name in PROFILE_PRESETS:
            gates = RunProfile.preset(name).gate_names(
                stock=["artifacts_exist", "claims_are_backed", "json_gate"],
                strict_extra=["tests_pass", "schema"])
            assert FLOOR_GATES <= set(gates), name

    def test_floor_gates_added_even_if_stock_forgets_them(self):
        p = RunProfile.preset("speed")
        gates = p.gate_names(stock=["some_custom_gate"], strict_extra=[])
        assert "artifacts_exist" in gates and "claims_are_backed" in gates


class TestMeasurement:
    def _events(self, gates=7, boundaries=7, checkpoints=2, escalations=0):
        log = EventLog()
        for _ in range(gates):
            log.emit("gate.checked", v="PASS")
        for _ in range(boundaries):
            log.emit("boundary.ok", agent="a")
        for _ in range(checkpoints):
            log.emit("governor.checkpoint", x=1)
        for _ in range(escalations):
            log.emit("task.escalated", task="t")
        for _ in range(7):
            log.emit("task.succeeded", task="t")
        return log.events()

    def test_control_stance_measures_high_control(self):
        p = RunProfile.preset("control")
        tri = measure_triangle(profile=p, events=self._events(),
                               cost_usd=0.4, tokens=5000, duration_s=4.0,
                               tasks=7, waves=7, isolation_used="process")
        assert tri.control > 0.75
        assert "bought verification" in tri.components["trade"]
        assert tri.speed_tasks_per_s == pytest.approx(1.75)

    def test_speed_stance_measures_fast(self):
        p = RunProfile.preset("speed")
        tri = measure_triangle(profile=p, events=self._events(gates=7, boundaries=7,
                                                              checkpoints=0),
                               cost_usd=0.1, tokens=3000, duration_s=0.5,
                               tasks=7, waves=3)
        assert tri.speed_tasks_per_s == pytest.approx(14.0)
        assert "paid with autonomy" in tri.components["trade"]

    def test_cost_stance_names_its_trade(self):
        tri = measure_triangle(profile=RunProfile.preset("cost"),
                               events=self._events(), cost_usd=0.02,
                               tokens=800, duration_s=3.0, tasks=7, waves=7)
        assert "capped at $0.25" in tri.components["trade"]

    def test_rendered_report_names_all_three_axes(self):
        tri = measure_triangle(profile=RunProfile.preset("balanced"),
                               events=self._events(), cost_usd=0.0,
                               tokens=0, duration_s=1.0, tasks=7, waves=7)
        text = tri.render()
        for axis in ("CONTROL", "COST", "SPEED", "THE TRADE"):
            assert axis in text


class TestEndToEnd:
    @pytest.mark.parametrize("profile", ["control", "balanced", "speed", "cost"])
    def test_reference_run_under_every_stance(self, tmp_path, profile):
        from aeos.pipeline import reference_run
        bundle = reference_run(tmp_path / profile, intent="Ship it",
                               profile=profile)
        assert bundle["accepted"] is True
        t = bundle["triangle"]
        assert 0.0 <= t["control"] <= 1.0
        assert t["speed_tasks_per_s"] > 0
        assert bundle["profile"]["name"] == profile

    def test_control_measures_more_control_than_speed(self, tmp_path):
        from aeos.pipeline import reference_run
        slow = reference_run(tmp_path / "c", profile="control")["triangle"]
        fast = reference_run(tmp_path / "s", profile="speed")["triangle"]
        # the law of the thumbnail, measured: more control, less speed
        assert slow["control"] >= fast["control"]

    def test_triangle_command_roundtrip(self, tmp_path, capsys):
        from aeos.pipeline import reference_run
        reference_run(tmp_path / "ws", profile="control")
        from aeos.cli import main
        rc = main(["triangle", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0 and "TRIANGLE" in out and "CONTROL" in out
