"""v8 — The Console: human authority with a face.

Static, self-contained HTML over the live state files — proposals,
sponsorship audit, catalog trust, and the exact commands to act. Same
protest as the Studio: the floor of governance is a page an auditor
can open with the lights off.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AEOS Console — Authority</title>
<style>
:root {{ --ink:#c9d1d9; --paper:#0d1117; --card:#161b22; --line:#30363d;
        --accent:#58a6ff; --good:#3fb950; --warn:#d29922; --bad:#f85149; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink);
  font:14px/1.55 ui-monospace,"SF Mono",Menlo,Consolas,monospace; }}
.wrap {{ max-width:960px; margin:0 auto; padding:36px 20px 90px; }}
h1 {{ font-size:20px; color:#fff; }} h1 span {{ color:var(--accent); }}
h2 {{ font-size:14px; letter-spacing:2px; text-transform:uppercase;
     color:var(--accent); margin:34px 0 10px; }}
.card {{ background:var(--card); border:1px solid var(--line);
         border-radius:8px; padding:14px 16px; margin:8px 0; }}
.tag {{ padding:1px 8px; border-radius:10px; font-size:11px; }}
.TRUSTED,.PASS,.SPENT {{ background:#0f2e17; color:var(--good); }}
.QUARANTINED {{ background:#3a2c07; color:var(--warn); }}
.REFUSED,.FAIL {{ background:#3d1216; color:var(--bad); }}
code {{ background:#1f2630; padding:2px 6px; border-radius:5px; font-size:12.5px;
        color:#a5d6ff; word-break:break-all; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ padding:7px 10px; border-bottom:1px solid var(--line); text-align:left; }}
.dim {{ color:#8b949e; }} footer {{ margin-top:50px; color:#8b949e; font-size:12px; }}
</style></head><body><div class="wrap">
<h1>AEOS <span>Console</span> — authority, on the record</h1>
<p class="dim">Everything on this page was decided by mechanism, not mood.</p>

<h2>Factory proposals</h2>
<div id="proposals"></div>

<h2>Federated catalog</h2>
<table><thead><tr><th>unit</th><th>kind</th><th>trust</th><th>origin</th></tr></thead>
<tbody id="catalog"></tbody></table>

<h2>Sponsorship audit trail</h2>
<div id="audit" class="card"></div>

<h2>Act</h2>
<div class="card" id="act">
  <div>Sponsor an install (one scope, one use, one hour):</div>
  <div style="margin-top:8px"><code>aeos sponsor --scope "factory:install:NAME"</code></div>
  <div style="margin-top:6px">Then spend it:</div>
  <div style="margin-top:8px"><code>aeos factory-demo --token &lt;issued-token&gt;</code></div>
</div>

<footer>aeos console · static by design · the record outlives the run</footer>
</div>
<script>
const DATA = {payload};
const P = document.getElementById("proposals");
if (!(DATA.proposals||[]).length) {{
  P.innerHTML = '<div class="card dim">no proposals on record — run ' +
    '<code>aeos factory-demo</code> to generate measured candidates</div>';
}} else for (const p of DATA.proposals) {{
  P.insertAdjacentHTML("beforeend",
    `<div class="card"><b>${{p.name}}</b> — sandbox <span class="tag ${{p.sandbox}}">${{p.sandbox}}</span>` +
    ` <span class="dim">from ${{p.signature}} (seen ${{p.count}}x)</span><br>` +
    `<span class="dim">scope to sponsor:</span> <code>factory:install:${{p.name}}</code></div>`);
}}
const C = document.getElementById("catalog");
if (!(DATA.catalog||[]).length) {{
  C.innerHTML = '<tr><td colspan="4" class="dim">catalog empty</td></tr>';
}} else for (const u of DATA.catalog) {{
  C.insertAdjacentHTML("beforeend",
    `<tr><td>${{u.name}} <span class="dim">v${{u.version}} ${{u.sha256}}</span></td>` +
    `<td>${{u.kind}}</td><td><span class="tag ${{u.trust}}">${{u.trust}}</span></td>` +
    `<td>${{u.origin}}</td></tr>`);
}}
const A = document.getElementById("audit");
const rows = (DATA.audit||[]).map(a =>
  `<div><span class="tag ${{a.outcome.startsWith("REFUSED") ? "REFUSED" :
      (a.outcome === "SPENT" ? "SPENT" : "PASS")}}">${{a.outcome.split(" ")[0]}}</span>` +
  ` <code>${{a.prefix}}…</code> ${{a.scope}}</div>`).join("");
A.innerHTML = rows || '<span class="dim">no tokens issued yet</span>';
</script></body></html>"""


def render_console(workspace: Path, out: Path | None = None) -> Path:
    proposals: list[dict] = []
    fs = workspace / ".aeos" / "factory-summary.json"
    if fs.exists():
        d = json.loads(fs.read_text(encoding="utf-8"))
        proposals = [{"name": n,
                      "sandbox": "PASS" if n in d.get("proposed", []) else "FAIL",
                      "signature": d.get("signatures", {}).get(n, "?"),
                      "count": d.get("counts", {}).get(n, 0)}
                     for n in d.get("proposed", [])]

    catalog: list[dict] = []
    cat_dir = workspace / ".aeos" / "catalog"
    fed = cat_dir / "federation.jsonl"
    if fed.exists():
        for line in fed.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                catalog.append({"name": c["name"], "kind": c["kind"],
                                "version": c["version"], "sha256": c.get("sha256", "")[:8],
                                "trust": c["trust"], "origin": c.get("origin", "foreign")})

    audit: list[dict] = []
    spons = workspace / ".aeos" / "sponsorships.jsonl"
    if spons.exists():
        for line in spons.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("rec") == "audit":
                audit.append({"prefix": d["prefix"], "scope": d["scope"],
                              "outcome": d["outcome"]})

    payload = json.dumps({"proposals": proposals, "catalog": catalog,
                          "audit": audit})
    out = out or (workspace / ".aeos" / "console.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.format(payload=payload), encoding="utf-8")
    return out
