"""Regression tests for the opinion filter's exemption rules."""
import re, sys
from pathlib import Path
from verifier import TYPE_C_TERMS
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location("a", "audit.py")

def strip(html):
    html = re.sub(r'<(\w+)[^>]*class="[^"]*tc-meta[^"]*"[^>]*>.*?</\1>', ' ', html, flags=re.S)
    html = re.sub(r'<(\w+)[^>]*class="[^"]*verbatim[^"]*"[^>]*>.*?</\1>', ' ', html, flags=re.S)
    html = re.sub(r'<div class="wire".*?</div>\s*</div>', ' ', html, flags=re.S)
    html = re.sub(r'<table>.*?</table>', ' ', html, flags=re.S)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.S)
    return html

def scan(html):
    text = re.sub(r'<[^>]+>', ' ', strip(html)).lower()
    return sorted({t for t in TYPE_C_TERMS if t in text})

fails = []
def t(name, ok):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if not ok: fails.append(name)

print("\nOPINION FILTER — exemption rules\n")

# The FCC really did title a rule this. We must be able to print it.
fcc = '<h3 class="verbatim">Advanced Methods To Target and Eliminate Unlawful Robocalls</h3>'
t("an agency's own title containing 'Unlawful' may be printed", scan(fcc) == [])

# ...but only inside a declared verbatim element.
fcc_bare = '<h3>Advanced Methods To Target and Eliminate Unlawful Robocalls</h3>'
t("the same words in OUR prose are still blocked", 'unlawful' in scan(fcc_bare))

# A quote may carry the word; our gloss beneath it may not.
ok  = '<blockquote class="verbatim">The Commission prohibits unlawful robocalls.</blockquote><div class="wy">FCC proposed rule. Open for public comment.</div>'
bad = '<blockquote class="verbatim">The Commission prohibits unlawful robocalls.</blockquote><div class="wy">The carriers were negligent.</div>'
t("verbatim quote clean, our 'why' line clean", scan(ok) == [])
t("verbatim quote clean, our 'why' line editorializing → blocked", 'negligent' in scan(bad))

# The exemption must not leak past the closing tag.
leak = '<h3 class="verbatim">Eliminate Unlawful Robocalls</h3><p>The company was reckless.</p>'
t("exemption does not leak into the next element", 'reckless' in scan(leak))

# Every entry actually on the site right now
import json
d = json.load(open('data/docket.json'))
tripped = [e['title'] for e in d['entries'] if any(x in e['title'].lower() for x in TYPE_C_TERMS)]
print(f"\n  live docket titles containing banned words: {len(tripped)}")
for x in tripped: print(f"    (exempt, verbatim) {x[:70]}")

print("\n" + "="*58)
print(f"{'ALL PASS' if not fails else str(len(fails)) + ' FAILURES'}")
sys.exit(1 if fails else 0)
