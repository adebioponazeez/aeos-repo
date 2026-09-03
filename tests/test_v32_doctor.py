"""v32 tests: the physician — the system audits its own claims."""

import json

from aeos.doctor import (check_repo, check_workspace, classify_imports,
                         doctor, render, scan_imports, zero_dep_audit)


class TestZeroDepAudit:
    def test_the_charter_claim_is_machine_checked(self):
        audit = zero_dep_audit()
        assert audit["modules"] >= 55          # the whole package scanned
        assert audit["violations"] == {}       # ADR-002 holds

    def test_scan_finds_imports(self, tmp_path):
        (tmp_path / "mod.py").write_text(
            "import json\nimport os.path\nfrom aeos import vault\n",
            encoding="utf-8")
        imports = scan_imports(tmp_path)
        assert imports["mod.py"] == ["aeos", "json", "os"]

    def test_violations_are_named(self, tmp_path):
        (tmp_path / "a.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("import numpy\nimport torch\n",
                                       encoding="utf-8")
        res = classify_imports(scan_imports(tmp_path))
        assert res["violations"] == {"b.py": ["numpy", "torch"]}
        assert res["clean"] == 1

    def test_relative_imports_are_internal(self, tmp_path):
        (tmp_path / "c.py").write_text(
            "from . import vault\nfrom .vault import durable_write\n",
            encoding="utf-8")
        res = classify_imports(scan_imports(tmp_path))
        assert res["violations"] == {}


class TestWorkspaceChecks:
    def test_healthy_workspace_passes(self, tmp_path):
        from aeos.pipeline import reference_run
        ws = tmp_path / "ws"
        reference_run(ws, intent="Ship it per [STD-1]")
        rows = {a: v for a, v, _ in check_workspace(ws)}
        assert rows.get("memory schema") == "PASS"

    def test_future_schema_fails(self, tmp_path):
        ws = tmp_path / "ws"
        (ws / ".aeos").mkdir(parents=True)
        (ws / ".aeos" / "memory.jsonl").write_text(
            json.dumps({"aeos_schema": 99}) + "\n", encoding="utf-8")
        rows = {a: v for a, v, _ in check_workspace(ws)}
        assert rows["memory schema"] == "FAIL"

    def test_torn_sidecar_warns(self, tmp_path):
        ws = tmp_path / "ws"
        (ws / ".aeos").mkdir(parents=True)
        (ws / ".aeos" / "memory.jsonl.torn").write_text("junk\n",
                                                        encoding="utf-8")
        rows = {a: v for a, v, _ in check_workspace(ws)}
        assert rows["torn writes"] == "WARN"

    def test_held_lock_warns(self, tmp_path):
        from aeos.vault import WorkspaceLock
        ws = tmp_path / "ws"
        (ws / ".aeos").mkdir(parents=True)
        lock = WorkspaceLock(ws / ".aeos" / "workspace.lock")
        lock.acquire()
        try:
            rows = {a: v for a, v, _ in check_workspace(ws)}
            assert rows["workspace lock"] == "WARN"
        finally:
            lock.release()


class TestRepoChecks:
    def test_clean_repo_passes(self, tmp_path):
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "x"],
                       cwd=tmp_path, check=True,
                       env={"GIT_AUTHOR_NAME": "t",
                            "GIT_AUTHOR_EMAIL": "t@t",
                            "GIT_COMMITTER_NAME": "t",
                            "GIT_COMMITTER_EMAIL": "t@t",
                            "PATH": "/usr/bin:/bin:/usr/local/bin"})
        rows = {a: v for a, v, _ in check_repo(tmp_path)}
        assert rows["working tree"] == "PASS"

    def test_no_repo_warns(self, tmp_path):
        rows = {a: v for a, v, _ in check_repo(tmp_path)}
        assert rows["version control"] == "WARN"


class TestDoctor:
    def test_full_doctor_healthy_on_this_repo(self):
        rep = doctor()
        assert rep["failed"] == 0
        areas = [r["area"] for r in rep["rows"]]
        assert "zero dependencies (ADR-002)" in areas

    def test_render_names_verdicts(self):
        text = render(doctor())
        assert "DOCTOR" in text and "PASS" in text

    def test_doctor_command_exits_by_health(self, tmp_path, capsys):
        from aeos.cli import main
        rc = main(["doctor"])
        out = capsys.readouterr().out
        assert rc == 0 and "DOCTOR" in out
