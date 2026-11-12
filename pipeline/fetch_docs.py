"""Find annual reports and concall transcripts for a ticker from screener.in.

    python -m pipeline.fetch_docs KAYNES

Only LINKS are collected here (no PDF download yet). Output: data/cache/docs/<TICKER>.json

Verified against real screener HTML: annual-report links read "Annual Report 2026".
ASSUMED (not yet seen): each concall row is an <li> whose first text is a month label
like "Oct 2026" and which holds an anchor reading "Transcript". If the printout looks
wrong, send me the "Concalls" HTML block and I will fix the parser.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "docs"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class ListItems(HTMLParser):
    """Collect every <li> as {text: [...], anchors: [(text, href)]}."""

    def __init__(self):
        super().__init__()
        self.items, self._cur, self._href, self._atext = [], None, None, []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self._cur = {"text": [], "anchors": []}
        elif tag == "a" and self._cur is not None:
            self._href, self._atext = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._cur is not None:
            if self._href is not None:
                self._atext.append(data)
            elif data.strip():
                self._cur["text"].append(" ".join(data.split()))

    def handle_endtag(self, tag):
        if tag == "a" and self._cur is not None and self._href is not None:
            self._cur["anchors"].append((" ".join("".join(self._atext).split()), self._href))
            self._href = None
        elif tag == "li" and self._cur is not None:
            self.items.append(self._cur)
            self._cur = None


def period_from_call(month: int, year: int) -> str:
    """Month a concall was held -> the quarter it discusses. Oct 2026 -> Q2FY27.

    Q1 results (Apr-Jun) are discussed Jul-Sep; Q2 in Oct-Dec; Q3 in Jan-Mar; Q4 in Apr-Jun.
    """
    if 7 <= month <= 9:
        return f"Q1FY{(year + 1) % 100:02d}"
    if 10 <= month <= 12:
        return f"Q2FY{(year + 1) % 100:02d}"
    if 1 <= month <= 3:
        return f"Q3FY{year % 100:02d}"
    return f"Q4FY{year % 100:02d}"


def parse_documents(html: str) -> dict:
    p = ListItems()
    p.feed(html)
    annual, transcripts = [], []
    for it in p.items:
        for text, href in it["anchors"]:
            m = re.fullmatch(r"Annual Report (\d{4})", text)
            if m:
                annual.append({"year": int(m.group(1)), "url": href,
                               "source": next((t for t in it["text"] if t.startswith("from ")), None)})
            elif text.lower() == "transcript":
                label = next((t for t in it["text"] if re.match(r"[A-Za-z]{3}\s+\d{4}", t)), None)
                period = None
                if label:
                    mon, yr = label.split()[:2]
                    if mon[:3].lower() in MONTHS:
                        period = period_from_call(MONTHS[mon[:3].lower()], int(yr))
                transcripts.append({"label": label, "period": period, "url": href})
    return {"annual_reports": sorted(annual, key=lambda a: -a["year"]),
            "transcripts": transcripts}


def parse_name(html: str):
    """Company name from the page heading, e.g. 'Tata Consultancy Services Ltd'. None if not found."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    name = " ".join(re.sub(r"<[^>]+>", "", m.group(1)).split()) if m else ""
    return name or None


def fetch_docs(ticker: str) -> dict:
    import requests
    for variant in ("consolidated/", ""):  # consolidated first, standalone as fallback
        r = requests.get(f"https://www.screener.in/company/{ticker}/{variant}",
                         headers={"User-Agent": UA}, timeout=25)
        if r.status_code == 200:
            docs = parse_documents(r.text)
            if docs["annual_reports"] or docs["transcripts"]:
                docs["name"] = parse_name(r.text)
                return docs
    return {"annual_reports": [], "transcripts": [], "name": None}


def main(tickers):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import time
    for t in tickers:
        d = fetch_docs(t)
        (OUT_DIR / f"{t}.json").write_text(json.dumps(d, indent=1))
        trs = d["transcripts"]
        print(f"{t}: {len(d['annual_reports'])} annual reports "
              f"(latest {d['annual_reports'][0]['year'] if d['annual_reports'] else '-'}), "
              f"{len(trs)} transcripts")
        for tr in trs[:4]:
            print(f"   {tr['label']!s:10s} {tr['period']!s:8s} {tr['url'][:90]}")
        time.sleep(1.5)


if __name__ == "__main__":
    from pipeline.config import TICKERS
    main([a.upper() for a in sys.argv[1:]] or TICKERS)
