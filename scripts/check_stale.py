"""Mark built companies whose research is behind the newest earnings call. No model, no model quota.

    python scripts/check_stale.py

For every row in companies_live: read the list of calls on screener.in, compare the newest with the newest call the
research was built from, and store the answer in newer_call. The website then offers "Update" for those companies only.
A company whose page cannot be read this time is left exactly as it was. Needs SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import staleness  # noqa: E402


def headers(key: str) -> dict:
    h = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_"):
        h["Authorization"] = f"Bearer {key}"
    return h


def decide(row: dict, docs: dict):
    """What to store for one company: {'built_call', 'newer_call'}, or None when the lookup gave nothing usable."""
    listed = staleness.newest_call(docs.get("transcripts"))
    built = staleness.built_call_of({**(row.get("data") or {}), "built_call": row.get("built_call")})
    if listed is None or built is None:
        return None
    return {"built_call": built, "newer_call": staleness.newer_call(built, listed)}


def run(rows: list, fetch_docs, save, pause=0.0) -> list:
    """Check every row. `fetch_docs` and `save` are passed in so tests need no network."""
    report = []
    for r in rows:
        t = r["ticker"]
        try:
            outcome = decide(r, fetch_docs(t))
        except Exception as e:  # one company failing must not stop the others
            report.append(f"{t}: skipped ({type(e).__name__})")
            continue
        if outcome is None:
            report.append(f"{t}: skipped (no readable call list)")
        else:
            save(t, {**outcome, "checked_at": datetime.now(timezone.utc).isoformat()})
            report.append(f"{t}: " + (f"newer call {outcome['newer_call']} (built from {outcome['built_call']})"
                                      if outcome["newer_call"] else f"up to date ({outcome['built_call']})"))
        time.sleep(pause)
    return report


def main() -> int:
    from pipeline import fetch_docs
    url, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"]
    h = headers(key)
    r = requests.get(f"{url}/rest/v1/companies_live?select=ticker,built_call,data&limit=500", headers=h, timeout=30)
    r.raise_for_status()

    def save(ticker, body):
        requests.patch(f"{url}/rest/v1/companies_live?ticker=eq.{ticker}", headers=h, json=body, timeout=30).raise_for_status()

    print("\n".join(run(r.json(), fetch_docs.fetch_docs, save, pause=2.0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
