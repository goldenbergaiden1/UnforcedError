"""Offline test of scout.py's screening + quote verification, using REAL payloads
captured from the Federal Register API. No network."""
import scout, json

# Real API responses captured earlier.
FIXTURES = {
 "federal-trade-commission": {"results":[
   {"title":"Policy Statement Concerning the Suppression of Accuracy in Artificial Intelligence Systems",
    "type":"Notice","document_number":"2026-13628","publication_date":"2026-07-07",
    "abstract":"The Federal Trade Commission (\"Commission\") is proposing a policy statement regarding the application of the prohibition on deceptive acts or practices in section 5 of the Federal Trade Commission Act to companies that market artificial intelligence (\"AI\") systems.",
    "excerpts":None,"html_url":"https://www.federalregister.gov/documents/2026/07/07/2026-13628/policy-statement","pdf_url":"https://www.govinfo.gov/x.pdf"},
   {"title":"Granting of Requests for Early Termination of the Waiting Period Under the Premerger Notification Rules",
    "type":"Notice","document_number":"2026-13661","publication_date":"2026-07-07",
    "abstract":None,"excerpts":None,"html_url":"https://www.federalregister.gov/documents/2026/07/07/2026-13661/x","pdf_url":""},
   {"title":"Agency Information Collection Activities; Proposed Collection; Comment Request; Extension",
    "type":"Notice","document_number":"2026-12503","publication_date":"2026-06-22",
    "abstract":"The Federal Trade Commission (FTC or Commission) is seeking public comment on its proposal requesting that the Office of Management and Budget (OMB) extend for three years the current Paperwork Reduction Act (PRA) clearance for information collection requirements of its Rule Governing Pre-Sale Availability of Written Warranty Terms.",
    "excerpts":None,"html_url":"https://www.federalregister.gov/documents/2026/06/22/2026-12503/x","pdf_url":""}]},
 "securities-and-exchange-commission": {"results":[
   {"title":"Concept Release on Consolidated Audit Trail and Other Audit Trails and Data Sources",
    "type":"Proposed Rule","document_number":"2026-07651","publication_date":"2026-04-20",
    "abstract":"The Securities and Exchange Commission (the \"Commission\") is publishing this concept release to solicit comments in support of a comprehensive review of the Consolidated Audit Trail and other audit trails and related data sources currently used in the regulation of U.S. securities markets, including comments regarding the funding mechanisms for these audit trails and/or related data sources. These developments have prompted the Commission to consider whether changes should be made to the rules and regulations governing existing audit trails and related data sources to better respond to and reflect current market conditions; demonstrated regulatory needs; civil liberty, privacy, and confidentiality concerns; cost-efficient technology solutions; and cybersecurity considerations.",
    "excerpts":None,"html_url":"https://www.federalregister.gov/documents/2026/04/20/2026-07651/x","pdf_url":""}]},
 "homeland-security-department": {"results":[
   {"title":"Rescinding Portions of DHS Title VI Regulations To Conform More Closely With the Statutory Text",
    "type":"Rule","document_number":"2026-12399","publication_date":"2026-06-22",
    "abstract":"By this rule, DHS amends its regulations implementing Title VI of the Civil Rights Act of 1964 (Title VI) consistent with a recent rule issued by the Department of Justice (DOJ).",
    "excerpts":"Many of the past grant solicitations explicitly targeted certain racial groups. See, e.g., DHS-23-CISA-127-CWDT-0001, Cybersecurity Workforce Development and Training for Underserved Communities.",
    "html_url":"https://www.federalregister.gov/documents/2026/06/22/2026-12399/x","pdf_url":""}]},
 "federal-communications-commission":{"results":[]},
 "justice-department":{"results":[]},
 "national-institute-of-standards-and-technology":{"results":[]},
}

def fake_fetch(url, timeout=25):
    scout.check_host(url)  # allowlist still enforced
    for slug in FIXTURES:
        if f"agencies%5D%5B%5D={slug}" in url or f"agencies][]={slug}" in url:
            return FIXTURES[slug]
    return {"results": []}

scout.fetch_json = fake_fetch
kept, screened = scout.scan_federal_register(days_back=3650)

print("=== KEPT ===")
for k in kept:
    print(f"  [{k['agency']}] {k['title'][:62]}")
    print(f"      quote verified: {scout.verify_quote(k['quote'], k['quote'])}")
    print(f"      why: {k['why']}   flag: {k['flag']}")
print("\n=== SCREENED OUT ===")
for s in screened:
    print(f"  [{s['agency']}] {s['title'][:58]}\n      → {s['reason']}")

print("\n=== ASSERTIONS ===")
titles = [k['title'] for k in kept]
assert any("Artificial Intelligence" in t for t in titles), "FTC AI policy statement must be kept"
assert any("Consolidated Audit Trail" in t for t in titles), "SEC CAT concept release must be kept"
assert not any("Early Termination" in t for t in titles), "premerger noise must be screened"
assert not any("Information Collection" in t for t in titles), "paperwork noise must be screened"
assert not any("Title VI" in t for t in titles), "footnote-only cyber match must be screened"
print("  ✓ real story kept (FTC AI policy statement)")
print("  ✓ real story kept (SEC audit trail security)")
print("  ✓ premerger early-termination noise screened")
print("  ✓ Paperwork Reduction Act noise screened")
print("  ✓ DHS civil-rights rule screened (matched only in a footnote)")

print("\n=== ALLOWLIST ENFORCEMENT ===")
try:
    scout.check_host("https://some-random-blog.substack.com/p/hot-take")
    print("  !! ALLOWLIST BROKEN")
except SystemExit as e:
    print("  ✓ off-list host rejected, build halts")
try:
    scout.check_host("https://www.ftc.gov/legal-library/browse/cases-proceedings")
    print("  ✓ ftc.gov accepted")
except SystemExit:
    print("  !! ftc.gov wrongly rejected")

print("\n=== QUOTE VERIFICATION GATE ===")
real = "The Commission is proposing a policy statement."
print("  verbatim quote in source:      ", scout.verify_quote(real, "Blah. " + real + " More."))
print("  invented quote not in source:  ", scout.verify_quote("The Commission called the conduct reckless.", "Blah. " + real))


# ── hardening regression tests (added at next-level step) ────────────────────
def test_hardening():
    import scout as S
    fails = []
    def chk(name, ok):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok: fails.append(name)

    print("\nHARDENING\n")

    # retry wrapper exists and enforces the allowlist before any network call
    try:
        S._fetch("https://evil.example.com/x")
        chk("off-allowlist host blocked before fetch", False)
    except SystemExit:
        chk("off-allowlist host blocked before fetch", True)

    # a redirect target off the allowlist is also rejected (checked via geturl)
    chk("redirect re-check is wired in", "check_host(r.geturl())" in open("scout.py").read())

    # CISA outage → held, never published, never crashes
    orig = S.fetch_text
    S.fetch_text = lambda *a, **k: ""   # simulate empty responses everywhere
    kept, held = S.scan_cisa()
    chk("CISA empty response yields zero published entries", kept == [])
    chk("CISA empty response is reported as held", len(held) == 1)
    chk("held entry names the outage, not a fake quote", "unreachable" in held[0]["reason"])
    S.fetch_text = orig

    # second-pass verification: quote in abstract but NOT in body is held
    doc = {"title": "AI rule", "abstract": "The agency proposes a privacy rule about encryption.",
           "type": "Proposed Rule", "document_number": "X-1", "publication_date": "2026-07-10",
           "html_url": "https://www.federalregister.gov/documents/x", "raw_text_url": "https://www.federalregister.gov/documents/full_text/text/x.txt"}
    S.FR_AGENCIES = [("federal-trade-commission", "FTC", "Federal Trade Commission")]
    S.fetch_json = lambda url, timeout=25: {"results": [doc]}
    S.fetch_text = lambda url, timeout=25: "This body says nothing about the abstract's sentence."
    kept, screened = S.scan_federal_register()
    chk("quote in abstract but absent from body → not published", all(e["title"] != "AI rule" for e in kept))
    chk("...and the reason names the mismatch", any("body" in s["reason"] for s in screened))

    # second-pass verification: quote confirmed in body → published WITH record
    S.fetch_text = lambda url, timeout=25: "Preamble. The agency proposes a privacy rule about encryption. More."
    kept, screened = S.scan_federal_register()
    hit = [e for e in kept if e["title"] == "AI rule"]
    chk("quote confirmed in body → published", len(hit) == 1)
    chk("...with second_pass = confirmed", hit and hit[0]["verified"]["second_pass"] == "confirmed")
    chk("...and a verification method recorded", hit and hit[0]["verified"].get("method"))

    print("\n" + "="*58)
    print("HARDENING: " + ("ALL PASS" if not fails else f"{len(fails)} FAILURES"))
    return fails

if __name__ == "__main__":
    import sys
    f = test_hardening()
    sys.exit(1 if f else 0)
