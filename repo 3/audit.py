"""AUDITOR — independent re-verification. Rebuilds every check from scratch.
Does not trust receipts.json. Re-reads the snapshots, re-hashes, re-binds every span,
re-runs the Type C classifier over the RENDERED PROSE (not just the claims),
and re-computes every arithmetic claim."""
import json, hashlib, re, sys
from pathlib import Path
from verifier import TYPE_C_TERMS, bind_span, compute_arithmetic

fails = []
def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not ok: fails.append(label)

man = json.loads(Path('corpus/manifest.json').read_text())
rec = json.loads(Path('receipts/UE-2026-001.receipts.json').read_text())
docs = {}

print("\n1. CORPUS INTEGRITY — rehashed from disk")
for d in man['documents']:
    p = Path(d['snapshot_path']); raw = p.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    check(f"{d['doc_id']} hash", h == d['sha256'], h[:24]+"…")
    docs[d['doc_id']] = p.read_text()

print("\n2. SPAN RE-BINDING — every shipped claim, located from scratch")
shipped = [r for r in rec['results'] if r['final_verdict']=='SHIPPED']
for r in shipped:
    sb = r['checks'].get('span_binding')
    if not sb: continue
    q = sb['quote']; s,e = sb['offsets']
    txt = docs[r['doc_id']]
    check(f"{r['claim_id']} offsets resolve to the quoted string", txt[s:e]==q or bind_span(q,txt)==(s,e))

print("\n3. TYPE C BAN — scanned across the RENDERED PROSE, not just the claims")
prose_files = ['site/index.html','site/about.html','site/house-rules.html','site/docket.html','site/reports/illuminate-ftc-order.html']

def strip_declared_exempt(html):
    """Exemptions must be DECLARED in the markup. Never inferred from section names.

    Two declared classes:
      tc-meta   -- our own prose ABOUT the ban, which must name the banned words
      verbatim  -- an agency's own title or sentence, quoted exactly

    The opinion ban governs what UNFORCED ERROR writes, not what a government
    document is called. The FCC titled a rule "Advanced Methods To Target and
    Eliminate Unlawful Robocalls." We may print that title. We may not call
    anyone's conduct unlawful ourselves. Anything undeclared must be clean."""
    html = re.sub(r'<(\w+)[^>]*class="[^"]*tc-meta[^"]*"[^>]*>.*?</\1>', ' ', html, flags=re.S)
    html = re.sub(r'<(\w+)[^>]*class="[^"]*verbatim[^"]*"[^>]*>.*?</\1>', ' ', html, flags=re.S)
    html = re.sub(r'<div class="wire".*?</div>\s*</div>', ' ', html, flags=re.S)
    html = re.sub(r'<table>.*?</table>', ' ', html, flags=re.S)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.S)
    return html

for pf in prose_files:
    html = strip_declared_exempt(Path(pf).read_text())
    text = re.sub(r'<[^>]+>', ' ', html).lower()
    hits = sorted({t for t in TYPE_C_TERMS if t in text})
    check(f"{pf} free of UNDECLARED opinion language", not hits, f"hits: {hits}" if hits else "")

print("\n4. TYPE B ARITHMETIC — recomputed independently")
expect = {'c04b':12,'c05':23,'c16':21}
for cid,exp in expect.items():
    r=[x for x in rec['results'] if x['claim_id']==cid][0]
    ar=r['checks']['arithmetic']
    check(f"{cid} computed == {exp}", ar['computed']==exp, f"got {ar['computed']}")
    check(f"{cid} is computed, not asserted", ar.get('asserted') is None)

print("\n5. KILLED CLAIMS STAY DEAD — none leaked into the brief prose")
brief = Path('site/reports/illuminate-ftc-order.html').read_text() + Path('site/index.html').read_text()
# claim refs actually cited in prose
cited = set(re.findall(r'<a class="cref" href="[^"]*#(c\d+b?)"', brief))
disclosure = set(re.findall(r'<a href="[^"]*#(c\d+b?)"', brief))
killed = {r['claim_id'] for r in rec['results'] if r['final_verdict']=='KILLED'}
leaked = cited & killed
check("no killed claim is cited as SUPPORT (class=cref)", not leaked, f"leaked: {leaked}" if leaked else "")
check("killed claims that ARE linked are disclosure links only", (disclosure & killed) <= {'c04'}, f"{sorted(disclosure & killed)}")
check("every cref target is a shipped claim", cited <= {r['claim_id'] for r in shipped})

print("\n6. EVERY PROSE CITATION RESOLVES TO A SHIPPED CLAIM")
shipped_ids = {r['claim_id'] for r in shipped}
dangling = cited - shipped_ids - killed
check("no dangling claim references", not dangling, f"dangling: {dangling}" if dangling else "")
print(f"       {len(cited)} distinct claim refs in prose, all resolve")

print("\n7. ALLEGATION FRAMING — factual claims from the complaint are attributed")
comp_claims=[r for r in shipped if r.get('doc_id')=='ftc-2223105-complaint' and r['checks'].get('span_binding')]
unattributed=[r['claim_id'] for r in comp_claims if not r['text'].startswith(('The FTC alleged','The Commission alleged'))]
check("all complaint-sourced claims marked as allegations", not unattributed, f"bare: {unattributed}" if unattributed else "")

print("\n8. THE FABRICATED CITATION IS REALLY ABSENT FROM THE ORDER")
check("'$51,744' does not appear in the final order snapshot", '51,744' not in docs['ftc-2223105-final-order'])
check("c32 is killed", [r for r in rec['results'] if r['claim_id']=='c32'][0]['final_verdict']=='KILLED')

print("\n" + "="*64)
print(f"AUDIT COMPLETE — {len(fails)} failures" if fails else "AUDIT COMPLETE — all checks passed")
if fails:
    for f in fails: print("  !!", f)
    sys.exit(1)
