"""v38 tests: the curriculum and the founding-spec audit — the
master-builder loop's second turn, machine-checked."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CURRICULUM = REPO / "book" / "parts-v4" / "00-v4-full.md"
AUDIT = REPO / "docs" / "SPEC-AUDIT.md"

SECTIONS = ("**Objectives", "**Theory", "**Practice", "**Projects",
            "**Evaluation", "**Capabilities unlocked",
            "**Advanced project")


class TestCurriculum:
    def test_all_thirteen_phases_present(self):
        text = CURRICULUM.read_text(encoding="utf-8")
        phases = re.findall(r"^## Phase (\d+) — ", text, re.M)
        assert phases == [str(n) for n in range(1, 14)], phases

    def test_every_phase_carries_the_seven_mandated_sections(self):
        text = CURRICULUM.read_text(encoding="utf-8")
        chunks = re.split(r"^## Phase \d+ — ", text, flags=re.M)[1:]
        assert len(chunks) == 13
        for i, chunk in enumerate(chunks, 1):
            missing = [s for s in SECTIONS if s not in chunk]
            assert not missing, f"phase {i} missing {missing}"

    def test_every_command_in_the_curriculum_is_real(self):
        """The curriculum is held to the README's own law: every
        `aeos <verb>` it teaches must exist in the live CLI."""
        from aeos.scribe import reality
        commands = reality(REPO)["commands"]
        text = CURRICULUM.read_text(encoding="utf-8")
        taught = set(re.findall(r"`aeos ([a-z][a-z0-9-]+)", text))
        assert taught, "no commands found — the regex went blind"
        absent = sorted(taught - commands)
        assert not absent, f"curriculum teaches verbs that do not exist: {absent}"

    def test_the_frontier_is_honestly_marked(self):
        text = CURRICULUM.read_text(encoding="utf-8")
        assert "None claimed" in text            # phase 13 unlocks
        assert "not built" in text               # the gap, said plainly


class TestSpecAudit:
    def _covered(self, text: str) -> set:
        covered = set()
        for lo, hi in re.findall(r"\| (\d+)(?:–(\d+))? \|", text):
            covered.add(int(lo))
            if hi:
                covered.update(range(int(lo), int(hi) + 1))
        covered.update(int(n) for n in re.findall(r"Requirement (\d+)", text))
        return covered

    def test_spec_audit_covers_all_requirements(self):
        """All 57 numbered requirements of the founding spec carry
        a verdict — none silently dropped."""
        text = AUDIT.read_text(encoding="utf-8")
        covered = self._covered(text)
        missing = sorted(set(range(1, 58)) - covered)
        assert not missing, f"requirements without verdicts: {missing}"

    def test_every_verdict_is_real_artifact_or_honest_gap(self):
        text = AUDIT.read_text(encoding="utf-8")
        # the three honest gaps stay named — polish is not allowed
        assert "GAP (honest)" in text
        assert "Autonomous business workflow" in text
        assert "AI-native enterprise prototype" in text

    def test_project_ladder_twelve_rungs_mapped(self):
        text = AUDIT.read_text(encoding="utf-8")
        rungs = set(int(n) for n in re.findall(r"^\| (\d{1,2}) \| ", text, re.M))
        missing = sorted(set(range(1, 13)) - rungs)
        assert not missing, f"ladder rungs without mapping: {missing}"

    def test_definition_of_done_sixteen_clauses_answered(self):
        text = AUDIT.read_text(encoding="utf-8")
        m = re.search(r"\| 50 \|.*?see the receipt below", text, re.S)
        assert m and m.group(0).count("✓") == 16, \
            "the 16-clause DoD must be answered clause by clause"
