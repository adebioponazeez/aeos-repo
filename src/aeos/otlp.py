"""v30 OTLP push: spans leave the building only on purpose.

The v24 exporter writes OTel-style spans to a file; this pushes them
to a collector over HTTP. Law: the endpoint is ALWAYS explicit; a
push is a bounded transaction — 2xx is a receipt, 429/5xx retry with
backoff (at most `retries`), and when the wire stays hostile the
receipt says so (ok=False, attempts named) — the system never hangs,
never raises network crud at the caller, never pretends it shipped.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVICE = "aeos"


def _spans_payload(spans: list) -> dict:
    return {"resourceSpans": [{
        "resource": {"attributes": [{"key": "service.name",
                                     "value": {"stringValue": SERVICE}}]},
        "scopeSpans": [{"scope": {"name": "aeos.fleet"},
                        "spans": spans}]}]}


def push_spans(endpoint: str, spans: list, *, timeout_s: float = 10.0,
               retries: int = 2, backoff_s: float = 0.2) -> dict:
    if not spans:
        return {"ok": True, "attempts": 0, "status": None,
                "pushed": 0, "note": "nothing to push"}
    body = json.dumps(_spans_payload(spans)).encode("utf-8")
    attempts, last = 0, None
    for attempt in range(retries + 1):
        attempts += 1
        req = urllib.request.Request(endpoint, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                if 200 <= r.status < 300:
                    return {"ok": True, "attempts": attempts,
                            "status": r.status, "pushed": len(spans)}
                last = r.status
        except urllib.error.HTTPError as exc:
            last = exc.code
            if exc.code not in (429, 500, 502, 503, 504):
                break                      # client error: do not retry
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = f"transport: {exc}"
        if attempt < retries:
            time.sleep(backoff_s * (attempt + 1))
    return {"ok": False, "attempts": attempts, "status": last,
            "pushed": 0,
            "note": "wire stayed hostile; spans remain safe on disk"}


def push_file(endpoint: str, spans_file: Path, **kw) -> dict:
    spans = [json.loads(ln) for ln in
             Path(spans_file).read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    return push_spans(endpoint, spans, **kw)
