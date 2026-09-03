"""v2.0 platform tests: adapters, fusion, runtime resume, tool layer."""

import pytest
from pathlib import Path

from aeos.adapters import (AdapterError, ErrorKind, FakeTransport,
                           FusionAdapter, ProviderAdapter, raise_transient,
                           raise_overflow)
from aeos.models import ModelCall, ModelReply


def call(agent="a"):
    return ModelCall(system="s", prompt="p", agent_name=agent)


class TestProviderAdapter:
    def test_transient_retries_then_succeeds(self):
        script = [raise_transient, lambda c: ModelReply(text="fine", model="m")]
        adapter = ProviderAdapter(FakeTransport(script=script), retries=2)
        assert adapter.complete(call()).text == "fine"

    def test_transient_exhausted_is_permanent(self):
        script = [raise_transient] * 5
        adapter = ProviderAdapter(FakeTransport(script=script), retries=1)
        with pytest.raises(AdapterError) as ei:
            adapter.complete(call())
        assert ei.value.kind is ErrorKind.PERMANENT

    def test_context_overflow_never_retries(self):
        adapter = ProviderAdapter(FakeTransport(script=[raise_overflow]), retries=3)
        with pytest.raises(AdapterError) as ei:
            adapter.complete(call())
        assert ei.value.kind is ErrorKind.CONTEXT_OVERFLOW

    def test_empty_reply_is_junk(self):
        adapter = ProviderAdapter(
            FakeTransport(script=[lambda c: ModelReply(text="   ", model="m")]))
        with pytest.raises(AdapterError) as ei:
            adapter.complete(call())
        assert ei.value.kind is ErrorKind.JUNK

    def test_circuit_opens_after_threshold(self):
        fail = FakeTransport(script=[raise_transient] * 20)
        adapter = ProviderAdapter(fail, retries=0, breaker_threshold=2)
        for _ in range(2):
            with pytest.raises(AdapterError):
                adapter.complete(call())
        with pytest.raises(AdapterError) as ei:
            adapter.complete(call())   # no script left, but breaker is open
        assert ei.value.kind is ErrorKind.CIRCUIT_OPEN


class TestFusion:
    def _fusion(self, texts):
        adapters = []
        for i, t in enumerate(texts):
            adapters.append(ProviderAdapter(
                FakeTransport(script=[(lambda tt: (lambda c: ModelReply(
                    text=tt, model=f"p{i}")))(t)])))
        return FusionAdapter(adapters)

    def test_agreement_when_streams_converge(self):
        f = self._fusion(["deploy the service now please",
                          "deploy the service now, please",
                          "deploy the service now!"])
        reply = f.complete(call())
        assert reply.agreement == "AGREED"

    def test_disagreement_is_surfaced_not_averaged(self):
        f = self._fusion(["rotate the database credentials daily",
                          "pineapple belongs on pizza actually",
                          "the migration needs a rollback plan"])
        reply = f.complete(call())
        assert reply.agreement == "DISAGREED"
        assert len(reply.opinions) == 3

    def test_fusion_needs_two(self):
        with pytest.raises(ValueError):
            FusionAdapter([ProviderAdapter(FakeTransport())])

    def test_all_streams_down_raises_permanent(self):
        f = FusionAdapter([
            ProviderAdapter(FakeTransport(script=[raise_transient] * 9), retries=0),
            ProviderAdapter(FakeTransport(script=[raise_transient] * 9), retries=0)])
        with pytest.raises(AdapterError):
            f.complete(call())


# ----------------------------------------------------------- runtime

from aeos.contracts import AgentSpec, TaskSpec, TaskState
from aeos.evaluation import Evaluator
from aeos.governor import Governor
from aeos.models import EchoModel
from aeos.observability import EventLog
from aeos.orchestrator import Orchestrator
from aeos.runtime import RunStore, RunState, attach_persistence, resume_plan


def _orch(ws, handler, store=None):
    spec = AgentSpec(name="a", mission="m", inputs=["i"], outputs=["o"],
                     tools=["t"], constraints=["c"], success_criteria=["s"],
                     evaluation_criteria=["e"], escalation_conditions=["x"],
                     termination_conditions=["t"])
    from aeos.contracts import AutonomyLevel
    gov = Governor(level=AutonomyLevel.L4_GUARDED_AUTONOMY, log=EventLog())
    return Orchestrator(agents={"a": spec}, handlers={"a": handler},
                        model=EchoModel(), governor=gov,
                        evaluator=Evaluator(), log=EventLog(),
                        workspace=ws, max_workers=1)


def _env(task, orch):
    from aeos.contracts import Envelope
    env = Envelope(agent="a", objective=task.description, claims=["ok"])
    env.add_evidence("ran", "exit 0")
    return env


class TestResume:
    def test_state_roundtrip(self, tmp_path):
        store = RunStore(tmp_path)
        tasks = [TaskSpec(name="t1", description="d", agent="a")]
        state = RunState(run_id="r1", objective="obj", tasks=tasks)
        saved = store.save(state)
        loaded = store.load("r1")
        assert loaded.objective == "obj"
        assert loaded.tasks[0].name == "t1"
        assert loaded.tasks[0].action_class.value == "READ"

    def test_failed_run_is_resumable_and_then_completes(self, tmp_path):
        store = RunStore(tmp_path)
        boom = {"n": 0}

        def flaky(task, orch):
            boom["n"] += 1
            if boom["n"] == 1:
                raise RuntimeError("crash mid-run")
            return _env(task, orch)

        orch = _orch(tmp_path / "ws", flaky)
        tasks = [TaskSpec(name="only", description="d", agent="a")]
        attach_persistence(orch, "r2", store, "obj", tasks)
        report = orch.run("obj", tasks, repair=False)
        assert report.states["only"] is TaskState.FAILED
        assert store.load("r2").tasks[0].state is TaskState.FAILED

        # a NEW process would do exactly this:
        state = store.load("r2")
        keep, rerun = resume_plan(state)
        assert keep == [] and rerun == ["only"]
        orch2 = _orch(tmp_path / "ws", flaky)
        report2 = orch2.run("obj", state.tasks, repair=False)
        assert report2.states["only"] is TaskState.SUCCEEDED
        assert report2.accepted

    def test_succeeded_tasks_are_not_rerun(self, tmp_path):
        state = RunState(run_id="r3", objective="o", tasks=[
            TaskSpec(name="done", description="d", agent="a"),
            TaskSpec(name="todo", description="d", agent="a"),
        ])
        state.tasks[0].state = TaskState.SUCCEEDED
        keep, rerun = resume_plan(state)
        assert keep == ["done"] and rerun == ["todo"]

    def test_unfinished_listing(self, tmp_path):
        store = RunStore(tmp_path)
        store.save(RunState(run_id="open", objective="o", tasks=[]))
        assert store.unfinished() == ["open"]
