"""Promised vs delivered, tier 1: headline promises checked by ARITHMETIC on reported quarters.

    python -m pipeline.verdicts KAYNES

Reads data/cache/guidance/<TICKER>_*.json (what was promised) and data/cache/quarters/<TICKER>.json
(what the company reported). No LLM here: the comparison is plain maths, so it is free, repeatable
and checkable. Claims it cannot check by maths (capex, segment targets, "2x the market") come back
"unclear" and are left for tier 2 (a model reading later transcripts).

Judging rule, written down so it is not a black box:
  delivered  actual is at or above the LOW end of the promised range
  partly     actual is just under the low end: within 10% of it for growth rates, 5% for rupee
             amounts, or 1 point for margins
  (pending also covers promises for a year that has not started: "due FY28")
  missed     further below than that
  pending    the promised period has not fully ended; we show the year-to-date number instead
"""
import json
import re
import sys
from pathlib import Path

from pipeline import llm

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"
GROWTH_FIELD = {"revenue_growth": "revenue", "ebitda_growth": "ebitda", "profit_growth": "pat"}


def parse_horizon(text):
    """'FY27' -> whole year, 'H1FY27' -> two quarters, 'Q3 FY27' -> one quarter. None if unclear."""
    t = re.sub(r"[\s'\-]", "", (text or "").upper())
    m = re.search(r"(Q[1-4]|H[12])?FY(?:20)?(\d{2})(?!\d)", t)
    if not m:
        return None
    tag, fy = m.group(1), int(m.group(2))
    return {"kind": tag or "FY", "fy": fy}


def quarter_labels(h: dict, fy_offset: int = 0) -> list:
    qs = {"FY": [1, 2, 3, 4], "H1": [1, 2], "H2": [3, 4]}.get(h["kind"]) or [int(h["kind"][1])]
    return [f"Q{q}FY{h['fy'] + fy_offset:02d}" for q in qs]


def total(quarters: dict, labels: list, field: str):
    vals = [quarters.get(l, {}).get(field) for l in labels]
    return None if any(v is None for v in vals) else sum(vals)


def judge(actual: float, low: float, high, tol: float) -> str:
    if actual >= low:
        return "delivered"
    return "partly" if actual >= low - tol else "missed"


def _measure(claim: dict, quarters: dict, labels: list):
    """Actual value of whatever the claim promised, over `labels`. Returns (value, unit) or None."""
    metric, basis = claim.get("metric"), claim.get("basis")
    if metric in GROWTH_FIELD and basis == "yoy_growth_pct":
        field = GROWTH_FIELD[metric]
        prior = [l[:-2] + f"{int(l[-2:]) - 1:02d}" for l in labels]
        cur, prev = total(quarters, labels, field), total(quarters, prior, field)
        if cur is None or not prev or prev <= 0:
            return None
        return (cur / prev - 1) * 100, "%"
    if metric == "ebitda_margin" and basis == "margin_pct":
        e, r = total(quarters, labels, "ebitda"), total(quarters, labels, "revenue")
        return (e / r * 100, "%") if e is not None and r else None
    if metric == "revenue_target" and basis == "absolute_crore":
        v = total(quarters, labels, "revenue")
        return (v, " cr") if v is not None else None
    return None


def reported_count(h: dict, quarters: dict) -> tuple:
    """(quarters of the promised period already reported, quarters in the period)."""
    labels = quarter_labels(h)
    return sum(1 for l in labels if quarters.get(l, {}).get("revenue") is not None), len(labels)


def not_yet_due(claim: dict, h: dict, quarters: dict, what: str) -> dict:
    done, of = reported_count(h, quarters)
    return {"outcome": "pending", "tier": "computed",
            "delivered_text": f"due {claim.get('horizon')}: {done} of {of} quarters reported so far. {what} is checked once the period is complete."}


def latest_reported_fy(quarters: dict):
    done = [int(k[-2:]) for k, v in quarters.items() if v.get("revenue") is not None]
    return max(done) if done else None


def _as_number(v):
    """A number, or None when the value is missing or not numeric."""
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def evaluate(claim: dict, quarters: dict) -> dict:
    out = {"outcome": "unclear", "delivered_text": None, "tier": "computed"}
    low, high = _as_number(claim.get("low")), _as_number(claim.get("high"))  # claims cached before the fix may hold text
    h = parse_horizon(claim.get("horizon"))
    latest = latest_reported_fy(quarters)
    if h and latest and h["fy"] > latest:  # promise about a year that has not started
        out.update(outcome="pending", delivered_text=f"due {claim.get('horizon')}; reported so far through FY{latest}")
        return out
    if low is None:
        out["reason"] = "no verified number to check against"
        return out
    if claim.get("scope") not in (None, "company", "unspecified", "consolidated"):
        if h and reported_count(h, quarters)[0] < reported_count(h, quarters)[1]:  # the period is still running
            return not_yet_due(claim, h, quarters, "A segment figure")
        out["reason"] = f"segment claim ({claim.get('scope')}): needs a later-transcript check"
        return out
    if h is None:
        out["reason"] = "no fiscal period stated"
        return out
    labels = quarter_labels(h)
    got = _measure(claim, quarters, labels)
    guided = f"{low:g}" + (f"-{high:g}" if high is not None else "")
    if got is None:
        # period not complete (or not reported): show year-to-date over the quarters we have
        have = [l for l in labels if quarters.get(l, {}).get("revenue") is not None]
        ytd = _measure(claim, quarters, have) if have else None
        if ytd is None:
            if reported_count(h, quarters)[0] < reported_count(h, quarters)[1]:
                return not_yet_due(claim, h, quarters, "This kind of figure")
            out["reason"] = "metric not computable from reported quarters"
            return out
        out.update(outcome="pending", actual=round(ytd[0], 1), computed_from=have,
                   delivered_text=f"so far {have[0]}-{have[-1]}: {ytd[0]:.1f}{ytd[1]} vs {guided}{ytd[1]} guided")
        return out
    actual, unit = got
    tol = {"margin_pct": 1.0, "absolute_crore": abs(low) * 0.05}.get(claim.get("basis"), abs(low) * 0.10)
    out.update(outcome=judge(actual, low, high, tol), actual=round(actual, 1), computed_from=labels,
               delivered_text=f"{actual:.1f}{unit} vs {guided}{unit} guided ({labels[0]}-{labels[-1]})")
    if high is not None and actual > high and out["outcome"] == "delivered":
        out["note"] = "above the promised range"
    return out


def evaluate_ticker(ticker: str) -> list:
    quarters = json.loads((ROOT / "quarters" / f"{ticker}.json").read_text())
    rows = []
    for path in sorted((ROOT / llm.derived("guidance")).glob(f"{ticker}_*.json")):
        g = json.loads(path.read_text())
        for c in g["claims"]:
            rows.append({"made_in": g["period"], "claim": c, **evaluate(c, quarters)})
    return rows


def main(ticker: str):
    rows = evaluate_ticker(ticker)
    out = ROOT / llm.derived("verdicts") / f"{ticker}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))
    print(f"{ticker}: {len(rows)} promises checked")
    for r in rows:
        c = r["claim"]
        print(f"  [{r['outcome']:9s}] {r['made_in']}: {c['target'][:55]}")
        print(f"              {r['delivered_text'] or r.get('reason')}")
    print(f"saved {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m pipeline.verdicts TICKER")
    main(sys.argv[1].upper())
