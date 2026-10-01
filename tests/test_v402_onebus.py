"""v40.2.0 — ONE BUS (ADR-059): the foreman and the boot stream onto
the shopfloor's event bus.

The audit named four disjoint event ledgers; after the spine
(v39.8) the runs dir became the pipeline's live bus, but the two
autonomous operators — foreman and ignition — were still invisible
to `aeos stream`. Now both write their lifecycle into the SAME
runs-dir bus (`<ts>-events.jsonl`), best-effort by law:
observability must never take the verdict. The boot's work stage
also streams live (it runs the pipeline with live_events=True), so
the shopfloor rolls from boot events to work events mid-boot.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

from aeos.foreman import run as foreman_run
from aeos.ignition import boot
from aeos.stream import ShopfloorServer, newest_events_file


def _ws_with_runs(tmp_path: Path, n: int = 15) -> Path:
    ws = tmp_path / "ws"
    runs = ws / ".aeos" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (runs / f"{1000 + i}-events.jsonl").write_text(
            '{"kind": "x", "ts": 1.0, "detail": {}}\n', encoding="utf-8")
    return ws


def _kinds(path: Path) -> list[str]:
    return [json.loads(l)["kind"] for l in
            path.read_text().splitlines() if l]


def _serve(ws: Path) -> ShopfloorServer:
    _PORT[0] += 1
    srv = ShopfloorServer(ws, port=_PORT[0])
    threading.Thread(target=srv.start, daemon=True).start()
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", srv.port),
                                          timeout=0.5):
                return srv
        except OSError:
            time.sleep(0.1)
    raise AssertionError("shopfloor never bound")


_PORT = [8910]


class TestForemanOnTheBus:
    def test_apply_streams_its_lifecycle(self, tmp_path):
        ws = _ws_with_runs(tmp_path)
        r = foreman_run(ws, apply_mode=True)
        assert r["exit_code"] == 0
        ev = Path(r["events_file"])
        assert ev.exists() and str(ev).endswith("-events.jsonl")
        kinds = _kinds(ev)
        for k in ("foreman.start", "finding.filed", "actions.start",
                  "action.done", "foreman.end"):
            assert k in kinds, k
        # its own events file is a run file like any other: groom
        # keeps the NEWEST 10, and the foreman's is the newest
        kept = list((ws / ".aeos" / "runs").glob("*-events.jsonl"))
        assert len(kept) == 10 and ev in kept

    def test_survey_streams_too_but_names_no_actions(self, tmp_path):
        ws = _ws_with_runs(tmp_path)
        r = foreman_run(ws, apply_mode=False)
        assert r["findings"]
        kinds = _kinds(Path(r["events_file"]))
        assert "foreman.start" in kinds and "foreman.end" in kinds
        assert "finding.filed" in kinds
        assert "action.done" not in kinds

    def test_the_shopfloor_sees_the_foreman_work(self, tmp_path):
        ws = _ws_with_runs(tmp_path)
        r = foreman_run(ws, apply_mode=True)
        srv = _serve(ws)
        try:
            import http.client
            c = http.client.HTTPConnection("127.0.0.1", srv.port,
                                           timeout=5)
            c.request("GET", "/health")
            d = json.loads(c.getresponse().read())
            c.close()
            assert d["ok"] and d["events"] > 0
            assert d["events_file"] == Path(r["events_file"]).name
        finally:
            srv.httpd.shutdown()

    def test_a_refused_bus_never_takes_the_verdict(self, tmp_path):
        # .aeos/runs is a FILE: the sink cannot be created — the
        # foreman must still survey, act and verdict, unwatched
        ws = tmp_path / "ws"
        (ws / ".aeos").mkdir(parents=True)
        (ws / ".aeos" / "runs").write_text("not a dir\n",
                                           encoding="utf-8")
        r = foreman_run(ws, apply_mode=True)      # must not raise
        assert r["exit_code"] in (0, 1, 2)
        assert "events_file" not in r


class TestTheBusSurvivesAFullDisk:
    def test_close_swallows_the_refused_flush_and_goes_memory(self,
                                                              tmp_path):
        # found by the E4 field test: a full disk + buffered events
        # raised 'Exception ignored' at interpreter exit. close()
        # must swallow the refused flush; emit becomes memory-only.
        from aeos.observability import EventLog

        class _Poisoned:                    # the disk now refuses all
            def write(self, s):
                raise OSError("No space left on device")

            def flush(self):
                raise OSError("No space left on device")

            def close(self):
                raise OSError("No space left on device")

        sink = tmp_path / "bus-events.jsonl"
        log = EventLog(sink=sink)
        log.emit("before.poison", ok=True)
        log._file = _Poisoned()
        log.close()                          # must not raise
        log.emit("after.close", ok=True)     # memory-only now
        assert len(log.events()) == 2
        assert "before.poison" in sink.read_text()


class TestBootOnTheBus:
    def test_the_boot_streams_its_stages(self, tmp_path):
        ws = tmp_path / "ws"
        b = boot(ws)
        assert b["outcome"] == "ok"
        ev = Path(b["events_file"])
        kinds = _kinds(ev)
        assert kinds[0] == "boot.start" and kinds[-1] == "boot.end"
        assert kinds.count("boot.stage") == 4      # all four stages
        # the work stage ran the pipeline LIVE on the same bus. A
        # same-second boot and work run SHARE the bus file (both
        # append; the shopfloor sees everything); a later work run
        # rolls the bus forward. Both are the one bus working.
        work = Path(b["run"]["events"])
        assert work.exists()
        assert "task.started" in _kinds(work)
        assert "boot.stage" in _kinds(ev)
        assert newest_events_file(ws) in {ev, work}

    def test_a_failed_boot_names_the_stage_on_the_bus(self, tmp_path):
        ws = tmp_path / "ws"
        (ws / ".aeos").mkdir(parents=True)
        # a held workspace lock: the work stage is refused — named,
        # receipted, and the bus carries boot.failed (torn jsonl is
        # TOLERATED by design: quarantine, not failure)
        from aeos.vault import WorkspaceLock
        lock = WorkspaceLock(ws / ".aeos" / "workspace.lock")
        assert lock.acquire(blocking=False)
        try:
            b = boot(ws)
        finally:
            lock.release()
        assert b["outcome"] != "ok"
        assert b["failed_stage"] == "work"
        kinds = _kinds(Path(b["events_file"]))
        assert "boot.start" in kinds and "boot.failed" in kinds
