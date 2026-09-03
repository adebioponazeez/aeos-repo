"""v8 — Child entry point for process-isolated sandbox validation.

Run as: python -m aeos.sandbox_runner <in.json> <out.json>
Never talks to the network; writes only inside its cwd; dies on its
own resource limits. The parent's wall-clock timeout is the outer
belt; these limits are the suspenders.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: aeos.sandbox_runner <in.json> <out.json>", file=sys.stderr)
        return 2
    inp, out = Path(argv[1]), Path(argv[2])
    payload = json.loads(inp.read_text(encoding="utf-8"))

    try:
        from aeos.contracts import ActionClass, AgentSpec
        from aeos.transport import smoke_validate

        d = payload["spec"]
        d["action_classes"] = [ActionClass(a)
                               for a in d.get("action_classes", ["READ"])]
        design = AgentSpec(**d)
        result = smoke_validate(design, Path.cwd())
    except Exception as exc:
        # a sandbox child never owes anyone a stack trace — only a verdict
        result = {"verdict": "FAIL", "why": f"{type(exc).__name__}: {exc}"}
    out.write_text(json.dumps(result, default=str), encoding="utf-8")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
