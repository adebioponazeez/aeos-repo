"""v3.0 — Sponsorship: human authority as a first-class, spendable,
expiring token. L7 promotions and meta-loop changes do not happen
because the system is confident; they happen because a human spent
irrevocable authority on them — one scope, one use, bounded time.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Sponsorship:
    token: str
    scope: str                     # what this sponsorship authorizes
    issued_by: str = "human"
    expires_at: float = 0.0
    spent: bool = False
    spent_on: str = ""

    def __post_init__(self) -> None:
        if not self.expires_at:
            self.expires_at = time.time() + 3600  # default: one hour

    @property
    def valid(self) -> bool:
        return not self.spent and time.time() <= self.expires_at


class SponsorshipGate:
    """Issue, inspect, spend. Spending is atomic and one-shot.

    v8: optional JSONL persistence — authority must survive restarts
    to be real. A spent token stays spent after the process dies."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.issued: dict[str, Sponsorship] = {}
        self.audit: list[tuple[str, str, str]] = []   # (token-prefix, scope, outcome)
        if path and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                if d["rec"] == "sponsorship":
                    s = Sponsorship(token=d["token"], scope=d["scope"],
                                    expires_at=d["expires_at"])
                    s.spent = d["spent"]
                    self.issued[s.token] = s
                else:
                    self.audit.append((d["prefix"], d["scope"], d["outcome"]))

    def _record(self, prefix: str, scope: str, outcome: str) -> None:
        self.audit.append((prefix, scope, outcome))
        self._flush()

    def _flush(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps({"rec": "sponsorship", "token": s.token,
                             "scope": s.scope, "expires_at": s.expires_at,
                             "spent": s.spent})
                 for s in self.issued.values()]
        lines += [json.dumps({"rec": "audit", "prefix": p, "scope": sc,
                              "outcome": o}) for p, sc, o in self.audit]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def issue(self, scope: str, *, ttl_s: float = 3600,
              issued_by: str = "human") -> Sponsorship:
        s = Sponsorship(token=secrets.token_hex(16), scope=scope,
                        issued_by=issued_by,
                        expires_at=time.time() + ttl_s)
        self.issued[s.token] = s
        self._record(s.token[:8], scope, "issued")
        return s

    def spend(self, token: str, scope: str) -> Sponsorship:
        s = self.issued.get(token)
        prefix = (token or "none")[:8]
        if s is None:
            self._record(prefix, scope, "REFUSED: unknown token")
            raise PermissionError("unknown sponsorship token")
        if not s.valid:
            why = "already spent" if s.spent else "expired"
            self._record(prefix, scope, f"REFUSED: {why}")
            raise PermissionError(f"sponsorship {why}")
        if s.scope != scope:
            self._record(prefix, scope, f"REFUSED: scope mismatch ({s.scope})")
            raise PermissionError(f"token scoped to '{s.scope}', not '{scope}'")
        s.spent = True
        s.spent_on = scope
        self._record(prefix, scope, "SPENT")
        return s

    def authorize(self, token: str | None, scope: str) -> bool:
        """Non-raising form for governor-style checks."""
        if token is None:
            self._record("none", scope, "REFUSED: no token presented")
            return False
        try:
            self.spend(token, scope)
            return True
        except PermissionError:
            return False
