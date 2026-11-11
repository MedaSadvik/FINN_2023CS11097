"""Write website data from the pipeline cache.

    python scripts/export_frontend.py KAYNES [TICKER ...]

Reads  data/cache/<verdicts>/TICKER.json, data/cache/quarters/TICKER.json, data/network/synthetic_network.json
Writes frontend/data/companies.json (merged by ticker). Commit that file: the website is built from it.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import llm
from pipeline.config import PORTFOLIO
from pipeline.export import build_company

OUT = ROOT / "frontend" / "data" / "companies.json"


def main(tickers):
    names = {t: n for t, n, _ in PORTFOLIO}
    employers = {e["ticker"]: e["key"] for e in
                 json.loads((ROOT / "data" / "network" / "synthetic_network.json").read_text())["employers"] if e["ticker"]}
    cache = ROOT / "data" / "cache"
    merged = json.loads(OUT.read_text()) if OUT.exists() else {}
    for t in tickers:
        verdicts = cache / llm.derived("verdicts") / f"{t}.json"
        quarters = cache / "quarters" / f"{t}.json"
        if not verdicts.exists() or not quarters.exists():
            raise SystemExit(f"{t}: run `python -m pipeline.build_company {t}` first (missing {verdicts.name} or quarters)")
        provider = llm.provider()
        merged[t] = build_company(t, names.get(t, t), employers.get(t), json.loads(verdicts.read_text()),
                                  json.loads(quarters.read_text()), provider)
        counts = {}
        for p in merged[t]["promises"]:
            counts[p["outcome"]] = counts.get(p["outcome"], 0) + 1
        print(f"{t}: {len(merged[t]['promises'])} promises {counts}, provider={provider}")
    OUT.write_text(json.dumps(merged, indent=1, ensure_ascii=False))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/export_frontend.py KAYNES [TICKER ...]")
    main([a.upper() for a in sys.argv[1:]])
