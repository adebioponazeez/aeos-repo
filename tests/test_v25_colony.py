"""v25 tests: the colony — explicit graph, fail-closed, never hangs."""

from aeos.colony import Colony, Node
from aeos.fleet import EventBus


class TestGraph:
    def test_dependency_order_is_respected(self):
        order = []
        c = Colony()
        c.add(Node("scout", lambda ctx: (order.append("scout"), "brief")[1]))
        c.add(Node("smith", lambda ctx: (order.append("smith"), "code")[1],
                   requires=("scout",)))
        c.add(Node("warden", lambda ctx: (order.append("warden"), "ok")[1],
                   requires=("smith",)))
        rep = c.run()
        assert rep.ok and rep.executed == ["scout", "smith", "warden"]
        assert order == ["scout", "smith", "warden"]

    def test_independent_nodes_run_in_the_first_wave(self):
        c = Colony()
        c.add(Node("a", lambda ctx: 1))
        c.add(Node("b", lambda ctx: 2))
        rep = c.run()
        assert rep.ok and rep.waves == 1 and len(rep.executed) == 2

    def test_ctx_carries_outputs_to_dependents(self):
        c = Colony()
        c.add(Node("scout", lambda ctx: {"risk": "high"}))
        c.add(Node("smith", lambda ctx: f"mitigated:{ctx['scout']['risk']}",
                   requires=("scout",)))
        rep = c.run(ctx={"seed": True})
        assert rep.executed == ["scout", "smith"]

    def test_condition_gate_skips_cleanly(self):
        c = Colony()
        c.add(Node("scout", lambda ctx: "ok"))
        c.add(Node("deploy", lambda ctx: "shipped", requires=("scout",),
                   condition=lambda ctx: ctx.get("deploy") is True))
        rep = c.run()
        assert rep.skipped == ["deploy"] and rep.executed == ["scout"]
        assert not rep.ok                       # skipped = degraded

    def test_failure_blocks_dependents_fail_closed(self):
        def boom(ctx):
            raise ValueError("gate refused")
        c = Colony()
        c.add(Node("a", boom))
        c.add(Node("b", lambda ctx: "never", requires=("a",)))
        c.add(Node("solo", lambda ctx: "fine"))
        rep = c.run()
        assert "a" in rep.failed and "b" in rep.blocked
        assert rep.executed == ["solo"] and not rep.ok

    def test_cycles_block_instead_of_hanging(self):
        c = Colony()
        c.add(Node("a", lambda ctx: 1, requires=("b",)))
        c.add(Node("b", lambda ctx: 2, requires=("a",)))
        rep = c.run(max_waves=10)
        assert sorted(rep.blocked) == ["a", "b"] and rep.executed == []

    def test_duplicate_node_refused(self):
        c = Colony().add(Node("only", lambda ctx: 1))
        try:
            c.add(Node("only", lambda ctx: 2))
            raised = False
        except ValueError:
            raised = True
        assert raised

    def test_every_transition_is_an_event(self, tmp_path):
        bus = EventBus(tmp_path / ".aeos" / "events.jsonl")
        c = Colony(bus)
        c.add(Node("solo", lambda ctx: 1))
        c.add(Node("gated", lambda ctx: 2, condition=lambda ctx: False))
        c.run()
        kinds = [e.kind for e in bus.replay()]
        assert kinds == ["NODE_STARTED", "NODE_DONE", "NODE_SKIPPED"]

    def test_two_runs_same_order(self):
        def build():
            c = Colony()
            c.add(Node("x", lambda ctx: 1))
            c.add(Node("y", lambda ctx: 2, requires=("x",)))
            return c
        r1 = build().run()
        r2 = build().run()
        assert r1.executed == r2.executed == ["x", "y"]


class TestCLI:
    def test_colony_command_renders(self, capsys):
        from aeos.cli import main
        rc = main(["colony"])
        out = capsys.readouterr().out
        assert rc == 0 and "COLONY" in out and "scout" in out
