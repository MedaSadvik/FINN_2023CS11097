"""Day-1 probe: which data sources actually work from THIS machine?

Run on your laptop (home internet; the cloud sandbox is blocked from these sites):
    pip install -r requirements.txt
    python scripts/probe_sources.py            # all 17 tickers
    python scripts/probe_sources.py KAYNES DIXON   # just some

Checks per ticker:
  1. prices    - yfinance last ~30 days: rows, latest day
  2. nse       - NSE corporate announcements API (needs a cookie from the home page first)
  3. screener  - screener.in page: counts of concall transcript and annual report links

Writes data/cache/probe_report.json and prints a table. Nothing here is saved to a database.
The screener parsing is a first guess from link text; read the report and tell me what it got wrong.
"""
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.classify import classify
from pipeline.config import TICKERS, yahoo_symbol

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OUT = Path(__file__).resolve().parent.parent / "data" / "cache" / "probe_report.json"


def probe_prices(ticker):
    try:
        import yfinance as yf
        df = yf.Ticker(yahoo_symbol(ticker)).history(period="1mo")
        if df.empty:
            return {"ok": False, "error": "no rows"}
        return {"ok": True, "rows": len(df), "latest_day": str(df.index[-1].date()),
                "latest_volume": int(df["Volume"].iloc[-1])}
    except Exception as e:  # probe: report anything
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}


def nse_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                      "Referer": "https://www.nseindia.com/"})
    s.get("https://www.nseindia.com/", timeout=20)  # sets the cookies the API requires
    return s


def probe_nse(session, ticker):
    try:
        r = session.get("https://www.nseindia.com/api/corporate-announcements",
                        params={"index": "equities", "symbol": ticker}, timeout=20)
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        items = r.json()
        sample = []
        for it in items[:5]:
            subject = it.get("desc") or it.get("subject") or ""
            cat, prio = classify(subject)
            sample.append({"date": it.get("an_dt") or it.get("sort_date"), "subject": subject[:90],
                           "ours": cat, "priority": prio, "pdf": it.get("attchmntFile")})
        return {"ok": True, "count": len(items), "keys": sorted(items[0].keys()) if items else [],
                "sample": sample}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def probe_screener(ticker):
    out = {}
    for variant in ("consolidated/", ""):
        try:
            r = requests.get(f"https://www.screener.in/company/{ticker}/{variant}",
                             headers={"User-Agent": UA}, timeout=25)
            if r.status_code != 200:
                out[variant or "standalone"] = {"ok": False, "error": f"HTTP {r.status_code}"}
                continue
            p = Anchors()
            p.feed(r.text)
            transcripts = [(t, h) for t, h in p.links if re.search(r"transcript", t, re.I)]
            reports = [(t, h) for t, h in p.links if re.search(r"financial year \d{4}", t, re.I)]
            out[variant or "standalone"] = {
                "ok": True, "transcripts": len(transcripts), "annual_reports": len(reports),
                "transcript_sample": transcripts[:4], "report_sample": reports[:2]}
        except Exception as e:
            out[variant or "standalone"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200]}
        time.sleep(1)
    return out


def main():
    tickers = [t.upper() for t in sys.argv[1:]] or TICKERS
    try:
        nse = nse_session()
    except Exception as e:
        nse = None
        print("NSE session failed:", e)
    report = {}
    print(f"{'ticker':11s} {'prices':8s} {'nse':14s} {'screener transcripts / ARs'}")
    for t in tickers:
        row = {"prices": probe_prices(t), "nse": probe_nse(nse, t) if nse else {"ok": False, "error": "no session"},
               "screener": probe_screener(t)}
        report[t] = row
        sc = row["screener"].get("consolidated/", {})
        sc = sc if sc.get("ok") else row["screener"].get("standalone", {})
        print(f"{t:11s} {'ok' if row['prices']['ok'] else 'FAIL':8s} "
              f"{(str(row['nse'].get('count')) + ' items') if row['nse']['ok'] else 'FAIL':14s} "
              f"{str(sc.get('transcripts', '-')) + ' / ' + str(sc.get('annual_reports', '-')) if sc.get('ok') else 'FAIL'}")
        time.sleep(1.5)  # be polite; NSE bans fast scrapers
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, default=str))
    print(f"\nfull report: {OUT}")


if __name__ == "__main__":
    main()
