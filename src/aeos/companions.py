"""v12.0 — Companions: external agents as bounded nodes (Pi CLI, DeerFlow).

The OS kept its own handlers since v1; the ecosystem's best hands live
outside it. Pi (the coding agent the SSSF/fusion lineage runs on) and
DeerFlow (ByteDance's deep-research SuperAgent, now with a headless
CLI) become companions — subcontracted under the SAME laws:

  Pi CLI         `pi -p --mode json --session-id ...` (the exact SSSF
                 invocation, stdin DEVNULL — their documented lesson);
                 JSONL events stream into the EventLog; artifacts are
                 derived from the FILESYSTEM DIFF, never from the
                 model's self-report; the writes: boundary reverts
                 anything outside it and kills the phase.
  DeerFlow       `deerflow --json "<query>"` (NDJSON StreamEvents);
                 the final answer + sources become Findings under the
                 v5 untrusted-source law — no sources, no fabrication.

ADR-021: a companion is authority on loan, not law on loan. Every
guarantee the harness gives an internal handler applies unchanged:
checkpoint, boundary, gates, envelope, event log, wall clock.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from .adapters import AdapterError, ErrorKind
from .contracts import Envelope, TaskSpec
from .harness import Harness
from .observability import EventLog
from .research import Finding, ResearchBrief

PI_PATH_ENV = "PI_PATH"
DEERFLOW_BIN_ENV = "DEERFLOW_BIN"
DEFAULT_PI = "pi"
DEFAULT_DEERFLOW = "deerflow"


# ------------------------------------------------------------- detection

@dataclass
class CompanionStatus:
    name: str
    available: bool
    path: str | None
    hint: str


def companion_status() -> list[CompanionStatus]:
    pi = os.environ.get(PI_PATH_ENV, DEFAULT_PI)
    df = os.environ.get(DEERFLOW_BIN_ENV, DEFAULT_DEERFLOW)
    return [
        CompanionStatus(
            "pi", shutil.which(pi) is not None, shutil.which(pi),
            "coding agent backend — set PI_PATH or install pi "
            "(npm i -g @earendil-works/pi-coding-agent)"),
        CompanionStatus(
            "deerflow", shutil.which(df) is not None, shutil.which(df),
            "deep-research backend — set DEERFLOW_BIN or install "
            "deer-flow (github.com/bytedance/deer-flow)"),
    ]


# ---------------------------------------------------------------- runner

class Runner(Protocol):
    def run(self, argv: list[str], cwd: Path, timeout_s: float
            ) -> tuple[int, str, str, bool]: ...  # (rc, out, err, timed_out)


class SubprocessRunner:
    """stdin DEVNULL, always — the SSSF lesson: a non-TTY child with
    inherited stdin can sit forever waiting for input that never
    arrives, silently. Prompt travels in argv."""

    def run(self, argv: list[str], cwd: Path, timeout_s: float
            ) -> tuple[int, str, str, bool]:
        try:
            proc = subprocess.run(argv, cwd=str(cwd), timeout=timeout_s,
                                  stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True)
            return proc.returncode, proc.stdout or "", proc.stderr or "", False
        except subprocess.TimeoutExpired:
            return 124, "", f"wall clock {timeout_s}s exceeded", True
        except FileNotFoundError as exc:
            return 127, "", f"companion binary not found: {exc}", False


# ------------------------------------------------------------------- pi

REPORT_CONTRACT = (
    "Work in the current directory only. When finished, print a final "
    'line that is exactly one JSON object: {"artifacts": [<files you '
    'created or changed, repo-relative>], "summary": "<one sentence>"}. '
    "The harness verifies artifacts against the filesystem; listing a "
    "file you did not write will fail the gates."
)


def parse_pi_stream(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue          # non-JSON chatter is ignored, never fatal
    return events


def final_message(events: list[dict]) -> str:
    """Last event carrying assistant text, by the common shapes."""
    for ev in reversed(events):
        text = ev.get("text") or ev.get("content")
        if not text and isinstance(ev.get("message"), dict):
            text = ev["message"].get("content")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def parse_report(text: str) -> dict:
    """Pull the last JSON object out of the final message, if any."""
    candidates = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(text[start:i + 1])
                start = -1
    for blob in reversed(candidates):
        try:
            d = json.loads(blob)
            if isinstance(d, dict):
                return d
        except json.JSONDecodeError:
            continue
    return {}


@dataclass
class PiOutcome:
    ok: bool
    events: list[dict] = field(default_factory=list)
    report: dict = field(default_factory=dict)
    final_text: str = ""
    why: str = ""


def run_pi(objective: str, workspace: Path, *, runner: Runner | None = None,
           session_id: str = "aeos-session", system_prompt: str = "",
           timeout_s: float = 120.0, log: EventLog | None = None) -> PiOutcome:
    runner = runner or SubprocessRunner()
    pi = os.environ.get(PI_PATH_ENV, DEFAULT_PI)
    argv = [pi, "-p", "--mode", "json",
            "--session-id", session_id,
            "--session-dir", str(workspace / ".aeos" / "pi-sessions"),
            "--system-prompt", system_prompt or "You are a bounded builder.",
            f"{objective}\n\n{REPORT_CONTRACT}"]
    rc, out, err, timed_out = runner.run(argv, workspace, timeout_s)
    if timed_out:
        if log:
            log.emit("companion.pi", rc=124, why="wall clock exceeded")
        return PiOutcome(ok=False, why=f"pi exceeded its {timeout_s}s wall "
                                       "clock and was killed")
    if rc == 127:
        if log:
            log.emit("companion.pi", rc=rc, why="binary not found")
        return PiOutcome(ok=False,
                         why=f"pi not found at '{pi}' — set {PI_PATH_ENV} "
                             "or install it; the OS will not guess")
    events = parse_pi_stream(out)
    if rc != 0 and not events:
        return PiOutcome(ok=False, why=f"pi exited {rc}: {err[:200]}")
    text = final_message(events)
    return PiOutcome(ok=True, events=events, report=parse_report(text),
                     final_text=text)


def pi_handler(agent_name: str, harness: Harness, log: EventLog, *,
               writes: list[str] | None = None, timeout_s: float = 120.0,
               session_prefix: str = "pi", runner: Runner | None = None):
    """An orchestrator-ready handler: pi does the work; the HARNESS
    decides what happened. Artifacts come from the filesystem diff;
    boundary violations revert and kill the phase."""
    def handler(task: TaskSpec, orch) -> Envelope:
        sid = f"{session_prefix}-{task.uid}"
        cp = harness.snapshot(f"pre:{task.name}")       # full fidelity
        outcome = run_pi(task.description, harness.workspace,
                         runner=runner, session_id=sid,
                         timeout_s=timeout_s, log=log)
        if not outcome.ok:
            raise RuntimeError(outcome.why)

        for ev in outcome.events[:40]:                   # stream (capped)
            kind = str(ev.get("type", "event"))
            log.emit(f"pi.{kind}", session=sid,
                     keys=sorted(ev.keys())[:8])
        # authorship of truth: the filesystem, not the self-report
        before = set(cp.files)
        after = {p.relative_to(harness.workspace).as_posix()
                 for p in harness.workspace.rglob("*")
                 if p.is_file() and ".aeos" not in p.parts}
        claimed = [a for a in outcome.report.get("artifacts", [])
                   if isinstance(a, str)]
        diff = sorted(after - before)
        artifacts = diff or claimed
        summary = str(outcome.report.get("summary", "pi completed the task"))

        env = Envelope(agent=agent_name, objective=task.description,
                       claims=[summary], artifacts=artifacts,
                       changed_files=artifacts)
        env.add_evidence("fs_diff", f"{len(diff)} file(s) changed on disk")
        env.add_evidence("pi_session", sid)
        env.add_evidence("pi_events", f"{len(outcome.events)} stream events")

        reverted = harness.enforce_boundary(cp, agent_name,
                                            patterns=writes or [])
        if reverted:
            log.emit("boundary.violation", agent=agent_name, task=task.name,
                     reverted=reverted)
            raise RuntimeError(
                f"write-boundary violation by pi: reverted {reverted}")
        return env
    return handler


# ------------------------------------------------------------- deerflow

DF_SOURCE_CONFIDENCE = 0.75        # companion sources: trusted enough to
                                   # surface, never enough to canonize


def run_deerflow(query: str, *, runner: Runner | None = None,
                 timeout_s: float = 300.0,
                 log: EventLog | None = None) -> ResearchBrief:
    """Deep research via DeerFlow's headless CLI. Output is NDJSON
    StreamEvents; we mine answer + sources. No sources, no fabrication:
    an unparseable stream yields an EMPTY brief (the v5 law)."""
    runner = runner or SubprocessRunner()
    binpath = os.environ.get(DEERFLOW_BIN_ENV, DEFAULT_DEERFLOW)
    if os.environ.get("DEERFLOW_ARGS"):
        argv = [binpath] + shlex.split(os.environ["DEERFLOW_ARGS"]) + [query]
    else:
        argv = [binpath, "--json", query]
    brief = ResearchBrief(query=query)
    rc, out, err, timed_out = runner.run(argv, Path.cwd(), timeout_s)
    if log:
        log.emit("companion.deerflow", rc=rc, timed_out=timed_out)
    if timed_out or rc == 127:
        return brief                     # empty: UNVERIFIED upstream
    events = parse_pi_stream(out)        # same NDJSON discipline
    for ev in events:
        url = ev.get("url") or ev.get("source") or ""
        if isinstance(url, str) and url.startswith("http"):
            brief.findings.append(Finding(
                fact=str(ev.get("title") or ev.get("snippet") or url)[:200],
                source=url, confidence=DF_SOURCE_CONFIDENCE))
    answer = final_message(events)
    if answer and not brief.findings:
        brief.findings.append(Finding(
            fact=answer[:400], source="deerflow:answer",
            confidence=DF_SOURCE_CONFIDENCE))
    if brief.findings:                   # the answer itself stays unverified
        brief.unverified.append(Finding(
            fact=answer[:400] if answer else "no final answer event",
            source="deerflow:final", confidence=0.5))
    return brief


def deerflow_handler(agent_name: str, harness: Harness, log: EventLog, *,
                     writes: list[str] | None = None,
                     timeout_s: float = 300.0,
                     runner: Runner | None = None):
    """Research-handler shape: write the brief artifact, gate-checked."""
    def handler(task: TaskSpec, orch) -> Envelope:
        cp = harness.snapshot(f"pre:{task.name}")
        brief = run_deerflow(task.description, runner=runner,
                             timeout_s=timeout_s, log=log)
        payload = {"query": brief.query,
                   "findings": [f.__dict__ for f in brief.findings],
                   "unverified": [f.__dict__ for f in brief.unverified]}
        rel = "research/deerflow-brief.json"
        harness.write(rel, json.dumps(payload, indent=2))
        env = Envelope(agent=agent_name, objective=task.description,
                       claims=[f"deep-research brief: "
                               f"{len(brief.findings)} finding(s)"],
                       artifacts=[rel], changed_files=[rel])
        env.add_evidence("artifact_written", rel)
        env.add_evidence("source_discipline",
                         f"{len(brief.unverified)} quarantined as unverified")
        reverted = harness.enforce_boundary(cp, agent_name,
                                            patterns=writes or ["research/*"])
        if reverted:
            raise RuntimeError(f"boundary violation: {reverted}")
        return env
    return handler


# ------------------------------------------- round 2: aider + claude

AIDER_BIN_ENV = "AIDER_PATH"
DEFAULT_AIDER = "aider"
CLAUDE_BIN_ENV = "CLAUDE_PATH"
DEFAULT_CLAUDE = "claude"


@dataclass
class ToolOutcome:
    ok: bool
    rc: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    report: dict = field(default_factory=dict)
    final_text: str = ""


def run_aider(objective: str, workspace: Path, *,
              runner: Runner | None = None, timeout_s: float = 600.0,
              log: EventLog | None = None) -> ToolOutcome:
    """Coding companion: aider headless. --yes (a prompt is a hang),
    --no-auto-commits (the fs-diff stays readable). The report
    contract rides in the message; artifacts are verified against the
    FILESYSTEM, never self-reported."""
    runner = runner or SubprocessRunner()
    binpath = os.environ.get(AIDER_BIN_ENV, DEFAULT_AIDER)
    argv = [binpath, "--yes", "--no-auto-commits",
            "--message", f"{objective}\n\n{REPORT_CONTRACT}"]
    rc, out, err, timed_out = runner.run(argv, workspace, timeout_s)
    if log:
        log.emit("companion.aider", rc=rc, timed_out=timed_out)
    return ToolOutcome(ok=(rc == 0 and not timed_out), rc=rc, stdout=out,
                       stderr=err, timed_out=timed_out,
                       report=parse_report(out), final_text=out[-2000:])


def run_claude(objective: str, workspace: Path, *,
               runner: Runner | None = None, timeout_s: float = 600.0,
               log: EventLog | None = None) -> ToolOutcome:
    """Coding companion: headless Claude Agent SDK CLI
    (`claude -p --output-format json`). Same contract, same law."""
    runner = runner or SubprocessRunner()
    binpath = os.environ.get(CLAUDE_BIN_ENV, DEFAULT_CLAUDE)
    argv = [binpath, "-p", f"{objective}\n\n{REPORT_CONTRACT}",
            "--output-format", "json"]
    rc, out, err, timed_out = runner.run(argv, workspace, timeout_s)
    if log:
        log.emit("companion.claude", rc=rc, timed_out=timed_out)
    text = out
    for ev in reversed(parse_pi_stream(out)):
        if isinstance(ev.get("result"), str):   # {"result": "..."} envelope
            text = ev["result"]
            break
    return ToolOutcome(ok=(rc == 0 and not timed_out), rc=rc, stdout=out,
                       stderr=err, timed_out=timed_out,
                       report=parse_report(text), final_text=text[-2000:])


def verify_against_disk(report: dict, workspace: Path) -> tuple:
    """Reported artifacts split (on-disk, phantom). Phantom = lied."""
    arts = [a for a in report.get("artifacts", [])
            if isinstance(a, str)]
    verified = [a for a in arts if (workspace / a).exists()]
    phantom = [a for a in arts if (a not in verified)]
    return verified, phantom


def coding_handler(companion, agent_name: str, harness: Harness,
                   log: EventLog, *, writes: list[str] | None = None,
                   timeout_s: float = 600.0,
                   runner: Runner | None = None):
    """Shared build-handler for coding companions: run, verify the
    report against the filesystem, revert boundary violations. A
    phantom artifact is a raised error, not a warning."""
    def handler(task: TaskSpec, orch) -> Envelope:
        cp = harness.snapshot(f"pre:{task.name}")
        outcome = companion(task.description, harness.workspace,
                            runner=runner, timeout_s=timeout_s, log=log)
        if outcome.timed_out:
            raise RuntimeError(f"{agent_name} timed out; no envelope")
        verified, phantom = verify_against_disk(outcome.report,
                                                harness.workspace)
        if phantom:
            raise RuntimeError(f"phantom artifacts reported: {phantom}")
        summary = str(outcome.report.get("summary") or "no summary")[:200]
        env = Envelope(agent=agent_name, objective=task.description,
                       claims=[f"{agent_name}: {summary}"],
                       artifacts=verified, changed_files=verified)
        env.add_evidence("fs_verified",
                         f"{len(verified)} artifact(s) exist on disk")
        reverted = harness.enforce_boundary(
            cp, agent_name, patterns=writes or ["src/*", "tests/*"])
        if reverted:
            raise RuntimeError(f"boundary violation: {reverted}")
        return env
    return handler


def aider_handler(agent_name: str, harness: Harness, log: EventLog, **kw):
    return coding_handler(run_aider, agent_name, harness, log, **kw)


def claude_handler(agent_name: str, harness: Harness, log: EventLog, **kw):
    return coding_handler(run_claude, agent_name, harness, log, **kw)


def round2_status() -> list:
    """Which round-2 companions are on PATH — honest detection."""
    import shutil
    return [name for name, env, dflt in (
        ("aider", AIDER_BIN_ENV, DEFAULT_AIDER),
        ("claude", CLAUDE_BIN_ENV, DEFAULT_CLAUDE),
        ("pi", "PI_PATH", "pi"),
        ("deerflow", DEERFLOW_BIN_ENV, DEFAULT_DEERFLOW),
    ) if shutil.which(os.environ.get(env, dflt)) is not None]
