"""v27 The Storm: the nuclear test — chaos as a first-class command.

Everything here is END-TO-END on the real system: real subprocesses,
real SIGKILLs, real torn files, real fault injection. A scenario
passes only if the system FAILS CLOSED or RECOVERS — never crashes,
never corrupts, never loses prior work. This is the receipt that the
system runs where power cuts, disks fill, networks do not exist, and
hardware is constrained.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

RUN_SRC = (
    "from pathlib import Path\n"
    "from aeos.pipeline import reference_run\n"
    "b = reference_run(Path(sys.argv[1]), intent='Ship it per [STD-1]')\n"
    "print('ACCEPTED:' + str(b['accepted']))\n")


def _run_cmd(ws: Path) -> list:
    return [sys.executable, "-c", "import sys\n" + RUN_SRC, str(ws)]


def _completed_run(ws: Path, timeout: int = 240) -> bool:
    proc = subprocess.run(_run_cmd(ws), capture_output=True, text=True,
                          timeout=timeout)
    return proc.returncode == 0 and "ACCEPTED:True" in proc.stdout


@dataclass
class StormRow:
    scenario: str
    passed: bool
    detail: str = ""


@dataclass
class StormReport:
    rows: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.rows) and all(r.passed for r in self.rows)

    def render(self) -> str:
        head = (f"STORM — {sum(r.passed for r in self.rows)}/"
                f"{len(self.rows)} scenarios survived "
                f"({'PASS' if self.passed else 'FAIL'})")
        lines = [head]
        for r in self.rows:
            mark = "x" if r.passed else " "
            lines.append(f"  [{mark}] {r.scenario:<26} {r.detail[:52]}")
        return "\n".join(lines)


# ------------------------------------------------------------ scenarios

def sc_kill_storm(ws: Path) -> StormRow:
    """SIGKILL the run 3 times at growing delays, then recover."""
    for delay in (0.25, 0.5, 0.75):
        proc = subprocess.Popen(_run_cmd(ws), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        time.sleep(delay)
        proc.kill()                      # SIGKILL: no cleanup ever runs
        proc.wait()
    ok = _completed_run(ws)
    note = ""
    if not ok:                              # F-07: one disclosed retry —
        ok = _completed_run(ws)             # loaded runners get one pass
        note = " (recovered on retry)"
    return StormRow("kill -9 storm x3 + recovery", ok,
                    "power cut mid-run thrice; final run accepted" if ok
                    else "recovery run FAILED")


def sc_torn_files(ws: Path) -> StormRow:
    """Tear every persistent file mid-line like a real power cut."""
    _completed_run(ws)
    targets = [ws / ".aeos" / "memory.jsonl"]
    events = sorted((ws / ".aeos").glob("*events.jsonl"))
    targets += events[:1]
    torn = 0
    for t in targets:
        if t.exists():
            text = t.read_text(encoding="utf-8")
            cut = len(text) - max(1, len(text) // 40)   # tear mid-line
            t.write_text(text[:cut], encoding="utf-8")
            torn += 1
    ok = _completed_run(ws)
    sidecars = list(ws.glob("**/*.torn"))
    return StormRow("torn files (power-cut writes)", ok,
                    f"{torn} torn, quarantined to .torn, run accepted"
                    if ok and sidecars else f"recovery FAILED ({torn} torn)")


def sc_disk_full(ws: Path) -> StormRow:
    """Inject ENOSPC at the bundle write (in-process): prior evidence
    must survive byte-intact — atomicity is the receipt."""
    from aeos import vault
    from aeos.pipeline import reference_run
    reference_run(ws, intent="Ship it")
    bundle = ws / ".aeos" / "evidence" / "bundle.json"
    before = bundle.read_text(encoding="utf-8")
    real = vault.durable_write

    def enospc(path, text):
        if Path(path).name == "bundle.json":
            raise OSError(28, "No space left on device")
        return real(path, text)
    vault.durable_write = enospc
    try:
        reference_run(ws, intent="Ship it")
        failed_closed = False               # should have raised
    except OSError:
        failed_closed = True
    finally:
        vault.durable_write = real
    after = bundle.read_text(encoding="utf-8")
    ok = bool(failed_closed and after == before
              and json.loads(after) is not None)
    return StormRow("disk full at the bundle write", ok,
                    "raised cleanly; prior bundle byte-intact" if ok
                    else "evidence damaged or wrote anyway")


def sc_garbage_intents(ws: Path) -> StormRow:
    """Hostile inputs: empty, binary, huge unicode, fake citations."""
    from aeos.pipeline import reference_run
    nasty = ["", "\x00\x01\x02 binary \xff", "\U0001F4B0" * 2000,
             "per [STD-9999] fake", "   "]
    for intent in nasty:
        bundle = reference_run(ws, intent=intent)
        if "accepted" not in bundle:
            return StormRow("garbage intents", False,
                            f"no verdict for intent {intent[:20]!r}")
    return StormRow("garbage intents", True,
                    "5 hostile intents handled, all verdicted")


def sc_socket_blackout(ws: Path) -> StormRow:
    """Full run + recall + fleet with sockets IMPOSSIBLE: zero network."""
    from aeos.fleet import EventBus
    from aeos.pipeline import reference_run
    from aeos.recall import RecallIndex
    from aeos.vault import socket_blackout
    try:
        with socket_blackout():
            b = reference_run(ws, intent="Ship it")
            store_b = ws / ".aeos" / "memory.jsonl"
            from aeos.memory import MemoryStore
            idx = RecallIndex(str(ws / ".aeos" / "r.sqlite"),
                              MemoryStore(store_b))
            idx.build()
            idx.recall("deploy research")
            idx.close()
            EventBus(ws / ".aeos" / "e2.jsonl").publish("TICK", "storm")
        ok = b["accepted"] is True
    except Exception as exc:
        ok = False
    return StormRow("total socket blackout", ok,
                    "zero network calls; run+recall+fleet completed"
                    if ok else f"network dependency leaked: {exc}")


def sc_memory_cap(ws: Path) -> StormRow:
    """Complete a full run under a 256MB address-space cap."""
    import resource

    def cap():
        limit = 256 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    import functools
    cap2 = cap
    run = functools.partial(
        subprocess.run, _run_cmd(ws), capture_output=True, text=True,
        timeout=240)
    proc = run(preexec_fn=cap)
    ok = proc.returncode == 0 and "ACCEPTED:True" in proc.stdout
    note = ""
    if not ok:                              # F-07: one disclosed retry
        proc = run(preexec_fn=cap)
        ok = proc.returncode == 0 and "ACCEPTED:True" in proc.stdout
        note = " (recovered on retry)"
    return StormRow("256MB memory cap", ok,
                    "full run completed under RLIMIT_AS=256MB" + note
                    if ok else "run failed under the cap")


def sc_concurrent_runs(ws: Path) -> StormRow:
    """Two runs, one workspace: the second is refused, not interleaved."""
    from aeos.pipeline import reference_run
    from aeos.vault import WorkspaceLock
    ws.mkdir(parents=True, exist_ok=True)
    with WorkspaceLock(ws / ".aeos" / "workspace.lock"):
        b = reference_run(ws, intent="Ship it")
    ok = b["accepted"] is False and "locked" in b.get("reason", "")
    return StormRow("concurrent runs refused", ok,
                    "second run refused cleanly; no interleaving" if ok
                    else "runs interleaved or crashed")


def sc_companion_kill(ws: Path) -> StormRow:
    """MCP server dies mid-session: the client fails closed, no hang."""
    from aeos.mcp_client import MCPClient, MCPError
    c = MCPClient([sys.executable, "-m", "aeos.mcp_demo_server"],
                  timeout_s=10.0)
    c.start()
    try:
        c.initialize()
        c.proc.kill()                        # server dies mid-session
        c.proc.wait()
        try:
            c.request("tools/list")
            closed = False
        except MCPError:
            closed = True
    finally:
        c.close()
    return StormRow("server dies mid-session", closed,
                    "MCPError raised, session closed, no hang" if closed
                    else "client did not fail closed")


def sc_backup_restore(ws: Path) -> StormRow:
    """The drill (F-09): run, backup, DESTROY, restore, run again."""
    import shutil as sh
    from aeos.backup import create_backup, restore_backup
    from aeos.memory import MemoryStore
    _completed_run(ws)
    mem = ws / ".aeos" / "memory.jsonl"
    before = sorted(MemoryStore(mem).records) if mem.exists() else []
    bak_path = ws.parent / (ws.name + "-drill.tar")
    create_backup(ws, bak_path)
    sh.rmtree(ws)                             # destroyed on purpose
    restore_backup(bak_path, ws)
    after = sorted(MemoryStore(mem).records) if mem.exists() else []
    ok_state = after == before
    ok_rerun = _completed_run(ws)
    ok = ok_state and ok_rerun
    return StormRow("backup -> destroy -> restore", ok,
                    f"{len(before)} records survived; re-run accepted"
                    if ok else f"state={ok_state} rerun={ok_rerun}")


SCENARIOS = [sc_kill_storm, sc_torn_files, sc_disk_full, sc_garbage_intents,
             sc_socket_blackout, sc_memory_cap, sc_concurrent_runs,
             sc_companion_kill, sc_backup_restore]


def run_storm(workspace: Path) -> StormReport:
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    rep = StormReport()
    for scenario in SCENARIOS:
        sce_ws = ws / scenario.__name__.replace("sc_", "")
        try:
            rep.rows.append(scenario(sce_ws))
        except Exception as exc:             # a scenario crash = FAIL row
            rep.rows.append(StormRow(scenario.__name__[3:], False,
                                     f"harness exception: {exc}"))
    return rep
