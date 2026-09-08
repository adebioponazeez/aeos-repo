"""v39.7 The Live Shopfloor: events streamed live (SSE), stdlib only.

The dark-factory roadmap's gap #5, closed: events were durable JSONL
but nothing streamed them. This module serves the shopfloor live:
Server-Sent Events over the same ThreadingHTTPServer pattern as the
Consulate (v31), with the same law — READ ONLY. The console is a
single HTML page with inline CSS/JS (no CDN, no framework, no
network beyond the stream itself); the transport is loopback by
default and opens wider only when the operator says so.

What streams: the workspace's newest .aeos/runs/*-events.jsonl,
replayed from the start, then tailed live; when a NEWER run file
appears (a new run started), the stream rolls over to it — the
shopfloor stays live across runs. Every event is the same durable
JSONL line already on disk; streaming adds zero new truth.
"""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

POLL_S = 0.4


# ----------------------------------------------------------------- console

CONSOLE_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AEOS — the live shopfloor</title>
<style>
 :root{--bg:#0d1117;--fg:#d6e2f0;--dim:#7b8ba3;--ok:#3fb950;--warn:#d29922;
      --err:#f85149;--line:#21293a;--card:#131a26}
 *{box-sizing:border-box} body{margin:0;font:14px/1.45 ui-monospace,monospace;
  background:var(--bg);color:var(--fg)}
 header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;
  gap:16px;align-items:baseline;flex-wrap:wrap}
 h1{font-size:15px;margin:0;letter-spacing:.4px}
 #status{font-size:12px;color:var(--dim)} #status.live{color:var(--ok)}
 main{display:grid;grid-template-columns:220px 1fr;gap:0;height:calc(100vh - 55px)}
 aside{border-right:1px solid var(--line);padding:14px;overflow:auto}
 aside h2{font-size:11px;color:var(--dim);margin:8px 0 6px;text-transform:
  uppercase;letter-spacing:.8px}
 .k{display:flex;justify-content:space-between;padding:2px 0;font-size:12px}
 .k b{color:var(--warn);font-weight:600}
 #feed{overflow:auto;padding:10px 16px}
 .ev{padding:6px 10px;border-left:2px solid var(--line);margin:4px 0;
  background:var(--card);border-radius:0 4px 4px 0;font-size:12.5px}
 .ev .k2{color:var(--warn)} .ev .t{color:var(--dim);float:right;font-size:11px}
 .ev.err{border-color:var(--err)} .ev.ok{border-color:var(--ok)}
 input{width:100%;padding:6px 8px;margin-top:10px;background:var(--card);
  color:var(--fg);border:1px solid var(--line);border-radius:4px;
  font:12px ui-monospace,monospace}
</style></head><body>
<header><h1>AEOS — the live shopfloor</h1>
 <span id="status">connecting…</span><span id="count"></span></header>
<main><aside><h2>event kinds</h2><div id="kinds"></div>
 <input id="filter" placeholder="filter: subplan, gate, failed…">
</aside><div id="feed"></div></main>
<script>
const kinds={}, feed=document.getElementById('feed'),
      st=document.getElementById('status'), ct=document.getElementById('count');
let n=0, filt='';
document.getElementById('filter').oninput=e=>{filt=e.target.value.toLowerCase();
  for(const el of feed.children) el.hidden=!match(el.dataset.kind)};
const match=k=>!filt||k.includes(filt);
function add(ev){
  n++; ct.textContent=n+' events';
  kinds[ev.kind]=(kinds[ev.kind]||0)+1;
  const ks=document.getElementById('kinds'); ks.innerHTML='';
  for(const[k,v]of Object.entries(kinds).sort((a,b)=>b[1]-a[1])){
    const d=document.createElement('div');d.className='k';
    d.innerHTML='<span>'+k+'</span><b>'+v+'</b>';ks.appendChild(d);}
  const el=document.createElement('div');el.className='ev';
  el.dataset.kind=ev.kind;
  if(/fail|denied|escalat|refus|veto/.test(ev.kind))el.classList.add('err');
  if(/succeed|finish|accepted/.test(ev.kind))el.classList.add('ok');
  const t=new Date((ev.ts||0)*1000).toLocaleTimeString();
  el.innerHTML='<span class="t">'+t+'</span><span class="k2">'+ev.kind+
    '</span> '+esc(JSON.stringify(ev.detail||{}).slice(0,160));
  if(!match(ev.kind))el.hidden=true;
  feed.prepend(el);
  while(feed.children.length>400)feed.lastChild.remove();
}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
const es=new EventSource('/events');
es.onopen=()=>{st.textContent='live';st.className='live'};
es.onerror=()=>{st.textContent='reconnecting…';st.className=''};
es.onmessage=e=>{try{add(JSON.parse(e.data))}catch(_){}}
</script></body></html>"""


# ----------------------------------------------------------------- events

def newest_events_file(workspace: Path) -> Path | None:
    runs = Path(workspace) / ".aeos" / "runs"
    if not runs.is_dir():
        return None
    files = sorted(runs.glob("*-events.jsonl"))
    return files[-1] if files else None


def _tail_forever(workspace: Path):
    """Yield (line, eof_reached) — replay then live-tail, rolling over
    to newer run files as they appear. Generator; caller stops on
    client disconnect."""
    current = newest_events_file(workspace)
    offset = 0
    while True:
        rolled = newest_events_file(workspace)
        if rolled is not None and (current is None or rolled != current):
            current, offset = rolled, 0        # a new run started
        if current is None:
            yield None                          # nothing yet
            time.sleep(POLL_S)
            continue
        try:
            size = current.stat().st_size
        except OSError:
            yield None
            time.sleep(POLL_S)
            continue
        if size > offset:
            with current.open("rb") as fh:
                fh.seek(offset)
                for raw in fh:
                    yield raw.decode("utf-8", "replace").rstrip("\n")
                offset = fh.tell()
        elif size < offset:                     # truncated/rotated
            offset = 0
        else:
            yield None                          # caught up: idle beat
            time.sleep(POLL_S)


# ----------------------------------------------------------------- server

class ShopfloorHandler(BaseHTTPRequestHandler):
    """Read-only by law: GET only; everything else is a named 405."""

    def log_message(self, *a):                  # quiet by default
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        ws = Path(self.server.workspace)        # type: ignore[attr-defined]
        if self.path in ("/", "/index.html"):
            body = CONSOLE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            ev = newest_events_file(ws)
            n = 0
            if ev is not None:
                try:
                    n = sum(1 for _ in ev.open("rb"))
                except OSError:
                    pass
            self._json(200, {"ok": True, "workspace": str(ws),
                             "events_file": ev.name if ev else None,
                             "events": n,
                             "uptime_s": round(time.time()
                                               - self.server.born, 1)})  # type: ignore[attr-defined]
            return
        if self.path == "/events":
            src = newest_events_file(ws)
            if src is None:
                self._json(404, {
                    "ok": False,
                    "reason": "no events yet — this workspace has no run "
                    "history; run `aeos up --workspace <ws>` first, then "
                    "reload: the shopfloor attaches to real runs only"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                self.wfile.write(b": shopfloor open\n\n")
                self.wfile.flush()
                for line in _tail_forever(ws):
                    if line is None:
                        self.wfile.write(b": beat\n\n")
                        self.wfile.flush()
                        continue
                    if line.strip():
                        self.wfile.write(f"data: {line}\n\n".encode())
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                return                          # client left; that is fine
            return
        self._json(404, {"ok": False,
                         "reason": f"unknown path {self.path!r} — / (console), "
                                   "/events (SSE stream), /health"})

    def do_POST(self) -> None:                  # read-only law
        self._json(405, {"ok": False,
                         "reason": "the shopfloor is READ-ONLY — it streams "
                         "events; it never accepts commands (the write "
                         "surface is the CLI, under the governor)"})

    do_PUT = do_POST
    do_DELETE = do_POST


class ShopfloorServer:
    def __init__(self, workspace: Path, *, bind: str = "127.0.0.1",
                 port: int = 8787):
        self.workspace = Path(workspace)
        self.bind = bind
        self.port = port
        self.httpd: ThreadingHTTPServer | None = None

    def start(self) -> int:
        """Bind and serve forever. A busy port is a NAMED refusal."""
        try:
            self.httpd = ThreadingHTTPServer((self.bind, self.port),
                                             ShopfloorHandler)
        except OSError as exc:
            print(f"SHOPFLOOR REFUSED — cannot bind {self.bind}:{self.port}: "
                  f"{exc.strerror or exc} — pick another --port or stop the "
                  "holder")
            return 2
        self.httpd.workspace = str(self.workspace)     # type: ignore[attr-defined]
        self.httpd.born = time.time()                  # type: ignore[attr-defined]
        print(f"SHOPFLOOR — live at http://{self.bind}:{self.port}")
        print(f"  workspace: {self.workspace}")
        print("  law: read-only; GET / (console) /events (SSE) /health;"
              " loopback by default")
        try:
            self.httpd.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            print("\nSHOPFLOOR — closed by operator")
        finally:
            self.httpd.server_close()
        return 0
