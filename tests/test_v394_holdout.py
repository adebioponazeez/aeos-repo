"""v39.4 The Holdout: digital-twin separation, tested as law.

The separation contract under test (ADR-050):
  1. scenarios are sealed — no plaintext instance on disk;
  2. instances are per-install — not derivable from this source;
  3. the run touches only a twin — the original is byte-identical;
  4. the report is verdict-only — no scenario content leaves the vault;
  5. a tampered seal refuses to run — integrity before evaluation;
  6. the evaluation itself is deterministic;
  7. the grading has teeth — a broken refusal naming FAILS a family.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from aeos.holdout import (HOSTILE_POOL, HoldoutVault, _family_refusal_named,
                          _dir_digest, run_holdout)
from aeos.pipeline import reference_run


@pytest.fixture()
def ws(tmp_path):
    w = tmp_path / "ws"
    reference_run(w, intent="seed a workspace worth evaluating")
    return w


@pytest.fixture()
def vault(tmp_path):
    v = HoldoutVault(tmp_path / "vault")
    v.init()
    return v


class TestSealing:
    def test_init_seals_and_verifies(self, tmp_path):
        v = HoldoutVault(tmp_path / "v")
        m = v.init()
        assert len(m["families"]) == 5
        ver = v.verify()
        assert ver["ok"] and ver["families"] == 5

    def test_no_plaintext_instances_on_disk(self, vault):
        blobs = list((vault.root / "sealed").rglob("*.blob"))
        assert len(blobs) == 5
        for f in vault.root.rglob("*"):
            if f.is_file():
                data = f.read_bytes()
                for phrase in HOSTILE_POOL:
                    assert phrase.encode() not in data, \
                        f"plaintext scenario leaked into {f.name}"

    def test_instances_are_per_install(self, tmp_path):
        """Two vaults, same source file: different instances. The
        holdout is not derivable from reading the codebase."""
        a = HoldoutVault(tmp_path / "a"); a.init()
        b = HoldoutVault(tmp_path / "b"); b.init()
        assert a.instances() != b.instances()

    def test_tampered_vault_refuses_to_run(self, vault, ws):
        blob = vault.root / "sealed" / "hostile_intents.blob"
        raw = bytearray(blob.read_bytes())
        raw[10] ^= 0xFF
        blob.write_bytes(bytes(raw))
        ver = vault.verify()
        assert ver["ok"] is False
        assert "integrity" in ver["reason"]
        rep = run_holdout(ws, vault)
        assert rep.passed is False
        assert rep.rows[0].family == "seal_integrity"
        assert "tampered" in rep.rows[0].detail or \
            "integrity" in rep.rows[0].detail


class TestDigitalTwin:
    def test_original_workspace_untouched(self, ws, vault):
        before = _dir_digest(ws)
        rep = run_holdout(ws, vault)
        assert rep.twin_untouched is True
        assert _dir_digest(ws) == before

    def test_report_is_verdict_only(self, ws, vault):
        rep = run_holdout(ws, vault)
        text = rep.render()
        for phrase in HOSTILE_POOL:
            assert phrase not in text, \
                "scenario content leaked into the report"
        assert rep.passed is True
        assert len(rep.rows) == 5

    def test_no_vault_material_in_workspace(self, ws, vault):
        run_holdout(ws, vault)
        for f in ws.rglob("*"):
            assert f.suffix != ".blob" and f.name not in (
                "nonce.key", "manifest.json"), \
                f"vault material copied into workspace: {f.name}"

    def test_holdout_evaluation_is_deterministic(self, tmp_path):
        v = HoldoutVault(tmp_path / "v"); v.init()
        w1 = tmp_path / "w1"
        reference_run(w1, intent="determinism of the holdout itself")
        w2 = shutil.copytree(w1, tmp_path / "w2")
        r1 = run_holdout(w1, v)
        r2 = run_holdout(w2, v)
        assert [r.__dict__ for r in r1.rows] == [r.__dict__ for r in r2.rows]
        assert r1.passed and r2.passed


class TestGradingHasTeeth:
    def test_unnamed_refusal_fails_the_family(self, tmp_path, monkeypatch):
        """A regression to unnamed refusals must be CAUGHT by the
        holdout, not silently passed."""
        import aeos.pipeline as pipe

        def broken_run(workspace, intent="", **kw):
            return {"accepted": False, "reason": "nope"}

        monkeypatch.setattr(pipe, "reference_run", broken_run)
        w = tmp_path / "w"
        w.mkdir()
        row = _family_refusal_named(w, {})
        assert row.passed is False
        assert "not named" in row.detail


class TestCLI:
    def test_cli_init_and_run(self, tmp_path, monkeypatch):
        from aeos.cli import main
        v = tmp_path / "cli-vault"
        ws = tmp_path / "cli-ws"
        reference_run(ws, intent="cli holdout roundtrip")
        monkeypatch.setattr("sys.argv", [
            "aeos", "holdout", "--init", "--vault", str(v)])
        assert main() == 0
        monkeypatch.setattr("sys.argv", [
            "aeos", "holdout", "--run", "--vault", str(v),
            "--workspace", str(ws)])
        assert main() == 0

class TestHonestEdges:
    def test_missing_workspace_refuses_named(self, tmp_path, vault):
        """A missing --workspace is a named refusal, never a
        traceback (the plain-language law, CLI edges included)."""
        rep = run_holdout(tmp_path / "does-not-exist", vault)
        assert rep.passed is False
        assert rep.rows[0].family == "workspace"
        assert "not found" in rep.rows[0].detail
        assert "Traceback" not in rep.render()
