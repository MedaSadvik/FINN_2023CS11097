"""Refresh the Today feed from live sources, and never make it worse than it was.

Each source can fail on its own: NSE blocks many cloud addresses, Yahoo and screener go down, the model runs out of
daily quota. A failed source keeps the previous data for that part and says so in the report, instead of
emptying the feed. The caller injects the fetchers, so this logic is tested without a network.

Parts:  filings (NSE)  ->  cards, routine count          all-or-nothing: partial filings would hide whole companies
        prices (Yahoo) ->  `market` rows for the alerts   per company: a failed company keeps its old rows
        quarters       ->  results numbers                per company: a failure shows the card without numbers
        people (model) ->  who the new executive is       per filing: a failure keeps what the last refresh knew
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional

from pipeline import feed as feedlib


@dataclass
class Fetchers:
    filings: Callable[[int], list]                 # days -> rows; must raise if any company could not be read
    prices: Callable[[str], list]                  # ticker -> [(day, close, volume)]
    quarters: Callable[[str], dict]                # ticker -> {quarter: {...}}
    people: Optional[Callable] = None              # (filings, employers, hours, now) -> {filing id: record}


@dataclass
class Report:
    lines: list = field(default_factory=list)
    failed: set = field(default_factory=set)

    def ok(self, part, text):
        self.lines.append(f"ok      {part}: {text}")

    def fail(self, part, text):
        self.failed.add(part)
        self.lines.append(f"FAILED  {part}: {text}")


def _old_people(old: dict) -> dict:
    return {i["id"]: i["person"] for i in old.get("items", []) if i.get("type") == "mgmt_change" and i.get("person")}


def refresh(old: dict, now: datetime, hours: int, tickers: list, names: dict, employers: dict,
            network_employers: list, fetch: Fetchers) -> tuple:
    """Return (new feed dict, report). `old` is the feed file as it stands now (may be empty)."""
    rep = Report()
    old = old or {}

    # ---- filings
    filings = None
    try:
        filings = fetch.filings(14)
        rep.ok("filings", f"{len(filings)} read from NSE")
    except Exception as e:
        rep.fail("filings", f"{type(e).__name__}: {e}. Keeping the filings from the last refresh.")

    # ---- prices, one company at a time
    prices, kept = {}, []
    old_rows = {t: [tuple(r) for r in m["rows"]] for t, m in (old.get("market") or {}).items()}
    for t in tickers:
        try:
            rows = sorted(fetch.prices(t))
            if not rows:
                raise ValueError("no rows")
            prices[t] = rows
        except Exception as e:
            if t in old_rows:
                prices[t] = old_rows[t]
                kept.append(t)
            rep.lines.append(f"        prices {t}: {type(e).__name__}: {e}")
    if not prices:
        rep.fail("prices", "no company could be read, so there is no price data")
    elif kept:
        rep.fail("prices", f"{len(kept)} of {len(tickers)} companies kept their old rows ({', '.join(kept)})")
    else:
        rep.ok("prices", f"{len(prices)} companies")

    # ---- build
    if filings is None:
        market = feedlib.market_block(prices, names, employers)
        out = {**{k: old[k] for k in ("items", "routine_hidden", "routine_filed", "provider") if k in old},
               "window": {"start": (now - timedelta(hours=hours)).isoformat(), "end": now.isoformat(), "hours": hours},
               "market": market,
               "filings_as_of": old.get("filings_as_of") or (old.get("window") or {}).get("end")}
        out.setdefault("items", [])
        out["items"] = [i for i in out["items"] if i.get("type") != "alert"]
        return out, rep

    quarters = {}
    for t in {f["ticker"] for f in filings if f["category"] == "results" and f["priority"] >= 2}:
        try:
            quarters[t] = fetch.quarters(t)
        except Exception as e:
            rep.lines.append(f"        quarters {t}: {type(e).__name__}: {e}")
    people = dict(_old_people(old))
    if fetch.people:
        try:
            people.update(fetch.people(filings, network_employers, hours, now))
        except Exception as e:  # a model outage must not stop the refresh
            rep.fail("people", f"{type(e).__name__}: {e}. Keeping what the last refresh knew.")
    out = feedlib.build_feed(filings, prices, quarters, names, employers, now, hours, people=people, bake_alerts=False)
    out["filings_as_of"] = now.isoformat()
    out["provider"] = old.get("provider")
    return out, rep
