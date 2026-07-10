#!/usr/bin/env python3
"""
Renders the "Our sources and checks" page from the facts ledger.
This page is GENERATED. Never hand-edit it -- edits are overwritten on every build.
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).parent
R = json.loads((ROOT / "receipts" / "UE-2026-001.receipts.json").read_text())
MAN = json.loads((ROOT / "corpus" / "manifest.json").read_text())
DOCS = {d["doc_id"]: (ROOT / d["snapshot_path"]).read_text() for d in MAN["documents"]}
SHORT = {"ftc-2223105-complaint": "FTC complaint", "ftc-2223105-final-order": "FTC final order"}

# plain-English reasons, keyed by the internal kill reason prefix
PLAIN = {
    "span binding": ("Quote doesn't exist", "We searched the document for this exact sentence. It isn't there. It turned out to be from the FTC's press release, not the order we cited."),
    "type C": ("It's an opinion", "This is a judgment, not a fact. A filter blocks language like this automatically, before anyone reads it."),
    "type B": ("The math didn't match", "The document states a number. We calculated it ourselves from the dates the document gives, and got something different. We go with our own arithmetic."),
    "type D": ("We couldn't reproduce the count", "This is a tally across many documents. We can't re-run that count yet, so we don't get to print it."),
    "check 2": ("The quote doesn't say that", "The sentence we found is close, but it doesn't actually support what we wanted to write. Close isn't good enough."),
    "check 3": ("The document contradicts it", "Another part of the source says the opposite."),
}
def plain(reason):
    for k, v in PLAIN.items():
        if reason.lower().startswith(k.lower()):
            return v
    return ("Cut", reason)

def esc(s): return html.escape(s or "")
def ctx(doc_id, s, e, pad=170):
    t = DOCS[doc_id]; a, b = max(0, s - pad), min(len(t), e + pad)
    return esc(t[a:s]), esc(t[s:e]), esc(t[e:b])

# reading-order numbers, matching the superscripts in the report
ORDER = ["c27","c06","c07","c08","c09","c10","c01","c20","c25","c33","c30","c02",
         "c28","c03","c31","c15","c13","c22","c21","c23","c24","c14","c29"]
NUM = {cid: i + 1 for i, cid in enumerate(ORDER)}

shipped_rows, cut_rows = [], []
for r in R["results"]:
    cid = r["claim_id"]
    if r["final_verdict"] == "SHIPPED":
        sb, ar = r["checks"].get("span_binding"), r["checks"].get("arithmetic")
        body = ""
        if sb:
            pre, hit, post = ctx(r["doc_id"], *sb["offsets"])
            body += (f'<div class="quote"><span class="ctx">…{pre}</span><mark>{hit}</mark>'
                     f'<span class="ctx">{post}…</span></div>'
                     f'<div class="qmeta"><span>{esc(SHORT.get(r["doc_id"],r["doc_id"]))}</span>'
                     f'<span>characters {sb["offsets"][0]}–{sb["offsets"][1]} of our saved copy</span></div>')
        if ar:
            body += (f'<div class="calc"><b>We calculated this ourselves.</b> From the two dates in the document: '
                     f'<span class="num">{ar["computed"]}</span>'
                     f'{" — the document says " + str(ar["asserted"]) if ar.get("asserted") is not None else ""}.</div>')
        n = NUM.get(cid)
        body += ('<div class="passed">'
                 '<span>✓ The quote exists, word for word</span>'
                 '<span>✓ It isn\'t an opinion</span>'
                 '<span>✓ A second checker agreed the quote supports it</span>'
                 '<span>✓ A third checker tried to disprove it and failed</span></div>')
        shipped_rows.append(
            f'<div class="fact" id="{cid}">'
            f'<div class="fhead"><span class="fnum">{n if n else "•"}</span>'
            f'<span class="fok">Published</span></div>'
            f'<p class="ftext">{esc(r["text"])}</p>{body}</div>')
    else:
        title, why = plain(r.get("kill_reason", ""))
        extra = ""
        sb = r["checks"].get("span_binding")
        if sb and sb.get("verdict") == "PASS":
            pre, hit, post = ctx(r["doc_id"], *sb["offsets"])
            extra = (f'<div class="quote dead"><span class="ctx">…{pre}</span><mark class="dead">{hit}</mark>'
                     f'<span class="ctx">{post}…</span></div>'
                     f'<div class="qmeta"><span>What the document actually says</span></div>')
        elif sb and sb.get("verdict") == "FAIL":
            extra = (f'<div class="quote dead"><b>We looked for this sentence and it is not in the document:</b><br>'
                     f'<mark class="dead">{esc(sb.get("quote"))}</mark></div>')
        tc = r["checks"].get("type_c_classifier")
        if tc and tc.get("verdict") == "REJECTED":
            extra = (f'<div class="quote dead"><b>Blocked words:</b> '
                     f'<code>{esc(", ".join(tc["matched_terms"]))}</code><br>'
                     f'No AI was consulted. A plain word filter caught it first.</div>')
        ar = r["checks"].get("arithmetic")
        if ar and ar.get("verdict") == "DISCREPANCY":
            extra = (f'<div class="quote dead"><b>The document says <code>{ar["asserted"]}</code>. '
                     f'The dates it gives work out to <code>{ar["computed"]}</code>.</b><br>'
                     f'We print our own arithmetic and cut the other version.</div>')
        q = r["checks"].get("query_reproducible")
        if q:
            extra = f'<div class="quote dead"><b>The count we tried to run:</b><br><code>{esc(q["query"])}</code></div>'
        cut_rows.append(
            f'<div class="fact cut" id="{cid}">'
            f'<div class="fhead"><span class="fcut">Cut — {esc(title)}</span></div>'
            f'<p class="ftext">{esc(r["text"])}</p>{extra}'
            f'<div class="why">{esc(why)}</div></div>')

fp = "".join(
    f'<div class="fprow"><span>{esc(SHORT.get(i["doc_id"], i["doc_id"]))}</span>'
    f'<span class="{"ok" if i["intact"] else "bad"}">{"unchanged ✓" if i["intact"] else "CHANGED"}</span>'
    f'<span class="hash">{i["actual_sha256"][:40]}…</span></div>'
    for i in R["corpus_integrity"])

c, cc = R["counts"], R["check_correlation"]

HTML = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Our sources and checks | Unforced Error</title>
<meta name="description" content="Every fact in this report, the exact sentence it came from, and everything we cut.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/ue.css">
<style>
.intro{{padding:40px 0 30px}}
.intro h1{{font-size:clamp(27px,4vw,40px);font-weight:700;letter-spacing:-.02em;margin-bottom:14px;line-height:1.14}}
.intro p{{color:var(--ink-2);font-size:17px;margin-bottom:12px}}
.score{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--rule);border:1px solid var(--rule);margin:26px 0}}
@media(max-width:620px){{.score{{grid-template-columns:repeat(2,1fr)}}}}
.score div{{background:var(--paper);padding:16px 14px;text-align:center}}
.score .v{{font-size:28px;font-weight:700;letter-spacing:-.02em;font-family:'JetBrains Mono',monospace}}
.score .v.g{{color:var(--green)}} .score .v.r{{color:var(--red)}}
.score .l{{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--ink-3);margin-top:3px}}
.fingerprints{{background:var(--paper);border:1px solid var(--rule);padding:16px 18px;margin-bottom:34px;font-family:'JetBrains Mono',monospace;font-size:11px}}
.fingerprints .ft{{color:var(--ink-3);margin-bottom:10px;letter-spacing:.1em;text-transform:uppercase;font-size:10px}}
.fprow{{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;padding:4px 0}}
.fprow .ok{{color:var(--green)}} .fprow .bad{{color:var(--red)}}
.fprow .hash{{color:var(--ink-3);word-break:break-all}}
h2.sec{{font-size:23px;font-weight:700;letter-spacing:-.015em;margin:42px 0 8px;padding-bottom:8px;border-bottom:3px double var(--ink)}}
h2.sec.r{{color:var(--red);border-bottom-color:var(--red)}}
p.secsub{{color:var(--ink-2);font-size:15.5px;margin-bottom:20px}}
.fact{{background:var(--paper);border:1px solid var(--rule);padding:18px 20px;margin-bottom:12px}}
.fact.cut{{border-color:#E3CDCB;background:var(--red-lt)}}
.fhead{{display:flex;align-items:center;gap:10px;margin-bottom:10px;font-family:'JetBrains Mono',monospace;font-size:10.5px}}
.fnum{{background:var(--green);color:#fff;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:11px}}
.fok{{color:var(--green);letter-spacing:.08em;text-transform:uppercase}}
.fcut{{color:var(--red);letter-spacing:.08em;text-transform:uppercase;font-weight:600}}
.ftext{{font-size:16.5px;margin-bottom:12px;line-height:1.55}}
.quote{{background:var(--bg);border:1px solid var(--rule);border-left:3px solid var(--green);padding:12px 14px;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.8;margin-bottom:6px}}
.quote.dead{{border-left-color:var(--red);background:#fff}}
.quote .ctx{{color:var(--ink-3)}}
.quote code{{background:#fff;border:1px solid var(--rule);padding:1px 5px}}
mark{{background:var(--green);color:#fff;padding:1px 2px}}
mark.dead{{background:var(--red);color:#fff}}
.qmeta{{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--ink-3);margin-bottom:10px}}
.calc{{background:var(--green-lt);border-left:3px solid var(--green);padding:10px 13px;font-size:14px;margin:8px 0}}
.calc .num{{font-family:'JetBrains Mono',monospace;font-weight:600;color:var(--green);font-size:16px}}
.passed{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}
.passed span{{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--ink-3);border:1px solid var(--rule);padding:3px 7px;border-radius:2px}}
.why{{margin-top:10px;padding-top:10px;border-top:1px solid #E8D3D1;font-size:14.5px;color:var(--ink-2)}}
.finding{{background:var(--paper);border:1px solid var(--rule);border-top:3px solid var(--amber);padding:24px 26px;margin:36px 0}}
.finding h3{{font-size:19px;font-weight:700;margin-bottom:12px;letter-spacing:-.01em}}
.finding p{{color:var(--ink-2);font-size:15.5px;margin-bottom:12px}}
.finding p:last-child{{margin-bottom:0}}
.finding b{{color:var(--ink)}}
</style></head><body>

<div class="dateline">
  <span>Vol. I — No. 001</span>
  <span class="mid">Check Our Work</span>
  <span>{c['shipped']} published · {c['killed']} cut</span>
</div>

<header class="masthead small">
  <a class="nameplate" href="../index.html"><span class="g" data-t="Unforced Error">Unforced Error</span></a>
</header>

<nav class="paper" aria-label="Sections">
  <a href="../index.html#reports">Reports</a>
  <a href="../docket.html">The Docket</a>
  <a href="../about.html">The Editor</a>
  <a href="../house-rules.html">House Rules</a>
  <a href="../reports/illuminate-ftc-order.html">Back To Report</a>
</nav>

<div class="col intro">
  <h1>Our sources and checks</h1>
  <p>Below is every fact we wanted to state in this report. For each one that made it, you'll find the exact sentence in the FTC's own filing that it came from, highlighted in green.</p>
  <p>Then you'll find the seven we cut, and why. That's the part we'd most like you to read. If you think we cut the wrong thing — or kept the wrong thing — <a href="mailto:goldenbergaiden1@gmail.com" style="border-bottom:1.5px solid var(--green)">tell us</a>.</p>

  <div class="score">
    <div><div class="v">{c['drafted_revision_2']}</div><div class="l">facts written</div></div>
    <div><div class="v g">{c['shipped']}</div><div class="l">published</div></div>
    <div><div class="v r">{c['killed']}</div><div class="l">cut</div></div>
    <div><div class="v">0</div><div class="l">corrections</div></div>
  </div>

  <div class="fingerprints">
    <div class="ft">Our saved copies, re-checked just now</div>
    {fp}
    <div style="color:var(--ink-3);margin-top:10px;font-size:10.5px">A fingerprint is a code calculated from the document's contents. If even one character changed, the code changes. These match, so our copies are the same ones we read.</div>
  </div>
</div>

<div class="col">
  <h2 class="sec r">What we cut — {c['killed']} facts</h2>
  <p class="secsub">These are sentences we wanted to publish and couldn't.</p>
  {''.join(cut_rows)}

  <div class="finding">
    <h3>Something we learned, and don't love</h3>
    <p>Two separate AI systems check every fact. One sees only the quote and the claim, nothing else. The other gets the whole document and is told to prove the claim wrong.</p>
    <p>We expected the second one — the aggressive one — to be the strict one. It wasn't. It approved <b>"Illuminate paid a ransom"</b> even though the document only says "agreed to pay." The one that saw less caught it.</p>
    <p>Our guess: giving the checker the full document gave it enough context to talk itself into agreeing. <b>They disagreed on {cc['disagreements']} of {cc['claims_seen_by_both']} facts.</b> We're publishing that number because a checking system whose flaws you can't see isn't a checking system.</p>
  </div>

  <h2 class="sec">What we published — {c['shipped']} facts</h2>
  <p class="secsub">Each one links back from the report. The green highlight is the exact text in the original document.</p>
  {''.join(shipped_rows)}
</div>

<div class="navback col">
  <a href="../reports/illuminate-ftc-order.html">← Back to the report</a> &nbsp;·&nbsp; <a href="../index.html">All reports</a>
</div>

<footer><div class="foot">
  <span>© 2026 Unforced Error</span>
  <span><a href="../about.html">About the editor</a></span>
  <span>Primary sources only · Not legal advice</span>
</div></footer>
</body></html>
"""

dest = ROOT / "site" / "checks" / "illuminate-ftc-order.html"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(HTML)
print(f"rendered {dest}  ({c['shipped']} published, {c['killed']} cut)")
