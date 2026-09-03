"""v11.0 — Live models behind the seam (OpenRouter, Abacus RouteLLM,
and any OpenAI-compatible endpoint).

The OS has spoken only to the deterministic EchoModel since v1.0 —
by design: every guarantee had to hold without a key. v11 adds the
live path WITHOUT touching a single guarantee:

  ChatCompletionsTransport  the OpenAI-compatible wire format
                            (system+user messages, usage accounting),
                            raising taxonomy-classifiable errors
  live_adapter()            env-resolved presets: openrouter, abacus,
                            openai — credentials come from the
                            environment and never touch the event log
  MeteredAdapter            records REAL token usage into the
                            economics layer and ENFORCES the budget
                            inline: spend past the cap and the next
                            call raises PERMANENT — a spend governor
                            inside the model seam

ADR-020. The whole live path is tested against localhost servers;
the only thing tests can't spend is your money.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .adapters import AdapterError, ErrorKind, ProviderAdapter
from .contracts import Decision
from .economics import Budget, CostTracker
from .models import ModelCall, ModelReply


# ------------------------------------------------------------ transport

class ChatCompletionsTransport:
    """POST /chat/completions with proper shape, auth, and usage.

    Error contract (so ProviderAdapter's taxonomy classifies):
      429/5xx            -> ConnectionError  (TRANSIENT: retry+backoff)
      4xx with 'context' -> ValueError carrying the provider message
                            (CONTEXT_OVERFLOW: never retry)
      other 4xx          -> ValueError       (PERMANENT: fail fast)
      timeouts           -> TimeoutError     (TRANSIENT)
      missing key        -> PermissionError  (fail before the wire)
    """

    def __init__(self, base_url: str, key_env: str, *,
                 extra_headers: dict[str, str] | None = None,
                 timeout_s: float = 60.0) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.key_env = key_env
        self.extra_headers = extra_headers or {}
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        key = os.environ.get(self.key_env, "")
        if not key:
            raise PermissionError(
                f"live models need {self.key_env} in the environment — "
                "bring your own key; the OS will not guess one")
        headers = {"Authorization": f"Bearer {key}",
                   "Content-Type": "application/json"}
        headers.update(self.extra_headers)
        return headers

    def post(self, call: ModelCall, model: str) -> ModelReply:
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": call.system},
                {"role": "user", "content": call.prompt},
            ],
            "max_tokens": call.max_output_tokens,
        }).encode()
        req = Request(self.url, data=payload, headers=self._headers())
        try:
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            if exc.code in (429, 502, 503, 504):
                raise ConnectionError(f"{exc.code} upstream: {body}") from exc
            raise ValueError(f"http {exc.code}: {body}") from exc
        except URLError as exc:
            if "timed out" in str(exc).lower():
                raise TimeoutError(f"timeout after {self.timeout_s}s") from exc
            raise ConnectionError(str(exc)) from exc

        choices = data.get("choices") or [{}]
        text = ((choices[0].get("message") or {}).get("content")) or ""
        usage = data.get("usage") or {}
        return ModelReply(text=text,
                          model=data.get("model", model),
                          tokens_in=int(usage.get("prompt_tokens", 0) or 0),
                          tokens_out=int(usage.get("completion_tokens", 0) or 0))


# -------------------------------------------------------------- presets

PRESETS: dict[str, dict] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "default_model": "openai/gpt-5-mini",
        "extra_headers": {"HTTP-Referer": "https://github.com/aeos",
                          "X-Title": "AEOS"},
    },
    "abacus": {
        # RouteLLM: OpenAI-compatible, included with ChatLLM Teams
        "base_url": "https://routellm.abacus.ai/v1",
        "key_env": "ABACUS_API_KEY",
        "default_model": "route-llm",
        "extra_headers": {},
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
        "default_model": "gpt-5-mini",
        "extra_headers": {},
    },
}


def live_adapter(provider: str | None = None, model: str | None = None,
                 *, retries: int = 2, timeout_s: float = 60.0,
                 require_key: bool = True) -> ProviderAdapter:
    """Build the live adapter from presets + environment.

    Provider resolution: argument > AEOS_PROVIDER > 'openrouter'.
    Model resolution:   argument > AEOS_MODEL   > preset default.
    Fails fast (before any wire) if the key is absent."""
    provider = (provider or os.environ.get("AEOS_PROVIDER") or "openrouter").lower()
    if provider not in PRESETS:
        raise ValueError(f"unknown provider '{provider}' — "
                         f"known: {sorted(PRESETS)}")
    preset = PRESETS[provider]
    model = model or os.environ.get("AEOS_MODEL") or preset["default_model"]
    transport = ChatCompletionsTransport(
        preset["base_url"], preset["key_env"],
        extra_headers=preset["extra_headers"], timeout_s=timeout_s)
    if require_key and not os.environ.get(preset["key_env"]):
        raise PermissionError(
            f"{preset['key_env']} not set — live mode refuses to guess. "
            f"Export it and retry.")
    return ProviderAdapter(transport, model=model, retries=retries,
                           breaker_threshold=3, name=f"live:{provider}")


# --------------------------------------------------------------- metering

class MeteredAdapter:
    """Wraps any ModelAdapter: records real usage, enforces the budget
    INLINE — the spend governor lives inside the seam, so no graph,
    gate, or governor needs to know that money exists."""

    def __init__(self, inner, costs: CostTracker, budget: Budget) -> None:
        self.inner = inner
        self.costs = costs
        self.budget = budget
        self.cutoffs: list[str] = []

    def complete(self, call: ModelCall) -> ModelReply:
        decision, why = self.budget.check(self.costs)
        if decision is Decision.DENY:
            self.cutoffs.append(why)
            raise AdapterError(ErrorKind.PERMANENT, f"live budget cutoff: {why}")
        reply = self.inner.complete(call)
        if reply.tokens_in or reply.tokens_out:
            self.costs.record(reply.model, reply.tokens_in, reply.tokens_out,
                              task=call.agent_name)
        return reply


def live_budget() -> Budget:
    """Spend ceiling for live runs: AEOS_MAX_COST (USD), default $2."""
    try:
        cap = float(os.environ.get("AEOS_MAX_COST", "2.0"))
    except ValueError:
        cap = 2.0
    return Budget(max_cost=cap)
