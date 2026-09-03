"""v24 OTel export: the fleet stream speaks the ecosystem's format.

The EventBus JSONL is our truth; OTel is the industry's lingua
franca. This module is a pure translator — every event becomes a span
with stable ids (derived from content, not clocks), so exports are
byte-stable and diffable. No SDK, no network: a file of spans any
OTel-compatible collector can ingest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .fleet import EventBus

SERVICE = "aeos"


def _sha(text: str, n: int) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def event_to_span(event, stream_name: str) -> dict:
    trace_id = _sha(f"{SERVICE}:{stream_name}", 32)
    span_id = _sha(event.as_line(), 16)
    failed = "FAILED" in event.kind
    return {
        "traceId": trace_id,
        "spanId": span_id,
        "name": event.kind,
        "kind": "INTERNAL",
        "startTimeUnixNano": int(event.ts * 1_000_000_000),
        "attributes": {
            "service.name": SERVICE,
            "agent": event.agent,
            "detail": event.detail,
        },
        "status": {"code": "ERROR"} if failed else {"code": "UNSET"},
    }


def export(bus: EventBus, out: Path) -> int:
    """Translate the whole stream; returns span count written."""
    events = bus.replay()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(event_to_span(ev, bus.path.name), sort_keys=True)
             for ev in events]
    out.write_text("\n".join(lines) + ("\n" if lines else ""),
                   encoding="utf-8")
    return len(lines)
