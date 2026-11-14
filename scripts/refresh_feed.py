"""Refresh Today from live sources in one command. Runs daily in GitHub Actions, or by hand on your laptop.

    python scripts/refresh_feed.py                 # 14 days of filings, prices, results numbers, new executives
    python scripts/refresh_feed.py --no-people     # skip the model step (no quota used)

Writes frontend/data/feed_live.json. A source that fails keeps its previous data and is listed in the report.
Exit code 1 only when nothing at all could be refreshed.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import fetch_filings, fetch_prices, fetch_quarters, llm, people
from pipeline.config import PORTFOLIO, TICKERS
from pipeline.refresh import Fetchers, refresh

IST = timezone(timedelta(hours=5, minutes=30))
OUT = ROOT / "frontend" / "data" / "feed_live.json"
HOURS = 14 * 24


def nse_filings(days: int) -> list:
    """All companies or an error: reading only some would silently drop the rest from the feed."""
    session = fetch_filings.nse_session()
    rows, failed = [], []
    for t in TICKERS:
        for attempt in (1, 2):
            try:
                rows += fetch_filings.fetch(session, t, days)
                break
            except Exception:
                if attempt == 2:
                    failed.append(t)
                time.sleep(2)
        time.sleep(1.5)  # NSE bans fast scrapers
    if failed:
        raise RuntimeError(f"NSE did not answer for {len(failed)} of {len(TICKERS)} companies ({', '.join(failed[:5])}...)")
    return rows


def main(with_people: bool):
    llm.load_env()
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    network = json.loads((ROOT / "data" / "network" / "synthetic_network.json").read_text())
    names = {t: n for t, n, _ in PORTFOLIO}
    by_ticker = {e["ticker"]: e["key"] for e in network["employers"] if e["ticker"]}
    fetchers = Fetchers(
        filings=nse_filings,
        prices=lambda t: [(d, c, v) for _, d, c, v in fetch_prices.fetch(t)],
        quarters=fetch_quarters.fetch_quarters,
        people=people.read_people if with_people else None,
    )
    now = datetime.now(IST)
    new, report = refresh(old, now, HOURS, TICKERS, names, by_ticker, network["employers"], fetchers)
    if with_people and "filings" not in report.failed:
        new["provider"] = llm.provider()
    # allow_nan=False: a NaN would make the file invalid JSON and break the website build. Fail here instead, before anything is written.
    OUT.write_text(json.dumps(new, indent=1, ensure_ascii=False, allow_nan=False))

    text = "\n".join(report.lines) + f"\n{len(new['items'])} cards, {new.get('routine_hidden', 0)} routine filings hidden, filings as of {new.get('filings_as_of')}"
    print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        Path(summary).write_text("```\n" + text + "\n```\n")
    return 1 if {"filings", "prices"} <= report.failed and not new.get("market") else 0  # nothing refreshed at all


if __name__ == "__main__":
    sys.exit(main("--no-people" not in sys.argv[1:]))
