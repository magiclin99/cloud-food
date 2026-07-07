# -*- coding: utf-8 -*-
import os, sys, html
sys.path.insert(0, os.path.dirname(__file__))
from outline_data import NODES

REPO = "/home/user/cloud-food"
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"

def load_verse(book, ch, vs):
    p = os.path.join(REPO, "verses", book, f"{book}_{ch:02d}_{vs:02d}.md")
    if not os.path.exists(p):
        return None
    body = []
    for ln in open(p, encoding="utf-8").read().splitlines():
        if ln.startswith(">"):
            body.append(ln[1:].strip())
        elif ln.strip() == "---":
            break
    return "".join(c for c in "".join(body) if c not in SUP).strip()

def esc(s): return html.escape(s)

TOC = [("壹", "神心頭的願望與新的復興"),
       ("貳", "在燔祭中經歷基督的生活"),
       ("叁", "主耶穌—不從自己作甚麼"),
       ("肆", "住在神的愛裏活出愛的生活")]

def verses_block(refs, lvl):
    rows = []
    for (b, c, v) in refs:
        vt = load_verse(b, c, v)
        rows.append(
            f'<p class="v"><span class="vref">{esc(b)} <span class="num">{c}:{v}</span></span>'
            f'<span class="vtext">{esc(vt)}</span></p>')
    return f'<div class="verses vb-{lvl}">' + "".join(rows) + "</div>"

parts = []
for n in NODES:
    lv, label, text, refs = n["level"], n["label"], n["text"], n["refs"]
    vb = verses_block(refs, {"reading":"r","p1":"1","p2":"2","p3":"3"}.get(lv,"2")) if refs else ""
    if lv == "reading":
        parts.append(f'<div class="reading"><span class="rd-label">{esc(label)}</span>'
                     f'<span>{esc(text)}</span></div>{vb}')
    elif lv == "p1":
        anchor = f' id="pt-{label}"' if label in dict(TOC) else ""
        parts.append(f'<section class="pt lvl1"{anchor}><span class="mk">{esc(label)}</span>'
                     f'<div class="bd"><p class="tx">{esc(text)}</p>{vb}</div></section>')
    elif lv in ("p2", "p3"):
        cls = "lvl2" if lv == "p2" else "lvl3"
        parts.append(f'<div class="pt {cls}"><span class="mk">{esc(label)}</span>'
                     f'<div class="bd"><p class="tx">{esc(text)}</p>{vb}</div></div>')

body_html = "\n".join(parts)
toc_html = "".join(
    f'<a href="#pt-{k}"><b>{esc(k)}</b><span>{esc(t)}</span></a>' for k, t in TOC)

TPL = '''<title>綱要附經文 · 為着新的復興之神人的生活</title>
<style>
:root{
  --paper:#EFEBE0; --paper-2:#E7E1D3; --ink:#221E18; --ink-soft:#5b5342;
  --accent:#A83B2C; --accent-soft:#8a3325; --rule:#C6B385; --rule-soft:#d8cbab;
  --chip-bg:#e6ddc8; --band:#e9e3d5; --shadow:rgba(60,45,20,.10);
  --maxw:44rem;
  --serif:"Noto Serif CJK TC","Source Han Serif TC","Songti TC","Songti SC","STSong","Noto Serif TC",serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --paper:#181510; --paper-2:#201b14; --ink:#E9E3D5; --ink-soft:#b3a88f;
    --accent:#DB6A5B; --accent-soft:#c9584a; --rule:#5a4d34; --rule-soft:#463c29;
    --chip-bg:#2a2318; --band:#221d15; --shadow:rgba(0,0,0,.4);
  }
}
:root[data-theme="light"]{
  --paper:#EFEBE0; --paper-2:#E7E1D3; --ink:#221E18; --ink-soft:#5b5342;
  --accent:#A83B2C; --accent-soft:#8a3325; --rule:#C6B385; --rule-soft:#d8cbab;
  --chip-bg:#e6ddc8; --band:#e9e3d5; --shadow:rgba(60,45,20,.10);
}
:root[data-theme="dark"]{
  --paper:#181510; --paper-2:#201b14; --ink:#E9E3D5; --ink-soft:#b3a88f;
  --accent:#DB6A5B; --accent-soft:#c9584a; --rule:#5a4d34; --rule-soft:#463c29;
  --chip-bg:#2a2318; --band:#221d15; --shadow:rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:var(--serif);line-height:1.85;
  text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased;
  font-feature-settings:"palt" 1;}
.num{font-variant-numeric:tabular-nums;font-family:"Iowan Old Style",Georgia,serif;}

/* ── top bar ── */
.bar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--paper) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--rule-soft);}
.bar-in{max-width:var(--maxw);margin:0 auto;display:flex;align-items:center;gap:.75rem;
  padding:.55rem 1.15rem;}
.bar .seal{width:1.7rem;height:1.7rem;flex:0 0 auto;border-radius:4px;background:var(--accent);
  color:var(--paper);display:grid;place-items:center;font-size:.9rem;font-weight:700;
  box-shadow:0 1px 3px var(--shadow);}
.bar .t{font-size:.82rem;color:var(--ink-soft);letter-spacing:.04em;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;flex:1;}
.bar button{font-family:var(--serif);font-size:.76rem;color:var(--ink);cursor:pointer;
  background:var(--chip-bg);border:1px solid var(--rule-soft);border-radius:999px;
  padding:.3rem .7rem;white-space:nowrap;transition:.15s;}
.bar button:hover{border-color:var(--accent);color:var(--accent);}
.bar button:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}

.wrap{max-width:var(--maxw);margin:0 auto;padding:0 1.15rem 6rem;}

/* ── masthead ── */
header.mast{text-align:center;padding:3.2rem 0 1.6rem;}
.mast .eyebrow{font-size:.8rem;letter-spacing:.14em;color:var(--ink-soft);margin-bottom:1.1rem;}
.mast .total{font-size:clamp(1.9rem,6vw,2.7rem);font-weight:700;color:var(--accent);
  letter-spacing:.06em;margin:0;text-wrap:balance;line-height:1.3;}
.mast .pian{font-size:.95rem;color:var(--ink-soft);letter-spacing:.28em;margin:1.4rem 0 .4rem;}
.mast .subject{font-size:clamp(1.25rem,4vw,1.6rem);font-weight:700;margin:0;letter-spacing:.04em;
  text-wrap:balance;}
.rule-orn{display:flex;align-items:center;justify-content:center;gap:.8rem;margin:1.8rem 0 .4rem;
  color:var(--rule);}
.rule-orn::before,.rule-orn::after{content:"";height:1px;width:34%;
  background:linear-gradient(to var(--dir,right),transparent,var(--rule));}
.rule-orn::after{--dir:left;}
.rule-orn i{width:6px;height:6px;background:var(--accent);transform:rotate(45deg);flex:0 0 auto;}

/* ── toc ── */
nav.toc{display:grid;grid-template-columns:repeat(2,1fr);gap:.55rem;margin:1.7rem 0 .5rem;}
nav.toc a{display:flex;align-items:baseline;gap:.55rem;text-decoration:none;color:var(--ink);
  background:var(--paper-2);border:1px solid var(--rule-soft);border-radius:8px;
  padding:.6rem .8rem;transition:.15s;}
nav.toc a:hover{border-color:var(--accent);transform:translateY(-1px);}
nav.toc a b{color:var(--accent);font-size:1.05rem;flex:0 0 auto;}
nav.toc a span{font-size:.85rem;color:var(--ink-soft);line-height:1.4;}

/* ── reading verse of the message ── */
.reading{background:var(--band);border-left:3px solid var(--accent);border-radius:0 6px 6px 0;
  padding:.85rem 1.1rem;margin:1.4rem 0 .4rem;font-size:.92rem;line-height:1.8;color:var(--ink-soft);}
.reading .rd-label{color:var(--accent);font-weight:700;}

/* ── outline points ── */
.pt{display:flex;gap:.55rem;align-items:baseline;}
.pt .mk{flex:0 0 auto;font-weight:700;color:var(--accent);text-align:center;}
.pt .bd{flex:1;min-width:0;}
.pt .tx{margin:0;text-align:justify;text-justify:inter-character;}
section.lvl1{margin:2.6rem 0 0;padding-top:1.4rem;border-top:1px solid var(--rule-soft);}
.lvl1>.mk{width:1.7rem;font-size:1.35rem;}
.lvl1 .tx{font-size:1.12rem;font-weight:700;color:var(--ink);line-height:1.7;}
.lvl2{margin:1.15rem 0 0;padding-left:1.7rem;}
.lvl2>.mk{width:1.5rem;}
.lvl3{margin:.8rem 0 0;padding-left:3.4rem;}
.lvl3>.mk{width:1.4rem;color:var(--accent-soft);}

/* ── verses ── */
.verses{margin:.7rem 0 .2rem;border-left:2px solid var(--rule);
  background:color-mix(in srgb,var(--paper-2) 60%,transparent);
  border-radius:0 5px 5px 0;padding:.45rem .2rem .45rem .9rem;}
.v{margin:.32rem 0;font-size:.9rem;line-height:1.75;text-indent:-3.6rem;padding-left:3.6rem;
  text-align:justify;}
.vref{display:inline-block;color:var(--accent);font-weight:700;margin-right:.5rem;
  white-space:nowrap;}
.vtext{color:var(--ink);opacity:.92;}
.vb-r{margin-left:0;}

/* collapse toggle */
body.hide-verses .verses{display:none;}
body.hide-verses .reading{margin-bottom:1rem;}

footer{max-width:var(--maxw);margin:0 auto;padding:2.5rem 1.15rem 3rem;text-align:center;
  color:var(--ink-soft);font-size:.8rem;border-top:1px solid var(--rule-soft);}
footer a{color:var(--accent);text-decoration:none;}
@media (prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}}
html{scroll-behavior:smooth;}
:target{scroll-margin-top:4rem;}
@media(max-width:520px){nav.toc{grid-template-columns:1fr;}
  .lvl2{padding-left:1.2rem;} .lvl3{padding-left:2.4rem;}
  .v{text-indent:-3.2rem;padding-left:3.2rem;}}
</style>

<div class="bar">
  <div class="bar-in">
    <span class="seal">祭</span>
    <span class="t">國殤節國際相調特會 · 第三篇</span>
    <button id="tg" aria-pressed="false">只看綱要</button>
    <button id="th" title="切換深淺色">☾</button>
  </div>
</div>

<div class="wrap">
  <header class="mast">
    <div class="eyebrow">二〇二六年五月二十二至二十五日 · 國殤節國際相調特會信息綱目</div>
    <p class="total">極其需要新的復興</p>
    <div class="pian">第 三 篇</div>
    <h1 class="subject">為着新的復興之神人的生活</h1>
    <div class="rule-orn"><i></i></div>
    <nav class="toc">__TOC__</nav>
  </header>
__BODY__
</div>
<footer>
  綱要附經文 · 經文採<b>恢復本聖經</b>本文，逐節列於各項綱要之下（共 204 節）。<br>
  © 2026 Living Stream Ministry · 綱要版權屬原出版者所有。
</footer>
<script>
(function(){
  var root=document.documentElement;
  var th=document.getElementById("th");
  function cur(){return root.getAttribute("data-theme")||
     (matchMedia("(prefers-color-scheme:dark)").matches?"dark":"light");}
  function paint(){th.textContent=cur()==="dark"?"☀":"☾";}
  th.addEventListener("click",function(){
    root.setAttribute("data-theme",cur()==="dark"?"light":"dark");paint();});
  matchMedia("(prefers-color-scheme:dark)").addEventListener("change",paint);paint();

  var tg=document.getElementById("tg");
  tg.addEventListener("click",function(){
    var on=document.body.classList.toggle("hide-verses");
    tg.setAttribute("aria-pressed",String(on));
    tg.textContent=on?"綱要附經文":"只看綱要";});
})();
</script>
'''

out_html = TPL.replace("__TOC__", toc_html).replace("__BODY__", body_html)
outp = os.path.join(os.path.dirname(__file__), "outline_web.html")
open(outp, "w", encoding="utf-8").write(out_html)
print("wrote", outp, len(out_html), "bytes")
