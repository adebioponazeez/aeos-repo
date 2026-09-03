"""v23 Evals: runs are graded, not watched.

The industry's gap we named in BENCHMARK-2026: offline eval suites.
An eval is a case, a deterministic judge, and a weight — no model
grades itself. Suites run any executor; the built-in self-eval suite
points the mirror at AEOS's own laws. A case that raises is a FAILED
case, never a crashed suite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalCase:
    name: str
    judge: object            # judge(output) -> float in [0, 1]
    inputs: dict = field(default_factory=dict)
    weight: float = 1.0


@dataclass
class EvalResult:
    name: str
    score: float
    weight: float
    detail: str = ""


@dataclass
class EvalReport:
    results: list = field(default_factory=list)
    threshold: float = 1.0

    @property
    def score(self) -> float:
        tw = sum(r.weight for r in self.results) or 1.0
        return sum(r.score * r.weight for r in self.results) / tw

    @property
    def passed(self) -> bool:
        return bool(self.results) and self.score >= self.threshold

    def render(self) -> str:
        head = (f"EVAL — {self.score:.2f}/{self.threshold:.2f} "
                f"({'PASS' if self.passed else 'FAIL'})")
        rows = [f"  {r.name:<32} {r.score:>4.2f}  {r.detail[:44]}"
                for r in self.results]
        return "\n".join([head] + rows)


class EvalSuite:
    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.cases: list = []

    def add(self, case: EvalCase) -> "EvalSuite":
        self.cases.append(case)
        return self

    def run(self, executor) -> EvalReport:
        """executor(inputs: dict) -> output; judged deterministically."""
        rep = EvalReport(threshold=self.threshold)
        for case in self.cases:
            try:
                output = executor(dict(case.inputs))
                score = float(case.judge(output))
                score = max(0.0, min(1.0, score))
                detail = ""
            except Exception as exc:               # a raised case FAILS
                score, detail = 0.0, f"raised: {type(exc).__name__}"
            rep.results.append(EvalResult(case.name, score,
                                          case.weight, detail))
        return rep


# ------------------------------------------------------- the self-eval mirror

def run_self_eval(workspace: Path) -> EvalReport:
    """AEOS grades its own laws: each case exercises a real mechanism
    on real fixtures. Judges are plain predicates — no model, no
    charm."""
    from .contracts import MemoryClass
    from .companions import verify_against_disk
    from .dividend import TokenLedger, stable_prefix
    from .mcp_client import MCPTool, import_tools
    from .memory import MemoryRecord, MemoryStore
    from .recall import RecallIndex
    from .standards import STANDARDS_TEMPLATE, check_plan

    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "STANDARDS.md").write_text(STANDARDS_TEMPLATE, encoding="utf-8")

    store = MemoryStore(ws / ".aeos" / "eval-memory.jsonl")
    store.write(MemoryRecord(key="semantic::deploy",
                             mclass=MemoryClass.SEMANTIC,
                             value="deploy: tests-first then gate-check",
                             source="distiller",
                             evidence=["distilled from 4 episodes"]))
    idx = RecallIndex(str(ws / ".aeos" / "eval-recall.sqlite"), store)
    idx.build()

    ledger = TokenLedger()
    ledger.record("deploy", 1, baseline_tokens=2000, actual_tokens=2000)
    for run in (2, 3, 4):
        ledger.record("deploy", run, baseline_tokens=2000,
                      actual_tokens=100, memory_overhead_tokens=50)

    def fx(inputs: dict) -> dict:
        tag = inputs["fixture"]
        if tag == "standards":
            return check_plan(inputs["plan"], ws / "STANDARDS.md")
        if tag == "recall":
            return idx.recall(inputs["query"], budget=inputs["budget"])
        if tag == "ledger":
            return ledger.marginal("deploy")
        if tag == "import":
            return import_tools([MCPTool(name="x")])["x"]
        if tag == "phantom":
            return verify_against_disk(
                {"artifacts": ["never-written.py"]}, ws)
        if tag == "prefix":
            stable = {"law": "evidence or silence"}
            a = stable_prefix(stable, {"q": "one"})
            b = stable_prefix(stable, {"q": "two"})
            return {"same": a.prefix == b.prefix,
                    "frac": a.cache_eligible_fraction}
        raise ValueError(f"unknown fixture {tag}")

    suite = EvalSuite()
    suite.add(EvalCase(
        "standards: uncited plan refused",
        inputs={"fixture": "standards", "plan": "just ship it"},
        judge=lambda out: 1.0 if out["gated"] and not out["ok"] else 0.0))
    suite.add(EvalCase(
        "recall: budget is law",
        inputs={"fixture": "recall", "query": "deploy", "budget": 40},
        judge=lambda out: 1.0 if out.recall_tokens <= 40 else 0.0))
    suite.add(EvalCase(
        "dividend: marginal goes negative",
        inputs={"fixture": "ledger"},
        judge=lambda out: 1.0 if out["negative_marginal"] else 0.0))
    suite.add(EvalCase(
        "mcp: imports enter untrusted",
        inputs={"fixture": "import"},
        judge=lambda out: 1.0 if out["trust"] == "UNTRUSTED" else 0.0))
    suite.add(EvalCase(
        "emissary: phantoms are caught",
        inputs={"fixture": "phantom"},
        judge=lambda out: 1.0 if out[1] else 0.0))
    suite.add(EvalCase(
        "prefix: byte-stable across queries",
        inputs={"fixture": "prefix"},
        judge=lambda out: 1.0 if out["same"] and out["frac"] > 0.5
        else 0.0))
    rep = suite.run(fx)
    idx.close()
    return rep
