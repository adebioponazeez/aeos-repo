"""Build the AEOS trilogy as PDFs in the Operator's Codex design.

Design tokens extracted from The-Operators-Codex-v2.pdf:
  paper  #FAF9F7 · ink #1A1E28 · dark panel #0A0E17 · navy #16202F
  muted #5C6577 · pale label #BBC1CC · gold #C9A327 · gold-dark #8A6D1A
  gold-light #E0C98A · slate rule #DFE0E8
  DejaVu Serif body (9pt) + DejaVu Sans headings, letterspaced caps
  kickers, gold hairlines, diamond separators, roman edition marks.
Run: python book/build_pdf.py   ->  book/print/volume-{I,II,III}.pdf
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BOOK = Path(__file__).resolve().parent
sys.path.insert(0, str(BOOK))
from build_book import (PARTS, VOL1_TITLES, VOL2_PARTS, VOL2_TITLES,
                        VOL3_PARTS, VOL3_TITLES)

import markdown
from weasyprint import HTML

CSS = """
@page {
  size: A4;
  margin: 66pt 58pt 64pt 58pt;
  background: #FAF9F7;
  @top-center {
    content: string(chap, first);
    font-family: "DejaVu Sans"; font-size: 6.6pt; letter-spacing: 0.32em;
    color: #5C6577; text-transform: uppercase;
    border-bottom: 0.5pt solid #DFE0E8; padding-bottom: 5pt;
    margin-bottom: 14pt; width: 100%;
  }
  @bottom-center {
    content: "\\25C6\\2004" counter(page) "\\2004\\25C6";
    font-family: "DejaVu Sans"; font-size: 7pt; color: #C9A327;
    letter-spacing: 0.2em;
  }
}
@page cover { margin: 0; background: #0A0E17; @top-center { content: none } @bottom-center { content: none } }
@page plain { @top-center { content: none } @bottom-center { content: none } }

html { font-size: 9pt; }
body { font-family: "DejaVu Serif"; color: #1A1E28; line-height: 1.58;
       font-size: 9pt; text-align: justify; hyphens: auto; }

/* ---------------- cover ---------------- */
section.cover { page: cover; width: 100%; height: 100%;
  color: #FAF9F7; position: relative; }
.cover-inner { padding: 74pt 62pt; }
.edition { font-family: "DejaVu Sans"; font-size: 7.5pt;
  letter-spacing: 0.5em; color: #BBC1CC; text-transform: uppercase; }
.edition b { color: #C9A327; font-weight: bold; }
.goldline { border: none; border-top: 0.8pt solid #C9A327; margin: 16pt 0; }
.motto { font-family: "DejaVu Sans"; font-size: 8pt; letter-spacing: 0.42em;
  color: #C9A327; text-transform: uppercase; margin-top: 14pt; }
.process { font-family: "DejaVu Sans"; font-size: 7pt; letter-spacing: 0.3em;
  color: #BBC1CC; text-transform: uppercase; margin-top: 8pt; }
.bigmark { position: absolute; top: 210pt; right: 34pt;
  font-family: "DejaVu Serif"; font-weight: bold; font-size: 240pt;
  color: #16202F; line-height: 1; }
.book-title { font-family: "DejaVu Serif"; font-weight: bold;
  font-size: 33pt; line-height: 1.18; color: #FAF9F7; margin: 40pt 0 0 0;
  text-align: left; letter-spacing: 0.01em; }
.cover-sub { font-family: "DejaVu Serif"; font-style: oblique;
  font-size: 12.5pt; color: #BBC1CC; margin-top: 18pt; text-align: left; }
.cover-sub2 { font-family: "DejaVu Sans"; font-size: 8pt;
  letter-spacing: 0.26em; color: #BBC1CC; text-transform: uppercase;
  margin-top: 12pt; text-align: left; line-height: 1.9; }
.sealrow { margin-top: 46pt; }
.seal { display: inline-block; width: 34pt; height: 34pt;
  border: 1pt solid #C9A327; color: #C9A327; text-align: center;
  line-height: 34pt; font-family: "DejaVu Sans"; font-size: 8pt;
  letter-spacing: 0.14em; transform: rotate(45deg); }
.sealwrap { display: inline-block; margin-right: 26pt; }
.sealtxt { display: inline-block; vertical-align: 16pt;
  font-family: "DejaVu Sans"; font-size: 7pt; letter-spacing: 0.3em;
  color: #BBC1CC; text-transform: uppercase; }
.pressline { position: absolute; bottom: 58pt; left: 62pt; right: 62pt;
  font-family: "DejaVu Sans"; font-size: 7pt; letter-spacing: 0.45em;
  color: #BBC1CC; text-transform: uppercase; text-align: center; }

/* ---------------- front matter ---------------- */
section.front { page: plain; page-break-before: always; }
.kicker { font-family: "DejaVu Sans"; font-size: 7.5pt;
  letter-spacing: 0.4em; color: #C9A327; text-transform: uppercase;
  margin: 0 0 10pt 0; }
.front h2 { font-family: "DejaVu Sans"; font-weight: bold; font-size: 15pt;
  color: #0A0E17; letter-spacing: 0.06em; text-transform: uppercase;
  border-bottom: 0.8pt solid #C9A327; padding-bottom: 8pt; margin: 0 0 14pt 0;
  text-align: left; }
.front p { font-size: 9pt; }
.toc { font-family: "DejaVu Sans"; font-size: 8pt; color: #1A1E28; }
.toc a { color: #1A1E28; text-decoration: none; }
.toc .l1 { margin: 7pt 0 2pt 0; font-weight: bold; font-size: 8.4pt;
  text-transform: uppercase; letter-spacing: 0.05em; }
.toc .l2 { margin: 2pt 0 2pt 14pt; color: #5C6577; font-size: 7.6pt; }
.toc a::after { content: leader(". ") target-counter(attr(href), page);
  color: #8A6D1A; font-weight: normal; }

/* ---------------- chapters ---------------- */
section.body { page-break-before: always; }
h2 { string-set: chap content(); font-family: "DejaVu Sans";
  font-weight: bold; font-size: 15pt; color: #0A0E17;
  text-transform: uppercase; letter-spacing: 0.05em; text-align: left;
  margin: 4pt 0 4pt 0; page-break-before: always;
  page-break-after: avoid; }
h2:first-of-type { page-break-before: avoid; }
.h2bar { border-top: 1.4pt solid #C9A327; width: 52pt; margin: 0 0 8pt 0; }
h3 { font-family: "DejaVu Serif"; font-weight: bold; font-size: 11pt;
  color: #16202F; margin: 16pt 0 6pt 0; page-break-after: avoid;
  text-align: left; }
h4 { font-family: "DejaVu Sans"; font-weight: bold; font-size: 8.4pt;
  color: #8A6D1A; text-transform: uppercase; letter-spacing: 0.18em;
  margin: 13pt 0 5pt 0; page-break-after: avoid; text-align: left; }
p { margin: 0 0 7.5pt 0; }
strong { color: #0A0E17; }
em { color: #16202F; }
a { color: #8A6D1A; text-decoration: none; }

blockquote { margin: 10pt 0; padding: 8pt 12pt;
  border-left: 1.6pt solid #C9A327; background: #FFFFFF;
  border-top: 0.5pt solid #DFE0E8; border-bottom: 0.5pt solid #DFE0E8;
  border-right: 0.5pt solid #DFE0E8; }
blockquote p { margin: 0 0 4pt 0; font-style: oblique; color: #16202F; }

pre { background: #16202F; color: #BBC1CC; padding: 9pt 11pt;
  font-family: "DejaVu Sans Mono"; font-size: 7.4pt; line-height: 1.5;
  white-space: pre-wrap; margin: 9pt 0; text-align: left;
  border-top: 1pt solid #C9A327; }
code { font-family: "DejaVu Sans Mono"; font-size: 7.6pt;
  background: #E0C98A; color: #0A0E17; padding: 0 2pt; }
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }

ul, ol { margin: 6pt 0 8pt 0; padding-left: 16pt; }
li { margin-bottom: 3pt; }

table { width: 100%; border-collapse: collapse; margin: 10pt 0;
  font-family: "DejaVu Sans"; font-size: 7.4pt; }
th { font-weight: bold; text-transform: uppercase; letter-spacing: 0.1em;
  color: #8A6D1A; border-bottom: 1pt solid #C9A327; padding: 4pt 5pt;
  text-align: left; }
td { border-bottom: 0.5pt solid #DFE0E8; padding: 4pt 5pt;
  vertical-align: top; color: #1A1E28; }

hr { border: none; text-align: center; margin: 14pt 0; }
hr::after { content: "\\25C6"; color: #C9A327; font-size: 9pt; }

.footnote { font-family: "DejaVu Sans"; font-size: 7pt; color: #5C6577;
  letter-spacing: 0.22em; text-transform: uppercase; text-align: center;
  margin-top: 20pt; }
"""

ROMAN = {"volume-I": "I", "volume-II": "II", "volume-III": "III"}
MARKS = {"volume-I": "PRIMA", "volume-II": "SECUNDA", "volume-III": "TERTIA"}


def slug(text: str) -> str:
    t = re.sub(r"<[^>]+>", "", text)
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return t[:60] or "sec"


def convert(parts_dir: str, parts: list) -> tuple:
    body, heads = [], []
    for name in parts:
        raw = (BOOK / parts_dir / name).read_text(encoding="utf-8")
        html = markdown.markdown(raw, extensions=["tables", "fenced_code",
                                                  "sane_lists"])
        body.append(html)

    def h2_id(m):
        sid = slug(m.group(1))
        heads.append(("l1", m.group(1), sid))
        return f'<h2 id="{sid}"><span class="h2bar"></span>{m.group(1)}</h2>'

    def h3_id(m):
        sid = slug(m.group(1))
        heads.append(("l2", m.group(1), sid))
        return f'<h3 id="{sid}">{m.group(1)}</h3>'

    text = "\n".join(body)
    text = re.sub(r"<h2>(.*?)</h2>", h2_id, text, flags=re.S)
    text = re.sub(r"<h3>(.*?)</h3>", h3_id, text, flags=re.S)
    # strip the inline title block (cover carries it) but keep chapters
    return text, heads


def cover_html(slug_vol: str, t: dict, words: int) -> str:
    r = ROMAN[slug_vol]
    clean = {k: re.sub(r"&[a-z]+;", " ", v) for k, v in t.items()}
    return f"""
<section class="cover"><div class="cover-inner">
  <p class="edition">AEOS &nbsp;&middot;&nbsp; HARNESS IS THE PRODUCT
    &nbsp;&nbsp; <b>&#9670;</b> &nbsp;&nbsp; STORM PRINTING &nbsp;
    <b>V&nbsp;27</b></p>
  <hr class="goldline">
  <p class="motto">TRIA VOLUMINA &middot; UNA LEX &middot; EVIDENTIA AUT SILENTIUM</p>
  <p class="process">BUILD &middot; TEST &middot; PROVE &middot; DOCUMENT &middot; SHIP</p>
  <div class="bigmark">{r}</div>
  <h1 class="book-title">{clean["title"].replace(" ENGINEERING", "<br>ENGINEERING")}</h1>
  <p class="cover-sub">{clean["sub1"]}</p>
  <p class="cover-sub2">{clean["sub2"]}</p>
  <div class="sealrow">
    <span class="sealwrap"><span class="seal">AEOS</span></span>
    <span class="sealtxt">VOLUMEN {r} &middot; {MARKS[slug_vol]} &middot;
      {words:,} VERBA &middot; ZERO DEPENDENTIAE</span>
  </div>
  <p class="pressline">EDITIO PRINCEPS &middot; AEOS PRESS &middot; MMXXVI
    &nbsp; &#9670; &nbsp; OPERA {MARKS[slug_vol]}</p>
</div></section>
"""


def front_html(slug_vol: str, heads: list) -> str:
    r = ROMAN[slug_vol]
    toc = "".join(
        f'<div class="{lvl}"><a href="#{sid}">{txt}</a></div>'
        for lvl, txt, sid in heads if lvl == "l1")
    return f"""
<section class="front">
  <p class="kicker">HOW TO READ THIS CODEX &nbsp;&#9670;&nbsp; VOLUMEN {r}</p>
  <h2>This is not a guide. This is a receipt.</h2>
  <p>A guide tells you what exists. A codex tells you what was <em>built</em>,
  in what order, with what proof, and how you can verify every claim with
  your own hands. Nothing in these pages is a proposal — every mechanism
  ships in the aeos repository, every property ends in the name of the test
  that enforces it, and the whole system runs offline with zero runtime
  dependencies.</p>
  <p>Read it as an operator: run the proofs, then read the law.</p>
  <pre>pip install -e .        # zero runtime dependencies
python -m pytest        # 426 proofs, chaos storm included
aeos run-demo           # the whole OS, end to end
aeos storm              # the nuclear receipt: 9/9 scenarios survive</pre>
  <p class="kicker" style="margin-top:26pt">INDEX OPERUM</p>
  <h2>Contents</h2>
  <div class="toc">{toc}</div>
</section>
"""


def build_pdf(parts_dir: str, parts: list, titles: dict, slug_vol: str) -> Path:
    body, heads = convert(parts_dir, parts)
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>AEOS — Volume {ROMAN[slug_vol]}</title>
<style>{CSS}</style></head><body>
{cover_html(slug_vol, titles, words)}
{front_html(slug_vol, heads)}
<section class="body">
{body}
<p class="footnote">&#9670; &nbsp; END OF VOLUME {ROMAN[slug_vol]} &middot;
{words:,} WORDS &middot; GENERATED FROM THE AEOS REPOSITORY &nbsp; &#9670;</p>
</section></body></html>"""
    out = BOOK / "print" / f"{slug_vol}.pdf"
    HTML(string=doc, base_url=str(BOOK)).write_pdf(out)
    print(f"[{slug_vol}.pdf] {out.stat().st_size // 1024} KB | {words:,} words")
    return out


if __name__ == "__main__":
    build_pdf("parts", PARTS, VOL1_TITLES, "volume-I")
    build_pdf("parts-v2", VOL2_PARTS, VOL2_TITLES, "volume-II")
    build_pdf("parts-v3", VOL3_PARTS, VOL3_TITLES, "volume-III")
