"""Step 1 of "promised vs delivered": what did management PROMISE on a concall?

    python -m pipeline.guidance KAYNES Q1FY27

Reads data/cache/text/<TICKER>_<PERIOD>.json (from pipeline.fetch_pdf), asks Gemini Flash
for forward-looking statements, then VERIFIES every quote against the page text.
A claim whose quote is not really on the page is dropped. That check is the
anti-hallucination guarantee: the model can paraphrase, but it cannot invent evidence.
"""
import json
import re
import sys
from pathlib import Path

from pipeline import llm

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"
VERSION = "guidance-v2"  # bump when the prompt changes, so old cache entries are not reused
MIN_QUOTE_CHARS = 25     # shorter quotes match by accident
METRICS = ["revenue_growth", "revenue_target", "ebitda_margin", "profit_growth",
           "capex", "order_book", "other_numeric"]

SYSTEM = f"""You read ONE earnings-call transcript and extract management's explicit forward guidance.
Use ONLY the text given. Never use outside knowledge of the company.

Extract a statement only if ALL are true:
- it is said by company management (not an analyst's question);
- it looks forward (a target, expectation, plan or range);
- it is about a number: growth, margin, revenue, profit, capex, order book, capacity.
  A commitment relative to a benchmark counts as a number, e.g. "we have committed to 2x the market
  growth" or "margins to stay above 14%". Management's ANSWERS to analyst questions count; the
  question itself does not.

For each, return:
  page     the page number from the [PAGE n] marker where the quote appears
  quote    one EXACT, verbatim passage copied from that page, 40-300 characters, within a single page
  metric   one of {METRICS}
  target   the promise in under 15 words, e.g. "FY27 revenue growth of 30-35%"
  horizon  the period it refers to, e.g. "FY27", "H2 FY26", "next 3 years"; "unspecified" if none

Rules: no paraphrasing inside quote. Skip vague optimism with no number. Skip past results.
Return JSON only: {{"claims": [ ... ]}}. If nothing qualifies, return {{"claims": []}}."""


def build_prompt(pages: list) -> str:
    return "\n\n".join(f"[PAGE {p['page']}]\n{p['text'].strip()}" for p in pages)


def squash(s: str) -> str:
    """Keep only letters and digits, lowercased. Forgives line breaks, smart quotes, hyphens and
    spacing from PDF extraction, but stays strict on every word and number."""
    return re.sub(r"[^0-9a-z]", "", s.lower())


def verify_claims(claims: list, pages: list) -> tuple:
    """Split claims into (kept, dropped). kept[i]['verified'] says how the quote was matched."""
    squashed = {p["page"]: squash(p["text"]) for p in pages}
    kept, dropped, seen = [], [], set()
    for c in claims:
        quote = c.get("quote") or ""
        q = squash(quote)
        if len(q) < MIN_QUOTE_CHARS:
            dropped.append({**c, "reason": "quote too short"})
            continue
        if q in seen:
            dropped.append({**c, "reason": "duplicate"})
            continue
        page = c.get("page")
        if page in squashed and q in squashed[page]:
            kept.append({**c, "verified": "exact_page"})
        else:  # model cited the wrong page: look elsewhere before giving up
            where = next((n for n, text in squashed.items() if q in text), None)
            if where is None:
                dropped.append({**c, "reason": "quote not found in transcript"})
                continue
            kept.append({**c, "page": where, "verified": "page_corrected"})
        seen.add(q)
    return kept, dropped


def extract_guidance(pages: list, call=None) -> dict:
    kwargs = {"call": call} if call else {}
    data = llm.generate_json(llm.flash_model(), SYSTEM, build_prompt(pages), VERSION, **kwargs)
    claims = data.get("claims", []) if isinstance(data, dict) else data
    kept, dropped = verify_claims(claims, pages)
    return {"claims": kept, "dropped": dropped, "model": llm.LAST_MODEL or llm.flash_model(),
            "prompt_version": VERSION}


def main(ticker: str, period: str):
    src = ROOT / "text" / f"{ticker}_{period}.json"
    if not src.exists():
        raise SystemExit(f"missing {src}; run: python -m pipeline.fetch_pdf {ticker} {period}")
    doc = json.loads(src.read_text())
    result = extract_guidance(doc["pages"])
    result.update(ticker=ticker, period=period, source_sha256=doc["sha256"])
    out = ROOT / "guidance" / f"{ticker}_{period}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    print(f"{len(result['claims'])} verified claims, {len(result['dropped'])} dropped")
    for c in result["claims"]:
        print(f"  p{c['page']:<3} [{c['metric']}] {c['target']}  ({c['horizon']})")
    for d in result["dropped"]:
        print(f"  DROPPED ({d['reason']}): {str(d.get('quote'))[:70]}")
    print(f"saved {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m pipeline.guidance TICKER Q1FY27")
    main(sys.argv[1].upper(), sys.argv[2].upper())
