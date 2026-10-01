"""v40.3.0 — THE OFFICIAL SEAM (ADR-060): persistence is typed, not
monkey-patched.

The audit's register of structural debt: "persistence via
monkey-patch (runtime.py)". attach_persistence wrapped the
orchestrator's private _execute_task from outside — invisible to
type checkers, fragile against signature drift, and it ran only on
normal returns. Now the orchestrator owns the seam:
`on_task_settled` fires after EVERY task transition — success,
failure, escalation, veto, subplan — in a finally, so even an
interrupt that blows past the handlers records the attempt.
"""

from __future__ import annotations

from pathlib import Path

from aeos.contracts import ActionClass, AgentSpec, TaskSpec, TaskState
from aeos.evaluation import Evaluator
from aeos.governor import Governor
from aeos.models import EchoModel
from aeos.observability import EventLog
from aeos.orchestrator import Orchestrator


def _spec(name="a", *classes):
    return AgentSpec(
        name=name, mission="m", inputs=["i"], outputs=["o"],
        tools=["t"], constraints=["c"], success_criteria=["s"],
        evaluation_criteria=["e"], escalation_conditions=["x"],
        termination_conditions=["t"], writes=[],
        action_classes=list(classes) or [ActionClass.READ])


def _orch(ws, handler, seam=None, hooks=None):
    return Orchestrator(
        agents={"a": _spec("a", ActionClass.READ, ActionClass.WRITE)},
        handlers={"a": handler}, model=EchoModel(),
        governor=Governor(log=EventLog()), evaluator=Evaluator(),
        log=EventLog(), workspace=ws, max_workers=1,
        hooks=hooks, on_task_settled=seam)


def _ok(task, orch):
    from aeos.contracts import Envelope
    env = Envelope(agent="a", objective=task.description, claims=["ok"])
    env.add_evidence("ran", "exit 0")
    return env


class TestTheSeamFiresOnEverySettle:
    def test_success_settles_the_seam(self, tmp_path):
        seen = []
        orch = _orch(tmp_path, _ok, seam=lambda t: seen.append(
            (t.name, t.state)))
        tasks = [TaskSpec(name="t1", description="d", agent="a")]
        orch.run("obj", tasks, repair=False)
        assert seen == [("t1", TaskState.SUCCEEDED)]

    def test_failure_settles_the_seam(self, tmp_path):
        def boom(task, orch):
            raise RuntimeError("handler exploded")

        seen = []
        orch = _orch(tmp_path, boom, seam=lambda t: seen.append(
            (t.name, t.state)))
        tasks = [TaskSpec(name="t1", description="d", agent="a")]
        orch.run("obj", tasks, repair=False)
        assert seen and seen[0] == ("t1", TaskState.FAILED)

    def test_veto_settles_the_seam(self, tmp_path):
        from aeos.hooks import BUS, HookVeto

        def guard(payload):
            raise HookVeto("not on my watch")

        reg = BUS.register("task.pre", guard)
        try:
            seen = []
            orch = _orch(tmp_path, _ok, seam=lambda t: seen.append(
                (t.name, t.state)))
            tasks = [TaskSpec(name="t1", description="d", agent="a")]
            orch.run("obj", tasks, repair=False)
            assert seen and seen[0] == ("t1", TaskState.ESCALATED)
        finally:
            BUS.unregister(reg)

    def test_subplan_parent_settles_the_seam(self, tmp_path):
        seen = []
        orch = _orch(tmp_path, _ok, seam=lambda t: seen.append(
            (t.name, t.state)))
        tasks = [TaskSpec(
            name="parent", description="d", agent="a",
            subplan=[TaskSpec(name="child", description="d",
                              agent="a")])]
        orch.run("obj", tasks, repair=False)
        names = [n for n, _ in seen]
        # the CHILD settles first (inside the nested harness), then
        # the parent — both through the same seam
        assert names == ["child", "parent"]
        assert all(s is TaskState.SUCCEEDED for _, s in seen)

    def test_an_interrupt_still_records_the_attempt(self, tmp_path):
        # the seam runs in a finally: KeyboardInterrupt blows past
        # the handlers' except Exception — and the attempt is still
        # recorded. This is the durability improvement the
        # monkey-patch could not offer (it ran only on normal
        # returns).
        def interrupt(task, orch):
            raise KeyboardInterrupt("operator pressed Ctrl-C")

        seen = []
        orch = _orch(tmp_path, interrupt, seam=lambda t: seen.append(
            (t.name, t.state, t.attempts)))
        tasks = [TaskSpec(name="t1", description="d", agent="a")]
        try:
            orch.run("obj", tasks, repair=False)
        except KeyboardInterrupt:
            pass
        assert seen and seen[0][0] == "t1" and seen[0][2] == 1


class TestAttachPersistenceUsesTheSeam:
    def test_no_private_method_is_wrapped(self, tmp_path):
        from aeos.runtime import RunStore, attach_persistence
        store = RunStore(tmp_path)
        orch = _orch(tmp_path, _ok)
        attach_persistence(orch, "r1", store, "obj",
                           [TaskSpec(name="t1", description="d",
                                     agent="a")])
        # the old monkey-patch lived in the instance dict; the seam
        # leaves the method on the class, untouched
        assert "_execute_task" not in orch.__dict__, \
            "persistence must not wrap the private method (ADR-060)"
        assert callable(orch.on_task_settled)

    def test_states_persist_through_the_seam(self, tmp_path):
        from aeos.runtime import RunStore, attach_persistence
        store = RunStore(tmp_path)

        def flaky(task, orch):
            raise RuntimeError("crash mid-run")

        orch = _orch(tmp_path / "ws", flaky)
        tasks = [TaskSpec(name="only", description="d", agent="a")]
        attach_persistence(orch, "r2", store, "obj", tasks)
        report = orch.run("obj", tasks, repair=False)
        assert report.states["only"] is TaskState.FAILED
        assert store.load("r2").tasks[0].state is TaskState.FAILED

    def test_the_spine_runs_unseamed_and_unchanged(self, tmp_path):
        # the default seam is None: the reference pipeline's behavior
        # is byte-for-byte what it was (pinned by the whole v398 suite;
        # here: a full run with a counting seam still ACCEPTS)
        from aeos.pipeline import reference_run
        seen = []
        import aeos.orchestrator as orch_mod
        orig = orch_mod.Orchestrator.__init__

        def patched(self, **kw):
            kw["on_task_settled"] = lambda t: seen.append(t.name)
            orig(self, **kw)

        orch_mod.Orchestrator.__init__ = patched
        try:
            b = reference_run(tmp_path / "ws")
        finally:
            orch_mod.Orchestrator.__init__ = orig
        assert b["accepted"] is True
        assert "define-objective" in seen and "release" in seen
