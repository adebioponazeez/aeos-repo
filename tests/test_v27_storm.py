"""v27 tests: the storm — chaos scenarios, all survived."""

from aeos.storm import run_storm


class TestStorm:
    def test_every_scenario_survives(self, tmp_path):
        rep = run_storm(tmp_path / "storm")
        assert rep.passed, rep.render()

    def test_report_names_all_scenarios(self, tmp_path):
        rep = run_storm(tmp_path / "storm")
        from aeos.storm import SCENARIOS
        names = [r.scenario for r in rep.rows]
        assert len(names) == len(SCENARIOS)
        assert any("kill" in n for n in names)
        assert any("blackout" in n for n in names)
        assert rep.passed, rep.render()


class TestCLI:
    def test_storm_command_renders_the_receipt(self, tmp_path, capsys):
        from aeos.cli import main
        from aeos.storm import SCENARIOS
        rc = main(["storm", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        n = len(SCENARIOS)
        assert rc == 0
        assert "STORM" in out and f"{n}/{n}" in out
        assert "kill -9 storm" in out and "blackout" in out

    def test_vault_command_scans_environment(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["vault", "--workspace", str(tmp_path / "ws")])
        out = capsys.readouterr().out
        assert rc == 0 and "VAULT" in out and "disk" in out
