"""Build research for the whole portfolio in one go, and keep going when one company fails.

    python scripts/build_portfolio.py                 # every portfolio stock not yet built
    python scripts/build_portfolio.py TCS INFY        # only these
    python scripts/build_portfolio.py --calls 2       # read fewer calls per company (faster, fewer promises)

Uses whatever model the root .env selects (LLM_PROVIDER). With the Hyde test model this costs no Gemini quota; the
output is labelled Draft on the website. Companies already built with Gemini are never replaced by another model.
Safe to stop and start again: every step caches, and finished companies are skipped.
Each finished company is written to frontend/data/companies.json straight away. Commit that file when done.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "frontend" / "data" / "companies.json"


def run(tickers, existing, build, export, provider, say=print):
    """Returns {ticker: 'built' | 'skipped' | 'no_data' | 'quota' | 'failed'}. `build` and `export` are injected."""
    result = {}
    for t in tickers:
        have = existing.get(t, {})
        if have.get("provider") == "gemini" and provider != "gemini":
            result[t] = "skipped"
            say(f"-- {t}: already built with Gemini, leaving it")
            continue
        if have and have.get("provider") == provider:
            result[t] = "skipped"
            say(f"-- {t}: already built with {provider}")
            continue
        started = time.time()
        try:
            build(t)
            export(t)
            result[t] = "built"
            say(f"-- {t}: built in {(time.time() - started) / 60:.1f} min")
        except SystemExit as e:  # the pipeline exits with a sentence for no transcripts or a stopped model
            text = str(e)
            result[t] = "quota" if "quota" in text.lower() else "no_data" if "no transcripts" in text.lower() else "failed"
            say(f"-- {t}: {result[t]}: {text.strip()[:160]}")
        except Exception as e:  # one company must never stop the rest
            result[t] = "failed"
            say(f"-- {t}: failed: {type(e).__name__}: {str(e)[:160]}")
        if result[t] == "quota":
            say("-- model quota is used up; stopping. Run the same command later and it continues.")
            break
    return result


def main(argv):
    from pipeline import build_company, llm
    from pipeline.config import PORTFOLIO
    import export_frontend

    calls = 4
    if "--calls" in argv:
        i = argv.index("--calls")
        calls = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    tickers = [a.upper() for a in argv] or [t for t, _, _ in PORTFOLIO]
    existing = json.loads(DATA.read_text()) if DATA.exists() else {}
    print(f"provider: {llm.provider()}, {len(tickers)} companies, {calls} calls each")
    result = run(tickers, existing, lambda t: build_company.build(t, calls),
                 lambda t: export_frontend.main([t]), llm.provider())
    print("\nsummary")
    for status in ("built", "skipped", "no_data", "quota", "failed"):
        names = [t for t, s in result.items() if s == status]
        if names:
            print(f"  {status:<8} {len(names)}: {' '.join(names)}")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    main(sys.argv[1:])
