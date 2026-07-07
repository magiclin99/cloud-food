# -*- coding: utf-8 -*-
import os, sys, html, re
sys.path.insert(0, os.path.dirname(__file__))
from outline_data import NODES

REPO = "/home/user/cloud-food"
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"

def verse_path(book, ch, vs):
    return os.path.join(REPO, "verses", book, f"{book}_{ch:02d}_{vs:02d}.md")

def load_verse(book, ch, vs):
    p = verse_path(book, ch, vs)
    if not os.path.exists(p):
        return None
    lines = open(p, encoding="utf-8").read().splitlines()
    body = []
    for ln in lines:
        if ln.startswith(">"):
            body.append(ln[1:].strip())
        elif ln.strip() == "---":
            break
    text = "".join(body)
    text = "".join(c for c in text if c not in SUP)  # 去除註解上標
    return text.strip()

# 驗證所有引用皆可解析
missing = []
for n in NODES:
    for (b, c, v) in n["refs"]:
        if load_verse(b, c, v) is None:
            missing.append((n["label"], b, c, v))
if missing:
    print("MISSING VERSES:")
    for m in missing:
        print("  ", m)
    sys.exit(1)
print("All %d verse references resolved." %
      sum(len(n["refs"]) for n in NODES))

# ── 產生 HTML ──────────────────────────────────────────
def esc(s):
    return html.escape(s)

def ref_label(b, c, v):
    return f"{b} {c}:{v}"

parts = []
for n in NODES:
    lv, label, text = n["level"], n["label"], n["text"]
    if lv == "title":
        parts.append(f'<div class="doc-title">{esc(text)}</div>')
        continue
    if lv == "total":
        parts.append(f'<div class="doc-total">{esc(text)}</div>')
        continue
    if lv == "pian":
        parts.append(f'<div class="doc-pian">{esc(text)}</div>')
        continue
    if lv == "subject":
        parts.append(f'<div class="doc-subject">{esc(text)}</div>')
        continue
    if lv == "reading":
        parts.append(f'<div class="reading"><span class="rd-label">{esc(label)}</span>{esc(text)}</div>')
    else:
        cls = {"p1": "lvl1", "p2": "lvl2", "p3": "lvl3"}[lv]
        parts.append(
            f'<div class="pt {cls}"><span class="num">{esc(label)}</span>'
            f'<span class="body">{esc(text)}</span></div>')
    # 經文區塊
    if n["refs"]:
        rows = []
        for (b, c, v) in n["refs"]:
            vt = load_verse(b, c, v)
            rows.append(
                f'<div class="v"><span class="vref">{esc(ref_label(b,c,v))}</span>'
                f'<span class="vtext">{esc(vt)}</span></div>')
        cls2 = {"reading": "vb-reading", "p1": "vb1", "p2": "vb2", "p3": "vb3"}[lv]
        parts.append(f'<div class="verses {cls2}">' + "".join(rows) + "</div>")

body_html = "\n".join(parts)

HTML = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<style>
@page {{ size: A4; margin: 18mm 16mm 16mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{
  font-family: "Noto Serif CJK TC", serif;
  color: #1a1a1a; line-height: 1.75; font-size: 11.5pt;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}}
.doc-title {{ text-align:center; font-size:12.5pt; margin-bottom:2mm; letter-spacing:.5px; }}
.doc-total {{ text-align:center; font-size:17pt; font-weight:700; margin:1mm 0; color:#7a1f1f; }}
.doc-pian  {{ text-align:center; font-size:13pt; margin-top:3mm; }}
.doc-subject {{ text-align:center; font-size:15pt; font-weight:700; margin:1mm 0 4mm; }}
.reading {{ font-size:10.5pt; margin:0 0 5mm; padding:2.5mm 3mm; background:#f4f1ea;
  border-left:3px solid #b08d57; border-radius:2px; line-height:1.7; }}
.rd-label {{ font-weight:700; }}
.pt {{ display:flex; margin-top:3mm; text-align:justify; }}
.pt .num {{ flex:0 0 auto; font-weight:700; }}
.pt .body {{ flex:1; }}
.lvl1 {{ font-weight:700; font-size:12pt; color:#5a1414; margin-top:6mm; }}
.lvl1 .num {{ width:8mm; }}
.lvl2 {{ margin-left:8mm; }}
.lvl2 .num {{ width:7mm; }}
.lvl3 {{ margin-left:16mm; }}
.lvl3 .num {{ width:6mm; }}
.verses {{ margin:1.5mm 0 1mm; border-left:2px solid #d8cdb3;
  background:#faf8f2; border-radius:2px; padding:1.5mm 3mm; }}
.vb-reading {{ margin-left:0; }}
.vb1 {{ margin-left:8mm; }}
.vb2 {{ margin-left:15mm; }}
.vb3 {{ margin-left:22mm; }}
.v {{ font-size:10.5pt; line-height:1.7; margin:.6mm 0; text-align:justify;
  text-indent:-6mm; padding-left:6mm; }}
.vref {{ display:inline-block; font-weight:700; color:#7a1f1f;
  margin-right:2mm; white-space:nowrap; }}
.vtext {{ color:#222; }}
</style></head>
<body>
{body}
</body></html>
""".format(body=body_html)

out = os.path.join(os.path.dirname(__file__), "outline.html")
open(out, "w", encoding="utf-8").write(HTML)
print("HTML written:", out)
