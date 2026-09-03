"""v11 tests: live providers behind the seam — wire shape, auth, error
taxonomy, usage metering, budget cutoff, env resolution. All against
localhost servers; zero network, zero keys, zero spend."""

import json
import os
import pytest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from aeos.adapters import AdapterError, ErrorKind, ProviderAdapter
from aeos.contracts import Decision
from aeos.economics import Budget, CostTracker
from aeos.models import ModelCall, ModelReply
from aeos.providers import (ChatCompletionsTransport, MeteredAdapter,
                            PRESETS, live_adapter, live_budget)


def _serve(handler_cls):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    import threading
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _echo_handler(status=200, body=None, note=""):
    captured = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            captured["payload"] = json.loads(self.rfile.read(length) or b"{}")
            captured["auth"] = self.headers.get("Authorization", "")
            if status != 200:
                self.send_error(status, note, body or "")
                return
            out = json.dumps(body or {}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

    return _serve(H), captured


class TestWireShape:
    def test_payload_and_auth_header(self, monkeypatch):
        monkeypatch.setenv("FAKE_KEY", "sk-test-123")
        srv, captured = _echo_handler(body={
            "choices": [{"message": {"content": "hi"}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7}})
        try:
            t = ChatCompletionsTransport(f"http://127.0.0.1:{srv.server_address[1]}/v1",
                                         "FAKE_KEY")
            reply = t.post(ModelCall(system="be brief", prompt="hello",
                                     agent_name="a"), "m-1")
            assert captured["payload"]["model"] == "m-1"
            msgs = captured["payload"]["messages"]
            assert msgs[0] == {"role": "system", "content": "be brief"}
            assert msgs[1] == {"role": "user", "content": "hello"}
            assert captured["auth"] == "Bearer sk-test-123"
            assert (reply.tokens_in, reply.tokens_out) == (11, 7)
        finally:
            srv.shutdown(); srv.server_close()

    def test_missing_key_fails_before_the_wire(self):
        t = ChatCompletionsTransport("http://127.0.0.1:1/v1", "NO_SUCH_KEY_ENV")
        with pytest.raises(PermissionError, match="bring your own key"):
            t.post(ModelCall(system="s", prompt="p", agent_name="a"), "m")


class TestTaxonomyMapping:
    def _adapter(self, srv, retries=2):
        t = ChatCompletionsTransport(f"http://127.0.0.1:{srv.server_address[1]}/v1",
                                     "FAKE_KEY")
        return ProviderAdapter(t, model="m", retries=retries, backoff_s=0.001)

    def test_429_is_transient(self, monkeypatch):
        monkeypatch.setenv("FAKE_KEY", "k")
        srv, _ = _echo_handler(status=429)
        try:
            with pytest.raises(AdapterError) as ei:
                self._adapter(srv, retries=0).complete(
                    ModelCall(system="s", prompt="p", agent_name="a"))
            assert ei.value.kind is ErrorKind.TRANSIENT
        finally:
            srv.shutdown(); srv.server_close()

    def test_context_overflow_never_retries(self, monkeypatch):
        monkeypatch.setenv("FAKE_KEY", "k")
        srv, _ = _echo_handler(status=400,
                               body="context_length_exceeded: too long")
        try:
            with pytest.raises(AdapterError) as ei:
                self._adapter(srv, retries=3).complete(
                    ModelCall(system="s", prompt="p", agent_name="a"))
            assert ei.value.kind is ErrorKind.CONTEXT_OVERFLOW
        finally:
            srv.shutdown(); srv.server_close()

    def test_401_is_permanent(self, monkeypatch):
        monkeypatch.setenv("FAKE_KEY", "k")
        srv, _ = _echo_handler(status=401, body="bad key")
        try:
            with pytest.raises(AdapterError) as ei:
                self._adapter(srv, retries=2).complete(
                    ModelCall(system="s", prompt="p", agent_name="a"))
            assert ei.value.kind is ErrorKind.PERMANENT
        finally:
            srv.shutdown(); srv.server_close()

    def test_empty_reply_is_junk(self, monkeypatch):
        monkeypatch.setenv("FAKE_KEY", "k")
        srv, _ = _echo_handler(body={"choices": [{"message": {"content": "  "}}]})
        try:
            with pytest.raises(AdapterError) as ei:
                self._adapter(srv).complete(
                    ModelCall(system="s", prompt="p", agent_name="a"))
            assert ei.value.kind is ErrorKind.JUNK
        finally:
            srv.shutdown(); srv.server_close()


class TestMetering:
    def _inner(self, tokens=(1000, 1000)):
        class Inner:
            def complete(self, call):
                return ModelReply(text="ok", model="m",
                                  tokens_in=tokens[0], tokens_out=tokens[1])
        return Inner()

    def test_usage_recorded_into_economics(self):
        costs = CostTracker()
        metered = MeteredAdapter(self._inner(), costs, Budget(max_cost=10))
        metered.complete(ModelCall(system="s", prompt="p", agent_name="builder"))
        assert costs.total_tokens() == 2000
        assert costs.per_task()["builder"] > 0

    def test_budget_cutoff_is_inline_and_permanent(self):
        costs = CostTracker()
        metered = MeteredAdapter(self._inner(), costs, Budget(max_cost=1.0))
        # each call costs 0.75 at default rates: call1 -> 0.75 (allow),
        # call2 -> 1.5 (allow, still under at CHECK time), call3 -> DENY
        call = ModelCall(system="s", prompt="p", agent_name="a")
        metered.complete(call)
        metered.complete(call)
        with pytest.raises(AdapterError, match="budget cutoff") as ei:
            metered.complete(call)
        assert ei.value.kind is ErrorKind.PERMANENT
        assert len(metered.cutoffs) == 1
        assert costs.total_cost() == pytest.approx(1.5)

    def test_zero_usage_not_recorded(self):
        costs = CostTracker()
        metered = MeteredAdapter(self._inner(tokens=(0, 0)), costs,
                                 Budget(max_cost=10))
        metered.complete(ModelCall(system="s", prompt="p", agent_name="a"))
        assert costs.usages == []


class TestEnvResolution:
    def test_openrouter_preset(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "k")
        a = live_adapter("openrouter")
        assert a.name == "live:openrouter"
        assert a.model == PRESETS["openrouter"]["default_model"]
        assert a.transport.url.endswith("openrouter.ai/api/v1/chat/completions")

    def test_abacus_preset_routellm(self, monkeypatch):
        monkeypatch.setenv("ABACUS_API_KEY", "k")
        a = live_adapter("abacus", "route-llm")
        assert a.transport.url.startswith("https://routellm.abacus.ai/v1")

    def test_env_provider_and_model(self, monkeypatch):
        monkeypatch.setenv("AEOS_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        monkeypatch.setenv("AEOS_MODEL", "gpt-5-mini")
        a = live_adapter()
        assert a.name == "live:openai" and a.model == "gpt-5-mini"

    def test_missing_key_fails_fast(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(PermissionError, match="refuses to guess"):
            live_adapter("openrouter")

    def test_unknown_provider_rejected(self):
        with pytest.raises(ValueError, match="unknown provider"):
            live_adapter("napster")

    def test_default_budget_two_dollars(self, monkeypatch):
        monkeypatch.delenv("AEOS_MAX_COST", raising=False)
        assert live_budget().max_cost == 2.0
        monkeypatch.setenv("AEOS_MAX_COST", "0.25")
        assert live_budget().max_cost == 0.25


class TestLiveEndToEnd:
    def test_reference_run_accepts_live_adapter(self, tmp_path, monkeypatch):
        """A live-shaped adapter (real transport, localhost wire) drives
        the SAME graph to acceptance — the seam proof, without spend."""
        monkeypatch.setenv("FAKE_KEY", "k")
        srv, _ = _echo_handler(body={
            "choices": [{"message": {"content":
                "Ship a verified seed module for the fleet"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20}})
        try:
            transport = ChatCompletionsTransport(
                f"http://127.0.0.1:{srv.server_address[1]}/v1", "FAKE_KEY")
            adapter = ProviderAdapter(transport, model="fake-live",
                                      retries=0, name="live:test")
            from aeos.pipeline import reference_run
            bundle = reference_run(tmp_path / "live", model=adapter,
                                   cost_budget=Budget(max_cost=5.0))
            assert bundle["accepted"] is True
            assert bundle["economics"]["mode"] == "live"
            assert bundle["economics"]["total_tokens"] > 0
        finally:
            srv.shutdown(); srv.server_close()

    @pytest.mark.skipif(os.environ.get("AEOS_LIVE") != "1",
                        reason="opt-in only: set AEOS_LIVE=1 + provider key "
                               "to spend real money on this smoke test")
    def test_real_live_smoke(self, tmp_path):
        adapter = live_adapter()
        from aeos.pipeline import reference_run
        bundle = reference_run(tmp_path / "real-live", model=adapter)
        assert bundle["accepted"] is True
        assert bundle["economics"]["mode"] == "live"
