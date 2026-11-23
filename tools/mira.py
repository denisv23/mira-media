#!/usr/bin/env python3
"""Render Mira Instagram posts (1080x1350 PNG) and reels (1080x1920 MP4) from a JSON spec.

Usage:
  python3 tools/mira.py post  spec.json out.png
  python3 tools/mira.py reel  spec.json out.mp4

Spec (both): see tools/SPEC.md. Text wrapped in *asterisks* in a headline is drawn in the accent colour.
"""
import html, json, os, re, subprocess, sys, tempfile, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"

ICONS = {
    "chat": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/><path d="M8 10h8M8 14h5"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="m9 16 2 2 4-4"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "chart": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "lang": '<path d="m5 8 6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6"/>',
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
}

def esc(s):
    return html.escape(str(s or ""))

def accent(s):
    """*word* -> accent span; keeps everything else escaped."""
    out, parts = [], re.split(r"(\*[^*]+\*)", str(s or ""))
    for p in parts:
        if p.startswith("*") and p.endswith("*") and len(p) > 1:
            out.append(f'<span class="acc">{esc(p[1:-1])}</span>')
        else:
            out.append(esc(p))
    return "".join(out).replace("\n", "<br>")

def icon(name, cls="ic"):
    return f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS.get(name, ICONS["chat"])}</svg>'

# ---------- blocks ----------

def msg_html(m):
    frm = m.get("from", "client")
    t = f'<div class="time">{esc(m["time"])}</div>' if m.get("time") else ""
    if frm == "booked":
        return (f'<div class="bub booked"><div class="bk-t">{icon("check","ic-s")} {esc(m.get("title","U rezervua"))}</div>'
                f'<div>{esc(m.get("text",""))}</div></div>')
    if frm == "mira":
        return f'<div class="bub mira">{esc(m.get("text",""))}{t}</div>'
    return f'<div class="bub client">{esc(m.get("text",""))}{t}</div>'

def block_html(b, upto=None):
    """upto: for chat blocks, how many messages to show (reel reveal)."""
    t = b.get("type")
    if t == "spacer":
        return '<div class="spacer"></div>'
    if t == "big":
        return (f'<div class="big"><div class="big-n">{esc(b.get("text"))}</div>'
                f'<div class="big-side">{esc(b.get("side",""))}</div></div>')
    if t == "chat":
        msgs = b.get("messages", [])
        if upto is not None:
            msgs = msgs[:upto]
        return f'<div class="chat">{"".join(msg_html(m) for m in msgs)}</div>'
    if t == "cards":
        items = b.get("items", [])
        if upto is not None:
            items = items[:upto] + [{"_ghost": True}] * (len(items) - upto)
        cs = []
        for it in items:
            if it.get("_ghost"):
                cs.append('<div class="card ghost"></div>')
                continue
            cs.append(f'<div class="card">{icon(it.get("icon","chat"))}<div class="c-t">{esc(it.get("title"))}</div>'
                      f'<div class="c-x">{esc(it.get("text"))}</div></div>')
        return f'<div class="cards n{len(items)}">{"".join(cs)}</div>'
    if t == "list":
        rows = "".join(f'<div class="lrow"><span>{esc(a)}</span><span class="mono">{esc(c)}</span></div>' for a, c in b.get("rows", []))
        return f'<div class="list"><div class="l-t mono">{esc(b.get("title","LISTA JOTE"))}</div>{rows}</div>'
    if t == "notif":
        app = b.get("app", "telegram")
        ic = "send" if app == "telegram" else "chat"
        when = f'<div class="when mono">{esc(b["when"])}</div>' if b.get("when") else ""
        return (f'{when}<div class="notif"><div class="n-ic {app}">{icon(ic,"ic-w")}</div>'
                f'<div><div class="n-l">{esc(b.get("label",""))}</div><div class="n-x">{esc(b.get("text",""))}</div></div></div>')
    if t == "stats":
        badge = f'<span class="badge">{esc(b["badge"])}</span>' if b.get("badge") else ""
        rows = "".join(f'<div class="srow mono"><span>{esc(a)}</span><span class="{ "pos" if i==1 else "" }">{esc(c)}</span></div>'
                       for i, (a, c) in enumerate(b.get("rows", [])))
        when = f'<div class="when mono">{esc(b["when"])}</div>' if b.get("when") else ""
        return f'{when}<div class="stats"><div class="s-h"><b>{esc(b.get("title",""))}</b>{badge}</div>{rows}</div>'
    if t == "quote":
        return f'<div class="quote">{accent(b.get("text",""))}</div>'
    if t == "bar":
        return f'<div class="tgbar">{icon("send","ic-s")} <b>Telegram</b> · {esc(b.get("text",""))}</div>'
    raise ValueError(f"unknown block type {t}")

def units(spec):
    """Reveal units for a reel: list of (block_index, upto) states."""
    states = [(-1, None)]
    for i, b in enumerate(spec.get("blocks", [])):
        t = b.get("type")
        if t == "spacer":
            continue
        if t == "chat":
            for k in range(1, len(b.get("messages", [])) + 1):
                states.append((i, k))
        elif t == "cards":
            for k in range(1, len(b.get("items", [])) + 1):
                states.append((i, k))
        else:
            states.append((i, None))
    return states

# ---------- page ----------

def css(fmt, theme):
    fonts = f"""
@font-face{{font-family:Brico;src:url('{(FONTS/'bricolage-grotesque-latin-800-normal.woff2').as_uri()}');font-weight:800}}
@font-face{{font-family:Brico;src:url('{(FONTS/'bricolage-grotesque-latin-700-normal.woff2').as_uri()}');font-weight:700}}
@font-face{{font-family:Brico;src:url('{(FONTS/'bricolage-grotesque-latin-600-normal.woff2').as_uri()}');font-weight:600}}
@font-face{{font-family:Fig;src:url('{(FONTS/'figtree-latin-400-normal.woff2').as_uri()}');font-weight:400}}
@font-face{{font-family:Fig;src:url('{(FONTS/'figtree-latin-500-normal.woff2').as_uri()}');font-weight:500}}
@font-face{{font-family:Fig;src:url('{(FONTS/'figtree-latin-600-normal.woff2').as_uri()}');font-weight:600}}
@font-face{{font-family:Fig;src:url('{(FONTS/'figtree-latin-700-normal.woff2').as_uri()}');font-weight:700}}
@font-face{{font-family:JBM;src:url('{(FONTS/'jetbrains-mono-latin-400-normal.woff2').as_uri()}');font-weight:400}}
@font-face{{font-family:JBM;src:url('{(FONTS/'jetbrains-mono-latin-500-normal.woff2').as_uri()}');font-weight:500}}
"""
    if theme == "dark":
        pal = "--bg:#111614;--ink:#EEF0EC;--mut:#9BA39E;--acc:#FF5A6E;--card:#1A211E;--line:#2A322E;--cli:#242B28;--mira:#1F3A2C;--miraink:#EEF0EC;--ok:#4CC38A;"
    elif theme == "red":
        pal = "--bg:#C41230;--ink:#FFFFFF;--mut:#FFE1E5;--acc:#FFFFFF;--card:#FFFFFF;--line:#E35A6E;--cli:#FFFFFF;--mira:#FFFFFF;--miraink:#121A17;--ok:#1E7B45;"
    else:
        pal = "--bg:#F3F3F1;--ink:#121A17;--mut:#5D6461;--acc:#C8102E;--card:#FFFFFF;--line:#E2E3E0;--cli:#FFFFFF;--mira:#DFF0E6;--miraink:#121A17;--ok:#1E7B45;"
    s = 1.0 if fmt == "post" else 0.62  # reel uses a tighter, smaller type scale like the existing reels
    W, H = (1080, 1350) if fmt == "post" else (1080, 1920)
    pad_top = 80 if fmt == "post" else 280
    pad_bot = 80 if fmt == "post" else 430
    def px(v): return f"{round(v*s)}px"
    return fonts + f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;background:var(--bg)}}
:root{{{pal}}}
body{{font-family:Fig,sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased}}
.page{{width:{W}px;height:{H}px;padding:{pad_top}px 80px {pad_bot}px;display:flex;flex-direction:column}}
.mono{{font-family:JBM,monospace}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:{px(70)}}}
.brand{{font-family:Brico;font-weight:700;font-size:{px(40) if fmt=='post' else '40px'};display:flex;align-items:center;gap:14px;letter-spacing:-.01em}}
.dot{{width:22px;height:22px;border-radius:50%;background:var(--acc)}}
.num{{font-family:JBM;color:var(--mut);font-size:{px(28)}}}
h1{{font-family:Brico;font-weight:800;font-size:{px(104) if fmt=='post' else '72px'};line-height:{'0.98' if fmt=='post' else '1.05'};letter-spacing:-.035em}}
.acc{{color:var(--acc)}}
.sub{{font-size:{px(40) if fmt=='post' else '38px'};color:var(--mut);margin-top:{px(30) if fmt=='post' else '22px'};line-height:1.35}}
.body{{flex:1;display:flex;flex-direction:column;gap:{px(26) if fmt=='post' else '20px'};margin-top:{px(50) if fmt=='post' else '34px'}}}
.spacer{{flex:1}}
.big{{display:flex;align-items:flex-end;gap:30px}}
.big-n{{font-family:JBM;font-weight:500;color:var(--acc);font-size:{px(190) if fmt=='post' else '170px'};line-height:.9;letter-spacing:-.02em}}
.big-side{{color:var(--mut);font-size:{px(34) if fmt=='post' else '34px'};line-height:1.25;max-width:300px;padding-bottom:10px}}
.chat{{background:{'#1A211E' if theme=='dark' else '#E8E9E5'};border-radius:36px;padding:{px(36) if fmt=='post' else '30px'};display:flex;flex-direction:column;gap:{px(22) if fmt=='post' else '18px'};border:{'2px solid #2A322E' if theme=='dark' else 'none'}}}
.bub{{max-width:86%;padding:{px(24) if fmt=='post' else '22px'} {px(30) if fmt=='post' else '26px'};border-radius:26px;font-size:{px(31) if fmt=='post' else '33px'};line-height:1.32}}
.client{{background:var(--cli);align-self:flex-start;color:var(--ink)}}
.mira{{background:var(--mira);align-self:flex-end;color:var(--miraink)}}
.booked{{background:var(--mira);align-self:flex-end;color:var(--miraink)}}
.bk-t{{color:var(--ok);font-weight:700;display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.time{{font-family:JBM;font-size:22px;color:var(--mut);text-align:right;margin-top:10px}}
.cards{{display:grid;gap:{px(26)};grid-template-columns:repeat(3,1fr)}}
.cards.n2{{grid-template-columns:repeat(2,1fr)}} .cards.n1{{grid-template-columns:1fr}} .cards.n4{{grid-template-columns:repeat(2,1fr)}}
.card{{background:var(--card);border:2px solid var(--line);border-radius:32px;padding:{px(32) if fmt=='post' else '28px'};min-height:{px(330) if fmt=='post' else '250px'}}}
.card.ghost{{background:transparent;border:2px dashed transparent}}
.ic{{width:{px(54)};height:{px(54)};color:var(--acc);stroke-width:2}}
.ic-s{{width:28px;height:28px}} .ic-w{{width:34px;height:34px;color:#fff}}
.c-t{{font-family:Brico;font-weight:800;font-size:{px(38) if fmt=='post' else '36px'};margin:{px(28)} 0 {px(14)};letter-spacing:-.01em}}
.c-x{{color:var(--mut);font-size:{px(30) if fmt=='post' else '29px'};line-height:1.3}}
.list{{background:var(--card);border-radius:30px;padding:{px(34) if fmt=='post' else '30px'};display:flex;flex-direction:column;gap:6px}}
.l-t{{font-size:22px;color:var(--mut);letter-spacing:.12em;margin-bottom:10px}}
.lrow{{display:flex;justify-content:space-between;font-size:{px(32) if fmt=='post' else '31px'};padding:14px 0;border-bottom:2px solid var(--line)}}
.lrow:last-child{{border-bottom:none}}
.when{{font-size:{px(26) if fmt=='post' else '26px'};color:var(--mut);margin-bottom:-6px}}
.notif{{background:var(--card);border:2px solid var(--line);border-radius:28px;padding:26px 28px;display:flex;gap:22px;align-items:flex-start}}
.n-ic{{width:64px;height:64px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center}}
.n-ic.telegram{{background:#2AA3E0}} .n-ic.whatsapp{{background:#1E7B45;border-radius:16px}}
.n-l{{font-size:24px;color:var(--mut);margin-bottom:6px}}
.n-x{{font-size:{px(31) if fmt=='post' else '31px'};line-height:1.32}}
.stats{{background:var(--card);border:2px solid var(--line);border-radius:28px;padding:28px 30px}}
.s-h{{display:flex;justify-content:space-between;align-items:center;font-size:30px;padding-bottom:18px;border-bottom:2px solid var(--line);margin-bottom:10px}}
.badge{{font-family:JBM;font-size:18px;background:#FBE3E7;color:#C8102E;padding:6px 12px;border-radius:20px}}
.srow{{display:flex;justify-content:space-between;font-size:30px;padding:12px 0}}
.pos{{color:var(--ok)}}
.quote{{font-family:Brico;font-weight:700;font-size:{px(64) if fmt=='post' else '64px'};line-height:1.08;letter-spacing:-.025em}}
.tgbar{{background:#121A17;color:#fff;border-radius:22px;padding:20px 26px;font-size:26px;display:flex;align-items:center;gap:12px}}
.foot{{display:flex;justify-content:space-between;align-items:center;border-top:2px solid var(--line);padding-top:{px(40)};margin-top:{px(40)};font-size:{px(29)};color:var(--mut)}}
.foot b{{color:var(--acc);font-weight:700;font-size:{px(31)}}}
/* red CTA end card */
.cta{{width:{W}px;height:{H}px;background:#C41230;color:#fff;padding:330px 90px 430px;display:flex;flex-direction:column;justify-content:center}}
.cta .brand{{color:#fff;margin-bottom:auto}} .cta .dot{{background:#fff}}
.cta h2{{font-family:Brico;font-weight:800;font-size:{'96px' if fmt=='reel' else '92px'};line-height:1.02;letter-spacing:-.03em}}
.pill{{display:inline-block;background:#fff;color:#C41230;font-weight:700;font-size:40px;padding:22px 42px;border-radius:60px;margin-top:56px;align-self:flex-start}}
.cta .note{{font-size:36px;font-weight:600;margin-top:34px;margin-bottom:auto}}
"""

def page_html(spec, fmt, state=None):
    theme = spec.get("theme", "light")
    num = f'<div class="num">{esc(spec["num"])}</div>' if spec.get("num") else "<div></div>"
    blocks = spec.get("blocks", [])
    body = []
    if state is not None:
        bi, upto = state
        for i, b in enumerate(blocks):
            if b.get("type") == "spacer":
                body.append(block_html(b)); continue
            if i < bi: body.append(block_html(b))
            elif i == bi: body.append(block_html(b, upto))
            else:
                # keep layout stable for cards (ghost), hide others
                if b.get("type") == "cards": body.append(block_html(b, 0))
    else:
        body = [block_html(b) for b in blocks]
    foot = ""
    if fmt == "post" and spec.get("footer"):
        l, r = (spec["footer"] + ["", ""])[:2]
        foot = f'<div class="foot"><span>{esc(l)}</span><b>{esc(r)}</b></div>'
    sub = f'<div class="sub">{accent(spec["sub"])}</div>' if spec.get("sub") else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css(fmt, theme)}</style></head><body>'
            f'<div class="page"><div class="top"><div class="brand"><span class="dot"></span>Mira</div>{num if fmt=="post" else "<div></div>"}</div>'
            f'<h1>{accent(spec.get("headline",""))}</h1>{sub}<div class="body">{"".join(body)}</div>{foot}</div></body></html>')

def cta_html(spec, fmt):
    c = spec.get("cta", {})
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css(fmt, "red")}</style></head><body>'
            f'<div class="cta"><div class="brand"><span class="dot"></span>Mira</div>'
            f'<h2>{accent(c.get("headline","Kush përgjigjet i pari, e merr klientin."))}</h2>'
            f'<div class="pill">{esc(c.get("pill","Provojeni falas për 14 ditë"))}</div>'
            f'<div class="note">{esc(c.get("note","Më shkruani MIRA në DM"))}</div></div></body></html>')

def shoot(pages, size, outdir):
    from playwright.sync_api import sync_playwright
    paths = []
    with sync_playwright() as p:
        kw = {}
        if not shutil.which("chromium") and Path("/usr/bin/google-chrome").exists():
            kw["executable_path"] = "/usr/bin/google-chrome"
        try:
            br = p.chromium.launch(**kw)
        except Exception:
            br = p.chromium.launch()
        pg = br.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=1)
        for i, h in enumerate(pages):
            f = Path(outdir) / f"f{i:03d}.html"
            f.write_text(h, encoding="utf-8")
            pg.goto(f.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            # auto-fit: shrink body/headline until nothing overflows the frame
            z = pg.evaluate("""() => {
              const page = document.querySelector('.page'); if (!page) return 1;
              const H = window.innerHeight; let z = 1;
              const over = () => [...page.children].some(c => c.getBoundingClientRect().bottom > H - 40) || page.scrollHeight > H;
              while (over() && z > 0.62) { z -= 0.03;
                for (const s of ['.body', 'h1', '.sub', '.foot']) { const e = document.querySelector(s); if (e) e.style.zoom = z; } }
              return over() ? -z : z; }""")
            if z < 0:
                print(f"WARNING: {f.name} still overflows at zoom {-z:.2f} — shorten the text", file=sys.stderr)
            elif z < 0.9:
                print(f"note: {f.name} auto-shrunk to {z:.2f} — consider less text", file=sys.stderr)
            out = Path(outdir) / f"f{i:03d}.png"
            pg.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": size[0], "height": size[1]})
            paths.append(out)
        br.close()
    return paths

def render_post(spec, out):
    with tempfile.TemporaryDirectory() as td:
        [png] = shoot([page_html(spec, "post")], (1080, 1350), td)
        shutil.copy(png, out)

def render_reel(spec, out):
    states = units(spec)
    pages = [page_html(spec, "reel", s) for s in states] + [cta_html(spec, "reel")]
    first, step, last_hold, cta_hold, xf = 1.6, 1.5, 2.2, 3.4, 0.3
    durs = [first] + [step] * (len(states) - 2) + [last_hold] + [cta_hold]
    if len(states) == 1:
        durs = [first + last_hold, cta_hold]
    with tempfile.TemporaryDirectory() as td:
        pngs = shoot(pages, (1080, 1920), td)
        inputs, filt = [], []
        for i, (p, d) in enumerate(zip(pngs, durs)):
            inputs += ["-loop", "1", "-t", f"{d + xf:.2f}", "-i", str(p)]
            filt.append(f"[{i}:v]fps=30,format=yuv420p,setsar=1[v{i}]")
        prev, t = "v0", durs[0]
        for i in range(1, len(pngs)):
            filt.append(f"[{prev}][v{i}]xfade=transition=fade:duration={xf}:offset={t - 0:.2f}[x{i}]")
            prev, t = f"x{i}", t + durs[i]
        total = sum(durs) + xf
        cmd = ["ffmpeg", "-v", "error", "-y", *inputs,
               "-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo",
               "-filter_complex", ";".join(filt), "-map", f"[{prev}]", "-map", f"{len(pngs)}:a",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
               "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    kind, spec_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    (render_post if kind == "post" else render_reel)(spec, out)
    print(out)
