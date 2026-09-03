#!/usr/bin/env python3
"""Build the book: concatenate parts -> self-contained HTML."""
from __future__ import annotations

import re
from pathlib import Path

import markdown  # build-time only

BOOK = Path(__file__).parent
PARTS = [
    "00-front-matter.md",
    "01-part-one.md",
    "02-part-two.md",
    "03-part-three.md",
    "04-part-four.md",
    "05-part-five.md",
    "06-part-six.md",
    "09-part-eight.md",
    "10-part-nine.md",
    "07-part-seven.md",
    "08-appendices.md",
]

CSS = """
:root { --ink:#1a1a20; --paper:#fbfaf7; --accent:#0e5a49; --rule:#d8d4cc; --soft:#6b6b74; }
* { box-sizing: border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  font-size:19px; line-height:1.62; }
.page { max-width:860px; margin:0 auto; padding:64px 48px 120px; }
header.titleblock { text-align:center; padding:90px 0 60px; border-bottom:3px double var(--rule); margin-bottom:64px; }
h1.book-title { font-size:52px; letter-spacing:2px; margin:0 0 10px; color:var(--accent); font-weight:800; }
p.subtitle { font-size:22px; font-style:italic; color:var(--soft); margin:6px 0; }
p.vol { font-size:16px; text-transform:uppercase; letter-spacing:4px; color:var(--soft); margin-top:28px; }
h1 { font-size:30px; margin-top:72px; padding-bottom:8px; border-bottom:1px solid var(--rule); color:var(--ink); }
h1.part { page-break-before:always; text-align:center; font-size:34px; color:var(--accent);
  border:none; margin-top:120px; padding:40px 0 0; letter-spacing:1px; }
h2 { font-size:24px; margin-top:52px; color:var(--ink); }
h2.chapter { border-left:5px solid var(--accent); padding-left:14px; }
h3 { font-size:19px; margin-top:32px; color:var(--soft); text-transform:none;}
pre { background:#12141a; color:#e8e6df; padding:18px 20px; border-radius:8px; overflow-x:auto;
  font-size:14px; line-height:1.5; font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace; }
code { font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace; font-size:0.86em;
  background:#eceae2; padding:1px 5px; border-radius:4px; }
pre code { background:none; padding:0; font-size:1em; }
table { border-collapse:collapse; width:100%; margin:24px 0; font-size:16px; }
th { background:var(--accent); color:#fff; text-align:left; padding:9px 12px; }
td { border-bottom:1px solid var(--rule); padding:8px 12px; vertical-align:top;}
tr:nth-child(even) td { background:#f2f0e9; }
blockquote { margin:28px 8px; padding:10px 22px; border-left:4px solid var(--accent);
  color:#33333c; font-style:italic; }
hr { border:none; border-top:1px solid var(--rule); margin:48px 0; }
nav.toc { background:#f2f0e9; border:1px solid var(--rule); border-radius:10px; padding:26px 34px; }
nav.toc h2 { margin-top:0; font-size:20px; letter-spacing:2px; text-transform:uppercase; color:var(--accent);}
nav.toc ul { list-style:none; padding-left:0; } nav.toc ul ul { padding-left:22px; }
nav.toc a { color:var(--ink); text-decoration:none; } nav.toc a:hover { color:var(--accent); }
nav.toc li { padding:2px 0; font-size:16px;}
a { color:var(--accent); }
em { color:inherit; }
.footnote { text-align:center; font-style:italic; color:var(--soft); margin-top:80px; font-size:16px;}
@media print { .page{padding:0 24px;} h1.part{page-break-before:always;} pre{white-space:pre-wrap;} }
"""

def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "sec"

VOL2_PARTS = [
    "00-v2-front-matter.md",
    "01-v2-part-one.md",
    "02-v2-part-two.md",
    "03-v2-part-three.md",
    "04-v2-parts-four-five.md",
    "05-v2-part-six.md",
    "06-v2-part-seven-appendices.md",
]

VOL3_PARTS = ["00-v3-full.md"]

VOL3_TITLES = {
    "title": "10,000,000&times; AI ENGINEERING",
    "sub1": "Volume III &mdash; The Arc Completed",
    "sub2": "The Vault and the Storm, the Shipyard and the schema law (v26&ndash;v28) &middot; the System at v28.0.0",
    "vol": "Shipyard printing (v28) &middot; 351 tests &middot; 51 modules &middot; 37 ADRs &middot; zero dependencies",
}

VOL2_TITLES = {
    "title": "10,000,000&times; AI ENGINEERING",
    "sub1": "Volume II &mdash; The Platform and the Factory",
    "sub2": "From Multi-Agent Platform to Autonomous Capability Factory &middot; the System at v7.0.0",
    "vol": "131 tests &middot; 26 modules &middot; zero dependencies",
}


def build_volume(parts_dir: str, parts: list[str], vol_titles: dict,
                 out_slug: str) -> dict:
    chunks = []
    for i, name in enumerate(parts):
        raw = (BOOK / parts_dir / name).read_text(encoding="utf-8").rstrip() + "\n"
        html = markdown.markdown(raw, extensions=["tables", "fenced_code", "sane_lists"])
        if i > 0:
            # class every structural h1 (PART / APPENDICES), not just the first
            html = re.sub(r"^<h1>(?=(PART |APPENDICES))", '<h1 class="part">',
                          html, flags=re.M)
        html = re.sub(r"^<h2([^>]*)>", r'<h2 class="chapter"\1>', html, flags=re.M)
        chunks.append(html)

    # attach ids + collect TOC entries by re-scanning with slugs
    body_parts, toc_items = [], []
    for html in chunks:
        def tag_id(m):
            level, attrs, inner = m.group(1), m.group(2), m.group(3)
            s = slug(re.sub(r"<[^>]+>", "", inner))
            text = re.sub(r"<[^>]+>", "", inner)
            if level == "1":
                toc_items.append((1, text, s))
            return f"<h{level}{attrs} id=\"{s}\">{inner}</h{level}>"
        html = re.sub(r"<h([12])([^>]*)>(.*?)</h\1>", tag_id, html, flags=re.S)
        body_parts.append(html)
    body = "\n\n".join(body_parts)

    toc_lines = ["<ul>"]
    for level, text, s in toc_items:
        toc_lines.append(f'<li><a href="#{s}">{text}</a></li>')
    toc_lines.append("</ul>")
    toc = f'<nav class="toc"><h2>Contents</h2>{"".join(toc_lines)}</nav>'

    t = vol_titles
    title_block = f"""
<header class="titleblock">
  <h1 class="book-title">{t["title"].replace(" ENGINEERING", "<br>ENGINEERING")}</h1>
  <p class="subtitle">{t["sub1"]}</p>
  <p class="subtitle">{t["sub2"]}</p>
  <p class="vol">{t["vol"]}</p>
</header>
"""

    words = len(re.sub(r"<[^>]+>", " ", body).split())
    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>10,000,000&times; AI Engineering &mdash; Volume I</title>
<style>{CSS}</style></head>
<body><div class="page">
{title_block}
{toc}
{body}
<p class="footnote">&mdash; end of Volume I &middot; {words:,} words &middot; generated from the aeos repository &mdash;</p>
</div></body></html>"""

    out = BOOK / "print" / f"{out_slug}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")
    md_out = BOOK / "print" / f"{out_slug}.md"
    md_out.write_text("\n\n---\n\n".join(
        (BOOK / parts_dir / n).read_text(encoding="utf-8") for n in parts), encoding="utf-8")
    print(f"[{out_slug}] HTML {out.stat().st_size//1024} KB | MD {md_out.stat().st_size//1024} KB | {words:,} words")
    return {"slug": out_slug, "words": words}


VOL1_TITLES = {
    "title": "10,000,000&times; AI ENGINEERING",
    "sub1": "Building Autonomous Engineering Systems That Build Systems",
    "sub2": "Context Engineering &middot; Harness Engineering &middot; Multi-Agent Systems &middot; Autonomous Capability Factories",
    "vol": "Volume I &mdash; The System v1.0.0 &middot; Built, Tested, Documented",
}

if __name__ == "__main__":
    build_volume("parts", PARTS, VOL1_TITLES, "volume-I")
    build_volume("parts-v2", VOL2_PARTS, VOL2_TITLES, "volume-II")
    build_volume("parts-v3", VOL3_PARTS, VOL3_TITLES, "volume-III")
