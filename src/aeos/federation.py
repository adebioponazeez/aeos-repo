"""v10.0 — Federation: the cross-organization capability market.

Foreign capability units are facts about someone else's system:
potentially valuable, categorically untrusted. The federation rule is
one sentence — IMPORT IS QUARANTINE. A unit from another catalog lands
QUARANTINED, cannot be installed by anyone (token or no token), and
becomes TRUSTED only by passing OUR sandbox with OUR gates. No amount
of foreign reputation substitutes for local validation (ADR-019).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import Catalog, CapabilityUnit
from .contracts import Verdict
from .transport import smoke_validate


@dataclass
class FederatedUnit:
    unit: CapabilityUnit
    trust: str = "QUARANTINED"        # QUARANTINED | TRUSTED
    origin: str = "foreign"
    imported_at: float = field(default_factory=time.time)
    revalidated_at: float | None = None

    def to_dict(self) -> dict:
        return {"name": self.unit.name, "kind": self.unit.kind,
                "version": self.unit.version, "sha256": self.unit.sha256[:12],
                "trust": self.trust, "origin": self.origin}


class FederationHub:
    def __init__(self, local_root: Path) -> None:
        self.local = Catalog(local_root)
        self.state_path = self.local.root / "federation.jsonl"
        self.units: dict[tuple[str, str, str], FederatedUnit] = {}
        if self.state_path.exists():
            import json
            for line in self.state_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    d = json.loads(line)
                    key = (d["kind"], d["name"], d["version"])
                    fu = FederatedUnit(
                        unit=next(u for u in self.local.list_units()
                                  if (u.kind, u.name, u.version) == key),
                        trust=d["trust"], origin=d.get("origin", "foreign"),
                        imported_at=d.get("imported_at", 0.0),
                        revalidated_at=d.get("revalidated_at"))
                    self.units[key] = fu

    # ------------------------------------------------------------ import
    def import_from(self, foreign: Catalog) -> list[FederatedUnit]:
        """Pull every verifiable foreign unit in as QUARANTINED.
        Units that fail their own hash are refused at the border."""
        imported = []
        for u in foreign.list_units():
            if not u.verify():
                continue           # tampered foreign artifacts never enter
            key = (u.kind, u.name, u.version)
            if key in self.units:
                continue
            # store a copy in the local catalog under the same identity
            self.local.publish(u)
            fu = FederatedUnit(unit=u)
            self.units[key] = fu
            imported.append(fu)
        self._flush()
        return imported

    # -------------------------------------------------------- revalidate
    def revalidate(self, kind: str, name: str, version: str,
                   sandbox_root: Path) -> Verdict:
        """The ONLY path from QUARANTINED to TRUSTED: a local sandbox
        run under local gates. Reputation is not a verdict."""
        key = (kind, name, version)
        fu = self.units.get(key)
        if fu is None:
            raise KeyError(f"no federated unit {key}")
        if fu.unit.kind != "agent":
            fu.trust = "TRUSTED"       # skills: hash + local review suffice
            fu.revalidated_at = time.time()
            self._flush()
            return Verdict.PASS
        from .contracts import ActionClass, AgentSpec
        d = dict(fu.unit.payload)
        d["action_classes"] = [ActionClass(a) for a in d.get("action_classes", ["READ"])]
        spec = AgentSpec(**d)
        result = smoke_validate(spec, sandbox_root / f"fed-{name}")
        if result["verdict"] == "PASS":
            fu.trust = "TRUSTED"
            fu.revalidated_at = time.time()
        self._flush()
        return Verdict(result["verdict"])

    # ------------------------------------------------------------ install
    def install(self, kind: str, name: str, version: str, into: Path,
                *, token: str | None, gate) -> tuple[bool, str]:
        key = (kind, name, version)
        fu = self.units.get(key)
        if fu is None:
            return False, f"no federated unit {key}"
        if fu.trust != "TRUSTED":
            return False, (f"'{name}' is {fu.trust} — revalidate locally "
                           "before any token can matter")
        scope = f"federation:install:{name}"
        if not gate.authorize(token, scope):
            return False, f"refused: sponsorship required for {scope}"
        self.local.install(kind, name, version, into)
        return True, f"installed federated '{name}' (origin {fu.origin})"

    # ------------------------------------------------------------- export
    def export_bundle(self, out: Path, provenance: str) -> Path:
        """Ship our capabilities with provenance — the same trust rule,
        viewed from the other side of the border."""
        import json
        bundle = {
            "provenance": provenance,
            "exported_at": time.time(),
            "units": [u.to_dict() | {"payload": u.unit.payload,
                                     "sha256": u.unit.sha256}
                      for u in self.units.values()],
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bundle, indent=2, default=str),
                       encoding="utf-8")
        return out

    def _flush(self) -> None:
        import json
        lines = [json.dumps({"kind": fu.unit.kind, "name": fu.unit.name,
                             "version": fu.unit.version, "trust": fu.trust,
                             "origin": fu.origin, "imported_at": fu.imported_at,
                             "revalidated_at": fu.revalidated_at})
                 for fu in self.units.values()]
        self.state_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def package_agent_for(spec):
    from dataclasses import asdict
    from .catalog import CapabilityUnit
    d = asdict(spec)
    d["action_classes"] = [a.value for a in spec.action_classes]
    return CapabilityUnit(name=spec.name, kind="agent", version="1.0.0",
                          payload=d)


def federation_demo(workspace: Path) -> dict:
    """The border, crossed honestly, in five witnessed stages:
    foreign catalog -> QUARANTINED import -> refused install (even
    with a token) -> local revalidation -> sponsored install."""
    from .factory import design_agent
    from .sponsorship import SponsorshipGate

    workspace.mkdir(parents=True, exist_ok=True)
    foreign_root = workspace / "foreign-catalog"
    foreign_root.mkdir(parents=True, exist_ok=True)
    foreign = Catalog(foreign_root)
    foreign.publish(package_agent_for(design_agent("phase:triage:WRITE")))

    hub = FederationHub(workspace / ".aeos" / "catalog")
    gate = SponsorshipGate(workspace / ".aeos" / "sponsorships.jsonl")

    imported = hub.import_from(foreign)
    quarantined = [u.to_dict() for u in imported]

    # 1) install while quarantined — refused before any token talk
    refused, why_refused = hub.install("agent", "triage-specialist", "1.0.0",
                                       workspace, token=None, gate=gate)

    # 2) a token cannot outrank quarantine either (and is NOT spent)
    early = gate.issue("federation:install:triage-specialist")
    refused2, why2 = hub.install("agent", "triage-specialist", "1.0.0",
                                 workspace, token=early.token, gate=gate)

    # 3) local revalidation under local gates
    verdict = hub.revalidate("agent", "triage-specialist", "1.0.0",
                             workspace / "sandboxes")

    # 4) sponsored install — the still-unspent token from stage 2
    ok, why_ok = hub.install("agent", "triage-specialist", "1.0.0",
                             workspace, token=early.token, gate=gate)

    bundle = hub.export_bundle(workspace / ".aeos" / "export-bundle.json",
                               provenance="aeos federation demo")
    return {
        "stage_1_import": {"imported": len(imported), "units": quarantined},
        "stage_2_refused_quarantined": {"no_token": why_refused,
                                        "with_token": why2},
        "stage_3_revalidated_locally": verdict.value,
        "stage_4_sponsored_install": {"ok": ok, "detail": why_ok},
        "stage_5_export": str(bundle),
    }
