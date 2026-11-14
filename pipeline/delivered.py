"""Promised vs delivered, tier 2: promises the quarterly tables cannot check, answered from LATER calls.

    python -m pipeline.delivered KAYNES

Tier 1 (pipeline.verdicts) does arithmetic on reported quarters. A promise like "OSAT revenue of
Rs 300 crore in FY26" has no row in those tables, but management usually says how it went on the
call that reports the year. This step finds that sentence.

Rules that keep it honest:
  - only promises that are unclear, numeric and whose period has ended are tried;
  - at most MAX_CALLS model requests per company (free-tier quotas are the bottleneck);
  - the model sees a handful of pages chosen by keywords, never the whole transcript;
  - its quote must appear verbatim on the cited page, the number must appear in the quote,
    and the unit must match what was promised, else the answer is thrown away;
  - the verdict itself is the same plain arithmetic as tier 1 (`verdicts.judge`);
  - running out of quota stops quietly: those promises just stay "unclear".
"""
import json
import re
import sys
from pathlib import Path

from pipeline import guidance, llm, verdicts

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"
VERSION = "delivered-v1"
MAX_CALLS = 3          # model requests per company
MAX_CLAIMS = 8         # promises per request
MAX_PAGES = 8          # transcript pages per request
CHECKABLE = ("absolute_crore", "yoy_growth_pct", "margin_pct")
KEYWORDS = {"capex": ["capex", "capitalexpenditure"], "order_book": ["orderbook", "orderinflow"],
            "revenue_target": ["revenue"], "ebitda_margin": ["margin"], "revenue_growth": ["growth"],
            "ebitda_growth": ["ebitda"], "profit_growth": ["profit"]}

SYSTEM = """You are given pages from ONE later earnings-call transcript and a list of earlier promises by management.
For each promise, find where management states what was ACTUALLY achieved for the promised period.
Use ONLY the pages given. Never use outside knowledge.

Answer for a promise only if the pages state a specific number for the SAME thing (same segment or
company-wide scope, same metric) and the SAME period. A plan for the future, a different period or a
different segment does not count. If unsure, leave it out.

For each answer return:
  id      the promise id given
  page    the page number from the [PAGE n] marker
  quote   one EXACT, verbatim passage from that page, 40-300 characters, that contains the number
  actual  the achieved number as a plain number, in the SAME unit as the promise (crore, or percent)
  basis   the promise's basis, repeated exactly
  period  the period the number is for, e.g. "FY26"
Return JSON only: {"findings": [ ... ]}. If nothing qualifies, return {"findings": []}."""


def period_key(p):
    """'Q4FY26' -> (26, 4). None if it is not a quarter label."""
    m = re.fullmatch(r"Q([1-4])FY(\d{2})", p or "")
    return (int(m.group(2)), int(m.group(1))) if m else None


def horizon_end(h: dict) -> tuple:
    q = {"FY": 4, "H1": 2, "H2": 4}.get(h["kind"]) or int(h["kind"][1])
    return h["fy"], q


def candidates(rows: list, quarters: dict) -> list:
    """Indexes of rows worth a second look: unclear, numeric, and the promised period has ended."""
    out = []
    for i, r in enumerate(rows):
        c = r["claim"]
        h = verdicts.parse_horizon(c.get("horizon"))
        if (r["outcome"] == "unclear" and h and c.get("basis") in CHECKABLE
                and verdicts._as_number(c.get("low")) is not None
                and (c.get("scope") not in (None, "company") or c.get("metric") not in verdicts.GROWTH_FIELD)
                and verdicts.reported_count(h, quarters)[0] == verdicts.reported_count(h, quarters)[1]):
            out.append(i)
    return out


def later_transcripts(ticker: str, claim: dict, made_in: str) -> list:
    """Cached transcripts of calls held after the promised period ended, oldest first."""
    h = verdicts.parse_horizon(claim.get("horizon"))
    end, made = horizon_end(h), period_key(made_in)
    found = []
    for path in (ROOT / "text").glob(f"{ticker}_*.json"):
        k = period_key(path.stem[len(ticker) + 1:])
        if k and k >= end and (made is None or k > made):
            found.append((k, path.stem[len(ticker) + 1:], path))
    return sorted(found)


def claim_words(claim: dict) -> list:
    words = [w for w in re.split(r"[^a-z0-9]+", str(claim.get("scope") or "").lower()) if len(w) >= 3]
    words = [w for w in words if w not in ("company", "unspecified", "and", "the")]
    return words + KEYWORDS.get(claim.get("metric"), [])


def pick_pages(pages: list, claims: list, limit: int = MAX_PAGES) -> list:
    """Pages mentioning the promises' scope or metric, best first, returned in page order."""
    words = {w for c in claims for w in claim_words(c)}
    scored = []
    for p in pages:
        text = guidance.squash(p["text"])
        score = sum(text.count(guidance.squash(w)) for w in words)
        if score:
            scored.append((score, p))
    top = sorted(scored, key=lambda s: -s[0])[:limit]
    return sorted((p for _, p in top), key=lambda p: p["page"])


def build_prompt(pages: list, claims: list) -> str:
    asked = [{"id": i, "promise": c["target"], "scope": c.get("scope"), "horizon": c.get("horizon"),
              "basis": c.get("basis"), "promised": c.get("low")} for i, c in claims]
    body = "\n\n".join(f"[PAGE {p['page']}]\n{p['text'].strip()}" for p in pages)
    return "PROMISES:\n" + json.dumps(asked, indent=1) + "\n\nPAGES:\n" + body


def quote_numbers(quote: str) -> list:
    return [float(t) for t in re.findall(r"\d+(?:\.\d+)?", (quote or "").replace(",", ""))]


def check_finding(f: dict, claim: dict, pages: list):
    """The verified answer for one promise, or None. Nothing the model says is trusted unchecked."""
    quote = f.get("quote") or ""
    kept, _ = guidance.verify_claims([{"quote": quote, "page": f.get("page")}], pages)
    actual = verdicts._as_number(f.get("actual"))
    h, said = verdicts.parse_horizon(claim.get("horizon")), verdicts.parse_horizon(f.get("period"))
    if (not kept or actual is None or f.get("basis") != claim.get("basis") or said != h
            or not any(abs(actual - t) < 1e-9 for t in quote_numbers(quote))):
        return None
    return {"actual": actual, "page": kept[0]["page"], "quote": " ".join(quote.split())}


def verdict_from(claim: dict, found: dict, period: str) -> dict:
    low, high = verdicts._as_number(claim.get("low")), verdicts._as_number(claim.get("high"))
    tol = {"margin_pct": 1.0, "absolute_crore": abs(low) * 0.05}.get(claim["basis"], abs(low) * 0.10)
    unit = {"absolute_crore": " cr", "yoy_growth_pct": "%", "margin_pct": "%"}[claim["basis"]]
    guided = f"{low:g}" + (f"-{high:g}" if high is not None else "")
    actual = found["actual"]
    out = {"outcome": verdicts.judge(actual, low, high, tol), "tier": "later_call", "actual": round(actual, 1),
           "delivered_text": f"{actual:g}{unit} vs {guided}{unit} guided, as said on the {period} call",
           "evidence": {"period": period, "page": found["page"], "quote": found["quote"]}}
    if high is not None and actual > high and out["outcome"] == "delivered":
        out["note"] = "above the promised range"
    return out


def enrich(ticker: str, rows: list, quarters: dict, call=None) -> list:
    """Return rows with tier-2 answers filled in where a later call states the actual number."""
    kwargs = {"call": call} if call else {}
    rows = [dict(r) for r in rows]
    todo = {}                                   # transcript period -> [row index]
    for i in candidates(rows, quarters):
        later = later_transcripts(ticker, rows[i]["claim"], rows[i]["made_in"])
        if later:
            todo.setdefault(later[0][1], []).append(i)
    used = 0
    for period, idxs in sorted(todo.items(), key=lambda kv: period_key(kv[0])):
        doc = json.loads((ROOT / "text" / f"{ticker}_{period}.json").read_text())
        for s in range(0, len(idxs), MAX_CLAIMS):
            if used >= MAX_CALLS:
                return rows
            batch = idxs[s:s + MAX_CLAIMS]
            asked = [(i, rows[i]["claim"]) for i in batch]
            pages = pick_pages(doc["pages"], [c for _, c in asked])
            if not pages:
                continue
            used += 1
            try:
                data = llm.generate_json(llm.flash_model(), SYSTEM, build_prompt(pages, asked), VERSION, **kwargs)
            except llm.QuotaExhausted as e:
                print(f"   later-call check stopped: {e}", file=sys.stderr)
                return rows
            for f in (data.get("findings", []) if isinstance(data, dict) else []):
                i = f.get("id")
                if i in batch:
                    found = check_finding(f, rows[i]["claim"], pages)
                    if found:
                        rows[i].update(verdict_from(rows[i]["claim"], found, period))
                        rows[i].pop("reason", None)
    return rows


def main(ticker: str):
    quarters = json.loads((ROOT / "quarters" / f"{ticker}.json").read_text())
    path = ROOT / llm.derived("verdicts") / f"{ticker}.json"
    rows = json.loads(path.read_text())
    out = enrich(ticker, rows, quarters)
    path.write_text(json.dumps(out, indent=1))
    n = sum(1 for a, b in zip(rows, out) if a["outcome"] != b["outcome"])
    print(f"{ticker}: {n} promises settled from later calls")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m pipeline.delivered TICKER")
    main(sys.argv[1].upper())
