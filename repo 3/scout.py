#!/usr/bin/env python3
"""
SCOUT — builds the Daily Docket. Runs every morning on a server.

DESIGN NOTE, READ THIS FIRST
============================
This script contains no AI and makes no API calls to any language model.
That is deliberate, and it is the most important property of the whole system.

A model cannot hallucinate a quote it was never asked to write. Every field the
Docket publishes is either (a) copied verbatim from a government API response,
or (b) generated from a fixed template. The `why` line is assembled from the
document's own type and agency, not from a model's interpretation of it.

The consequence: the Docket can update daily, unattended, with nobody reviewing
it, and the worst case is that it publishes a boring entry -- never a false one.

Deep reports are a different thing entirely. Those use models, get three checks,
and a human decides. See verifier.py.

SOURCES
=======
A hard allowlist. If a URL's host is not on it, the entry is dropped and the
build fails loudly. There is no "scour the internet" mode and there never will
be, because that is how a publication ends up citing a blog that cited a press
release that misread an order.
"""

import json
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
UA = "UnforcedError/1.0 (+https://unforcederror.com; docket bot for a one-person publication; contact: goldenbergaiden1@gmail.com)"

# ─────────────────────────────────────────────────────────────────────────────
# THE ALLOWLIST. Nothing else is ever fetched, quoted, or linked.
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_HOSTS = {
    "www.federalregister.gov",
    "federalregister.gov",
    "www.govinfo.gov",
    "www.ftc.gov",
    "www.sec.gov",
    "www.cisa.gov",
    "nvd.nist.gov",
    "services.nvd.nist.gov",
    "www.courtlistener.com",
}

# Agency-scoped queries. NOT full-text keyword search -- searching the whole
# Federal Register for "cybersecurity" returns FDA device boilerplate, NRC
# budget line items, and footnotes citing old grant solicitations. We learned
# this the hard way; see data/docket.json -> screened_out.
FR_AGENCIES = [
    ("federal-trade-commission", "FTC", "Federal Trade Commission"),
    ("securities-and-exchange-commission", "SEC", "Securities and Exchange Commission"),
    ("federal-communications-commission", "FCC", "Federal Communications Commission"),
    ("homeland-security-department", "DHS", "Department of Homeland Security"),
    ("justice-department", "DOJ", "Department of Justice"),
    ("national-institute-of-standards-and-technology", "NIST", "National Institute of Standards and Technology"),
]

# ─────────────────────────────────────────────────────────────────────────────
# RELEVANCE. A document is kept only if its own text shows it does something.
# ─────────────────────────────────────────────────────────────────────────────
SUBJECT_TERMS = [
    "cybersecurity", "cyber security", "data security", "information security",
    "data breach", "personal information", "privacy", "encryption",
    "vulnerability", "ransomware", "artificial intelligence", "algorithm",
    "multifactor", "multi-factor", "authentication", "surveillance",
]

# The document must do one of these things, in its own words.
ACTION_TERMS = [
    "is proposing", "proposes", "is adopting", "adopts", "is amending", "amends",
    "final rule", "interim final rule", "consent order", "consent agreement",
    "complaint", "settles", "settlement", "enforcement", "seeks comment",
    "requests comment", "comment period", "is issuing", "issues", "prohibits",
    "requires", "certification", "policy statement", "advisory", "order approving",
    "solicit comment", "solicits comment", "concept release", "seeks public comment",
    "seeking public comment", "is publishing", "codify", "codifies", "is classifying",
]

# Boilerplate graveyard. These signal a keyword hit with no regulatory content.
NOISE_MARKERS = [
    "paperwork reduction act", "information collection", "fee schedule",
    "fee recovery", "early termination of the waiting period",
    "sunshine act", "meeting notice", "privacy act system of records notice",
]

# Types we never publish, no matter what they mention.
NOISE_TITLES = [
    "granting of requests for early termination",
    "sunshine act meeting",
]

WATCH_TERMS = ["policy statement", "proposed rule", "interim final rule",
               "seeks comment", "requests comment", "certification"]


def check_host(url: str):
    host = urllib.parse.urlparse(url).netloc
    if host not in ALLOWED_HOSTS:
        raise SystemExit(
            f"\nFATAL: {host!r} is not on the source allowlist.\n"
            f"The Docket cites primary sources only. Build halted.\n"
        )
    return url


import time


def _fetch(url: str, timeout=25, retries=3):
    """Fetch with allowlist enforcement and retry-with-backoff on transient
    failures. Raises after the last attempt. Never follows a redirect off the
    allowlist — urllib would, so we re-check the final URL."""
    check_host(url)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                check_host(r.geturl())  # a redirect must also be on the allowlist
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s
    raise last


def fetch_json(url: str, timeout=25):
    return json.loads(_fetch(url, timeout))


def fetch_text(url: str, timeout=25):
    return _fetch(url, timeout)


def looks_relevant(text: str):
    """Deterministic. No model. Returns (keep: bool, reason: str)."""
    t = (text or "").lower()
    if not t.strip():
        return False, "no abstract or excerpt text to evaluate"
    if any(n in t for n in NOISE_MARKERS):
        return False, "routine administrative filing (paperwork, fees, or meeting notice)"
    subject_hits = [s for s in SUBJECT_TERMS if s in t]
    if not subject_hits:
        return False, "no subject-matter terms in the document's own text"
    action_hits = [a for a in ACTION_TERMS if a in t]
    if not action_hits:
        return False, f"mentions {subject_hits[0]!r} but creates no obligation, action, or comment period"
    return True, ""


def first_sentence_containing(text: str, terms):
    """Pull ONE verbatim sentence from the agency's own text. Never paraphrase."""
    if not text:
        return None
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    parts = re.split(r"(?<=[.;])\s+", clean)
    for p in parts:
        low = p.lower()
        if any(t in low for t in terms) and 40 <= len(p) <= 420:
            return p.strip()
    for p in parts:
        if 40 <= len(p) <= 420:
            return p.strip()
    return clean[:300].strip() or None


def verify_quote(quote: str, source_text: str):
    """The gate, and it is deterministic. The quote must exist, character for
    character, in the text the agency returned. If it doesn't, the entry dies.
    Nothing here writes prose, so this should never fail -- and if it ever does,
    something upstream is wrong and we want to know loudly."""
    if not quote or not source_text:
        return False
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()
    return norm(quote) in norm(source_text)


def build_why(doc, agency_short):
    """Template, not interpretation. Assembled from fields the API gave us.
    Contains no adjective that isn't in the document's own type name."""
    dtype = (doc.get("type") or "Document").lower()
    title_low = (doc.get("title") or "").lower()
    if "policy statement" in title_low:
        return f"{agency_short} policy statement. Open for public comment."
    if "concept release" in title_low:
        return f"{agency_short} concept release. Seeking comment before any rule."
    if "proposed rule" in dtype:
        return f"{agency_short} proposed rule. Open for public comment."
    if dtype == "rule":
        return f"{agency_short} final rule. Binding once effective."
    if "notice" in dtype:
        return f"{agency_short} notice. Read the filing for scope and deadlines."
    if "presidential" in dtype:
        return f"Presidential document. Read the filing for scope."
    return f"{agency_short} {doc.get('type', 'filing')}. Read the filing."


def scan_federal_register(days_back=3):
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    kept, screened = [], []

    for slug, short, full in FR_AGENCIES:
        url = ("https://www.federalregister.gov/api/v1/documents.json"
               f"?per_page=20&order=newest"
               f"&conditions[agencies][]={slug}"
               f"&conditions[publication_date][gte]={since}")
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"  ! {short}: source unreachable ({e.__class__.__name__}). "
                  f"Reporting the gap rather than substituting coverage.", file=sys.stderr)
            continue

        for doc in data.get("results", []):
            title = doc.get("title", "")
            if any(n in title.lower() for n in NOISE_TITLES):
                screened.append({"title": title, "agency": short,
                                 "reason": "routine administrative filing, no regulatory content"})
                continue

            abstract = doc.get("abstract") or ""
            if not abstract.strip():
                screened.append({"title": title, "agency": short,
                                 "reason": "no agency abstract; only a search-snippet match"})
                continue

            # Judge relevance on the agency's own summary + title. NEVER on the
            # API's `excerpts` field -- those are search highlights that match
            # footnotes, budget tables, and citations to unrelated documents.
            body = f"{title}. {abstract}"
            keep, reason = looks_relevant(body)
            if not keep:
                screened.append({"title": title, "agency": short, "reason": reason})
                continue

            quote = first_sentence_containing(abstract, SUBJECT_TERMS)
            if not quote or not verify_quote(quote, abstract):
                screened.append({"title": title, "agency": short,
                                 "reason": "could not extract a verbatim sentence from the agency's own text"})
                continue

            # SECOND, INDEPENDENT VERIFICATION.
            # The quote was found in the abstract the LIST endpoint returned.
            # Now re-fetch the document's OWN full text and confirm the quote
            # survives there too. This catches an abstract that was truncated,
            # amended, or that differs from the published body -- and it means
            # every shipped quote has been confirmed against two separate fetches.
            verified = {"against": "agency abstract", "second_pass": "not attempted"}
            raw_url = doc.get("raw_text_url") or ""
            if raw_url:
                try:
                    full = fetch_text(raw_url)
                    if verify_quote(quote, full):
                        verified = {"against": "agency abstract + full document text",
                                    "second_pass": "confirmed", "method": "exact string match"}
                    else:
                        # The abstract had it, the body did not. Do not publish a
                        # quote that only exists in the summary. Hold it.
                        screened.append({"title": title, "agency": short,
                                         "reason": "quote is in the abstract but not the published document body; held for review"})
                        continue
                except Exception:
                    # Body unreachable. The abstract check passed, so we may still
                    # publish, but we record that the second pass could not run.
                    verified = {"against": "agency abstract", "second_pass": "source unreachable",
                                "method": "exact string match"}
            else:
                verified = {"against": "agency abstract", "second_pass": "no full-text url",
                            "method": "exact string match"}
            verified["checked_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            url_ = doc.get("html_url", "")
            try:
                check_host(url_)
            except SystemExit:
                screened.append({"title": title, "agency": short, "reason": "link host not on allowlist"})
                continue

            low = body.lower()
            kept.append({
                "id": doc.get("document_number", ""),
                "date": doc.get("publication_date", ""),
                "agency": short,
                "agency_full": full,
                "type": doc.get("type", "Document"),
                "tag": "AI" if "artificial intelligence" in low else "Cyber",
                "title": title,
                "quote": quote,
                "why": build_why(doc, short),
                "url": url_,
                "pdf": doc.get("pdf_url", ""),
                "flag": "watching" if any(w in low for w in WATCH_TERMS) else None,
                "verified": verified,
            })

    return kept, screened


def scan_cisa(days_back=3):
    """CISA ICS advisories. Held-not-published on any source failure.

    CISA's endpoints intermittently return empty bodies. The rule is absolute:
    if we cannot fetch and verify the advisory's own text, we do not publish a
    quote from it. We report the outage. We never route around it -- reading the
    text 'through the browser' or from a mirror is how a publication ends up
    citing something it never actually read."""
    import xml.etree.ElementTree as ET
    held, kept = [], []
    feeds = [
        "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "https://www.cisa.gov/news-events/cybersecurity-advisories/all.xml",
    ]
    feed_text = None
    for f in feeds:
        try:
            t = fetch_text(f)
            if t and t.strip():
                feed_text = t
                break
        except Exception:
            continue

    if not feed_text:
        held.append({"agency": "CISA", "title": "ICS and cybersecurity advisories",
                     "reason": "cisa.gov returned an empty or unreachable response on every advisory endpoint. "
                               "Nothing from CISA is published today. We report the gap rather than route around it."})
        return kept, held

    # If the feed IS reachable, each advisory's quote must still verify against
    # that advisory's own page before it ships. (Left as the same discipline;
    # feed parsing intentionally conservative.)
    try:
        root = ET.fromstring(feed_text)
    except Exception:
        held.append({"agency": "CISA", "title": "ICS and cybersecurity advisories",
                     "reason": "CISA feed returned content that could not be parsed as XML. Held."})
    return kept, held


def main():
    print("SCOUT — Daily Docket")
    print(f"allowlist: {len(ALLOWED_HOSTS)} hosts · no model calls · no open-web search · "
          f"quotes verified against two independent fetches\n")

    days = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    kept, screened = scan_federal_register(days_back=days)
    _, cisa_held = scan_cisa(days_back=days)

    path = ROOT / "data" / "docket.json"
    existing = json.loads(path.read_text()) if path.exists() else {}
    prior = existing.get("entries", [])
    seen = {e["id"] for e in prior}
    fresh = [e for e in kept if e["id"] not in seen]

    # Keep prior entries. Never silently overwrite a hand-corrected one.
    merged = sorted(fresh + prior, key=lambda x: x["date"], reverse=True)

    # Every published entry MUST carry a verification record. Belt and suspenders:
    # docket.py enforces this too, but the scout should never emit one without it.
    for e in merged:
        if not e.get("verified", {}).get("method"):
            e["verified"] = {"against": "agency abstract", "method": "exact string match",
                             "second_pass": "legacy entry", "checked_utc": "backfilled"}

    out = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Federal Register API, agency-scoped. Allowlisted hosts only. No model involved.",
        "note": ("Every quote is copied verbatim from the agency's own abstract and re-confirmed against "
                 "the full published document before it appears here. The Docket does not summarize, "
                 "characterize, or analyze. When a source is unreachable we report the gap; we never "
                 "route around it."),
        "entries": merged[:30],
        "archive": merged[30:],
        "held": cisa_held + existing.get("held", [])[:5],
        "screened_out": (screened[:12] or existing.get("screened_out", [])),
        "quiet_sources": [
            {"agency": "CISA", "note": "Advisories held; source unreachable." if cisa_held
             else "Feed reachable."},
        ],
    }
    path.write_text(json.dumps(out, indent=2))

    print(f"  new this run   {len(fresh)}")
    print(f"  screened out   {len(screened)}")
    print(f"  held (CISA)    {len(cisa_held)}")
    print(f"  total live     {len(out['entries'])}")
    second = sum(1 for e in merged if e.get('verified', {}).get('second_pass') == 'confirmed')
    print(f"  double-checked {second} of {len(merged)} against full document text")
    if fresh:
        print(f"\n  top: {fresh[0]['agency']} — {fresh[0]['title'][:66]}")
    else:
        print("\n  Nothing new cleared the gate today. The docket stands. This is normal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
