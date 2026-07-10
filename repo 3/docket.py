#!/usr/bin/env python3
"""
DAILY DOCKET renderer.

The Docket is not analysis. It reports what was filed, quotes the agency's own
words, and links to the document. Minimal writing means minimal room to invent.
The scout agent appends to data/docket.json every morning; this renders it.

Outputs:
  site/docket.html        the full feed
  data/_rail.html         the homepage sidebar fragment (injected by build.py)
"""
import json, html
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
D = json.loads((ROOT / "data" / "docket.json").read_text())
E = sorted(D["entries"], key=lambda x: x["date"], reverse=True)

# GATE: an entry without a verification record does not render. A quote nobody
# checked is indistinguishable from a quote nobody wrote down correctly.
_unverified = [e["id"] for e in E if not e.get("verified", {}).get("method")]
if _unverified:
    raise SystemExit(
        f"\nFATAL: {len(_unverified)} docket entries carry no verification record: "
        f"{', '.join(_unverified)}\nEvery published quote must record how it was checked. Build halted.\n")


def esc(s):
    return html.escape(s or "")


def pretty(iso):
    y, m, d = map(int, iso.split("-"))
    return date(y, m, d).strftime("%b %-d, %Y")


def longdate(iso):
    y, m, d = map(int, iso.split("-"))
    return date(y, m, d).strftime("%A, %B %-d, %Y").upper()


# ── homepage rail ────────────────────────────────────────────────────────────
rail_items = "".join(
    f'''<a class="dk-item" href="{esc(e["url"])}" target="_blank" rel="noopener">
      <div class="dk-top">
        <span class="dk-ag">{esc(e["agency"])}</span>
        <span class="dk-dt">{pretty(e["date"])}</span>
        <span class="dk-ty">{esc(e["type"])}</span>
        {'<span class="dk-watch">watching</span>' if e.get("flag") == "watching" else ''}
      </div>
      <div class="dk-t verbatim">{esc(e["title"])}</div>
      <div class="dk-q verbatim">{esc(e["quote"][:175])}{'…' if len(e["quote"]) > 175 else ''}</div>
      <div class="dk-w">{esc(e["why"])}</div>
    </a>''' for e in E[:5])

RAIL = f'''<aside class="rail">
  <div class="docket">
    <div class="dk-h">
      <span>daily_docket</span>
      <span class="live"><i></i>updated {pretty(E[0]["date"])}</span>
    </div>
    {rail_items}
    <div class="dk-f">
      Filed documents only. Quoted verbatim. Never summarized.<br>
      <span class="killed">{len(D["screened_out"])} screened out</span>{f' · <span style="color:#C89A4A">{len(D.get("held",[]))} held, source unreachable</span>' if D.get("held") else ''}<br>
      <a href="docket.html">→ Full docket ({len(E)} filings)</a>
    </div>
  </div>
</aside>'''

(ROOT / "data" / "_rail.html").write_text(RAIL)

# ── full docket page ─────────────────────────────────────────────────────────
by_day = defaultdict(list)
for e in E:
    by_day[e["date"]].append(e)

days = ""
for d in sorted(by_day, reverse=True):
    rows = "".join(
        f'''<a class="dkrow" href="{esc(e["url"])}" target="_blank" rel="noopener">
        <div class="top">
          <span class="ag">{esc(e["agency"])}</span>
          <span class="ty">{esc(e["type"])}</span>
          <span class="dt">FR {esc(e["id"])}</span>
          {'<span class="wt">watching</span>' if e.get("flag") == "watching" else ''}
        </div>
        <h3 class="verbatim">{esc(e["title"])}</h3>
        <blockquote class="verbatim">"{esc(e["quote"])}"</blockquote>
        <div class="wy">{esc(e["why"])}</div>
        <div class="lk">→ {esc(e["agency_full"])} · Read the filing on federalregister.gov</div>
      </a>''' for e in by_day[d])
    days += f'<div class="dkday">{longdate(d)}</div>{rows}'

screened = "".join(
    f'<div class="sr"><b>CUT</b><div><b style="color:var(--ink);font-family:inherit;font-size:14.5px">'
    f'{esc(s["agency"])} — {esc(s["title"])}</b><br>{esc(s["reason"])}</div></div>'
    for s in D["screened_out"])

held = "".join(
    f'<div class="sr"><b style="color:var(--amber)">HELD</b><div>'
    f'<b style="color:var(--ink);font-family:inherit;font-size:14.5px">{esc(h["agency"])} — {esc(h["title"])}</b>'
    f'<br>{esc(h["reason"])}</div></div>'
    for h in D.get("held", []))

quiet = "".join(
    f'<div class="sr"><b style="color:var(--ink-3)">QUIET</b><div>'
    f'<b style="color:var(--ink);font-family:inherit;font-size:14.5px">{esc(q["agency"])}</b>'
    f'<br>{esc(q["note"])}</div></div>'
    for q in D.get("quiet_sources", []))

held_block = f'''<div class="screened" style="border-color:var(--amber);background:#FCF9F2">
    <h4 style="color:var(--amber)">Held — we could not check the quote</h4>
    {held}
    <p style="margin-top:14px;font-size:13.5px;color:var(--ink-2)">
      When a source is unreachable we report the gap. We do not go find the text somewhere else,
      and we do not publish a quote we could not confirm. These will run when the source comes back.
    </p>
  </div>''' if held else ""

quiet_block = f'''<div class="screened">
    <h4>Sources with nothing to report</h4>
    {quiet}
  </div>''' if quiet else ""

HTML = f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Daily Docket | Unforced Error</title>
<meta name="description" content="What the agencies filed, quoted from the filings themselves. Updated every morning.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/ue.css">
</head><body>

<div class="dateline">
  <span>Vol. I — No. 001</span>
  <span class="mid">The Daily Docket</span>
  <span>{len(E)} filings · {len(D.get("held",[]))} held · {len(D["screened_out"])} screened out</span>
</div>

<header class="masthead small">
  <a class="nameplate" href="index.html"><span class="g" data-t="Unforced Error">Unforced Error</span></a>
</header>

<nav class="paper" aria-label="Sections">
  <a href="index.html#reports">Reports</a>
  <a href="docket.html">The Docket</a>
  <a href="about.html">The Editor</a>
  <a href="house-rules.html">House Rules</a>
  <a href="index.html#subscribe">Subscribe</a>
</nav>

<div class="dkpage">
  <div style="padding:38px 0 8px">
    <div class="eyebrow">Updated every morning</div>
    <h1 style="font-size:clamp(28px,4.2vw,42px);font-weight:700;letter-spacing:-.02em;line-height:1.12;margin-bottom:14px">The Daily Docket</h1>
    <p style="font-size:19px;color:var(--ink-2);line-height:1.5;max-width:62ch">Every morning an agent reads what the agencies published and posts the ones that matter. It quotes the filing and links to it. It doesn't summarize, and it doesn't tell you what to think — that's what the reports are for.</p>
  </div>

  {days}

  {held_block}

  <div class="screened">
    <h4>Screened out — matched a keyword, carried no substance</h4>
    {screened}
    <p style="margin-top:14px;font-size:13.5px;color:var(--ink-3)">Full-text search for "cybersecurity" turns up budget line items, footnotes, and medical-device boilerplate. We list what we threw away so you can judge whether we threw away the right things. Entries marked "in error" were published here and then removed.</p>
  </div>

  {quiet_block}

  <div style="border-top:3px double var(--ink);margin-top:36px;padding:20px 0 10px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--ink-2);line-height:1.9">
    <b style="color:var(--ink)">Sources polled each morning:</b><br>
    Federal Register API (agency-scoped) · FTC cases and proceedings · SEC litigation releases · CISA advisories<br>
    <span style="color:var(--ink-3)">News coverage is never a source. It sometimes tells us where to look.</span>
  </div>
</div>

<div class="wrap navback"><a href="index.html">← Front page</a> &nbsp;·&nbsp; <a href="house-rules.html">How we work →</a></div>

<footer><div class="foot">
  <span>© 2026 Unforced Error</span>
  <span><a href="about.html">Aiden Goldenberg, Editor</a></span>
  <span>Primary sources only · Not legal advice</span>
</div></footer>
</body></html>
'''

(ROOT / "site" / "docket.html").write_text(HTML)
print(f"docket: {len(E)} filings across {len(by_day)} days, {len(D['screened_out'])} screened out")
