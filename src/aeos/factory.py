"""v7.0 — The Capability Factory (L7): the system that designs,
validates, and (only under sponsorship) installs new capabilities.

The loop: history -> repeated signatures -> DESIGN a contract ->
VALIDATE it in a sandbox on the deterministic engine -> PROPOSE ->
(sponsorship) -> INSTALL into roster + catalog. Every stage emits
evidence; the human's token is the only key to the last door.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .catalog import Catalog, CapabilityUnit, package_agent
from .contracts import (ActionClass, AgentSpec, Envelope, TaskSpec, TaskState,
                        Verdict)
from .discovery import CapabilityDiscovery
from .evaluation import Evaluator
from .governor import Governor
from .harness import Harness
from .models import EchoModel, ModelCall
from .observability import EventLog
from .skills import SkillsRegistry
from .sponsorship import SponsorshipGate


@dataclass
class FactoryCandidate:
    signature: str            # e.g. "phase:triage:WRITE"
    count: int
    agent_name: str
    design: AgentSpec | None = None
    sandbox_verdict: Verdict = Verdict.UNVERIFIED
    installed: bool = False


def design_agent(signature: str) -> AgentSpec:
    """Derive a contract from a measured signature.

    The boundary comes from the signature's action class — WRITE-heavy
    patterns get a scoped tree under their own name; READ patterns get
    no write surface at all. The design is conservative by template."""
    parts = signature.split(":")
    role = parts[1] if len(parts) > 1 else "worker"
    klass = parts[2] if len(parts) > 2 else "READ"
    writes = [f"{role}/*"] if klass in ("WRITE", "EXECUTE") else []
    classes = [ActionClass.READ]
    if klass in ("WRITE", "EXECUTE"):
        classes.append(ActionClass.WRITE)
    if klass == "EXECUTE":
        classes.append(ActionClass.EXECUTE)
    return AgentSpec(
        name=f"{role}-specialist",
        mission=f"Own the repeated '{signature}' workload end to end",
        inputs=["upstream envelopes"], outputs=[f"{role} artifacts"],
        tools=["fs.read"] + (["fs.write"] if writes else []),
        constraints=["stay inside the writes: boundary",
                     "evidence or silence — no unbacked claims"],
        success_criteria=[f"{role} artifact exists, parses, non-empty",
                          "gates pass on first envelope"],
        evaluation_criteria=["stock gates all PASS"],
        escalation_conditions=["3 failed attempts", "spec ambiguity"],
        termination_conditions=["gates pass"],
        writes=writes, action_classes=classes,
        model_hint="default")


class CapabilityFactory:
    def __init__(self, *, skills: SkillsRegistry, discovery: CapabilityDiscovery,
                 governor: Governor, gate: SponsorshipGate,
                 catalog: Catalog, log: EventLog) -> None:
        self.skills = skills
        self.discovery = discovery
        self.governor = governor
        self.gate = gate
        self.catalog = catalog
        self.log = log

    # -------------------------------------------------------- pipeline
    def candidates(self) -> list[FactoryCandidate]:
        out = []
        for p in self.discovery.proposals():
            cand = FactoryCandidate(signature=p["signature"], count=p["count"],
                                    agent_name=design_agent(p["signature"]).name)
            cand.design = design_agent(p["signature"])
            out.append(cand)
        return out

    def validate_in_sandbox(self, cand: FactoryCandidate,
                            sandbox_dir: Path,
                            isolation: str = "inprocess") -> Verdict:
        """Prove the contract. v8 adds `isolation="process"`: the same
        smoke validation in a killable subprocess with wall-clock
        timeout and resource limits (ADR-017)."""
        assert cand.design is not None
        from .transport import run_isolated, smoke_validate
        if isolation == "process":
            result = run_isolated(cand.design, sandbox_dir)
            cand.sandbox_verdict = Verdict(result["verdict"])
            self.log.emit("factory.sandbox", candidate=cand.agent_name,
                          verdict=result["verdict"], isolation="process",
                          why=result.get("why", result.get("summary", "")))
            return cand.sandbox_verdict
        result = smoke_validate(cand.design, sandbox_dir)
        cand.sandbox_verdict = Verdict(result["verdict"])
        self.log.emit("factory.sandbox", candidate=cand.agent_name,
                      verdict=result["verdict"], isolation="inprocess",
                      why=result.get("why", result.get("summary", "")))
        return cand.sandbox_verdict

    def install(self, cand: FactoryCandidate, roster: dict[str, AgentSpec],
                *, token: str | None) -> tuple[bool, str]:
        assert cand.design is not None
        if cand.sandbox_verdict is not Verdict.PASS:
            return False, (f"refused: sandbox verdict is "
                           f"{cand.sandbox_verdict.value}, not PASS")
        scope = f"factory:install:{cand.agent_name}"
        if not self.gate.authorize(token, scope):
            return False, f"refused: sponsorship required for {scope}"
        roster[cand.agent_name] = cand.design
        unit = package_agent(cand.design)
        self.catalog.publish(unit)
        cand.installed = True
        self.log.emit("factory.installed", agent=cand.agent_name,
                      unit=unit.sha256[:12], signature=cand.signature,
                      version=__version__)
        return True, f"installed '{cand.agent_name}' into roster + catalog"

    def run(self, roster: dict[str, AgentSpec], sandbox_dir: Path,
            *, token: str | None = None,
            isolation: str = "inprocess") -> dict:
        started = time.time()
        cands = self.candidates()
        summary = {"candidates": len(cands), "validated": 0,
                   "proposed": [], "installed": [], "refused": [],
                   "candidates_detail": []}
        for cand in cands:
            v = self.validate_in_sandbox(cand, sandbox_dir / cand.agent_name,
                                         isolation=isolation)
            summary["candidates_detail"].append(
                {"name": cand.agent_name, "signature": cand.signature,
                 "count": cand.count, "sandbox": v.value})
            if v is Verdict.PASS:
                summary["validated"] += 1
                summary["proposed"].append(cand.agent_name)
                ok, why = self.install(cand, roster, token=token)
                (summary["installed"] if ok else summary["refused"]).append(why)
            else:
                summary["refused"].append(
                    f"{cand.agent_name}: sandbox {v.value}")
        summary["duration_s"] = round(time.time() - started, 3)
        self.log.emit("factory.run", **{k: v for k, v in summary.items()
                                        if isinstance(v, (int, float))})
        return summary
