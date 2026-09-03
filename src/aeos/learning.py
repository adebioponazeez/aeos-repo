"""Learning OS: ACT -> OBSERVE -> EXTRACT -> VALIDATE -> UPDATE -> REUSE.

The hard gate: failed behavior is NEVER canonicalized. Successful
behavior becomes PROCEDURAL memory / a skill only with attached
evidence (spec §22)."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import MemoryClass, SkillSpec, TaskState
from .memory import MemoryRecord, MemoryStore
from .skills import SkillsRegistry


@dataclass
class Lesson:
    task: str
    outcome: str                 # success | failure
    pattern: str
    validated: bool = False


class LearningLoop:
    """ACT -> OBSERVE -> EXTRACT -> VALIDATE -> UPDATE -> REUSE."""

    def __init__(self, memory: MemoryStore, skills: SkillsRegistry) -> None:
        self.memory = memory
        self.skills = skills
        self.lessons: list[Lesson] = []

    def observe(self, task_name: str, state: TaskState, pattern: str) -> Lesson:
        lesson = Lesson(task=task_name,
                        outcome="success" if state is TaskState.SUCCEEDED else "failure",
                        pattern=pattern)
        self.lessons.append(lesson)
        self.memory.write(MemoryRecord(
            key=f"lesson::{task_name}::{len(self.lessons)}",
            value=pattern, mclass=MemoryClass.EPISODIC,
            source="learning-loop", confidence=0.6))
        return lesson

    def validate_and_promote(self, lesson: Lesson, evidence: list[str]) -> bool:
        """No evidence, no canonicalization. Ever."""
        if lesson.outcome != "success" or not evidence:
            lesson.validated = False
            return False
        lesson.validated = True
        self.memory.write(MemoryRecord(
            key=f"proven::{lesson.task}", value=lesson.pattern,
            mclass=MemoryClass.PROCEDURAL, source="learning-loop",
            confidence=0.9, evidence=evidence))
        return True

    def promote_to_skill(self, lesson: Lesson, name: str,
                         evidence: list[str]) -> SkillSpec:
        if not lesson.validated:
            raise ValueError("cannot promote unvalidated lesson — "
                             "that is how failure becomes folklore")
        spec = SkillSpec(
            name=name, purpose=lesson.pattern,
            trigger=f"recurring: {lesson.task}",
            procedure=[f"repeat what succeeded in {lesson.task}"],
            success_evidence=evidence, origin=f"promoted:{lesson.task}",
            version="0.1.0", win_rate=1.0, usage_count=1)
        self.skills.register(spec)
        return spec
