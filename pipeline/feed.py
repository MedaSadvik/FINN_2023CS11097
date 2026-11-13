"""Build the Today feed from real filings and prices. Plain rules, no model.

Push has two parts (per the brief): a WINDOWED DIGEST of filings, ranked by priority, and TRIGGERED
ALERTS from volume and price. Routine paperwork is counted but not shown, so the feed stays short.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

from pipeline import alerts

DEFAULT_RULES = {"volume_multiple": 2.0, "price_move": 5.0}
DETAIL_CHARS = 280
LABEL = {"results": "Results", "M&A": "Deal", "litigation": "Legal", "capex": "Capex",
         "fund_raise": "Fund raise", "credit_rating": "Credit rating", "dividend": "Dividend",
         "bonus_split": "Bonus or split", "pledging": "Share pledge", "press_release": "Company update",
         "management_change": "Management change"}


def load_prices(path: Path) -> dict:
    out = {}
    if path.exists():
        for r in csv.DictReader(path.open()):
            out.setdefault(r["ticker"], []).append((r["day"], float(r["close"]), int(r["volume"])))
    return {t: sorted(rows) for t, rows in out.items()}


def short(text: str, n: int = DETAIL_CHARS) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"


def filing_item(f: dict, name: str, employer_key, person=None) -> dict:
    base = {"id": f["exchange_id"], "ticker": f["ticker"], "company": name, "filed": f["announced_at"],
            "employer_key": employer_key, "pdf_url": f.get("pdf_url"), "category": f["category"],
            "label": LABEL.get(f["category"], f["category"]), "priority": f["priority"]}
    if f["category"] == "management_change":
        return {**base, "type": "mgmt_change", "headline": f["subject"], "detail": short(f.get("detail")),
                "person": person}
    return {**base, "type": "event", "headline": f["subject"], "detail": short(f.get("detail"))}


def alert_items(prices: dict, names: dict, employers: dict, rules: dict) -> list:
    out = []
    for t, rows in prices.items():
        hits = {h["kind"]: h for h in alerts.check_all(rows, rules)}
        if not hits:
            continue
        v, p = hits.get("volume_multiple"), hits.get("price_move")
        out.append({"id": f"alert-{t}-{rows[-1][0]}", "type": "alert", "ticker": t, "company": names.get(t, t),
                    "filed": rows[-1][0], "employer_key": employers.get(t), "priority": 2,
                    "volume_x": v["ratio"] if v else None, "price_pct": p["pct"] if p else None,
                    "rules": rules})
    return out


def results_item(f: dict, name: str, quarters: dict):
    """Real numbers for a results filing: newest reported quarter vs the previous quarter and a year ago."""
    done = sorted((q for q, v in quarters.items() if v.get("revenue") is not None),
                  key=lambda q: (int(q[-2:]), q[1]))
    if not done:
        return None
    cur = done[-1]
    n, fy = int(cur[1]), int(cur[-2:])
    prev = f"Q{n - 1}FY{fy:02d}" if n > 1 else f"Q4FY{fy - 1:02d}"
    ago = f"Q{n}FY{fy - 1:02d}"
    if prev not in quarters or ago not in quarters:
        return None
    pick = lambda q: {"quarter": q, **{k: quarters[q][k] for k in ("revenue", "ebitda", "pbt", "pat")}}
    return {"id": f["exchange_id"], "type": "results", "ticker": f["ticker"], "company": name, "priority": 3,
            "filed": f["announced_at"], "quarter": cur, "cur": pick(cur), "qoq": pick(prev), "yoy": pick(ago),
            "pdf_url": f.get("pdf_url")}


MARKET_ROWS = 45  # 20 days for the average + the longest window (14 days is about 10 trading days) + slack


def market_block(prices: dict, names: dict, employers: dict) -> dict:
    """Recent end-of-day rows per ticker, so the app can check the investor's own thresholds."""
    return {t: {"company": names.get(t, t), "employer_key": employers.get(t),
                "rows": [[d, c, v] for d, c, v in rows[-MARKET_ROWS:]]}
            for t, rows in prices.items() if rows}


def build_feed(filings: list, prices: dict, quarters: dict, names: dict, employers: dict, now: datetime,
               hours: int = 48, rules: dict = None, people: dict = None, bake_alerts: bool = True) -> dict:
    """quarters: ticker -> {quarter: {...}}. people: filing exchange_id -> verified person record.

    bake_alerts=False leaves alerts out of `items` and ships the price rows instead (`market`), so the app
    checks the investor's own thresholds. `routine_filed` lists when each routine filing came in, so the app
    can count what is hidden for whichever window is picked.
    """
    rules = DEFAULT_RULES if rules is None else rules
    start = now - timedelta(hours=hours)
    recent = [f for f in filings if datetime.fromisoformat(f["announced_at"]) >= start]
    items, routine, routine_filed = [], 0, []
    for f in recent:
        if f["priority"] == 0:  # hidden outright (investor-meeting notices, routine paperwork)
            continue
        if f["priority"] == 1:  # counted so the user knows something was left out
            routine += 1
            routine_filed.append(f["announced_at"])
            continue
        name, key = names.get(f["ticker"], f["ticker"]), employers.get(f["ticker"])
        item = None
        if f["category"] == "results" and f["ticker"] in quarters:
            item = results_item(f, name, quarters[f["ticker"]])
        items.append(item or filing_item(f, name, key, (people or {}).get(f["exchange_id"])))
    if bake_alerts:
        items += alert_items(prices, names, employers, rules)
    items.sort(key=lambda i: (i["priority"], i["filed"]), reverse=True)  # priority first, then newest
    out = {"window": {"start": start.isoformat(), "end": now.isoformat(), "hours": hours},
           "routine_hidden": routine, "routine_filed": routine_filed, "items": items}
    if not bake_alerts:
        out["market"] = market_block(prices, names, employers)
    return out
