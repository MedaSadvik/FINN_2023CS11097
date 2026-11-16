"""Put the portfolio companies into the database, so they are treated like any company built on request.

    python scripts/seed_portfolio.py            # add the ones that are missing, leave existing rows alone
    python scripts/seed_portfolio.py --force    # overwrite existing rows with the file's version

Reads frontend/data/companies.json (written by scripts/enrich_portfolio.py and the export). The website prefers the
database row, so after this the nightly staleness check covers these companies and their pages can offer an update.
Run it with --force after you refresh the file by hand and want that version live. Needs SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import staleness  # noqa: E402
from scripts.check_stale import headers  # noqa: E402

FILE = ROOT / "frontend" / "data" / "companies.json"


def rows_from(companies: dict) -> list:
    """Database rows for the portfolio file. The newest call each was built from is worked out from its promises."""
    out = []
    for ticker, c in sorted(companies.items()):
        out.append({"ticker": ticker.upper(), "name": c.get("name") or ticker, "provider": c.get("provider") or "gemini",
                    "data": c, "built_call": staleness.built_call_of(c), "newer_call": None})
    return out


def main(argv: list) -> int:
    force = "--force" in argv
    rows = rows_from(json.loads(FILE.read_text()))
    url, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"]
    prefer = "resolution=merge-duplicates" if force else "resolution=ignore-duplicates"
    h = {**headers(key), "Prefer": prefer + ",return=representation"}
    r = requests.post(f"{url}/rest/v1/companies_live?on_conflict=ticker", headers=h, json=rows, timeout=60)
    r.raise_for_status()
    wrote = {x["ticker"] for x in r.json()}
    print(f"{len(rows)} portfolio companies in the file; {len(wrote)} written" + (" (forced)" if force else ", the rest were already there"))
    for row in rows:
        print(f"  {row['ticker']:<12} {row['provider']:<14} built from {row['built_call']}" + ("" if row["ticker"] in wrote else "  (kept existing row)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
