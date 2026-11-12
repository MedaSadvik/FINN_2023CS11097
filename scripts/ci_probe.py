"""Can GitHub's servers reach the sources the pipeline needs? No keys, no model calls.

    python scripts/ci_probe.py TCS
Prints one OK/FAIL line per step. Used by .github/workflows/probe.yml.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import fetch_docs, fetch_pdf, fetch_quarters

ticker = (sys.argv[1] if len(sys.argv) > 1 else "TCS").upper()
failed = 0


def step(name, fn):
    global failed
    t = time.time()
    try:
        detail = fn()
        print(f"OK    {name:<28} {detail}  ({time.time() - t:.1f}s)")
        return True
    except Exception as e:  # report, keep going
        failed += 1
        print(f"FAIL  {name:<28} {type(e).__name__}: {str(e)[:160]}")
        return False


docs = {}
step("screener: document links", lambda: docs.update(fetch_docs.fetch_docs(ticker)) or
     f"{len(docs['transcripts'])} transcripts, {len(docs.get('annual_reports', []))} annual reports")
step("screener: quarterly numbers", lambda: f"{len(fetch_quarters.fetch_quarters(ticker))} quarters")
if docs.get("transcripts"):
    t = docs["transcripts"][0]
    step("transcript PDF download", lambda: f"{t['url'].split('/')[2]}, "
         f"{len(fetch_pdf.ensure_text(ticker, t['period'] or 'probe', t['url'])['pages'])} pages")
print("RESULT:", "all reachable" if not failed else f"{failed} step(s) blocked")
sys.exit(1 if failed else 0)
