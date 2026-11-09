"""Fetch end-of-day price and volume for the portfolio into a local CSV.

    python -m pipeline.fetch_prices            # whole portfolio, last 3 months
    python -m pipeline.fetch_prices KAYNES     # one ticker

NOT yet tested against live Yahoo (the build sandbox is blocked). Run on your laptop.
Loading into Supabase comes after the probe tells us what works.
"""
import csv
import sys
from pathlib import Path

from pipeline.config import TICKERS, yahoo_symbol

OUT = Path(__file__).resolve().parent.parent / "data" / "cache" / "prices.csv"


def fetch(ticker: str, period: str = "3mo") -> list:
    import yfinance as yf  # imported here so tests do not need it
    df = yf.Ticker(yahoo_symbol(ticker)).history(period=period)
    return [(ticker, idx.date().isoformat(), float(r["Close"]), int(r["Volume"]))
            for idx, r in df.iterrows() if r["Volume"] > 0]  # drop holidays / empty days


def main(tickers):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "day", "close", "volume"])
        for t in tickers:
            rows = fetch(t)
            w.writerows(rows)
            total += len(rows)
            print(f"{t:11s} {len(rows)} rows")
    print(f"wrote {total} rows to {OUT}")


if __name__ == "__main__":
    main([a.upper() for a in sys.argv[1:]] or TICKERS)
