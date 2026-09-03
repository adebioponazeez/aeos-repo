"""v3.0 — Capability Catalog: package, verify, distribute (the-library
pattern). Skills and agents become units with content hashes; install
verifies integrity — tampered units are refused, not installed.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path


def _sha(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


@dataclass
class CapabilityUnit:
    name: str
    kind: str                      # "skill" | "agent"
    version: str
    payload: dict                  # SkillSpec / AgentSpec as dict
    created_at: float = 0.0
    sha256: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        if not self.sha256:
            self.sha256 = _sha({"kind": self.kind, "name": self.name,
                                "version": self.version, "payload": self.payload})

    def verify(self) -> bool:
        return self.sha256 == _sha({"kind": self.kind, "name": self.name,
                                    "version": self.version,
                                    "payload": self.payload})

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CapabilityUnit":
        return cls(name=d["name"], kind=d["kind"], version=d["version"],
                   payload=d["payload"], created_at=d.get("created_at", 0.0),
                   sha256=d.get("sha256", ""))


class Catalog:
    """A directory of signed units + install with verification."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, unit: CapabilityUnit) -> Path:
        if not unit.verify():
            raise ValueError(f"unit '{unit.name}' fails its own hash — refusing to publish")
        target = self.root / f"{unit.kind}.{unit.name}.v{unit.version}.json"
        target.write_text(json.dumps(unit.to_dict(), indent=2), encoding="utf-8")
        return target

    def list_units(self) -> list[CapabilityUnit]:
        return [CapabilityUnit.from_dict(json.loads(p.read_text(encoding="utf-8")))
                for p in sorted(self.root.glob("*.json"))]

    def install(self, kind: str, name: str, version: str,
                into: Path) -> CapabilityUnit:
        """Install == verify hash, then stamp payload into `into/.aeos/installed/`."""
        for unit in self.list_units():
            if (unit.kind, unit.name, unit.version) == (kind, name, version):
                if not unit.verify():
                    raise ValueError(
                        f"unit '{name}' v{version} tampered (hash mismatch) — "
                        "refusing install")
                dest = into / ".aeos" / "installed" / f"{kind}.{name}.json"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(unit.to_dict(), indent=2),
                                encoding="utf-8")
                return unit
        raise KeyError(f"no such unit: {kind}/{name} v{version}")


def package_skill(spec) -> CapabilityUnit:
    from dataclasses import asdict as _asdict
    return CapabilityUnit(name=spec.name, kind="skill", version=spec.version,
                          payload=_asdict(spec))


def package_agent(spec) -> CapabilityUnit:
    from dataclasses import asdict as _asdict
    d = _asdict(spec)
    d["action_classes"] = [a.value for a in spec.action_classes]
    return CapabilityUnit(name=spec.name, kind="agent", version="1.0.0",
                          payload=d)
