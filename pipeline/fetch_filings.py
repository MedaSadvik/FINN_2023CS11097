"""Fetch NSE corporate announcements, classify them, save to data/cache/filings.json.

    python -m pipeline.fetch_filings              # whole portfolio, last 7 days
    python -m pipeline.fetch_filings KAYNES 30    # one ticker, last 30 days

Field names come from the real NSE response seen in the Day-1 probe:
  an_dt, desc, attchmntText, attchmntFile, seq_id, symbol, sm_name, ...
Works from a home connection; NSE blocks most cloud IPs.
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.classify import classify
from pipeline.config import TICKERS

IST = timezone(timedelta(hours=5, minutes=30))
OUT = Path(__file__).resolve().parent.parent / "data" / "cache" / "filings.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def parse_nse_time(s: str) -> datetime:
    """'02-Nov-2026 20:37:31' -> aware datetime in IST."""
    return datetime.strptime(s.strip(), "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST)


def normalise(item: dict, ticker: str) -> dict:
    """One raw NSE item -> one row shaped like the `filings` table."""
    subject = (item.get("desc") or "").strip()
    detail = (item.get("attchmntText") or "").strip()
    category, priority = classify(subject, detail)
    return {
        "ticker": ticker,
        "exchange": "NSE",
        "exchange_id": str(item.get("seq_id") or f'{item.get("an_dt")}|{item.get("attchmntFile")}'),
        "announced_at": parse_nse_time(item["an_dt"]).isoformat(),
        "category": category,
        "priority": priority,
        "subject": subject,
        "detail": detail[:600],
        "pdf_url": item.get("attchmntFile") or None,
    }


def nse_session():
    import requests
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                      "Referer": "https://www.nseindia.com/"})
    s.get("https://www.nseindia.com/", timeout=20)  # cookies the API needs
    return s


def fetch(session, ticker: str, days: int) -> list:
    r = session.get("https://www.nseindia.com/api/corporate-announcements",
                    params={"index": "equities", "symbol": ticker}, timeout=25)
    r.raise_for_status()
    cutoff = datetime.now(IST) - timedelta(days=days)
    rows = []
    for item in r.json():
        if not item.get("an_dt"):
            continue
        row = normalise(item, ticker)
        if datetime.fromisoformat(row["announced_at"]) >= cutoff:
            rows.append(row)
    return rows


def main(tickers, days):
    session = nse_session()
    all_rows = []
    for t in tickers:
        try:
            rows = fetch(session, t, days)
        except Exception as e:  # one bad ticker should not kill the run
            print(f"{t:11s} FAILED {type(e).__name__}: {e}")
            continue
        by_prio = {p: sum(r["priority"] == p for r in rows) for p in (3, 2, 1, 0)}
        print(f"{t:11s} {len(rows):3d} filings | important {by_prio[3]} notable {by_prio[2]} "
              f"routine {by_prio[1]} hidden {by_prio[0]}")
        all_rows += rows
        time.sleep(1.5)  # NSE bans fast scrapers
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(all_rows, indent=1))
    print(f"wrote {len(all_rows)} filings to {OUT}")
    print("\nTop 10 by priority:")
    newest_first = sorted(all_rows, key=lambda r: r["announced_at"], reverse=True)
    for r in sorted(newest_first, key=lambda r: -r["priority"])[:10]:  # stable: priority, then newest
        print(f'  [{r["priority"]}] {r["ticker"]:10s} {r["category"]:18s} {r["subject"][:60]}')


if __name__ == "__main__":
    args = sys.argv[1:]
    days = int(args.pop()) if args and args[-1].isdigit() else 7
    main([a.upper() for a in args] or TICKERS, days)
