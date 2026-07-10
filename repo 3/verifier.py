#!/usr/bin/env python3
"""
UNFORCED ERROR — VERIFIER
Stage 4 of the pipeline. The gate.

Check 1  (span binding)   deterministic, no model. Does the quote exist in the snapshot?
Check 1b (type C ban)     deterministic, no model. Characterization rejected by sentence class.
Check 1c (type B compute) deterministic, no model. Arithmetic computed, never asserted.
Check 1d (type D query)   deterministic, no model. Aggregate must be reproducible from the corpus.

Checks 2 (blind entailment) and 3 (negation probe) require independent models and are
run separately -- they see ONLY the span and the claim, never the brief. Their verdicts
are merged into the receipts by merge_model_verdicts().

A claim that fails ANY check is killed. Killed claims are published.
"""

import json
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Check 1b: the Type C ban, mechanized.
# This is not a high bar. It is a structural prohibition, enforced by sentence class.
# These are conclusions a court reaches, not facts a document states.
# ---------------------------------------------------------------------------
TYPE_C_TERMS = [
    # fault and blame
    "self-inflicted", "self inflicted", "negligent", "negligence", "reckless",
    "careless", "egregious", "willful", "wanton", "culpable", "at fault",
    "blame", "blameworthy", "grossly", "malicious", "bad faith",
    # sophistication and difficulty
    "sophisticated", "unsophisticated", "trivial", "amateurish", "elementary",
    # quality judgments
    "shoddy", "sloppy", "lax", "abysmal", "inexcusable", "indefensible",
    "incompetent", "reckless disregard", "shocking", "appalling", "damning",
    # legal conclusions reserved to adjudicators
    "unlawful", "illegal", "criminal", "fraudulent", "deceptive practice",
    "violated the law", "guilty",
    # editorializing intensifiers
    "obviously", "clearly should have", "any competent", "no excuse",
]

# Legal terms of art that LOOK like characterization but are quoted statutory
# language. If the term appears inside a bound quotation, it survives; the ban
# applies to UNFORCED ERROR's own prose, not to the primary text it quotes.
QUOTED_TERM_EXEMPTIONS = ["unfair", "deceptive", "reasonable"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_corpus(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text())
    docs = {}
    integrity = []
    for d in manifest["documents"]:
        p = ROOT / Path(d["snapshot_path"]).name if not (ROOT / d["snapshot_path"]).exists() \
            else ROOT / d["snapshot_path"]
        actual = sha256_file(p)
        ok = actual == d["sha256"]
        integrity.append({
            "doc_id": d["doc_id"],
            "expected_sha256": d["sha256"],
            "actual_sha256": actual,
            "intact": ok,
        })
        if not ok:
            raise SystemExit(f"CORPUS INTEGRITY FAILURE: {d['doc_id']} hash mismatch. Halting.")
        docs[d["doc_id"]] = {"text": p.read_text(), "meta": d}
    return docs, manifest, integrity


def normalize_for_search(s: str) -> str:
    """Collapse whitespace only. No semantic change. Offsets are reported against
    the raw snapshot, so we search the raw text first and fall back to a
    whitespace-tolerant regex."""
    return re.sub(r"\s+", " ", s).strip()


def bind_span(quote: str, text: str):
    """Check 1. Deterministic. Returns (start, end) or None.
    This is a diff, not a judgment. It catches fabricated citations at zero
    model involvement. Cheapest check, highest value. Run first, fail fast."""
    idx = text.find(quote)
    if idx != -1:
        return (idx, idx + len(quote))
    # whitespace-tolerant retry: the only permitted flexibility
    pattern = re.escape(normalize_for_search(quote)).replace(r"\ ", r"\s+")
    m = re.search(pattern, text)
    if m:
        return (m.start(), m.end())
    return None


def classify_type_c(claim_text: str):
    """Check 1b. Deterministic. A characterization cannot pass. Ever."""
    lowered = claim_text.lower()
    hits = [t for t in TYPE_C_TERMS if t in lowered]
    return hits


def parse_flexible_date(s: str) -> date:
    parts = s.split("-")
    if len(parts) == 3:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    if len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 1)
    raise ValueError(f"unparseable date: {s}")


def compute_arithmetic(arith: dict):
    """Check 1c. Type B claims must be COMPUTED from two independently bound
    dates. Never asserted. If the document asserts a number and the computation
    disagrees, the computation wins and the discrepancy is published."""
    a = parse_flexible_date(arith["operand_a"]["value"])
    b = parse_flexible_date(arith["operand_b"]["value"])
    op = arith["operation"]
    if op == "date_difference_days":
        computed = abs((b - a).days)
    elif op == "date_difference_months":
        computed = abs((b.year - a.year) * 12 + (b.month - a.month))
    else:
        return {"ok": False, "reason": f"unknown operation {op}"}
    asserted = arith.get("asserted_value")
    result = {"ok": True, "computed": computed, "asserted": asserted, "operation": op}
    if asserted is not None and asserted != computed:
        result["discrepancy"] = True
    return result


def verify(claims_path: Path, manifest_path: Path):
    docs, manifest, integrity = load_corpus(manifest_path)
    ledger = json.loads(claims_path.read_text())
    results = []

    for c in ledger["claims"]:
        r = {
            "claim_id": c["claim_id"],
            "type": c["type"],
            "text": c["text"],
            "doc_id": c.get("doc_id"),
            "checks": {},
        }

        # ---- Check 1b FIRST for type C. Structural ban. No further work. ----
        if c["type"] == "C":
            r["checks"]["type_c_classifier"] = {
                "verdict": "REJECTED",
                "matched_terms": classify_type_c(c["text"]),
            }
            r["verdict"] = "KILLED"
            r["kill_reason"] = "type C -- characterization rejected at classifier"
            results.append(r)
            continue

        # ---- Type D: must be reproducible from the corpus. ----
        if c["type"] == "D":
            corpus_docs = len(docs)
            r["checks"]["query_reproducible"] = {
                "verdict": "FAIL",
                "query": c.get("query"),
                "reason": (
                    f"Corpus contains {corpus_docs} documents. The query ranges over an "
                    "ftc_enforcement table that does not exist. A Type D claim must be "
                    "reproducible by re-running a stored query against the corpus. "
                    "Publish the query or kill the claim."
                ),
            }
            r["verdict"] = "KILLED"
            r["kill_reason"] = "type D -- aggregate not reproducible; corpus does not exist yet"
            results.append(r)
            continue

        # ---- Check 1: span binding. Deterministic. Fail fast. ----
        quote = c.get("quote")
        if quote:
            doc = docs.get(c["doc_id"])
            if doc is None:
                r["checks"]["span_binding"] = {"verdict": "FAIL", "reason": "unknown doc_id"}
                r["verdict"] = "KILLED"
                r["kill_reason"] = "span binding -- doc_id not in corpus"
                results.append(r)
                continue
            span = bind_span(quote, doc["text"])
            if span is None:
                r["checks"]["span_binding"] = {
                    "verdict": "FAIL",
                    "quote": quote,
                    "reason": "quoted string does not occur in the snapshot",
                }
                r["verdict"] = "KILLED"
                r["kill_reason"] = "span binding -- FABRICATED CITATION"
                results.append(r)
                continue
            r["checks"]["span_binding"] = {
                "verdict": "PASS",
                "doc_sha256": doc["meta"]["sha256"],
                "offsets": [span[0], span[1]],
                "quote": quote,
            }

        # ---- Check 1b for A/B claims: our own prose must be clean. ----
        c_hits = classify_type_c(c["text"])
        if c_hits:
            r["checks"]["type_c_classifier"] = {"verdict": "REJECTED", "matched_terms": c_hits}
            r["verdict"] = "KILLED"
            r["kill_reason"] = f"type C language in claim text: {c_hits}"
            results.append(r)
            continue
        r["checks"]["type_c_classifier"] = {"verdict": "PASS", "matched_terms": []}

        # ---- Check 1c: Type B arithmetic. ----
        if c["type"] == "B":
            arith = compute_arithmetic(c["arithmetic"])
            r["checks"]["arithmetic"] = arith
            if not arith["ok"]:
                r["verdict"] = "KILLED"
                r["kill_reason"] = "type B -- arithmetic could not be computed"
                results.append(r)
                continue
            if arith.get("discrepancy"):
                r["checks"]["arithmetic"]["verdict"] = "DISCREPANCY"
                r["verdict"] = "KILLED"
                r["kill_reason"] = (
                    f"type B -- asserted {arith['asserted']} but computation from two "
                    f"independently bound dates yields {arith['computed']}. "
                    "An asserted number that disagrees with the computation does not ship."
                )
                results.append(r)
                continue
            r["checks"]["arithmetic"]["verdict"] = "PASS"

        r["verdict"] = "PASS_DETERMINISTIC"
        r["note"] = "awaiting Check 2 (blind entailment) and Check 3 (negation probe)"
        results.append(r)

    passed = [r for r in results if r["verdict"] == "PASS_DETERMINISTIC"]
    killed = [r for r in results if r["verdict"] == "KILLED"]

    return {
        "brief_id": ledger["brief_id"],
        "verifier_version": "0.1",
        "corpus_integrity": integrity,
        "counts": {
            "drafted": len(results),
            "passed_deterministic": len(passed),
            "killed_deterministic": len(killed),
        },
        "results": results,
    }


if __name__ == "__main__":
    out = verify(ROOT / "claims" / "UE-2026-001.claims.json", ROOT / "corpus" / "manifest.json")
    (ROOT / "receipts").mkdir(exist_ok=True)
    dest = ROOT / "receipts" / "UE-2026-001.check1.json"
    dest.write_text(json.dumps(out, indent=2))

    print(f"corpus integrity: all {len(out['corpus_integrity'])} snapshots intact")
    print(f"drafted             {out['counts']['drafted']}")
    print(f"passed check 1      {out['counts']['passed_deterministic']}")
    print(f"killed at check 1   {out['counts']['killed_deterministic']}")
    print()
    for r in out["results"]:
        if r["verdict"] == "KILLED":
            print(f"  {r['claim_id']}  KILLED  {r['kill_reason']}")
