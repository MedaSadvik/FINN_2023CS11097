"""Step 1 of "promised vs delivered": what did management PROMISE on a concall?

    python -m pipeline.guidance KAYNES Q1FY27

Reads data/cache/text/<TICKER>_<PERIOD>.json (from pipeline.fetch_pdf). The transcript is cut
into overlapping ~10-page chunks (same total tokens, better recall than one huge prompt), each
chunk goes to Gemini Flash, and every answer is VERIFIED against the page text:
  - the quote must really appear on the cited page (else the claim is dropped);
  - any number the model puts in low/high must appear as a number inside the quote
    (else the numbers are blanked and the claim is kept as unquantified).
The model can paraphrase, but it cannot invent evidence.
"""
import json
import re
import sys
from pathlib import Path

from pipeline import llm

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"
VERSION = "guidance-v4"  # bump when the prompt changes, so old cache entries are not reused
MIN_QUOTE_CHARS = 25     # shorter quotes match by accident
CHUNK_PAGES, CHUNK_OVERLAP = 10, 1
METRICS = ["revenue_growth", "ebitda_growth", "profit_growth", "ebitda_margin", "revenue_target",
           "capex", "order_book", "other_numeric"]
BASES = ["yoy_growth_pct", "margin_pct", "absolute_crore", "other"]

SYSTEM = f"""You read part of ONE earnings-call transcript and extract management's explicit forward guidance.
Use ONLY the text given. Never use outside knowledge of the company.

Extract a statement only if ALL are true:
- it is said by company management (not an analyst's question);
- it looks forward (a target, expectation, plan or range);
- it is about a number: growth, margin, revenue, profit, capex, order book, capacity.
  A commitment relative to a benchmark counts, e.g. "we have committed to 2x the market growth" or
  "margins to stay above 14%". Management's ANSWERS to analyst questions count; the question itself does not.

For each, return these fields:
  page     the page number from the [PAGE n] marker where the quote appears
  quote    one EXACT, verbatim passage copied from that page, 40-300 characters, within a single page
  metric   one of {METRICS}
  target   the promise in under 15 words, e.g. "FY27 revenue growth of 30-35%"
  basis    one of {BASES}: yoy_growth_pct for growth rates, margin_pct for margins as % of revenue,
           absolute_crore for rupee amounts in crore, other for anything else (e.g. "2x the market")
  low      the lower number exactly as stated, as a plain number (30 not 0.30; crore not lakh); null if none
  high     the upper number of a range; null for a single number or no number
  horizon  the fiscal period promised: "FY27", "Q3FY27" or "H1FY27"; "unspecified" if not stated
  scope    "company" if about the whole company, otherwise the segment name, e.g. "OSAT"

Rules: no paraphrasing inside quote. Never put a number in low/high that is not in the quote.
Skip vague optimism with no number. Skip past results.
Return JSON only: {{"claims": [ ... ]}}. If nothing qualifies, return {{"claims": []}}."""


MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def fiscal_context(call_label) -> str:
    """'May 2026' -> text telling the model what 'this year' means. Indian FY runs April-March."""
    m = re.match(r"([A-Za-z]{3})\w*\s+(\d{4})", call_label or "")
    if not m or m.group(1).lower() not in MONTHS:
        return ""
    month, year = MONTHS.index(m.group(1).lower()) + 1, int(m.group(2))
    cur = year + 1 if month >= 4 else year
    return (f"CONTEXT: this call was held in {call_label}. The fiscal year runs April to March. On that date "
            f"'this year' and 'current year' mean FY{cur % 100:02d}, 'next year' means FY{(cur + 1) % 100:02d}, "
            f"'last year' means FY{(cur - 1) % 100:02d}. Use this only to fill `horizon`.\n\n")


def build_prompt(pages: list, call_label=None) -> str:
    body = "\n\n".join(f"[PAGE {p['page']}]\n{p['text'].strip()}" for p in pages)
    return fiscal_context(call_label) + body


def chunk_pages(pages: list, size: int = CHUNK_PAGES, overlap: int = CHUNK_OVERLAP) -> list:
    """Split into the fewest roughly-equal windows of at most ~`size` pages, 1 page of overlap.
    Fewer calls matter: free-tier quotas are the real bottleneck."""
    if len(pages) <= size + 2:
        return [pages]
    k = -(-len(pages) // size)           # ceil
    step = -(-len(pages) // k)
    return [pages[max(0, i * step - (overlap if i else 0)):(i + 1) * step] for i in range(k)]


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


def check_numbers(claim: dict) -> dict:
    """Every number in low/high must appear as a number in the quote, else blank them."""
    tokens = [float(t) for t in re.findall(r"\d+(?:\.\d+)?", (claim.get("quote") or "").replace(",", ""))]
    claimed = [claim.get(k) for k in ("low", "high") if claim.get(k) is not None]
    try:
        ok = all(any(abs(float(v) - t) < 1e-9 for t in tokens) for v in claimed)
    except (TypeError, ValueError):
        ok = False
    if not ok:
        claim.update(low=None, high=None, basis="other", numbers="unverified_in_quote")
    else:
        claim["numbers"] = "verified" if claimed else "none"
    return claim


def merge_same_promise(claims: list) -> list:
    """One promise is often stated several times in a call. Keep the first, attach the others'
    quotes as extra evidence. Same numbers+metric+scope+period = same promise; with no numbers,
    near-identical wording is required."""
    from difflib import SequenceMatcher
    kept = []
    for c in claims:
        twin = next((k for k in kept if k["metric"] == c["metric"] and k.get("scope") == c.get("scope")
                     and k.get("low") == c.get("low") and k.get("high") == c.get("high")
                     and (k.get("horizon") == c.get("horizon") if c.get("low") is not None else True)
                     and (c.get("low") is not None
                          or SequenceMatcher(None, k["target"].lower(), c["target"].lower()).ratio() >= 0.75)), None)
        if twin:
            twin.setdefault("also_quoted", []).append({"page": c["page"], "quote": c["quote"]})
        else:
            kept.append(c)
    return kept


def extract_guidance(pages: list, call=None, call_label=None) -> dict:
    kwargs = {"call": call} if call else {}
    raw, seen = [], set()
    for chunk in chunk_pages(pages):
        data = llm.generate_json(llm.flash_model(), SYSTEM, build_prompt(chunk, call_label), VERSION, **kwargs)
        for c in (data.get("claims", []) if isinstance(data, dict) else data):
            key = squash(c.get("quote") or "")
            if key not in seen:  # overlap pages can yield the same claim twice
                seen.add(key)
                raw.append(c)
    kept, dropped = verify_claims(raw, pages)
    kept = merge_same_promise([check_numbers(c) for c in kept])
    return {"claims": kept, "dropped": dropped, "model": llm.LAST_MODEL or llm.flash_model(),
            "prompt_version": VERSION}


def run(ticker: str, period: str, doc: dict, call_label=None) -> dict:
    """Extract guidance for one transcript and save it. `doc` is the dict from pipeline.fetch_pdf;
    `call_label` is the month the call was held, e.g. "May 2026" (from screener)."""
    result = extract_guidance(doc["pages"], call_label=call_label)
    result.update(ticker=ticker, period=period, source_sha256=doc["sha256"], source_url=doc.get("url"))
    out = ROOT / "guidance" / f"{ticker}_{period}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    return result


def describe(c: dict) -> str:
    nums = ""
    if c.get("low") is not None:
        nums = f" [{c['low']}{'-' + str(c['high']) if c.get('high') is not None else ''} {c.get('basis')}]"
    return f"p{c['page']:<3} {c['metric']:<15} {c['target']} ({c['horizon']}, {c.get('scope', '?')}){nums}"


def main(ticker: str, period: str):
    src = ROOT / "text" / f"{ticker}_{period}.json"
    if not src.exists():
        raise SystemExit(f"missing {src}; run: python -m pipeline.fetch_pdf {ticker} {period}")
    result = run(ticker, period, json.loads(src.read_text()))
    print(f"{len(result['claims'])} verified claims, {len(result['dropped'])} dropped")
    for c in result["claims"]:
        print("  " + describe(c))
    for d in result["dropped"]:
        print(f"  DROPPED ({d['reason']}): {str(d.get('quote'))[:70]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m pipeline.guidance TICKER Q1FY27")
    main(sys.argv[1].upper(), sys.argv[2].upper())
