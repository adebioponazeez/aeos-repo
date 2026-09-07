"""v36 The Notary, part 3: the edge outbox — writes wait for the wire.

SEF-X handover 5.1/6.5/NFR-05 (adopted, law-compatible): under
blackout or metered bandwidth, records are buffered in a local SQLite
WAL outbox and replayed when the operator says so. The queue is
always local and always works offline; the wire stays exactly where
ADR-039/040 put it — behind an EXPLICIT endpoint, never ambient.
Content-hash idempotency keys make replay safe: the same record
enqueued twice is ONE row, and a delivered row is never redelivered.
Retries are bounded and honest — three failed attempts and the row
is dead-lettered, named, waiting for a human, not silently spun.

Delivery semantics, stated plainly: local bookkeeping is
exactly-once (a row flips pending -> sent exactly one time); toward
the endpoint it is at-least-once — the consumer dedupes on the
idempotency key we sent. That is the honest contract a queue can
actually keep.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
import sqlite3
from pathlib import Path

DEFAULT_DIR = Path.home() / ".aeos"
SCHEMA = 1
MAX_ATTEMPTS = 3


def db_path() -> Path:
    """AEOS_OUTBOX_DB overrides; default ~/.aeos/outbox.db."""
    env = os.environ.get("AEOS_OUTBOX_DB")
    return Path(env) if env else DEFAULT_DIR / "outbox.db"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(
        timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the WAL outbox. WAL = a reader never
    blocks a writer and a power cut never tears a committed row."""
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS outbox ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " idem_key TEXT UNIQUE NOT NULL,"
        " endpoint TEXT NOT NULL,"
        " payload TEXT NOT NULL,"
        " status TEXT NOT NULL DEFAULT 'pending'"
        "   CHECK (status IN ('pending','sent','dead')),"
        " attempts INTEGER NOT NULL DEFAULT 0,"
        " created_at TEXT NOT NULL,"
        " sent_at TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_status"
                 " ON outbox (status)")
    conn.commit()
    return conn


def idem_key_for(endpoint: str, payload: str) -> str:
    """Content-addressed idempotency: same destination + same record =
    same key, forever. (SEF-X 5.1: 'cryptographic content hashing'.)"""
    return hashlib.sha256(
        (endpoint + "\x00" + payload).encode("utf-8")).hexdigest()


def enqueue(conn: sqlite3.Connection, endpoint: str, payload: str,
            idem_key: str | None = None) -> dict:
    """Idempotent enqueue: a repeat is a no-op that tells the truth."""
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("endpoint must be an explicit http(s) URL")
    key = idem_key or idem_key_for(endpoint, payload)
    cur = conn.execute(
        "INSERT OR IGNORE INTO outbox"
        " (idem_key, endpoint, payload, status, attempts, created_at)"
        " VALUES (?, ?, ?, 'pending', 0, ?)",
        (key, endpoint, payload, _now()))
    conn.commit()
    created = cur.rowcount == 1
    row = conn.execute("SELECT id, status FROM outbox WHERE idem_key = ?",
                       (key,)).fetchone()
    return {"id": row["id"], "created": created, "status": row["status"]}


def counts(conn: sqlite3.Connection) -> dict:
    out = {"pending": 0, "sent": 0, "dead": 0, "endpoints": {}}
    for row in conn.execute("SELECT status, COUNT(*) AS n FROM outbox"
                            " GROUP BY status"):
        out[row["status"]] = row["n"]
    for row in conn.execute("SELECT endpoint, COUNT(*) AS n FROM outbox"
                            " WHERE status = 'pending' GROUP BY endpoint"):
        out["endpoints"][row["endpoint"]] = row["n"]
    return out


def drain(conn: sqlite3.Connection, deliver, *, endpoint: str | None = None,
          limit: int = 100, max_attempts: int = MAX_ATTEMPTS) -> dict:
    """Replay pending rows through `deliver(row) -> bool`. True marks
    sent; False burns an attempt (dead after max_attempts). Rows are
    only ever marked for work that actually happened — a crash between
    deliver and mark replays one row at the endpoint, which the
    idempotency key exists to absorb."""
    sql = ("SELECT id, idem_key, endpoint, payload, attempts FROM outbox"
           " WHERE status = 'pending'")
    args: tuple = ()
    if endpoint:
        sql += " AND endpoint = ?"
        args = (endpoint,)
    sql += " ORDER BY id LIMIT ?"
    rows = conn.execute(sql, args + (limit,)).fetchall()

    receipt = {"considered": len(rows), "delivered": 0,
               "failed": 0, "dead": 0}
    for row in rows:
        try:
            ok = bool(deliver(row))
        except Exception:                    # the wire never crashes us
            ok = False
        if ok:
            conn.execute("UPDATE outbox SET status = 'sent', sent_at = ?"
                         " WHERE id = ?", (_now(), row["id"]))
            receipt["delivered"] += 1
        else:
            attempts = row["attempts"] + 1
            status = "dead" if attempts >= max_attempts else "pending"
            conn.execute("UPDATE outbox SET attempts = ?, status = ?"
                         " WHERE id = ?", (attempts, status, row["id"]))
            receipt["failed"] += 1
            if status == "dead":
                receipt["dead"] += 1
        conn.commit()
    receipt["remaining_pending"] = counts(conn)["pending"]
    return receipt


def health(path: Path | None = None) -> tuple[str, str]:
    """For the doctor: (verdict, detail). Corruption is a FAIL; a
    queue with work in it is PASS — buffering is the design, not a
    fault; dead letters are a WARN asking for a human."""
    path = Path(path) if path else db_path()
    if not path.exists():
        return "PASS", "not initialized (nothing enqueued yet)"
    try:
        conn = connect(path)
    except sqlite3.DatabaseError as exc:
        return "FAIL", f"outbox unreadable: {exc}"
    try:
        check = conn.execute("PRAGMA quick_check").fetchone()[0]
        if check != "ok":
            return "FAIL", f"integrity check: {check}"
        c = counts(conn)
        detail = (f"{c['pending']} pending (buffered by design), "
                  f"{c['sent']} sent, {c['dead']} dead")
        if c["dead"]:
            return "WARN", detail + " — dead letters want a human"
        return "PASS", detail
    finally:
        conn.close()


def deliver_http(row) -> bool:
    """One bounded POST to the row's explicit endpoint. 2xx is a
    receipt; anything else is a named failure — never an exception in
    the caller's face (the wire gets receipts, not crashes)."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        row["endpoint"], data=row["payload"].encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json",
                 "X-Idempotency-Key": row["idem_key"]})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            ValueError):
        return False
