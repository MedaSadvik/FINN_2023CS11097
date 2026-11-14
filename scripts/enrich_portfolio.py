"""Add the newer research steps to companies already built, using transcripts already downloaded.

    python scripts/enrich_portfolio.py KAYNES          # one company, Gemini (the shipped data)
    python scripts/enrich_portfolio.py                 # every company in the portfolio
    LLM_PROVIDER=openai_compat python scripts/enrich_portfolio.py CGPOWER   # test model: output is labelled Draft

For each company: re-check promises (free arithmetic, now with "pending" for years still running),
settle segment promises from later calls (up to 3 model requests), write the business summary and
bull/bear (1 request), then re-export frontend/data/companies.json. Nothing is downloaded again.
When the daily free quota runs out it stops cleanly; run it again tomorrow and it carries on, since
every answer is cached.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import delivered, insight, llm, verdicts  # noqa: E402
from pipeline.config import TICKERS  # noqa: E402
import scripts.export_frontend as export_frontend  # noqa: E402

llm.load_env()


def enrich(ticker: str) -> str:
    cache = llm.ROOT / "data" / "cache"
    if not (cache / "quarters" / f"{ticker}.json").exists() or not list((cache / "text").glob(f"{ticker}_*.json")):
        return "skipped (not built here yet)"
    verdicts.main(ticker)
    delivered.main(ticker)
    insight.main(ticker)
    return "done"


def main(tickers, force=False):
    done = []
    for t in tickers:
        print(f"\n== {t}")
        try:
            status = enrich(t)
        except llm.QuotaExhausted as e:
            print(f"STOPPED: {e}. Run again later; finished work is cached.")
            break
        print(f"   {status}")
        if status == "done":
            done.append(t)
    if done:
        export_frontend.main(done, force=force)
    print(f"\nenriched: {', '.join(done) or 'none'}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    main([a.upper() for a in args] or TICKERS, force="--force" in sys.argv)
