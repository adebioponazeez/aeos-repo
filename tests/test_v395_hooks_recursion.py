"""v39.5 Hooks & Recursion: first-class interception + nested harness
graphs, tested as law (ADR-051).

Cole Medin's advocacy compiled: hooks are the critical mechanism —
decoupled, ordered, veto-NAMED, redirect-not-just-reject, observers
that can never crash the run. The RAH pattern compiled: a task may
expand into a full nested harness (its own waves, gates, events),
depth-capped so recursion is a tool, not a trap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aeos.contracts import (ActionClass, AgentSpec, AutonomyLevel, Envelope,
                            TaskSpec, TaskState)
from aeos.evaluation import Evaluator
from aeos.governor import Governor
from aeos.hooks import BUS, HookBus, HookVeto
from aeos.models import EchoModel
from aeos.observability import EventLog
from aeos.orchestrator import MAX_SUBPLAN_DEPTH, Orchestrator


def agent(name, writes=None, classes=None):
    return AgentSpec(
        name=name, mission=f"m-{name}", inputs=["i"], outputs=["o"],
        tools=["t"], constraints=["c"], success_criteria=["s"],
        evaluation_criteria=["e"], escalation_conditions=["x"],
        termination_conditions=["t"], writes=writes or [],
        action_classes=classes or [ActionClass.READ])


def ok_handler(name):
    def h(task, orch):
        from aeos.contracts import Evidence, Verdict
        return Envelope(
            agent=name, objective=task.description,
            claims=[f"{name} done"],
            evidence=[Evidence(kind="gate", detail=f"{name} ran",
                               verdict=Verdict.PASS)])
    return h


def make_orch(agents, handlers, level=None, hooks=None):
    gov = Governor(level=level or AutonomyLevel.L4_GUARDED_AUTONOMY,
                   log=EventLog())
    return Orchestrator(agents=agents, handlers=handlers,
                        model=EchoModel(), governor=gov,
                        evaluator=Evaluator(), log=EventLog(),
                        workspace=Path("."), max_workers=2,
                        hooks=hooks if hooks is not None else HookBus())


def events(orch):
    return [{"event": e.kind, **e.detail} for e in orch.log.events()]


class TestHookSurface:
    def test_veto_refuses_named_never_traceback(self):
        bus = HookBus()

        def no_rm(payload):
            raise HookVeto(
                "bash command refused: rm -rf outside the project dir")

        bus.register("task.pre", no_rm)
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")},
                         hooks=bus)
        rep = orch.run("o", [TaskSpec(name="t1", description="d",
                                      agent="a")])
        assert rep.states["t1"] is TaskState.ESCALATED
        es = [e for e in events(orch) if e["event"] == "task.escalated"]
        assert es and "hook veto" in es[0]["why"]
        assert "rm -rf outside" in es[0]["why"]

    def test_redirect_downgrades_danger_preserves_intent(self):
        """Redirect, don't just reject: a hook rewrites WRITE->READ and
        the task RUNS (intent preserved, danger removed)."""
        bus = HookBus()

        def soften(payload):
            if payload["action_class"] == "WRITE":
                return {**payload, "action_class": "READ"}
            return payload

        bus.register("task.pre", soften, order=10)
        # L1: unsupervised WRITE would be denied outright
        orch = make_orch({"a": agent("a", classes=[ActionClass.WRITE])},
                         {"a": ok_handler("a")},
                         level=AutonomyLevel.L1_AI_ASSISTANCE, hooks=bus)
        rep = orch.run("o", [TaskSpec(
            name="t1", description="d", agent="a",
            action_class=ActionClass.WRITE)])
        assert rep.states["t1"] is TaskState.SUCCEEDED
        redir = [e for e in events(orch)
                 if e["event"] == "task.redirected"]
        assert redir and redir[0]["action_class"] == "READ"

    def test_observer_errors_never_crash_the_run(self):
        bus = HookBus()
        seen = []

        def broken(payload):
            seen.append(payload)
            raise RuntimeError("observer bug")

        bus.register("task.post", broken)
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")},
                         hooks=bus)
        rep = orch.run("o", [TaskSpec(name="t1", description="d",
                                      agent="a")])
        assert rep.states["t1"] is TaskState.SUCCEEDED
        assert seen, "the observer ran"
        # and the errors were collected, not raised
        errs = bus.emit_post("task.post", {"task": "probe"})
        assert errs and "observer bug" in errs[0]

    def test_refusal_observer_sees_every_refusal(self):
        bus = HookBus()
        refusals = []
        bus.register("refusal", refusals.append)
        orch = make_orch({"a": agent("a", classes=[ActionClass.DESTRUCTIVE])},
                         {"a": ok_handler("a")},
                         level=AutonomyLevel.L1_AI_ASSISTANCE, hooks=bus)
        orch.run("o", [TaskSpec(
            name="t1", description="d", agent="a",
            action_class=ActionClass.DESTRUCTIVE)])
        assert refusals and refusals[0]["where"] == "governor"

    def test_registration_is_decoupled_and_inspectable(self):
        bus = HookBus()
        reg = bus.register("wave.pre", lambda p: None, name="watcher")
        assert bus.registered("wave.pre") == [reg]
        bus.unregister(reg)
        assert bus.registered("wave.pre") == []
        with pytest.raises(ValueError, match="vocabulary is law"):
            bus.register("not.a.point", lambda p: None)
        assert "HOOKS —" in bus.describe()

    def test_hooks_thread_safe_under_parallel_waves(self):
        bus = HookBus()
        seen = []
        bus.register("task.post", lambda p: seen.append(p["task"]))
        agents = {f"a{i}": agent(f"a{i}") for i in range(4)}
        handlers = {f"a{i}": ok_handler(f"a{i}") for i in range(4)}
        orch = make_orch(agents, handlers, hooks=bus)
        tasks = [TaskSpec(name=f"t{i}", description="d", agent=f"a{i}")
                 for i in range(4)]
        rep = orch.run("o", tasks)
        assert rep.accepted
        assert sorted(seen) == ["t0", "t1", "t2", "t3"]


class TestRecursiveHarness:
    def _deep(self, n_levels):
        """A chain: t0 -> subplan(t1 -> subplan(t2 ... )) n deep."""
        task = TaskSpec(name=f"leaf{n_levels}", description="leaf",
                        agent="a")
        for i in range(n_levels - 1, -1, -1):
            task = TaskSpec(name=f"n{i}", description=f"level {i}",
                            agent="a", subplan=[task])
        return [task]

    def test_subplan_nests_and_completes(self):
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")})
        tasks = [
            TaskSpec(name="top", description="d", agent="a", subplan=[
                TaskSpec(name="kid-a", description="d", agent="a"),
                TaskSpec(name="kid-b", description="d", agent="a",
                         subplan=[TaskSpec(name="grandkid", description="d",
                                           agent="a")]),
            ]),
        ]
        rep = orch.run("o", tasks)
        assert rep.accepted
        es = events(orch)
        starts = [e for e in es if e["event"] == "subplan.start"]
        ends = [e for e in es if e["event"] == "subplan.end"]
        assert len(starts) == 2 and len(ends) == 2
        assert {e["depth"] for e in starts} == {1, 2}
        assert all(e["accepted"] for e in ends)

    def test_depth_cap_refuses_named_not_crashes(self):
        bus = HookBus()
        refusals = []
        bus.register("refusal", refusals.append)
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")},
                         hooks=bus)
        rep = orch.run("o", self._deep(MAX_SUBPLAN_DEPTH + 2))
        assert not rep.accepted
        named = [r for r in refusals
                 if r["where"] == "subplan.depth"]
        assert named and "not a trap" in named[0]["reason"]

    def test_subplan_pre_veto_escalates_named(self):
        bus = HookBus()

        def no_nesting(payload):
            raise HookVeto("subagents refused: this run stays flat")

        bus.register("subplan.pre", no_nesting)
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")},
                         hooks=bus)
        rep = orch.run("o", [TaskSpec(
            name="t", description="d", agent="a",
            subplan=[TaskSpec(name="kid", description="d", agent="a")])])
        assert rep.states["t"] is TaskState.ESCALATED
        es = [e for e in events(orch) if e["event"] == "task.escalated"]
        assert es and "subagents refused" in es[0]["why"]

    def test_child_failure_fails_parent_named(self):
        def flaky(task, orch):
            raise RuntimeError("child handler broke")

        orch = make_orch({"a": agent("a"), "f": agent("f")},
                         {"a": ok_handler("a"), "f": flaky})
        rep = orch.run("o", [TaskSpec(
            name="t", description="d", agent="a", subplan=[
                TaskSpec(name="bad", description="d", agent="f",
                         max_attempts=1)])])
        assert rep.states["t"] is TaskState.FAILED
        why = [e for e in events(orch)
               if e["event"] == "task.failed" and e["task"] == "t"]
        assert why and "subplan unresolved" in why[0]["why"]

    def test_global_bus_wiring_survives_the_real_pipeline(self):
        """The reference pipeline runs green with hooks emitting —
        the surface composes with the kernel, not against it."""
        from aeos.pipeline import reference_run
        waves = []
        reg = BUS.register("wave.post", lambda p: waves.append(p["wave"]))
        try:
            b = reference_run(Path("/tmp/v395-hook-pipeline-ws"),
                              intent="hooks compose with the kernel")
        finally:
            BUS.unregister(reg)
        assert b["accepted"] is True
        assert waves, "wave hooks fired inside the real pipeline"


class TestDefaultBus:
    def test_default_bus_exists_and_is_empty_by_law(self):
        # no stray registrations leak between tests / modules
        assert BUS.registered() == []
