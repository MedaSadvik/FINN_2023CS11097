"""Write the Today feed from real filings and prices.

    python -m pipeline.fetch_filings 14        # NSE announcements (home connection)
    python -m pipeline.fetch_prices            # Yahoo end-of-day prices
    python scripts/export_feed.py 336          # last 14 days (the app's window picker goes up to this)
    python scripts/export_feed.py 120          # last 120 hours
    python scripts/export_feed.py 120 --people # also read management-change PDFs (uses the model)

Writes frontend/data/feed_live.json. Commit it: the website is built from it.
Alerts are not decided here: the file carries recent price rows and the app checks the investor's own thresholds.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import feed, llm
from pipeline.config import PORTFOLIO

IST = timezone(timedelta(hours=5, minutes=30))
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "frontend" / "data" / "feed_live.json"


def read_people(filings, employers, hours, now):
    """Management-change filings in the window -> verified person records (needs the PDF text and a model)."""
    from pipeline import fetch_pdf, people
    out = {}
    for f in filings:
        recent = datetime.fromisoformat(f["announced_at"]) >= now - timedelta(hours=hours)
        if f["category"] != "management_change" or not recent or not f.get("pdf_url"):
            continue
        try:
            path, _ = fetch_pdf.download(f["pdf_url"], referer="https://www.nseindia.com/")
            text = "\n".join(p["text"] for p in fetch_pdf.extract_pages(path))
            rec = people.extract_person(text, employers)
        except Exception as e:
            print(f"  {f['ticker']}: could not read filing ({type(e).__name__}: {e})")
            continue
        print(f"  {f['ticker']}: {rec['person'] if rec else 'no named person found'}")
        if rec:
            out[f["exchange_id"]] = rec
    return out


def main(hours, with_people):
    filings_path = CACHE / "filings.json"
    if not filings_path.exists():
        raise SystemExit("missing data/cache/filings.json: run `python -m pipeline.fetch_filings 14` first")
    filings = json.loads(filings_path.read_text())
    network = json.loads((ROOT / "data" / "network" / "synthetic_network.json").read_text())
    names = {t: n for t, n, _ in PORTFOLIO}
    by_ticker = {e["ticker"]: e["key"] for e in network["employers"] if e["ticker"]}
    quarters = {p.stem: json.loads(p.read_text()) for p in (CACHE / "quarters").glob("*.json")} if (CACHE / "quarters").exists() else {}
    now = datetime.now(IST)
    people = read_people(filings, network["employers"], hours, now) if with_people else {}
    result = feed.build_feed(filings, feed.load_prices(CACHE / "prices.csv"), quarters, names, by_ticker,
                             now, hours, people=people, bake_alerts=False)
    result["provider"] = llm.provider() if with_people else None
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    kinds = {}
    for i in result["items"]:
        kinds[i["type"]] = kinds.get(i["type"], 0) + 1
    print(f"{len(result['items'])} cards {kinds}; {result['routine_hidden']} routine filings hidden")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    args = sys.argv[1:]
    people_flag = "--people" in args
    nums = [a for a in args if a.isdigit()]
    main(int(nums[0]) if nums else 48, people_flag)
