"""v35 tests: the scribe — documentation that cannot drift."""

from pathlib import Path

import pytest

from aeos.scribe import ScribeReport, _claims_in_line, audit, reality

REPO = Path(__file__).resolve().parents[1]


class TestReality:
    def test_reality_is_live(self):
        r = reality(REPO)
        assert r["tests"] > 400
        assert r["modules"] > 55
        assert r["adrs"] > 40
        assert "run-demo" in r["commands"] and "storm" in r["commands"]


class TestClaimExtraction:
    def test_counts_found(self):
        found = _claims_in_line("**414 tests + 1 live smoke, 58 modules**")
        assert ("tests", "414") in found and ("modules", "58") in found

    def test_proofs_count_as_tests(self):
        assert ("tests", "414") in _claims_in_line("414 proofs, ~110s")

    def test_adrs_found(self):
        assert ("adrs", "43") in _claims_in_line("43 ADRs on record")


class TestAudit:
    def test_honest_readme_passes(self, tmp_path):
        r = reality(REPO)
        (tmp_path / "README.md").write_text(
            f"**Version {r['version']}** — {r['tests']} tests, "
            f"{r['modules']} modules. Try `aeos storm` and "
            f"`aeos doctor`.\n", encoding="utf-8")
        rep = audit(tmp_path, ("README.md",), reality_from=REPO)
        assert rep.passed, rep.render()

    def test_drifted_readme_fails_with_location(self, tmp_path):
        (tmp_path / "README.md").write_text(
            "**Version 0.0.1** — 12 tests, 3 modules. `aeos warp`.\n",
            encoding="utf-8")
        rep = audit(tmp_path, ("README.md",), reality_from=REPO)
        kinds = {(c.kind, c.claimed) for c in rep.drift}
        assert ("version", "0.0.1") in kinds
        assert ("tests", "12") in kinds
        assert ("modules", "3") in kinds
        assert ("command", "warp") in kinds
        assert rep.drift[0].line == 1

    def test_lower_bound_form_is_honest(self, tmp_path):
        r = reality(REPO)
        (tmp_path / "README.md").write_text(
            f"{r['tests'] - 100}+ tests and growing\n", encoding="utf-8")
        rep = audit(tmp_path, ("README.md",), reality_from=REPO)
        assert rep.passed, rep.render()

    def test_missing_doc_is_a_drift(self, tmp_path):
        rep = audit(tmp_path, ("NOPE.md",))
        assert not rep.passed

    def test_version_table_rows_are_history(self, tmp_path):
        r = reality(REPO)
        (tmp_path / "README.md").write_text(
            f"| v1.0 | Kernel | 15 modules, 68 tests |\n"
            f"now: {r['tests']} tests\n", encoding="utf-8")
        rep = audit(tmp_path, ("README.md",), reality_from=REPO)
        assert rep.passed            # the v1.0 row is exempt, the now-line checks

    def test_the_real_readme_is_truthful_today(self):
        rep = audit(REPO, ("README.md",))
        assert rep.passed, rep.render()


class TestDoctorRow:
    def test_doctor_checks_the_readme(self):
        from aeos.doctor import doctor
        rep = doctor()
        row = next((r for r in rep["rows"]
                    if r["area"] == "README tells the truth"), None)
        assert row is not None and row["verdict"] == "PASS", row


class TestCLI:
    def test_repo_root_prefers_cwd_checkout(self, monkeypatch):
        from aeos.doctor import repo_root
        monkeypatch.chdir(REPO)
        assert repo_root() == REPO.resolve()

    def test_scribe_from_cwd_with_any_install(self, capsys, monkeypatch):
        from aeos.cli import main
        monkeypatch.chdir(REPO)          # wheel or editable: cwd wins
        rc = main(["scribe"])
        out = capsys.readouterr().out
        assert rc == 0 and "TRUTHFUL" in out

    def test_scribe_command(self, capsys):
        from aeos.cli import main
        rc = main(["scribe"])
        out = capsys.readouterr().out
        assert rc == 0 and "SCRIBE" in out and "claim" in out
