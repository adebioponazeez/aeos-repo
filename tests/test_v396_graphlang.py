"""v39.6 The Graph Language: declarative DOT + routing stylesheets,
tested as law (ADR-052).

The contract under test: workflows are version-controlled graphs
(DOT subset); clusters compile to NESTED HARNESSES (subplans, the
v39.5 recursion, now declarative); stylesheets route per-key with
fallback; and the safety law — ROUTING NEVER DECLASSIFIES — is
refused at compile time, named, in both places it could hide
(edges and stylesheets). The compiled graph is the SAME TaskSpec
the orchestrator already runs: same governor, hooks, gates.
"""

from __future__ import annotations

import json

import pytest

from aeos.contracts import ActionClass, TaskState
from aeos.graphlang import (GraphError, apply_style, compile_graph,
                            parse_style, render_plan)


DEMO = '''
digraph ship {
  define   [label="Formalize the intent", agent="executive"];
  research [label="Ground in facts", agent="researcher", class="NETWORK"];
  define -> research;
  subgraph cluster_build {
    core [agent="builder", class="WRITE", label="core module"];
    cli  [agent="builder", class="WRITE", label="cli module"];
    core -> cli;
  }
  research -> core;
  cli -> evaluate;
  evaluate [agent="evaluator", label="grade it"];
}
'''


def canon(tasks):
    def d(ts):
        return [{"name": t.name, "agent": t.agent,
                 "class": t.action_class.value, "model": t.model,
                 "deps": sorted(t.depends_on),
                 "attempts": t.max_attempts,
                 "sub": d(t.subplan) if t.subplan else None}
                for t in ts]
    return json.dumps(d(tasks), sort_keys=True)


class TestParsing:
    def test_nodes_edges_attrs(self):
        tasks = {t.name: t for t in compile_graph(DEMO)}
        assert tasks["research"].agent == "researcher"
        assert tasks["research"].action_class is ActionClass.NETWORK
        assert tasks["research"].description == "Ground in facts"
        assert "define" in tasks["research"].depends_on
        assert tasks["define"].action_class is ActionClass.READ

    def test_edge_direction_is_after(self):
        tasks = {t.name: t for t in compile_graph(DEMO)}
        # define -> research means research runs AFTER define
        assert "define" in tasks["research"].depends_on
        assert "research" not in tasks["define"].depends_on

    def test_determinism_same_input_same_compile(self):
        assert canon(compile_graph(DEMO)) == canon(compile_graph(DEMO))


class TestClusters:
    def test_cluster_becomes_nested_harness(self):
        tasks = {t.name: t for t in compile_graph(DEMO)}
        assert tasks["build"].subplan is not None
        sub = {t.name: t for t in tasks["build"].subplan}
        assert set(sub) == {"core", "cli"}
        assert "core" in sub["cli"].depends_on   # intra-cluster edge

    def test_cross_level_edge_attaches_through_parent(self):
        tasks = {t.name: t for t in compile_graph(DEMO)}
        # research -> core (core lives in the cluster): the PARENT
        # task build depends on research; no phantom 'core' at top
        assert "research" in tasks["build"].depends_on
        assert "core" not in tasks
        assert "build" in tasks["evaluate"].depends_on  # cli -> evaluate

    def test_no_phantom_nodes_from_cross_edges(self):
        tasks = compile_graph(DEMO)
        top = {t.name for t in tasks}
        assert "core" not in top and "cli" not in top

    def test_intra_cluster_edge_declared_at_parent_goes_inside(self):
        dot = ('digraph g { subgraph cluster_c { a [agent="x"]; '
               'b [agent="y"]; } a -> b; }')
        tasks = {t.name: t for t in compile_graph(dot)}
        sub = {t.name: t for t in tasks["c"].subplan}
        assert "a" in sub["b"].depends_on

    def test_nested_clusters_two_levels(self):
        dot = ('digraph g { subgraph cluster_outer { '
               'subgraph cluster_inner { a [agent="x"]; } '
               'b [agent="y"]; } }')
        tasks = {t.name: t for t in compile_graph(dot)}
        outer = tasks["outer"]
        assert outer.subplan is not None
        names = {t.name for t in outer.subplan}
        assert names == {"inner", "b"}
        inner = [t for t in outer.subplan if t.name == "inner"][0]
        assert inner.subplan and inner.subplan[0].name == "a"

    def test_depth_cap_is_a_named_compile_error(self):
        from aeos.orchestrator import MAX_SUBPLAN_DEPTH
        inner = 'a [agent="x"]'
        for _ in range(MAX_SUBPLAN_DEPTH + 1):
            inner = f'subgraph cluster_c {{ {inner} }}'
        with pytest.raises(GraphError, match="not a trap"):
            compile_graph(f"digraph g {{ {inner} }}")


class TestStyleSheet:
    STYLE = '''
[research*]
model=echo-fast

[cluster_build]
max_attempts=3

[*]
model=echo
'''

    def test_per_key_fallback(self):
        tasks = {t.name: t for t in compile_graph(DEMO, self.STYLE)}
        assert tasks["research"].model == "echo-fast"
        assert tasks["define"].model == "echo"
        # build matched [cluster_build] (max_attempts) and falls
        # through to [*] for the model key
        assert tasks["build"].max_attempts == 3
        assert tasks["build"].model == "echo"

    def test_cluster_name_matches_parent(self):
        tasks = {t.name: t for t in compile_graph(DEMO, self.STYLE)}
        assert tasks["build"].max_attempts == 3

    def test_style_walks_into_subplans(self):
        style = "[core]\nmodel=deep-echo\n"
        tasks = {t.name: t for t in compile_graph(DEMO, style)}
        sub = {t.name: t for t in tasks["build"].subplan}
        assert sub["core"].model == "deep-echo"
        assert sub["cli"].model is None

    def test_stylesheet_never_declassifies(self):
        with pytest.raises(GraphError, match="never declassify"):
            parse_style("[x]\nclass=READ\n")

    def test_bad_ini_is_named(self):
        with pytest.raises(GraphError, match="not valid INI"):
            parse_style("[unterminated\nmodel=x\n")

    def test_bad_max_attempts_is_named(self):
        with pytest.raises(GraphError, match="integer"):
            compile_graph(DEMO, "[*]\nmax_attempts=lots\n")


class TestNamedErrors:
    def test_undeclared_edge_target(self):
        with pytest.raises(GraphError, match="never declared"):
            compile_graph('digraph g { a [agent="x"]; a -> b; }')

    def test_cycle(self):
        with pytest.raises(GraphError, match="cycle"):
            compile_graph('digraph g { a [agent="x"]; b [agent="y"]; '
                          'a -> b; b -> a; }')

    def test_no_agent(self):
        with pytest.raises(GraphError, match="no agent"):
            compile_graph('digraph g { a; }')

    def test_unknown_class(self):
        with pytest.raises(GraphError, match="unknown class"):
            compile_graph('digraph g { a [agent="x", class="MAGIC"]; }')

    def test_non_cluster_subgraph(self):
        with pytest.raises(GraphError, match="cluster_"):
            compile_graph('digraph g { subgraph s { a [agent="x"]; } }')

    def test_edge_cannot_set_class(self):
        with pytest.raises(GraphError, match="cannot set class"):
            compile_graph('digraph g { a [agent="x"]; b [agent="y"]; '
                          'a -> b [class="READ"]; }')

    def test_lex_error_names_the_language(self):
        with pytest.raises(GraphError, match="DOT subset"):
            compile_graph('digraph g { a @ b; }')


class TestExecution:
    def _roster_and_handlers(self):
        from aeos.contracts import (ActionClass, AgentSpec, Envelope,
                                    Evidence, Verdict)
        from aeos.models import EchoModel
        from aeos.evaluation import Evaluator
        from aeos.governor import Governor
        from aeos.hooks import HookBus
        from aeos.observability import EventLog
        from aeos.orchestrator import Orchestrator
        from pathlib import Path

        def spec(name, *classes):
            return AgentSpec(name=name, mission=f"m-{name}",
                             inputs=["i"], outputs=["o"], tools=["t"],
                             constraints=["c"], success_criteria=["s"],
                             evaluation_criteria=["e"],
                             escalation_conditions=["x"],
                             termination_conditions=["t"], writes=[],
                             action_classes=list(classes)
                             or [ActionClass.READ])
        roster = {"executive": spec("executive", ActionClass.WRITE),
                  "researcher": spec("researcher", ActionClass.NETWORK),
                  "builder": spec("builder", ActionClass.WRITE),
                  "evaluator": spec("evaluator")}

        def handler(agent):
            def h(task, orch):
                return Envelope(
                    agent=agent, objective=task.description,
                    claims=[f"{agent} handled {task.name}"],
                    evidence=[Evidence(kind="gate", detail="ran",
                                       verdict=Verdict.PASS)])
            return h

        log = EventLog()
        bus = HookBus()
        orch = Orchestrator(agents=roster,
                            handlers={n: handler(n) for n in roster},
                            model=EchoModel(), governor=Governor(log=log),
                            evaluator=Evaluator(), log=log,
                            workspace=Path("."), hooks=bus)
        return orch, log, bus

    def test_compiled_graph_runs_green_with_subplans(self):
        orch, log, bus = self._roster_and_handlers()
        waves = []
        bus.register("wave.post", lambda p: waves.append(p["wave"]))
        rep = orch.run("graph", compile_graph(DEMO))
        assert rep.accepted
        kinds = [e.kind for e in log.events()]
        assert "subplan.start" in kinds and "subplan.end" in kinds
        assert waves, "wave hooks fired through the compiled graph"

    def test_routing_is_visible_on_the_compiled_tasks(self):
        style = "[research*]\nmodel=echo-fast\n"
        tasks = {t.name: t for t in compile_graph(DEMO, style)}
        assert tasks["research"].model == "echo-fast"


class TestCLI:
    def test_dry_run_and_refusals(self, tmp_path, monkeypatch, capsys):
        from aeos.cli import main
        dot = tmp_path / "p.dot"
        dot.write_text('digraph g { a [agent="executive"]; }')
        monkeypatch.setattr("sys.argv",
                            ["aeos", "graph", "--file", str(dot)])
        assert main() == 0
        assert "compiled plan" in capsys.readouterr().out
        monkeypatch.setattr("sys.argv",
                            ["aeos", "graph", "--file",
                             str(tmp_path / "missing.dot")])
        assert main() == 2
        assert "not found" in capsys.readouterr().out
        bad = tmp_path / "bad.dot"
        bad.write_text("digraph g { a @ b; }")
        monkeypatch.setattr("sys.argv",
                            ["aeos", "graph", "--file", str(bad)])
        assert main() == 2
        assert "DOT subset" in capsys.readouterr().out

    def test_run_executes_the_demo_graph(self, tmp_path, monkeypatch,
                                         capsys):
        from aeos.cli import main
        import shutil
        repo = shutil.copytree("/home/user/aeos/examples",
                               tmp_path / "examples") \
            if (Path("/home/user/aeos/examples").exists()) else None
        if repo is None:                       # cold/CI checkout layout
            repo = Path(__file__).resolve().parent.parent / "examples"
        monkeypatch.setattr(
            "sys.argv", ["aeos", "graph", "--file",
                         str(repo / "ship-graph.dot"), "--style",
                         str(repo / "routing.style"), "--run",
                         "--workspace", str(tmp_path / "ws")])
        assert main() == 0
        out = capsys.readouterr().out
        assert "GRAPH RUN — ACCEPTED" in out
        assert "routing:" in out and "research->echo-fast" in out
        assert "subplan.start" in out


from pathlib import Path  # noqa: E402  (used above in test_run)
