"""Entropy control + Learning OS + Capability Discovery.

Three small engines, one loop (spec §§ 22–24):

  ENTROPY      detect drift, staleness, duplication -> IGNORE/MONITOR/
               REPAIR/REMOVE/ESCALATE
  LEARNING     ACT -> OBSERVE -> EXTRACT -> VALIDATE -> UPDATE -> REUSE,
               with a hard gate: failed behavior is never canonicalized
  DISCOVERY    measure repetition across work, propose promotion up the
               ladder TASK->SKILL->AGENT->WORKFLOW->SERVICE->CAPABILITY
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .contracts import MemoryClass, SkillSpec, TaskState, Verdict
from .memory import MemoryRecord, MemoryStore
from .skills import SkillsRegistry


# ------------------------------------------------------------- entropy

class EntropyAction(str, Enum):
    IGNORE = "IGNORE"
    MONITOR = "MONITOR"
    REPAIR = "REPAIR"
    REMOVE = "REMOVE"
    ESCALATE = "ESCALATE"


@dataclass
class EntropyFinding:
    kind: str
    detail: str
    action: EntropyAction


class EntropyScanner:
    """Continuously detect the eleven entropies of spec §23."""

    def __init__(self, skills: SkillsRegistry, memory: MemoryStore,
                 workspace: Path) -> None:
        self.skills = skills
        self.memory = memory
        self.workspace = workspace

    def scan(self) -> list[EntropyFinding]:
        findings: list[EntropyFinding] = []
        findings.extend(self._stale_docs())
        findings.extend(self._duplicate_skills())
        findings.extend(self._memory_pollution())
        findings.extend(self._dead_code())
        findings.extend(self._weak_tests())
        return findings

    # ---- v1.1 extensions: the entropies the first pass deferred ----

    def _weak_tests(self) -> list[EntropyFinding]:
        """Test files with zero assertions assert nothing."""
        out: list[EntropyFinding] = []
        for p in self.workspace.rglob("test_*.py"):
            if ".aeos" in p.parts:
                continue
            src = p.read_text(encoding="utf-8", errors="ignore")
            if src.strip() and "assert" not in src and "pytest.raises" not in src:
                out.append(EntropyFinding(
                    "weak_tests",
                    f"{p.name} contains no assertions — it verifies nothing",
                    EntropyAction.REPAIR))
        return out

    def unused_tools(self, declared: list[str],
                     used: list[str]) -> list[EntropyFinding]:
        """Tools in the registry no agent references are attack surface."""
        used_set = {u.lower() for u in used}
        return [EntropyFinding(
                    "unused_tools", f"tool '{t}' declared but never referenced",
                    EntropyAction.REMOVE)
                for t in declared if t.lower() not in used_set]

    def architectural_drift(self, documented: list[str],
                            actual: list[str]) -> list[EntropyFinding]:
        """Docs naming modules that don't exist (and vice versa)."""
        out: list[EntropyFinding] = []
        for m in documented:
            if m not in actual:
                out.append(EntropyFinding(
                    "architectural_drift",
                    f"docs reference module '{m}' that does not exist",
                    EntropyAction.REPAIR))
        for m in actual:
            if m not in documented:
                out.append(EntropyFinding(
                    "architectural_drift",
                    f"module '{m}' exists but no doc maps it",
                    EntropyAction.MONITOR))
        return out

    def _stale_docs(self) -> list[EntropyFinding]:
        out: list[EntropyFinding] = []
        docs = list(self.workspace.rglob("*.md"))
        code_mtime = max((p.stat().st_mtime for p in self.workspace.rglob("*.py")),
                         default=0)
        for d in docs:
            if d.stat().st_mtime < code_mtime - 86_400:
                out.append(EntropyFinding(
                    "stale_documentation",
                    f"{d.relative_to(self.workspace)} predates newest code by >1 day",
                    EntropyAction.REPAIR))
        return out

    def _duplicate_skills(self) -> list[EntropyFinding]:
        return [EntropyFinding("duplicate_skills", f"{a} ~= {b} (sim {s})",
                               EntropyAction.MONITOR)
                for a, b, s in self.skills.duplicates()]

    def _memory_pollution(self) -> list[EntropyFinding]:
        low = [r for r in self.memory.records.values()
               if r.mclass in MemoryStore.CANONICAL and r.confidence < 0.5]
        return [EntropyFinding(
            "memory_pollution",
            f"{len(low)} canonical record(s) below 0.5 confidence — revalidate or demote",
            EntropyAction.REPAIR if low else EntropyAction.IGNORE)
        ] if low else []

    def _dead_code(self) -> list[EntropyFinding]:
        py = [p for p in self.workspace.rglob("*.py") if ".aeos" not in p.parts]
        findings = []
        for p in py:
            src = p.read_text(encoding="utf-8", errors="ignore")
            if src.strip() and len(src) < 40 and "def " not in src:
                findings.append(EntropyFinding(
                    "dead_code", f"{p.name} is an empty shell", EntropyAction.REMOVE))
        return findings
