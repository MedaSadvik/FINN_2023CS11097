"""NSE's official list of listed equities: symbol and company name. Used by the website's search and "did you mean".

    python scripts/fetch_symbols.py

The list is public and small (about 2,000 rows). It is saved as frontend/data/symbols.json, so the website needs no
lookup service and works even when NSE is slow.
"""
import csv
import io

MIN_ROWS = 500   # a real NSE list has far more; fewer means a broken download, and we keep the old file
URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"


def parse_equity_csv(text: str) -> list:
    """[[symbol, name], ...] sorted by symbol. Header names in NSE's file carry stray spaces, so strip them."""
    rows, seen = [], set()
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        r = {(k or "").strip().upper(): (v or "").strip() for k, v in r.items()}
        sym, name = r.get("SYMBOL", ""), r.get("NAME OF COMPANY", "")
        if sym and name and sym not in seen:
            seen.add(sym)
            rows.append([sym, name])
    rows.sort(key=lambda x: x[0])
    if len(rows) < MIN_ROWS:
        raise ValueError(f"only {len(rows)} companies in the list; expected at least {MIN_ROWS}")
    return rows
