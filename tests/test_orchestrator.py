"""Orchestrator tests: graphs, waves, conflicts, repair, escalation."""

import pytest

from aeos.contracts import (ActionClass, AgentSpec, Envelope, TaskSpec,
                            TaskState, Verdict)
from aeos.evaluation import Evaluator
from aeos.governor import Governor
from aeos.models import EchoModel
from aeos.observability import EventLog
from aeos.orchestrator import Orchestrator


def agent(name, writes=None, classes=None):
    return AgentSpec(
        name=name, mission=f"m-{name}", inputs=["i"], outputs=["o"],
        tools=["t"], constraints=["c"], success_criteria=["s"],
        evaluation_criteria=["e"], escalation_conditions=["x"],
        termination_conditions=["t"], writes=writes or [],
        action_classes=classes or [ActionClass.READ])


def make_orch(agents, handlers, level=None):
    from aeos.contracts import AutonomyLevel
    gov = Governor(level=level or AutonomyLevel.L4_GUARDED_AUTONOMY, log=EventLog())
    return Orchestrator(agents=agents, handlers=handlers, model=EchoModel(),
                        governor=gov, evaluator=Evaluator(), log=EventLog(),
                        workspace=__import__("pathlib").Path("."), max_workers=2)


def ok_handler(name):
    def h(task, orch):
        return Envelope(agent=name, objective=task.description,
                        claims=[f"{name} done"],
                        evidence=[])
    return h


class TestGraphValidation:
    def test_cycle_is_rejected(self):
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")})
        tasks = [TaskSpec(name="t1", description="d", agent="a", depends_on=["t2"]),
                 TaskSpec(name="t2", description="d", agent="a", depends_on=["t1"])]
        problems = orch.validate_graph(tasks)
        assert any("cycle" in p for p in problems)

    def test_unknown_agent_is_rejected(self):
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")})
        tasks = [TaskSpec(name="t1", description="d", agent="ghost")]
        assert any("unknown agent" in p for p in orch.validate_graph(tasks))

    def test_parallel_writers_to_same_boundary_rejected(self):
        agents = {"a": agent("a", writes=["src/*"], classes=[ActionClass.WRITE]),
                  "b": agent("b", writes=["src/*"], classes=[ActionClass.WRITE])}
        orch = make_orch(agents, {"a": ok_handler("a"), "b": ok_handler("b")})
        tasks = [TaskSpec(name="t1", description="d", agent="a", action_class=ActionClass.WRITE),
                 TaskSpec(name="t2", description="d", agent="b", action_class=ActionClass.WRITE)]
        assert any("parallel writers" in p for p in orch.validate_graph(tasks))

    def test_ordered_writers_accepted(self):
        agents = {"a": agent("a", writes=["src/*"], classes=[ActionClass.WRITE]),
                  "b": agent("b", writes=["src/*"], classes=[ActionClass.WRITE])}
        orch = make_orch(agents, {"a": ok_handler("a"), "b": ok_handler("b")})
        tasks = [TaskSpec(name="t1", description="d", agent="a", action_class=ActionClass.WRITE),
                 TaskSpec(name="t2", description="d", agent="b", depends_on=["t1"],
                          action_class=ActionClass.WRITE)]
        assert orch.validate_graph(tasks) == []


class TestWaves:
    def test_independent_tasks_share_a_wave(self):
        orch = make_orch({"a": agent("a")}, {"a": ok_handler("a")})
        tasks = [TaskSpec(name="x", description="d", agent="a"),
                 TaskSpec(name="y", description="d", agent="a"),
                 TaskSpec(name="z", description="d", agent="a", depends_on=["x", "y"])]
        waves = orch.waves(tasks)
        assert {t.name for t in waves[0]} == {"x", "y"}
        assert [t.name for t in waves[1]] == ["z"]

    def test_upstream_failure_skips_dependents(self):
        def failing(task, orch):
            raise RuntimeError("boom")
        orch = make_orch({"good": agent("good"), "bad": agent("bad")},
                         {"good": ok_handler("good"), "bad": failing})
        tasks = [TaskSpec(name="explode", description="d", agent="bad"),
                 TaskSpec(name="aftermath", description="d", agent="good",
                          depends_on=["explode"])]
        report = orch.run("objective", tasks, repair=False)
        assert report.states["explode"] is TaskState.FAILED
        assert report.states["aftermath"] is TaskState.SKIPPED
        assert not report.accepted

    def test_repair_cycle_revives_failed_task(self):
        attempts = {"n": 0}

        def flaky(task, orch):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("transient")
            env = Envelope(agent="a", objective=task.description, claims=["ok"])
            env.add_evidence("ran", "exit 0")
            return env
        orch = make_orch({"a": agent("a")}, {"a": flaky})
        report = orch.run("objective", [TaskSpec(name="t", description="d", agent="a")],
                          repair=True)
        assert report.states["t"] is TaskState.SUCCEEDED
        assert report.repair_cycles == 1

    def test_handler_must_return_envelope(self):
        orch = make_orch({"a": agent("a")}, {"a": lambda t, o: "trust me"})
        report = orch.run("o", [TaskSpec(name="t", description="d", agent="a")],
                          repair=False)
        assert report.states["t"] is TaskState.FAILED


class TestGovernorIntegration:
    def test_destructive_task_escalates(self):
        from aeos.contracts import AutonomyLevel
        orch = make_orch({"a": agent("a", classes=[ActionClass.DESTRUCTIVE])},
                         {"a": ok_handler("a")}, level=AutonomyLevel.L2_AI_EXECUTION_WITH_APPROVAL)
        report = orch.run("o", [TaskSpec(name="nuke", description="d", agent="a",
                                         action_class=ActionClass.DESTRUCTIVE)],
                          repair=False)
        assert report.states["nuke"] is TaskState.ESCALATED
