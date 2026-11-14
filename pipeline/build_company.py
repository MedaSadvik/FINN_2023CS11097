"""Build everything FINN needs for ONE company, from nothing. Works for any NSE ticker on screener.

    python -m pipeline.build_company KAYNES          # last 4 earnings calls
    python -m pipeline.build_company TCS 6

Steps: find documents -> quarterly actuals -> for each of the latest N calls: download the
transcript, extract text, extract guidance (verified) -> check promises against actuals.
Every step caches, so a second run is instant. This is the "cold path": the same code serves
the demo stocks and a ticker nobody planned for.
"""
import json
import sys
import time

from pipeline import delivered, fetch_docs, fetch_pdf, fetch_quarters, guidance, insight, llm, verdicts


def build(ticker: str, n_calls: int = 4, exit_on_quota: bool = True) -> list:
    print(f"== {ticker}: finding documents")
    docs = fetch_docs.fetch_docs(ticker)
    seen, calls = set(), []
    for t in docs["transcripts"]:  # screener lists newest first
        if t["period"] and t["period"] not in seen:
            seen.add(t["period"])
            calls.append(t)
    calls = calls[:n_calls]
    if not calls:
        raise SystemExit(f"{ticker}: no transcripts found on screener.in")

    print(f"== {ticker}: quarterly actuals")
    q = fetch_quarters.fetch_quarters(ticker)
    fetch_quarters.OUT_DIR.mkdir(parents=True, exist_ok=True)
    (fetch_quarters.OUT_DIR / f"{ticker}.json").write_text(json.dumps(q, indent=1))
    print(f"   {len(q)} quarters, latest {list(q)[-1] if q else '-'}")

    for t in calls:
        period = t["period"]
        print(f"== {ticker} {period}: transcript + guidance")
        try:
            doc = fetch_pdf.ensure_text(ticker, period, t["url"])
        except Exception as e:  # one bad link must not stop the rest
            print(f"   SKIPPED: {type(e).__name__}: {str(e)[:100]}")
            continue
        try:
            result = guidance.run(ticker, period, doc, call_label=t.get("label"))
        except llm.QuotaExhausted as e:
            if not exit_on_quota:
                raise  # a caller that runs unattended (the on-demand worker) reports this itself
            raise SystemExit(f"\nSTOPPED: {e}.\nNothing is lost: finished calls are cached. Run the same command "
                             f"again later and it continues from here.")
        print(f"   {len(doc['pages'])} pages -> {len(result['claims'])} verified claims "
              f"({len(result['dropped'])} dropped), model {result['model']}")
        time.sleep(1)

    print(f"== {ticker}: promised vs delivered")
    rows = verdicts.evaluate_ticker(ticker)
    verdicts.main(ticker)
    for name, step in (("later-call check", delivered.main), ("business snapshot", insight.main)):
        print(f"== {ticker}: {name}")
        try:  # extras: the research is still worth keeping if one of them cannot run
            step(ticker)
        except llm.QuotaExhausted as e:
            print(f"   left for later (quota): {e}")
        except Exception as e:
            print(f"   skipped: {type(e).__name__}: {str(e)[:100]}")
    return rows


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit("usage: python -m pipeline.build_company TICKER [N_CALLS]")
    build(args[0].upper(), int(args[1]) if len(args) > 1 else 4)
