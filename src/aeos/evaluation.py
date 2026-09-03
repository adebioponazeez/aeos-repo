"""Evaluation OS: creation and evaluation are structurally separated.

The builder never grades its own work (spec §17). Evaluators receive
claims + artifacts and produce *evidence-checked* verdicts. The verdict
vocabulary is closed — PASS / FAIL / PARTIAL / UNVERIFIED — and
"the agent says it works" is mechanically excluded: an unbacked claim
can never be graded PASS, no matter who signs it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .contracts import Envelope, Evidence, Verdict


@dataclass
class CheckResult:
    name: str
    verdict: Verdict
    detail: str


@dataclass
class EvaluationReport:
    subject: str
    verdict: Verdict = Verdict.UNVERIFIED
    checks: list[CheckResult] = field(default_factory=list)
    unbacked_claims: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict is Verdict.PASS

    def add(self, name: str, verdict: Verdict, detail: str = "") -> "EvaluationReport":
        self.checks.append(CheckResult(name, verdict, detail))
        return self

    def finalize(self) -> "EvaluationReport":
        """Verdict = the WORST passing check, but UNVERIFIED beats nothing.

        If no check produced evidence, the report stays UNVERIFIED —
        absence of failure is not success."""
        verdicts = [c.verdict for c in self.checks]
        if not verdicts:
            self.verdict = Verdict.UNVERIFIED
        elif Verdict.FAIL in verdicts:
            self.verdict = Verdict.FAIL
        elif Verdict.UNVERIFIED in verdicts or Verdict.PARTIAL in verdicts:
            self.verdict = Verdict.PARTIAL if Verdict.PARTIAL in verdicts else Verdict.UNVERIFIED
        else:
            self.verdict = Verdict.PASS
        return self


class Gate:
    """One mechanically checkable assertion about an envelope."""

    def __init__(self, name: str, fn: "callable") -> None:  # type: ignore[valid-type]
        self.name = name
        self.fn = fn

    def run(self, envelope: Envelope, workspace: Path) -> CheckResult:
        try:
            ok, detail = self.fn(envelope, workspace)
            return CheckResult(self.name, Verdict.PASS if ok else Verdict.FAIL, detail)
        except Exception as exc:  # a broken gate is a failed gate, not a crash
            return CheckResult(self.name, Verdict.FAIL, f"gate error: {exc}")


# ------------------------------------------------------------ stock gates

def artifacts_exist(envelope: Envelope, ws: Path) -> tuple[bool, str]:
    if not envelope.artifacts:
        return True, "no artifacts declared"
    missing = [a for a in envelope.artifacts if not (ws / a).exists()]
    return (not missing, f"{len(envelope.artifacts)} checked, missing: {missing or 'none'}")


def artifacts_non_empty(envelope: Envelope, ws: Path) -> tuple[bool, str]:
    empty = [a for a in envelope.artifacts
             if (ws / a).exists() and (ws / a).stat().st_size == 0]
    return (not empty, f"empty artifacts: {empty or 'none'}")


def json_artifacts_parse(envelope: Envelope, ws: Path) -> tuple[bool, str]:
    for a in envelope.artifacts:
        p = ws / a
        if p.suffix == ".json" and p.exists():
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return False, f"{a} does not parse: {exc}"
    return True, "all JSON artifacts parse"


def changed_files_exist(envelope: Envelope, ws: Path) -> tuple[bool, str]:
    missing = [f for f in envelope.changed_files if not (ws / f).exists()]
    return (not missing, f"missing claimed files: {missing or 'none'}")


def claims_are_backed(envelope: Envelope, ws: Path) -> tuple[bool, str]:
    """THE anti-hallucination gate: every claim needs >=1 PASS evidence."""
    unbacked = [c for c in envelope.claims
                if not any(e.verdict is Verdict.PASS for e in envelope.evidence)]
    if envelope.claims and unbacked and not envelope.evidence:
        return False, f"{len(unbacked)} claim(s) with zero evidence attached"
    return True, "claims carry evidence"


STOCK_GATES = [
    Gate("artifacts_exist", artifacts_exist),
    Gate("artifacts_non_empty", artifacts_non_empty),
    Gate("json_artifacts_parse", json_artifacts_parse),
    Gate("changed_files_exist", changed_files_exist),
    Gate("claims_are_backed", claims_are_backed),
]


# ------------------------------------------------- v1.1 gate library
# Composable, opt-in gates beyond the stock set. Compose an Evaluator
# with these when a project's acceptance criteria demand them.

def schema_gate(required: dict[str, list[str]]) -> Gate:
    """Require each named JSON artifact to contain the required keys."""
    def check(envelope: Envelope, ws: Path) -> tuple[bool, str]:
        for artifact, keys in required.items():
            p = ws / artifact
            if not p.exists():
                continue  # existence is artifacts_exist's job
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return False, f"{artifact} is not a JSON object"
            missing = [k for k in keys if k not in data]
            if missing:
                return False, f"{artifact} missing keys: {missing}"
        return True, "schema satisfied"
    return Gate(f"schema({','.join(sorted(required))})", check)


def tests_pass_gate(envelope: Envelope, ws: Path) -> tuple[bool, str]:
    """Any test_run evidence must show N passed with no failures."""
    import re
    runs = [e for e in envelope.evidence if e.kind == "test_run"]
    if not runs:
        return True, "no test evidence claimed"
    for e in runs:
        if not re.search(r"\d+ passed", e.detail):
            return False, f"test evidence does not show passes: {e.detail!r}"
        if re.search(r"\d+ (failed|error)", e.detail):
            return False, f"test evidence shows failures: {e.detail!r}"
    return True, f"{len(runs)} test run(s) clean"


def regression_gate(book: "RegressionBook | None") -> Gate:
    """Changed-file patterns matching a recorded regression block ship."""
    def check(envelope: Envelope, ws: Path) -> tuple[bool, str]:
        if book is None:
            return True, "no regression book"
        hits = book.check(envelope.changed_files)
        return (not hits, f"regression signatures matched: {hits or 'none'}")
    return Gate("regressions", check)


class Evaluator:
    """Independent evaluator: different role, no shared state with builders."""

    def __init__(self, gates: list[Gate] | None = None) -> None:
        self.gates = gates if gates is not None else list(STOCK_GATES)
        self.reports: list[EvaluationReport] = []

    def evaluate(self, envelope: Envelope, workspace: Path) -> EvaluationReport:
        report = EvaluationReport(subject=envelope.agent)
        for gate in self.gates:
            report.checks.append(gate.run(envelope, workspace))
        # Claims with no evidence at all can never be counted as covered.
        if envelope.claims and not envelope.evidence:
            report.unbacked_claims = list(envelope.claims)
        return report.finalize()
