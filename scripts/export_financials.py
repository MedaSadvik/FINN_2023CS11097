"""Read multi-year financials for the portfolio from screener.in and write frontend/data/financials.json.

    python scripts/export_financials.py                # every portfolio company
    python scripts/export_financials.py TITAN INFY     # just these (added to the file)

A company that fails keeps what the file already had for it. The report lists rows screener did not give for the latest
year, so a renamed label shows up here instead of as a blank on the website.
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.config import TICKERS
from pipeline.fetch_financials import fetch_financials, missing_fields

OUT = ROOT / "frontend" / "data" / "financials.json"


def main(tickers: list) -> int:
    have = json.loads(OUT.read_text()) if OUT.exists() else {}
    failed = []
    for t in tickers:
        try:
            f = fetch_financials(t)
        except Exception as e:
            f = {}
            print(f"{t}: {type(e).__name__}: {e}")
        if not f:
            failed.append(t)
            print(f"{t}: FAILED, keeping {'the old data' if t in have else 'nothing'}")
        else:
            have[t] = {**f, "fetched": date.today().isoformat()}
            gaps = missing_fields(f)
            print(f"{t}: {f['basis']}, {f['years'][0]} to {f['years'][-1]}" + (f", no latest value for: {', '.join(gaps)}" if gaps else ""))
        time.sleep(1.5)  # be polite to screener
    OUT.write_text(json.dumps(dict(sorted(have.items())), indent=1, allow_nan=False))
    print(f"\n{len(tickers) - len(failed)} of {len(tickers)} read. {len(have)} companies in the file.")
    return 1 if len(failed) == len(tickers) else 0


if __name__ == "__main__":
    sys.exit(main([a.upper() for a in sys.argv[1:]] or TICKERS))
