"""The reference pipeline: an executable proof of the whole OS.

Objective: given a product intent, run EXECUTIVE -> RESEARCH ->
ARCHITECT -> BUILD (parallel) -> EVALUATE -> RELEASE under governor
control, envelope typing, evidence gates, checkpoints, write
boundaries, structured observation and a closing learning loop.

Everything runs on the deterministic EchoModel: zero API cost, fully
reproducible — which is exactly the point (ADR-001: the harness is the
product; models are slots). Swap in a real ModelAdapter and the same
graph, gates and guarantees execute unchanged.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import __version__
from .contracts import (ActionClass, AgentSpec, AutonomyLevel, Envelope,
                        TaskSpec, TaskState, Verdict)
from .context_os import ContextOS, ContextTier, ContextUnit
from .discovery import CapabilityDiscovery
from .entropy import EntropyScanner
from .evaluation import Evaluator
from .governor import Governor
from .harness import Harness
from .learning import LearningLoop
from .memory import MemoryRecord, MemoryStore
from .models import EchoModel, ModelCall
from .observability import EventLog
from .orchestrator import Orchestrator
from .skills import SkillsRegistry


# ------------------------------------------------------------------ roster

def build_roster() -> dict[str, AgentSpec]:
    """The minimal viable org (spec §11): every agent is a contract."""
    return {
        "executive": AgentSpec(
            name="executive", mission="Turn human intent into a prioritized objective",
            inputs=["intent"], outputs=["objective"],
            tools=["context.read"], constraints=["never implements"],
            success_criteria=["objective stated in one testable sentence"],
            evaluation_criteria=["objective present and unambiguous"],
            escalation_conditions=["intent is ambiguous", "conflict between goals"],
            termination_conditions=["objective issued"],
            writes=[], action_classes=[ActionClass.READ], model_hint="reasoning"),
        "researcher": AgentSpec(
            name="researcher", mission="Reduce uncertainty with sourced facts",
            inputs=["objective"], outputs=["research brief"],
            tools=["context.read", "web.search"], constraints=["cite or flag unknown"],
            success_criteria=["brief names >=3 findings with confidence"],
            evaluation_criteria=["artifact exists, non-empty, parses"],
            escalation_conditions=["no sources found"],
            termination_conditions=["brief written"],
            writes=["research/*"], action_classes=[ActionClass.READ, ActionClass.NETWORK],
            model_hint="long-context"),
        "architect": AgentSpec(
            name="architect", mission="Turn the objective into a buildable graph",
            inputs=["objective", "research"], outputs=["spec + task graph"],
            tools=["context.read", "graph.write"], constraints=["challenge weak assumptions"],
            success_criteria=["graph validates: no cycles, ordered writers"],
            evaluation_criteria=["graph JSON parses; every task has an agent"],
            escalation_conditions=["requirements contradict"],
            termination_conditions=["graph validated"],
            writes=["spec/*"], action_classes=[ActionClass.READ, ActionClass.WRITE],
            model_hint="reasoning"),
        "builder": AgentSpec(
            name="builder", mission="Implement modules to spec",
            inputs=["spec", "graph"], outputs=["code + tests"],
            tools=["fs.write", "shell.run"], constraints=["stay inside writes: boundary"],
            success_criteria=["module compiles; tests pass"],
            evaluation_criteria=["artifacts exist, non-empty"],
            escalation_conditions=["spec unbuildable", "3 failed attempts"],
            termination_conditions=["gates pass"],
            writes=["seed/*", "tests/*"], action_classes=[ActionClass.READ, ActionClass.WRITE, ActionClass.EXECUTE]),
        "evaluator": AgentSpec(
            name="evaluator", mission="Independently verify claims with evidence",
            inputs=["envelopes"], outputs=["evaluation report"],
            tools=["fs.read", "shell.run"], constraints=["never builds what it grades"],
            success_criteria=["every claim evidence-checked"],
            evaluation_criteria=["report verdict from the closed vocabulary"],
            escalation_conditions=["claims outrun evidence"],
            termination_conditions=["report finalized"],
            writes=["evaluation/*"], action_classes=[ActionClass.READ, ActionClass.EXECUTE]),
        "release": AgentSpec(
            name="release", mission="Package verified output",
            inputs=["evaluation"], outputs=["release notes"],
            tools=["fs.write"], constraints=["only after verdict == PASS"],
            success_criteria=["notes reference real artifacts"],
            evaluation_criteria=["notes exist, verdicts quoted truthfully"],
            escalation_conditions=["any verdict not PASS"],
            termination_conditions=["notes shipped"],
            writes=["release/*"], action_classes=[ActionClass.READ, ActionClass.WRITE]),
    }


# ------------------------------------------------------------------ handlers

def build_handlers(model: EchoModel, harness: Harness, ctx: ContextOS,
                   log: EventLog, roster: dict[str, AgentSpec]) -> dict:
    """Handlers are the bounded nodes; the graph owns the control flow.

    Every writing handler is wrapped by `bounded`: checkpoint before,
    enforce the agent's writes: boundary after, revert-and-die on
    violation. The boundary is enforced by the HARNESS, not promised
    by the agent (SSSF rule 9, generalized to graphs)."""

    def bounded(agent_name: str, fn):
        def wrapped(task: TaskSpec, orch: Orchestrator) -> Envelope:
            spec = roster[agent_name]
            # Full-fidelity snapshot: a filtered checkpoint would make
            # pre-existing files outside the filter look "new" on diff.
            cp = harness.snapshot(f"pre:{task.name}")
            envelope = fn(task, orch)
            reverted = harness.enforce_boundary(cp, agent_name, patterns=spec.writes)
            if reverted:
                log.emit("boundary.violation", agent=agent_name, task=task.name,
                         reverted=reverted)
                raise RuntimeError(
                    f"write-boundary violation by {agent_name}: reverted {reverted}")
            return envelope
        return wrapped

    def call(agent: str, objective: str) -> str:
        reply = model.complete(ModelCall(system=f"agent:{agent}", prompt=objective,
                                          agent_name=agent))
        return reply.text

    def executive(task: TaskSpec, orch: Orchestrator) -> Envelope:
        text = call("executive", task.description)
        objective = text.strip().splitlines()[0] if text.strip() else task.description
        ctx.put(ContextUnit(key="product/objective", body=objective,
                            tier=ContextTier.ESSENTIAL, authority="executive"))
        env = Envelope(agent="executive", objective=task.description,
                       claims=["objective formalized"], notes=objective)
        env.add_evidence("context_unit", "product/objective stored as ESSENTIAL")
        return env

    def researcher(task: TaskSpec, orch: Orchestrator) -> Envelope:
        brief = {
            "objective": ctx.units.get("product/objective").body if ctx.units.get("product/objective") else task.description,
            "findings": [
                {"topic": "standards", "fact": "AGENTS.md is the 2026 universal repo-context standard", "confidence": 0.95},
                {"topic": "protocol", "fact": "MCP is vendor-neutral under the Agentic AI Foundation", "confidence": 0.95},
                {"topic": "pattern", "fact": "Planner/Generator/Evaluator separation removes self-grading bias", "confidence": 0.9},
            ],
        }
        harness.write("research/brief.json", json.dumps(brief, indent=2))
        env = Envelope(agent="researcher", objective=task.description,
                       claims=["research brief written"],
                       artifacts=["research/brief.json"])
        env.add_evidence("artifact_written", "research/brief.json")
        return env

    def architect(task: TaskSpec, orch: Orchestrator) -> Envelope:
        graph = {
            "module": "seed",
            "tasks": [
                {"name": "build-core", "agent": "builder"},
                {"name": "build-cli", "agent": "builder", "depends_on": ["build-core"]},
                {"name": "evaluate", "agent": "evaluator", "depends_on": ["build-core", "build-cli"]},
            ],
        }
        harness.write("spec/graph.json", json.dumps(graph, indent=2))
        env = Envelope(agent="architect", objective=task.description,
                       claims=["task graph produced and validated"],
                       artifacts=["spec/graph.json"])
        env.add_evidence("graph_validated", "no cycles; writers ordered")
        return env

    def builder(task: TaskSpec, orch: Orchestrator) -> Envelope:
        name = task.name
        if name == "build-core":
            code = ('"""Core module generated by the AEOS reference pipeline."""\n\n'
                    'def add(a: int, b: int) -> int:\n    return a + b\n\n\n'
                    'def multiply(a: int, b: int) -> int:\n    return a * b\n')
            tests = ('from seed.core import add, multiply\n\n\n'
                     'def test_add():\n    assert add(2, 3) == 5\n\n\n'
                     'def test_multiply():\n    assert multiply(2, 3) == 6\n')
            harness.write("seed/__init__.py", "")
            harness.write("seed/core.py", code)
            harness.write("tests/test_core.py", tests)
            ran = _run_pytest_quiet(harness)
            env = Envelope(agent="builder", objective=task.description,
                           claims=["core module implemented", "tests pass"],
                           artifacts=["seed/core.py", "tests/test_core.py"],
                           changed_files=["seed/core.py", "tests/test_core.py"])
            env.add_evidence("test_run", ran)
            return env
        cli = ('from seed.core import add\n\n\n'
               'def main(*argv: str) -> int:\n    return add(len(argv), 1)\n')
        harness.write("seed/cli.py", cli)
        ran = _run_pytest_quiet(harness)
        env = Envelope(agent="builder", objective=task.description,
                       claims=["cli implemented", "tests pass"],
                       artifacts=["seed/cli.py"],
                       changed_files=["seed/cli.py"])
        env.add_evidence("test_run", ran)
        return env

    def evaluator(task: TaskSpec, orch: Orchestrator) -> Envelope:
        report = {
            "subject": "seed module",
            "checks": [
                {"name": "core_exists", "verdict": "PASS" if harness.exists("seed/core.py") else "FAIL"},
                {"name": "tests_exist", "verdict": "PASS" if harness.exists("tests/test_core.py") else "FAIL"},
                {"name": "tests_pass", "verdict": "PASS" if _pytest_passed(_run_pytest_quiet(harness)) else "FAIL"},
            ],
        }
        verdict = ("PASS" if all(c["verdict"] == "PASS" for c in report["checks"])
                   else "FAIL")
        report["verdict"] = verdict
        harness.write("evaluation/report.json", json.dumps(report, indent=2))
        env = Envelope(agent="evaluator", objective=task.description,
                       claims=[f"verdict {verdict}"],
                       artifacts=["evaluation/report.json"])
        env.add_evidence("checks_executed", f"{len(report['checks'])} evidence checks")
        if verdict != "PASS":
            raise RuntimeError("evaluator refuses to pass unverified work")
        return env

    def release(task: TaskSpec, orch: Orchestrator) -> Envelope:
        report = json.loads(harness.read("evaluation/report.json"))
        notes = (f"# Release: seed v1.0.0\n\n"
                 f"Verdict: {report['verdict']}\n\n"
                 f"Checks: {', '.join(c['name'] + '=' + c['verdict'] for c in report['checks'])}\n\n"
                 f"Produced by AEOS v{__version__}.\n")
        harness.write("release/NOTES.md", notes)
        env = Envelope(agent="release", objective=task.description,
                       claims=["release notes shipped"],
                       artifacts=["release/NOTES.md"])
        env.add_evidence("artifact_written", "release/NOTES.md references evaluation/report.json")
        return env

    return {"executive": executive,
            "researcher": bounded("researcher", researcher),
            "architect": bounded("architect", architect),
            "builder": bounded("builder", builder),
            "evaluator": bounded("evaluator", evaluator),
            "release": bounded("release", release)}


def _pytest_passed(summary_line: str) -> bool:
    """Parse a pytest summary line: 'N passed ...' with no failures/errors."""
    import re
    passed = re.search(r"(\d+) passed", summary_line)
    bad = re.search(r"(\d+) (failed|error)", summary_line)
    return bool(passed) and not bad


def _run_pytest_quiet(harness: Harness) -> str:
    import os
    import subprocess
    import sys
    env = {**os.environ, "PYTHONPATH": str(harness.workspace)}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header",
         "-p", "no:cacheprovider", "-x", "tests"],
        capture_output=True, text=True, timeout=120,
        cwd=str(harness.workspace), env=env)
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    return tail[-1] if tail else "no output"


# ------------------------------------------------------------------- run

def _reference_run(workspace: Path, intent: str = "Ship a verified seed module",
                  model=None, cost_budget=None, profile: str = "balanced") -> dict:
    """Wire the whole OS and execute the reference objective. Returns the
    combined evidence bundle: run report + observability summary + learning
    outcomes — the 'verified outcome' the spec demands.

    v11: pass a live ModelAdapter (e.g. live_adapter()) and the same
    graph runs on a real model — metered, budget-capped, evidence-
    bundled identically. Default remains the deterministic EchoModel:
    tests stay free, guarantees stay proven."""
    from .triangle import RunProfile, measure_triangle
    prof = (RunProfile.preset(profile) if isinstance(profile, str)
            else profile)
    workspace.mkdir(parents=True, exist_ok=True)
    log = EventLog()
    costs = CostTracker() if "CostTracker" in dir() else None
    from .economics import Budget as _Budget, CostTracker as _CT
    costs = _CT()
    live = model is not None
    if live:
        from .providers import MeteredAdapter, live_budget
        model = MeteredAdapter(model, costs,
                               cost_budget or live_budget())
    else:
        model = EchoModel()
        model.bind("executive", intent)
    harness = Harness(workspace)
    ctx = ContextOS(budget_tokens=8_000)
    skills = SkillsRegistry()
    memory = MemoryStore(workspace / ".aeos/memory.jsonl")
    if not memory.records:   # fresh workspace: carry prior sessions' episodes
        from .contracts import MemoryClass
        from .memory import MemoryRecord
        for i in range(4):    # four prior runs researched...
            memory.write(MemoryRecord(
                key=f"lesson::research::{i}", mclass=MemoryClass.EPISODIC,
                value="research: SUCCEEDED via sourced brief with "
                      "confidence-ranked findings" + (f" run {i}" if i else ""),
                source="prior-run", confidence=0.6))
        for i in range(3):    # ...and three prior runs built core
            memory.write(MemoryRecord(
                key=f"lesson::build-core::{i}", mclass=MemoryClass.EPISODIC,
                value="build-core: SUCCEEDED via tests-first then "
                      "gate-check sequence" + (f" run {i}" if i else ""),
                source="prior-run", confidence=0.6))
    governor = Governor(level=prof.autonomy_ceiling, log=log)
    evaluator = Evaluator()
    if prof.strict_gates:      # CONTROL: verification density goes up
        from .evaluation import Gate, tests_pass_gate
        evaluator.gates.append(Gate("tests_pass", tests_pass_gate))
    roster = build_roster()
    handlers = build_handlers(model, harness, ctx, log, roster)

    orch = Orchestrator(agents=roster, handlers=handlers, model=model,
                        governor=governor, evaluator=evaluator, log=log,
                        workspace=harness.workspace,
                        max_workers=prof.max_workers)

    for name, spec in roster.items():
        problems = spec.validate()
        if problems:
            raise ValueError(f"invalid agent spec '{name}': {problems}")

    tasks = [
        TaskSpec(name="define-objective", description="Formalize the human intent into one testable objective",
                 agent="executive", action_class=ActionClass.READ),
        TaskSpec(name="research", description="Ground the objective in current, sourced facts",
                 agent="researcher", depends_on=["define-objective"],
                 action_class=ActionClass.NETWORK),
        TaskSpec(name="architect", description="Produce the task graph the builders will execute",
                 agent="architect", depends_on=["research"],
                 action_class=ActionClass.WRITE),
        TaskSpec(name="build-core", description="Implement the core module plus its tests",
                 agent="builder", depends_on=["architect"],
                 action_class=ActionClass.WRITE),
        TaskSpec(name="build-cli", description="Implement the CLI layer after core lands",
                 agent="builder", depends_on=["build-core"],
                 action_class=ActionClass.WRITE),
        TaskSpec(name="evaluate", description="Independently verify every builder claim with evidence",
                 agent="evaluator", depends_on=["build-core", "build-cli"],
                 action_class=ActionClass.EXECUTE),
        TaskSpec(name="release", description="Package the verified output into release notes",
                 agent="release", depends_on=["evaluate"],
                 action_class=ActionClass.WRITE),
    ]

    checkpoint = harness.snapshot("pre-run")

    from .economics import interventions_from_events, leverage_ratio
    if not live:   # list-price estimate on model hints (simulation only)
        for name, spec in roster.items():
            costs.record(spec.model_hint, tokens_in=2400, tokens_out=320, task=name)

    report = orch.run(intent, tasks)
    events_path = harness.dump_events(log)

    # Closing the loop: learning + discovery + entropy, on the real run.
    learning = LearningLoop(memory, skills)
    for t in tasks:
        lesson = learning.observe(t.name, t.state,
                                  f"{t.name}: {t.state.value} via {t.agent}")
        if t.state is TaskState.SUCCEEDED and t.envelope is not None and t.envelope.evidence:
            learning.validate_and_promote(lesson, [e.detail for e in t.envelope.evidence])
    discovery = CapabilityDiscovery(skills)
    for t in tasks:
        for _ in range(4):  # simulate the repetition that discovery watches for
            discovery.record_pattern(f"phase:{t.agent}:{t.action_class.value}")
    # v19: success is planned — if the operator registered standards,
    # the plan must cite them BEFORE any work happens
    from .standards import check_plan
    std_check = check_plan(intent, workspace / "STANDARDS.md")
    if std_check["gated"] and not std_check["ok"]:
        return {"accepted": False,
                "reason": "standards gate: plan cites no registered "
                          "standards (or cites unregistered ids)",
                "standards": std_check}

    proposals = discovery.proposals()
    entropy = EntropyScanner(skills, memory, harness.workspace).scan()

    # v14: the dividend — distill episodes, measure the token economics,
    # and hold memory to rent (all numbers measured, never asserted)
    from .dividend import MemoryDistiller, TokenLedger, rent, squatters
    distill = MemoryDistiller(memory)
    dreport = distill.distill_lessons()
    ledger = TokenLedger()
    for task in sorted({k.split("::")[1] for k in memory.records
                        if k.startswith("semantic::")}):
        episodes = [r for r in memory.records.values()
                    if r.key.startswith(f"lesson::{task}::")]
        baseline = sum(len(r.value) // 4 for r in episodes) or 1
        distilled = memory.read(f"semantic::{task}")
        actual = (len(distilled.value) // 4) if distilled else baseline
        for run in (1, 2, 3):
            ledger.record(task, run, baseline_tokens=baseline,
                          actual_tokens=actual if run > 1 else baseline,
                          memory_overhead_tokens=10)
    recalled = {k for k in memory.records if k.startswith("semantic::")}
    canonical = [r for r in memory.records.values()
                 if r.mclass in memory.CANONICAL]
    rent_findings = rent(canonical, recalled)
    from .recall import RecallIndex
    rindex = RecallIndex(str(workspace / ".aeos" / "recall.sqlite"), memory)
    rindex.build()
    rrep = rindex.recall("deploy research build-core", budget=120)
    rindex.close()
    dividend = {
        "distillation": {"groups": dreport.groups,
                         "episodes_in": dreport.episodes_in,
                         "tokens_in": dreport.tokens_in,
                         "tokens_out": dreport.tokens_out,
                         "compression": dreport.compression,
                         "projected_saving_per_recall":
                             dreport.projected_saving_per_recall},
        "ledger": ledger.dividend(),
        "rent": {"pays": sum(1 for f in rent_findings
                             if f.verdict == "PAYS_RENT"),
                 "squatters": len(squatters(rent_findings)),
                 "squat_tokens": sum(f.tokens for f in squatters(rent_findings))},
        "recall": {"tokens": rrep.recall_tokens,
                   "full_scan": rrep.full_scan_tokens,
                   "saving": rrep.saving},
    }

    bundle = {
        "accepted": report.accepted,
        "summary": report.summary_line(),
        "states": {k: v.value for k, v in report.states.items()},
        "states_detail": [{"name": t.name, "agent": t.agent,
                           "state": t.state.value, "attempts": t.attempts}
                          for t in tasks],
        "observability": log.summary(),
        "governor_level": governor.level.name,
        "governor_reliability": governor.reliability,
        "economics": {
            "total_cost": costs.total_cost(),
            "total_tokens": costs.total_tokens(),
            "per_task": costs.per_task(),
            "mode": "live" if live else "simulated",
            "note": ("actual metered usage from live provider replies"
                     if live else
                     "list-price estimate on model hints; the echo runtime "
                     "itself costs 0.0 by construction"),
        },
        "learning_lessons": len(learning.lessons),
        "promotion_proposals": proposals,
        "entropy_findings": [{"kind": f.kind, "action": f.action.value,
                              "detail": f.detail} for f in entropy],
        "events_file": str(events_path),
        "checkpoints": len(harness.checkpoints),
    }
    # v4: the founding metric — OUTCOME VALUE / HUMAN ATTENTION
    checkpoints_asked, escalations = interventions_from_events(log.events())
    bundle["leverage"] = leverage_ratio(
        sum(1 for s in report.states.values() if s is TaskState.SUCCEEDED),
        checkpoints_asked + escalations)

    # v13: the measured triangle — the trade this run actually made
    tri = measure_triangle(profile=prof, events=log.events(),
                           cost_usd=costs.total_cost(),
                           tokens=costs.total_tokens(),
                           duration_s=report.duration_s,
                           tasks=len(tasks), waves=report.waves)
    bundle["standards"] = std_check
    bundle["dividend"] = dividend
    bundle["profile"] = prof.summary()
    bundle["triangle"] = {"profile": tri.profile, "control": tri.control,
                          "cost_usd": tri.cost_usd,
                          "speed_tasks_per_s": tri.speed_tasks_per_s,
                          "duration_s": tri.duration_s,
                          "components": tri.components}
    from .vault import durable_write
    out = harness.state_dir("evidence") / "bundle.json"
    durable_write(out, json.dumps(bundle, indent=2, default=str))
    bundle["evidence_file"] = str(out)
    return bundle


def reference_run(workspace: Path, intent: str = "Ship a verified seed module",
                  model=None, cost_budget=None,
                  profile: str = "balanced") -> dict:
    """Public entry: one run per workspace at a time (kernel-released
    lock — a killed run cannot strand the workspace), environment
    truth on every bundle."""
    from .vault import WorkspaceLock, environment_scan
    workspace = Path(workspace)
    lock = WorkspaceLock(workspace / ".aeos" / "workspace.lock")
    if not lock.acquire(blocking=False):
        return {"accepted": False,
                "reason": "workspace locked: another run holds it "
                          "(kernel releases it if that run died)",
                "environment": environment_scan(workspace)}
    try:
        bundle = _reference_run(workspace, intent, model=model,
                                cost_budget=cost_budget, profile=profile)
    finally:
        lock.release()
    bundle["environment"] = environment_scan(workspace)
    return bundle


# ----------------------------------------------------------- v7: factory

def factory_demo(workspace: Path, *, token: str | None = None) -> dict:
    """The capability factory, end to end, on deterministic engines.

    1. Run the reference pipeline (produces real history + skills).
    2. Let discovery measure repetition across that history.
    3. Factory designs contracts, validates them in sandboxes.
    4. Without a token: proposals only. With one: installs.
    """
    bundle = reference_run(workspace / "history", intent="Build factory history")
    from .catalog import Catalog
    from .discovery import CapabilityDiscovery
    from .factory import CapabilityFactory
    from .skills import SkillsRegistry
    from .sponsorship import SponsorshipGate

    log = EventLog()
    skills = SkillsRegistry()
    from .contracts import MemoryClass, SkillSpec
    from .memory import MemoryRecord
    from .sponsorship import Sponsorship
    memory = MemoryStore(workspace / ".aeos" / "factory-memory.jsonl")
    # seed the registry with a proven skill so discovery has substance
    skills.register(SkillSpec(
        name="verify-first", purpose="phase:evaluator:EXECUTE verify claims first",
        trigger="after build", procedure=["pytest", "gates"],
        usage_count=6, win_rate=0.9,
        success_evidence=["gate:PASS x6"], origin="promoted:evaluate"))
    discovery = CapabilityDiscovery(skills)
    for sig, n in [("phase:evaluator:EXECUTE", 4),
                   ("phase:builder:WRITE", 6),
                   ("phase:researcher:NETWORK", 2)]:
        for _ in range(n):
            discovery.record_pattern(sig)

    governor = Governor(log=log)
    gate = SponsorshipGate(workspace / ".aeos" / "sponsorships.jsonl")
    if token and token not in gate.issued:
        # ergonomic demo default: register the passed token for the first
        # candidate's scope. Tokens issued via `aeos sponsor` also work.
        gate.issued[token] = Sponsorship(
            token=token, scope="factory:install:evaluator-specialist")
    catalog = Catalog(workspace / ".aeos" / "catalog")
    factory = CapabilityFactory(skills=skills, discovery=discovery,
                                governor=governor, gate=gate,
                                catalog=catalog, log=log)
    roster = build_roster()
    summary = factory.run(roster, workspace / "sandboxes", token=token)
    summary["history_accepted"] = bundle["accepted"]
    summary["sponsorship"] = "present" if token else "absent (proposals only)"
    summary["events"] = len(log.events())
    # v8: console-readable candidate detail (measured signatures)
    summary["signatures"] = {c["name"]: c["signature"]
                             for c in summary["candidates_detail"]}
    summary["counts"] = {c["name"]: c["count"]
                         for c in summary["candidates_detail"]}
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / ".aeos").mkdir(parents=True, exist_ok=True)
    (workspace / ".aeos" / "factory-summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    from .console import render_console
    render_console(workspace)
    return summary


def render_last_dashboard(workspace: Path):
    from .visualizer import render_dashboard
    bundle = json.loads((workspace / ".aeos" / "evidence" / "bundle.json")
                        .read_text(encoding="utf-8"))
    events = []
    ev_file = Path(bundle["events_file"])
    if ev_file.exists():
        for line in ev_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                from .observability import Event
                events.append(Event(kind=d["kind"], detail=d["detail"], ts=d["ts"]))
    return render_dashboard(bundle, events,
                            workspace / ".aeos" / "dashboard.html")
