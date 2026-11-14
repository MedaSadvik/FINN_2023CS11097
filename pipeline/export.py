"""Turn pipeline output (verdicts + quarters) into the JSON the website reads.

    python scripts/export_frontend.py KAYNES

No LLM here and no network: it only reshapes files already in data/cache. The website never
reads the cache directly, so what is published is exactly what this file writes.
"""
import json
import re
from pathlib import Path

ORDER = ["missed", "partly", "delivered", "pending", "unclear"]
UNCHECKED_REASON = "Can't be checked from the quarterly tables yet."


def mark_span(quote: str, low, high) -> str:
    """The part of the quote worth highlighting: the stretch around the promised numbers.
    Falls back to the whole quote when there are no numbers. Always a real substring."""
    nums = [str(int(v)) if float(v).is_integer() else str(v) for v in (low, high) if v is not None]
    # "4000" must also match "4,000": allow an optional comma between digits
    hits = [m for n in nums for m in re.finditer(",?".join(re.escape(ch) for ch in n), quote)]
    if not hits:
        return quote
    start = max(0, min(m.start() for m in hits) - 40)
    end = min(len(quote), max(m.end() for m in hits) + 25)
    while start > 0 and quote[start - 1] != " ":
        start -= 1
    while end < len(quote) and quote[end] != " ":
        end += 1
    return quote[start:end].strip()


def to_pledge(row: dict) -> dict:
    c = row["claim"]
    quote = " ".join((c.get("quote") or "").split())
    out = {
        "made_in": row["made_in"], "target": c["target"], "horizon": c.get("horizon") or "unspecified",
        "page": c["page"], "quote": quote, "mark": mark_span(quote, c.get("low"), c.get("high")),
        "outcome": row["outcome"], "result": row.get("delivered_text"),
    }
    if row.get("evidence"):  # a later call said how it went; the page shows that quote
        out["evidence"] = row["evidence"]
    if row["outcome"] == "unclear":
        out["reason"] = row.get("reason") or UNCHECKED_REASON
    return out


def build_company(ticker: str, name: str, employer_key, rows: list, quarters: dict, provider: str,
                  snapshot: dict = None) -> dict:
    pledges = sorted((to_pledge(r) for r in rows), key=lambda p: ORDER.index(p["outcome"]))
    qs = [{"quarter": q, **{k: v[k] for k in ("revenue", "ebitda", "pbt", "pat")}}
          for q, v in quarters.items() if v.get("revenue") is not None]
    qs.sort(key=lambda q: (int(q["quarter"][-2:]), q["quarter"][1]))
    out = {"ticker": ticker, "name": name, "employer_key": employer_key, "provider": provider,
           "quarters": qs[-8:], "promises": pledges}
    if snapshot and (snapshot["business"]["segments"] or snapshot["bull"] or snapshot["bear"]):
        out["snapshot"] = {k: snapshot[k] for k in ("business", "bull", "bear", "period")}
    return out
