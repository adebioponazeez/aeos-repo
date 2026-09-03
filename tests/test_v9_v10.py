"""v9 co-design + v10 federation tests."""

import pytest
from pathlib import Path

from aeos.codesign import (CoDesignSession, co_design, score_variant,
                           validate_slate, variants_for)
from aeos.federation import (FederationHub, package_agent_for,
                             federation_demo)
from aeos.catalog import Catalog
from aeos.contracts import Verdict
from aeos.factory import design_agent
from aeos.sponsorship import SponsorshipGate


# ------------------------------------------------------------------- v9

class TestVariants:
    def test_three_philosophies_generated(self):
        slate = variants_for("phase:triage:WRITE")
        labels = [v.label for v in slate]
        assert set(labels) == {"conservative", "minimal-privilege",
                               "reviewer-first"}

    def test_every_variant_is_contract_complete(self):
        for v in variants_for("phase:triage:WRITE"):
            assert v.spec.validate() == []

    def test_least_privilege_ranks_first(self):
        slate = variants_for("phase:triage:WRITE")   # already sorted
        assert slate[0].label == "minimal-privilege"
        assert slate[0].spec.writes == []
        assert score_variant(slate[0].spec) >= score_variant(slate[-1].spec)

    def test_sandbox_validates_whole_slate(self, tmp_path):
        session = co_design("phase:triage:WRITE", tmp_path / "sb")
        assert all(v.sandbox_verdict is Verdict.PASS
                   for v in session.slate)

    def test_choice_requires_sponsored_variant_scope(self, tmp_path):
        session = co_design("phase:triage:WRITE", tmp_path / "sb")
        gate = SponsorshipGate()
        ok, why = session.choose("minimal-privilege", token=None, gate=gate)
        assert not ok and "sponsorship required" in why
        assert session.chosen is None

    def test_choice_with_token_and_scope(self, tmp_path):
        session = co_design("phase:triage:WRITE", tmp_path / "sb")
        gate = SponsorshipGate()
        token = gate.issue(
            f"codesign:triage-specialist:minimal-privilege").token
        ok, why = session.choose("minimal-privilege", token=token, gate=gate)
        assert ok and session.chosen == "minimal-privilege"
        # one-shot: choosing again (even another variant) is refused
        ok2, why2 = session.choose("conservative", token=token, gate=gate)
        assert not ok2

    def test_wrong_variant_token_scope_refused(self, tmp_path):
        session = co_design("phase:triage:WRITE", tmp_path / "sb")
        gate = SponsorshipGate()
        token = gate.issue("codesign:triage-specialist:conservative").token
        ok, why = session.choose("minimal-privilege", token=token, gate=gate)
        assert not ok

    def test_unknown_variant_refused(self, tmp_path):
        session = CoDesignSession(signature="s")
        ok, why = session.choose("nope", token=None, gate=SponsorshipGate())
        assert not ok and "no variant" in why


# ------------------------------------------------------------------ v10

class TestFederation:
    def _foreign(self, root: Path) -> Catalog:
        cat = Catalog(root)
        cat.publish(package_agent_for(design_agent("phase:triage:WRITE")))
        return cat

    def test_import_lands_quarantined(self, tmp_path):
        foreign = self._foreign(tmp_path / "foreign")
        hub = FederationHub(tmp_path / "local")
        imported = hub.import_from(foreign)
        assert len(imported) == 1
        assert imported[0].trust == "QUARANTINED"

    def test_quarantined_install_refused_even_with_token(self, tmp_path):
        foreign = self._foreign(tmp_path / "foreign")
        hub = FederationHub(tmp_path / "local")
        hub.import_from(foreign)
        gate = SponsorshipGate()
        token = gate.issue("federation:install:triage-specialist").token
        ok, why = hub.install("agent", "triage-specialist", "1.0.0",
                              tmp_path, token=token, gate=gate)
        assert not ok and "QUARANTINED" in why

    def test_revalidate_promotes_and_install_succeeds(self, tmp_path):
        foreign = self._foreign(tmp_path / "foreign")
        hub = FederationHub(tmp_path / "local")
        hub.import_from(foreign)
        verdict = hub.revalidate("agent", "triage-specialist", "1.0.0",
                                 tmp_path / "sb")
        assert verdict is Verdict.PASS
        assert hub.units[("agent", "triage-specialist", "1.0.0")].trust == "TRUSTED"
        gate = SponsorshipGate()
        token = gate.issue("federation:install:triage-specialist").token
        ok, why = hub.install("agent", "triage-specialist", "1.0.0",
                              tmp_path, token=token, gate=gate)
        assert ok

    def test_tampered_foreign_unit_never_enters(self, tmp_path):
        foreign = self._foreign(tmp_path / "foreign")
        # tamper on disk after publishing
        target = next((tmp_path / "foreign").glob("*.json"))
        import json as _json
        d = _json.loads(target.read_text())
        d["payload"]["mission"] = "hacked"
        target.write_text(_json.dumps(d))
        hub = FederationHub(tmp_path / "local")
        assert hub.import_from(foreign) == []

    def test_export_bundle_carries_provenance(self, tmp_path):
        foreign = self._foreign(tmp_path / "foreign")
        hub = FederationHub(tmp_path / "local")
        hub.import_from(foreign)
        out = hub.export_bundle(tmp_path / "bundle.json", provenance="team-a")
        import json as _json
        data = _json.loads(out.read_text())
        assert data["provenance"] == "team-a" and len(data["units"]) == 1

    def test_federation_demo_end_to_end(self, tmp_path):
        summary = federation_demo(tmp_path / "fed")
        assert summary["stage_1_import"]["imported"] == 1
        assert "QUARANTINED" in summary["stage_2_refused_quarantined"]["with_token"]
        assert summary["stage_3_revalidated_locally"] == "PASS"
        assert summary["stage_4_sponsored_install"]["ok"] is True
