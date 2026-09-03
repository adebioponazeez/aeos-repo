"""v16 tests: fleet CRUD lifecycle + append-only event stream."""

import pytest

from aeos.fleet import EventBus, FleetOrchestrator


@pytest.fixture
def fleet(tmp_path):
    bus = EventBus(tmp_path / ".aeos" / "events.jsonl")
    return FleetOrchestrator(bus), bus


class TestFleetCRUD:
    def test_register_dispatch_retire_lifecycle(self, fleet):
        orch, bus = fleet
        orch.register("scout", "research", skills=("brief",))
        orch.register("smith", "build")
        assert [a["name"] for a in orch.roster()] == ["scout", "smith"]
        orch.dispatch("scout", "survey the landscape")
        orch.retire("smith")
        assert [a["name"] for a in orch.roster()] == ["scout"]

    def test_duplicate_registration_refused(self, fleet):
        orch, _ = fleet
        orch.register("scout", "research")
        with pytest.raises(ValueError):
            orch.register("scout", "duplicate")

    def test_dispatch_to_unknown_agent_refused(self, fleet):
        orch, _ = fleet
        with pytest.raises(KeyError):
            orch.dispatch("ghost", "anything")

    def test_retire_unknown_agent_refused(self, fleet):
        orch, _ = fleet
        with pytest.raises(KeyError):
            orch.retire("ghost")


class TestEventBus:
    def test_events_replay_in_publish_order(self, fleet):
        orch, bus = fleet
        orch.register("a", "r1")
        orch.register("b", "r2")
        orch.dispatch("a", "t1")
        kinds = [e.kind for e in bus.replay()]
        assert kinds == ["AGENT_REGISTERED", "AGENT_REGISTERED",
                         "AGENT_TASK_SENT", "AGENT_TASK_DONE"]

    def test_subscribers_fire_on_publish(self, fleet):
        _, bus = fleet
        seen = []
        bus.subscribe(lambda ev: seen.append(ev.kind))
        bus.publish("AGENT_REGISTERED", "x")
        assert seen == ["AGENT_REGISTERED"]

    def test_tail_returns_last_n(self, fleet):
        _, bus = fleet
        for i in range(30):
            bus.publish("TICK", f"a{i}")
        assert len(bus.tail(5)) == 5
        assert bus.tail(5)[-1].agent == "a29"

    def test_replay_is_byte_stable(self, fleet):
        _, bus = fleet
        bus.publish("AGENT_REGISTERED", "x", "role=r")
        one = [e.as_line() for e in bus.replay()]
        two = [e.as_line() for e in bus.replay()]
        assert one == two


class TestCLI:
    def test_fleet_command_runs_a_governed_demo(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["fleet", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0
        assert "FLEET" in out and "AGENT_REGISTERED" in out

    def test_dashboard_live_tails_the_stream(self, tmp_path, capsys):
        from aeos.cli import main
        ws = tmp_path / "ws"
        main(["fleet", "--workspace", str(ws)])
        rc = main(["dashboard", "--workspace", str(ws), "--live"])
        out = capsys.readouterr().out
        assert rc == 0 and "AGENT_TASK_DONE" in out
