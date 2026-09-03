"""v8 tests: transports, remote workers, process sandboxes, persistence."""

import json
import time
import pytest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aeos.adapters import AdapterError, ErrorKind, ProviderAdapter
from aeos.contracts import Envelope, Evidence
from aeos.models import ModelCall, ModelReply
from aeos.transport import (HTTPModelTransport, RemoteWorker, WorkerServer,
                            call_remote_tool, run_isolated, smoke_validate)


def _serve(handler_cls) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    import threading
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class TestHTTPModelTransport:
    def test_ok_roundtrip(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                body = json.dumps({"text": "hello wire", "tokens_in": 10}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        srv = _serve(H)
        try:
            t = HTTPModelTransport(f"http://127.0.0.1:{srv.server_address[1]}/v1")
            reply = t.post(ModelCall(system="s", prompt="p", agent_name="a"), "m")
            assert reply.text == "hello wire"
        finally:
            srv.shutdown(); srv.server_close()

    def test_503_maps_to_transient(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                self.send_error(503)
        srv = _serve(H)
        try:
            t = HTTPModelTransport(f"http://127.0.0.1:{srv.server_address[1]}/")
            adapter = ProviderAdapter(t, retries=0)
            with pytest.raises(AdapterError) as ei:
                adapter.complete(ModelCall(system="s", prompt="p", agent_name="a"))
            assert ei.value.kind is ErrorKind.TRANSIENT
        finally:
            srv.shutdown(); srv.server_close()

    def test_timeout_maps_to_transient(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                time.sleep(1.0)
                self.send_error(500)
        srv = _serve(H)
        try:
            t = HTTPModelTransport(f"http://127.0.0.1:{srv.server_address[1]}/",
                                   timeout_s=0.15)
            with pytest.raises(TimeoutError):
                t.post(ModelCall(system="s", prompt="p", agent_name="a"), "m")
        finally:
            srv.shutdown(); srv.server_close()


class TestRemoteToolCalls:
    def test_remote_tool_result_untrusted_over_the_wire(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                body = json.dumps({"result": {"answer": 42},
                                   "isError": False}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        srv = _serve(H)
        try:
            out = call_remote_tool(f"http://127.0.0.1:{srv.server_address[1]}/t",
                                   "web_search", {"query": "x"})
            assert out.result == {"answer": 42}
            assert out.untrusted is True   # the wire does not launder trust
        finally:
            srv.shutdown(); srv.server_close()

    def test_remote_error_is_structured(self):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                body = json.dumps({"isError": True,
                                   "error": {"message": "tool exploded",
                                             "code": -32000}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        srv = _serve(H)
        try:
            out = call_remote_tool(f"http://127.0.0.1:{srv.server_address[1]}/t",
                                   "bomb", {})
            assert out.is_error and "tool exploded" in out.error
        finally:
            srv.shutdown(); srv.server_close()

    def test_dead_endpoint_is_structured_not_raised(self):
        out = call_remote_tool("http://127.0.0.1:1/nope", "x", {},
                               timeout_s=0.3)
        assert out.is_error and "transport" in out.error


class TestRemoteWorkers:
    def _worker(self):
        def triage(req):
            env = Envelope(agent="remote-triage", objective=req["description"])
            env.add_evidence("triaged", f"against {req['description'][:30]}")
            return env.to_dict()
        return WorkerServer({"remote-triage": triage}).serve_forever_in_thread()

    def test_health_lists_agents(self):
        ws = self._worker()
        try:
            import urllib.request
            with urllib.request.urlopen(ws.url) as r:
                data = json.loads(r.read())
            assert data["status"] == "ok" and "remote-triage" in data["agents"]
        finally:
            ws.shutdown()

    def test_delegation_roundtrips_envelope(self):
        ws = self._worker()
        try:
            worker = RemoteWorker(url=ws.url, agent="remote-triage")
            env = worker.delegate("triage the inbound queue")
            assert env.agent == "remote-triage"
            assert env.evidence[0].kind == "triaged"
        finally:
            ws.shutdown()

    def test_broken_handler_becomes_error_not_stacktrace(self):
        def bomb(req):
            raise RuntimeError("boom")
        ws = WorkerServer({"bomb-agent": bomb}).serve_forever_in_thread()
        try:
            worker = RemoteWorker(url=ws.url, agent="bomb-agent")
            with pytest.raises(RuntimeError, match="worker error"):
                worker.delegate("anything")
        finally:
            ws.shutdown()


# --------------------------------------------------- process sandboxes

def _design(name="probe-specialist"):
    from aeos.factory import design_agent
    return design_agent("phase:probe:WRITE")


class TestProcessSandbox:
    def test_inprocess_smoke_passes(self, tmp_path):
        from aeos.contracts import Verdict
        result = smoke_validate(_design(), tmp_path / "in")
        assert result["verdict"] == "PASS"

    def test_process_isolation_passes(self, tmp_path):
        result = run_isolated(_design(), tmp_path / "proc", timeout_s=30)
        assert result["verdict"] == "PASS"

    def test_hanging_candidate_is_killed(self, tmp_path):
        # a timeout so small the child cannot finish startup: the parent
        # must kill it and return a FAIL verdict — never hang, never raise
        result = run_isolated(_design(), tmp_path / "hang", timeout_s=0.001)
        assert result["verdict"] == "FAIL"
        assert "wall clock" in result["why"]

    def test_poisoned_input_child_writes_verdict(self, tmp_path):
        # corrupt input (unknown field) -> the defensive child writes a
        # FAIL verdict and exits non-zero; it never owes a stack trace
        import subprocess
        import sys as _sys
        from dataclasses import asdict
        spec = asdict(_design())
        spec["action_classes"] = ["READ", "WRITE"]
        spec["bogus_field"] = "poison"
        inp, out = tmp_path / "in.json", tmp_path / "out.json"
        inp.write_text(json.dumps({"spec": spec}), encoding="utf-8")
        proc = subprocess.run([_sys.executable, "-m", "aeos.sandbox_runner",
                               str(inp), str(out)], cwd=str(tmp_path),
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 1
        verdict = json.loads(out.read_text(encoding="utf-8"))
        assert verdict["verdict"] == "FAIL"
        assert "bogus_field" in verdict["why"]


class TestSponsorshipPersistence:
    def test_tokens_survive_restart(self, tmp_path):
        from aeos.sponsorship import SponsorshipGate
        path = tmp_path / "sponsorships.jsonl"
        gate = SponsorshipGate(path)
        s = gate.issue("factory:install:x")
        gate2 = SponsorshipGate(path)
        assert s.token in gate2.issued

    def test_spent_stays_spent_after_reload(self, tmp_path):
        from aeos.sponsorship import SponsorshipGate
        path = tmp_path / "sponsorships.jsonl"
        gate = SponsorshipGate(path)
        s = gate.issue("scope")
        assert gate.authorize(s.token, "scope")
        gate2 = SponsorshipGate(path)   # "restart"
        assert not gate2.authorize(s.token, "scope")   # replay refused

    def test_factory_isolation_process_mode(self, tmp_path):
        from aeos.catalog import Catalog
        from aeos.contracts import SkillSpec, Verdict
        from aeos.discovery import CapabilityDiscovery
        from aeos.factory import CapabilityFactory
        from aeos.governor import Governor
        from aeos.observability import EventLog
        from aeos.skills import SkillsRegistry
        from aeos.sponsorship import SponsorshipGate
        skills = SkillsRegistry()
        skills.register(SkillSpec(
            name="verify-first", purpose="phase:evaluator:EXECUTE verify",
            trigger="t", procedure=["x"], usage_count=6, win_rate=0.9))
        d = CapabilityDiscovery(skills)
        for _ in range(4):
            d.record_pattern("phase:evaluator:EXECUTE")
        f = CapabilityFactory(skills=skills, discovery=d,
                              governor=Governor(log=EventLog()),
                              gate=SponsorshipGate(),
                              catalog=Catalog(tmp_path / "cat"),
                              log=EventLog())
        cand = f.candidates()[0]
        verdict = f.validate_in_sandbox(cand, tmp_path / "sb",
                                        isolation="process")
        assert verdict is Verdict.PASS
