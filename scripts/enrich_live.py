"""List on-demand companies that were built before the newer research sections existed.

    python scripts/enrich_live.py            # prints a JSON list of tickers, e.g. ["TITAN", "SBIN"]

Used by the enrich-live workflow, which rebuilds each listed company with the normal worker. The
rebuild reuses cached transcripts and model answers, so it costs only the new steps (at most 4
model requests per company). Needs SUPABASE_URL and SUPABASE_SERVICE_KEY, like the build worker.
"""
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def lacks_new_sections(data: dict) -> bool:
    """True when the stored company has no business snapshot or no multi-year numbers."""
    return not data.get("snapshot") or not data.get("financials")


def missing(rows: list) -> list:
    return sorted(r["ticker"] for r in rows if lacks_new_sections(r.get("data") or {}))


def fetch_rows(url: str, key: str) -> list:
    headers = {"apikey": key}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    r = requests.get(f"{url.rstrip('/')}/rest/v1/companies_live?select=ticker,data&limit=500", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    print(json.dumps(missing(fetch_rows(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]))))
