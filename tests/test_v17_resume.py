"""v17 tests: durable plans — crash, resume, side effects once."""

import pytest

from aeos.resume import PlanCheckpoint, PlanTask, ResumeNeeded, execute_plan


def tasks():
    return [PlanTask(f"t{i}", "build", f"step {i}") for i in range(5)]


class TestCheckpoint:
    def test_save_load_roundtrip(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        cp.save("plan-1", tasks(), ["t0", "t1"])
        st = cp.state()
        assert st["plan_id"] == "plan-1"
        assert st["done"] == ["t0", "t1"]
        assert st["pending"] == ["t2", "t3", "t4"]

    def test_missing_checkpoint_is_empty_state(self, tmp_path):
        st = PlanCheckpoint(tmp_path / "cp.json").state()
        assert st["pending"] == [] and st["plan_id"] is None


class TestCrashAndResume:
    def test_crash_midplan_keeps_prior_progress(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        calls = []
        with pytest.raises(ResumeNeeded):
            execute_plan("p", tasks(), lambda t: calls.append(t.id),
                         cp, fail_at="t2")
        assert cp.state()["done"] == ["t0", "t1"]

    def test_resume_executes_only_pending(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        calls = []
        with pytest.raises(ResumeNeeded):
            execute_plan("p", tasks(), lambda t: calls.append(t.id),
                         cp, fail_at="t2")
        report = execute_plan("p", tasks(), lambda t: calls.append(t.id), cp)
        assert report["executed"] == ["t2", "t3", "t4"]
        assert report["done"] == ["t0", "t1", "t2", "t3", "t4"]

    def test_side_effects_happen_exactly_once(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        calls = []
        with pytest.raises(ResumeNeeded):
            execute_plan("p", tasks(), lambda t: calls.append(t.id),
                         cp, fail_at="t3")
        execute_plan("p", tasks(), lambda t: calls.append(t.id), cp)
        assert sorted(calls) == [f"t{i}" for i in range(5)]
        assert len(calls) == len(set(calls))

    def test_completed_plan_resume_is_a_noop(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        execute_plan("p", tasks(), lambda t: None, cp)
        calls = []
        report = execute_plan("p", tasks(), lambda t: calls.append(t.id), cp)
        assert calls == [] and report["executed"] == []

    def test_progress_survives_a_new_process(self, tmp_path):
        cp = PlanCheckpoint(tmp_path / "cp.json")
        with pytest.raises(ResumeNeeded):
            execute_plan("p", tasks(), lambda t: None, cp, fail_at="t1")
        # fresh objects, same disk — the AFK reality
        cp2 = PlanCheckpoint(tmp_path / "cp.json")
        calls = []
        execute_plan("p", tasks(), lambda t: calls.append(t.id), cp2)
        assert calls == ["t1", "t2", "t3", "t4"]


class TestCLI:
    def test_resume_command_renders_recovery(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["resume", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0 and "RESUME" in out and "exactly once" in out
