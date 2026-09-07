"""v37 tests: the ignition — one front door, staged boot, and
failures that speak plain language with remedies."""

import json
import os
import sys
from pathlib import Path

import pytest

from aeos.ignition import (EXIT_OK, EXIT_PREFLIGHT, EXIT_WORK,
                           EXIT_WORKSPACE, boot, post, prepare, render)
from aeos.cli import main


def _future_schema(ws: Path) -> None:
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".aeos").mkdir(exist_ok=True)
    (ws / ".aeos" / "memory.jsonl").write_text(
        '{"aeos_schema": 99, "kind": "memory"}\n', encoding="utf-8")


class TestPreflight:
    def test_healthy_workspace_is_all_clear(self, tmp_path):
        checks = post(tmp_path)
        verdicts = {c.name: c.verdict for c in checks}
        assert verdicts["python"] == "PASS"
        assert verdicts["zero dependencies (ADR-002)"] == "PASS"
        assert verdicts["workspace writable"] == "PASS"
        assert not [c for c in checks if c.verdict == "FAIL"]

    def test_state_from_the_future_fails_with_remedy(self, tmp_path):
        _future_schema(tmp_path)
        checks = post(tmp_path)
        bad = [c for c in checks if c.name == "state schema"]
        assert bad[0].verdict == "FAIL"
        assert "from the future" in bad[0].detail
        assert "upgrade" in bad[0].remedy        # what to do, in one word

    def test_every_fail_carries_a_remedy(self, tmp_path):
        # the plain-language law, enforced structurally
        _future_schema(tmp_path)
        (tmp_path / ".aeos" / "x.torn").write_text("cut", encoding="utf-8")
        checks = post(tmp_path)
        for c in checks:
            if c.verdict == "FAIL":
                assert c.remedy.strip(), f"{c.name} failed silently"
        torn = [c for c in checks if c.name == "torn writes"]
        assert torn[0].verdict == "WARN"          # quarantined = continue

    def test_live_without_key_names_the_env_vars(self, tmp_path,
                                                 monkeypatch):
        for k in ("OPENROUTER_API_KEY", "ABACUS_API_KEY",
                  "OPENAI_API_KEY"):
            monkeypatch.delenv(k, raising=False)
        checks = post(tmp_path, live_requested=True)
        bad = [c for c in checks if c.name == "live key"]
        assert bad[0].verdict == "FAIL"
        assert "OPENROUTER_API_KEY" in bad[0].remedy

    def test_live_with_key_never_reads_the_value(self, tmp_path,
                                                 monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-SECRET-VALUE-xyz")
        checks = post(tmp_path, live_requested=True)
        good = [c for c in checks if c.name == "live key"]
        assert good[0].verdict == "PASS"
        assert "SECRET" not in good[0].detail      # presence, not value

    def test_unwritable_workspace_fails_with_permissions_remedy(
            self, tmp_path):
        if os.geteuid() == 0:
            pytest.skip("root ignores permission bits")
        dead = tmp_path / "locked"
        dead.mkdir()
        dead.chmod(0o500)
        checks = post(dead / "ws")
        bad = [c for c in checks if c.name == "workspace writable"]
        assert bad[0].verdict == "FAIL"
        assert "permission" in bad[0].remedy.lower()
        dead.chmod(0o700)

    def test_preflight_is_deterministic(self, tmp_path):
        a = [(c.name, c.verdict, c.detail) for c in post(tmp_path)]
        b = [(c.name, c.verdict, c.detail) for c in post(tmp_path)]
        assert a == b


class TestBoot:
    def test_happy_path_four_stages_and_receipt(self, tmp_path, capsys):
        rc = main(["up", "--workspace", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == EXIT_OK
        assert "BOOT — outcome: OK" in out
        assert "[1/4] PREFLIGHT" in out and "[4/4] SHUTDOWN" in out
        receipts = list((tmp_path / ".aeos" / "boots").glob("boot-*.json"))
        assert len(receipts) == 1
        r = json.loads(receipts[0].read_text(encoding="utf-8"))
        assert r["outcome"] == "ok" and r["stages"] == [
            "preflight", "workspace", "work", "shutdown"]
        assert r["run"]["accepted"] is True

    def test_boot_ledger_grows_and_remember(self, tmp_path):
        boot(tmp_path)
        boot(tmp_path)
        boots = sorted((tmp_path / ".aeos" / "boots").glob("boot-*.json"))
        assert len(boots) == 2
        assert json.loads(boots[1].read_text(encoding="utf-8"))[
            "boot_seq"] == 2

    def test_preflight_failure_exits_2_and_speaks(self, tmp_path,
                                                  capsys):
        _future_schema(tmp_path)
        rc = main(["up", "--workspace", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == EXIT_PREFLIGHT
        assert "what happened:" in out and "what to do:" in out
        assert "from the future" in out and "upgrade" in out
        # the failure is receipted too — the ledger explains itself
        r = json.loads(sorted(
            (tmp_path / ".aeos" / "boots").glob("boot-*.json"))[-1]
            .read_text(encoding="utf-8"))
        assert r["outcome"] == "preflight-failed"

    def test_work_failure_is_named_not_traced(self, tmp_path, capsys,
                                              monkeypatch):
        import aeos.pipeline as pipeline

        def explode(ws, intent="x", profile="balanced"):
            raise RuntimeError("the model seam refused the envelope")

        monkeypatch.setattr(pipeline, "reference_run", explode)
        rc = main(["up", "--workspace", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == EXIT_WORK
        assert "RuntimeError: the model seam refused" in out
        assert "what to do:" in out
        assert "Traceback" not in out
        r = json.loads(sorted(
            (tmp_path / ".aeos" / "boots").glob("boot-*.json"))[-1]
            .read_text(encoding="utf-8"))
        assert r["outcome"] == "work-failed"

    def test_next_boot_reports_the_previous_crash(self, tmp_path,
                                                  monkeypatch):
        import aeos.pipeline as pipeline

        def explode(ws, intent="x", profile="balanced"):
            raise RuntimeError("simulated production fault")

        monkeypatch.setattr(pipeline, "reference_run", explode)
        r1 = boot(tmp_path)
        assert r1["outcome"] == "work-failed"
        monkeypatch.undo()
        checks = post(tmp_path)
        prev = [c for c in checks if c.name == "previous boot"]
        assert prev[0].verdict == "WARN"
        assert "work-failed" in prev[0].detail
        assert "no torn state" in prev[0].remedy   # the reassurance
        r2 = boot(tmp_path)
        assert r2["outcome"] == "ok"               # and it continues

    def test_workspace_failure_path_exits_3(self, tmp_path, monkeypatch):
        import aeos.ignition as ign

        def refuse(ws):
            raise OSError(13, "permission denied")

        monkeypatch.setattr(ign, "prepare", refuse)
        r = boot(tmp_path)
        assert r["outcome"] == "workspace-failed"
        assert r["exit_code"] == EXIT_WORKSPACE
        assert r["remedy"]                   # named, with a fix

    def test_receipt_carries_no_secrets(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-TOPSECRET-42")
        boot(tmp_path)
        text = "\n".join(p.read_text(encoding="utf-8")
                         for p in (tmp_path / ".aeos" / "boots")
                         .glob("boot-*.json"))
        assert "TOPSECRET" not in text

    def test_save_proof_without_checkout_is_an_honest_skip(
            self, tmp_path, monkeypatch):
        # a proof nested inside a proof is refused by the guard below;
        # here we simulate NO checkout context: the resolver returns
        # None and the boot says so honestly instead of guessing
        monkeypatch.setattr("aeos.doctor.repo_root", lambda: None)
        r = boot(tmp_path, save_proof=True)
        assert r["outcome"] == "ok"
        assert r["save_proof"].startswith("skipped — no checkout")

    def test_nested_proof_is_refused_not_recursive(self, tmp_path,
                                                   monkeypatch):
        # found the hard way: `aeos up --save-proof` inside a test
        # run spawned the suite inside the suite. The guard: proof
        # commands run with AEOS_PROOF_INNER; a notary asked for the
        # DEFAULT SUITE COMMAND seeing it refuses.
        from aeos.saveproof import SaveProofError, run_notary
        monkeypatch.setenv("AEOS_PROOF_INNER", "1")
        with pytest.raises(SaveProofError) as ei:
            run_notary(tmp_path)          # default command = the suite
        assert "one proof at a time" in str(ei.value)
        # sharpened after the first guard proved too blunt (the
        # notary refused this very release's first proof): explicit
        # bounded commands are NOT recursion and must still work
        cert = run_notary(tmp_path, [sys.executable, "-c", "pass"])
        assert cert["outcome"] == "verified"


class TestDoctorRow:
    def test_doctor_reports_boot_blockers(self, tmp_path):
        from aeos.doctor import doctor
        _future_schema(tmp_path)
        rep = doctor(tmp_path)
        row = [r for r in rep["rows"] if r["area"] == "boot preflight"]
        assert row and row[0]["verdict"] == "FAIL"
        assert "would block `aeos up`" in row[0]["detail"]

    def test_doctor_preflight_healthy_workspace(self, tmp_path):
        from aeos.doctor import doctor
        prepare(tmp_path)
        rep = doctor(tmp_path)
        row = [r for r in rep["rows"] if r["area"] == "boot preflight"]
        assert row and row[0]["verdict"] in ("PASS", "WARN")
        assert rep["failed"] == 0


class TestRender:
    def test_failure_render_names_stage_and_remedy(self, tmp_path):
        _future_schema(tmp_path)
        r = boot(tmp_path)
        text = render(r)
        assert "IGNITION FAILED at stage 1/4 (preflight)" in text
        assert "what to do:" in text
        assert "exit code 2" in text

class TestPortability:
    def test_no_multiline_fstring_expressions(self):
        # v37.0.0 shipped an f-string expression spanning lines —
        # legal only under PEP 701 (3.12+); the CI matrix on 3.10
        # refused the whole module. The floor is 3.10, so the guard
        # is law: no f-string expression may span lines, ever.
        import ast
        import aeos
        pkg = Path(aeos.__file__).resolve().parent
        offenders = []
        for py in sorted(pkg.glob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.JoinedStr):
                    for v in node.values:
                        if (isinstance(v, ast.FormattedValue)
                                and v.lineno != v.end_lineno):
                            offenders.append(f"{py.name}:{v.lineno}")
        assert not offenders, \
            f"3.10-illegal multiline f-string: {offenders}"
