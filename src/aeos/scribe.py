"""v35 The Scribe: documentation that cannot drift.

Every version bumps counts in six documents by hand; hands drift.
The scribe extracts VERIFIABLE claims from the living docs (the
README is the storefront contract) and checks each against live
reality: test counts, module counts, ADR counts, the version
headline, and every `aeos <command>` it mentions. Historical records
(CHANGELOG entries, ADRs, the book — counts at tag time) are exempt
by design: history is not a claim about the present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Claim:
    file: str
    line: int
    kind: str
    claimed: str
    actual: str
    ok: bool


@dataclass
class ScribeReport:
    claims: list = field(default_factory=list)

    @property
    def drift(self) -> list:
        return [c for c in self.claims if not c.ok]

    @property
    def passed(self) -> bool:
        return bool(self.claims) and not self.drift

    def render(self) -> str:
        head = (f"SCRIBE — {len(self.claims)} claim(s) checked, "
                f"{len(self.drift)} drift(s) "
                f"({'TRUTHFUL' if self.passed else 'DRIFTED'})")
        lines = [head]
        for c in self.claims:
            mark = "." if c.ok else "X"
            lines.append(f"  [{mark}] {c.file}:{c.line:<4} {c.kind:<12} "
                         f"claimed {c.claimed} | actual {c.actual}")
        return "\n".join(lines)


def reality(repo: Path) -> dict:
    """Live counts — never cached, never believed; tolerant of partial
    checkouts (missing pieces count as zero, not crashes)."""
    repo = Path(repo)
    import aeos
    pkg = Path(aeos.__file__).resolve().parent
    tests_dir = repo / "tests"
    tests = sum(len(re.findall(r"\bdef test_", t.read_text(
        encoding="utf-8", errors="replace")))
        for t in (tests_dir.glob("test_*.py") if tests_dir.exists()
                  else ()))
    cli = repo / "src" / "aeos" / "cli.py"
    commands = set(re.findall(
        r'add_parser\(\s*"([^"]+)"',
        cli.read_text(encoding="utf-8"))) if cli.exists() else set()
    adrs_dir = repo / "docs" / "adr"
    return {
        "version": aeos.__version__,
        "tests": tests,
        "modules": len(list(pkg.glob("*.py"))),
        "adrs": len(list(adrs_dir.glob("ADR-*.md"))) if adrs_dir.exists()
        else 0,
        "commands": commands,
    }


def _claims_in_line(line: str) -> list:
    out = []
    for m in re.finditer(r"(\d+)\s*\+?\s*(?:tests|proofs)\b", line):
        out.append(("tests", m.group(1)))
    for m in re.finditer(r"(\d+)\s*modules\b", line):
        out.append(("modules", m.group(1)))
    for m in re.finditer(r"(\d+)\s*ADRs\b", line):
        out.append(("adrs", m.group(1)))
    return out


def audit(repo: Path, docs: tuple = ("README.md",), *,
          reality_from: Path | None = None) -> ScribeReport:
    """Audit docs under `repo` against reality measured from
    `reality_from` (default: repo itself)."""
    repo = Path(repo)
    real = reality(reality_from or repo)
    rep = ScribeReport()

    for doc in docs:
        path = repo / doc
        if not path.exists():
            rep.claims.append(Claim(doc, 0, "exists", "file", "missing",
                                    False))
            continue
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("|") and re.search(
                    r"\bv\d+\.\d+\b", line):
                continue          # version-table rows are history
            for kind, claimed in _claims_in_line(line):
                actual = str(real[kind])
                # "N+" / "N or more" forms are honest lower bounds
                ok = (int(claimed) == int(actual)) or (
                    f"{claimed}+" in line and int(claimed) <= int(actual))
                rep.claims.append(Claim(doc, lineno, kind, claimed,
                                        actual, ok))
            m = re.search(r"\*\*Version (\d+\.\d+\.\d+)", line)
            if m:
                rep.claims.append(Claim(
                    doc, lineno, "version", m.group(1), real["version"],
                    m.group(1) == real["version"]))
            for cm in re.finditer(r"`aeos ([a-z][a-z0-9-]+)`", line):
                cmd = cm.group(1)
                rep.claims.append(Claim(
                    doc, lineno, "command", cmd,
                    "in CLI" if cmd in real["commands"] else "absent",
                    cmd in real["commands"]))
    return rep
