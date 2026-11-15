"""Download NSE's list of listed companies and write frontend/data/symbols.json.

    python scripts/fetch_symbols.py

If the download fails or looks wrong, the existing file is kept and this exits with an error.
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.symbols import URL, parse_equity_csv  # noqa: E402

OUT = ROOT / "frontend" / "data" / "symbols.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
           "Accept": "text/csv,*/*", "Referer": "https://www.nseindia.com/"}


def main() -> int:
    last = None
    for attempt in range(3):
        try:
            r = requests.get(URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            rows = parse_equity_csv(r.text)
            break
        except Exception as e:  # NSE sometimes refuses the first request
            last = e
            time.sleep(3 * (attempt + 1))
    else:
        print(f"could not read the NSE list: {type(last).__name__}: {last}. Kept the existing file.")
        return 1
    OUT.write_text(json.dumps({"asof": date.today().isoformat(), "source": "NSE equity list", "rows": rows}, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {len(rows)} companies to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
