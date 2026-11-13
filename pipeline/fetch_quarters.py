"""Quarterly actuals (Revenue, EBITDA, PBT, PAT) from screener.in's "Quarterly Results" table.

    python -m pipeline.fetch_quarters KAYNES

This is the "delivered" side of promised-vs-delivered, and a cross-check for the results
filings. Plain HTML parsing, no LLM, no cost. Output: data/cache/quarters/<TICKER>.json

Verified against real screener HTML: <th data-date-key="2026-06-30"> column headers, and the
first row (Sales). ASSUMED, not yet seen: the other rows are labelled "Operating Profit",
"Profit before tax", "Net Profit" in a <td class="text"> first cell. The printout shows what
was found so a wrong guess is obvious.
Banks label rows differently ("Revenue", "Financing Profit"); both spellings are accepted.
"""
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "quarters"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# screener row label (lowercase, start of text) -> our field
ROW_MAP = [("sales", "revenue"), ("revenue", "revenue"), ("operating profit", "ebitda"),
           ("financing profit", "ebitda"), ("profit before tax", "pbt"), ("net profit", "pat"),
           ("opm", "opm_pct"), ("financing margin", "opm_pct")]


def quarter_label(date_key: str) -> str:
    """Quarter-end date -> Indian fiscal label. 2026-06-30 -> Q1FY27, 2026-03-31 -> Q4FY26."""
    year, month = int(date_key[:4]), int(date_key[5:7])
    q = {6: 1, 9: 2, 12: 3, 3: 4}[month]
    fy = year + 1 if month >= 6 else year
    return f"Q{q}FY{fy % 100:02d}"


def to_number(text: str):
    t = text.replace(",", "").replace("%", "").strip()
    try:
        return float(t)
    except ValueError:
        return None  # blank or "-" : the company had not reported that line


class Table(HTMLParser):
    """Collect header date keys and each body row as (label, [cell texts])."""

    def __init__(self):
        super().__init__()
        self.dates, self.rows = [], []
        self._row, self._cell, self._in_thead = None, None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "thead":
            self._in_thead = True
        elif tag == "th" and a.get("data-date-key"):
            self.dates.append(a["data-date-key"])
        elif tag == "tr" and not self._in_thead:
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag == "thead":
            self._in_thead = False
        elif tag == "td" and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).replace("\xa0", " ").split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append((self._row[0], self._row[1:]))
            self._row = None


def parse_quarters(html: str) -> dict:
    """{'Q1FY27': {'revenue': 297.0, 'ebitda': ..., 'pbt': ..., 'pat': ..., 'opm_pct': ...}, ...}"""
    start = html.find('id="quarters"')
    if start == -1:
        return {}
    end = html.find("</section>", start)
    t = Table()
    t.feed(html[start:end if end != -1 else None])
    out = {quarter_label(d): {} for d in t.dates}
    for label, cells in t.rows:
        clean = re.sub(r"[+\s]+$", "", label).strip().lower()
        field = next((f for prefix, f in ROW_MAP if clean.startswith(prefix)), None)
        if field is None:
            continue
        for date_key, cell in zip(t.dates, cells):
            out[quarter_label(date_key)].setdefault(field, to_number(cell))  # first matching row wins
    return out


def fetch_quarters(ticker: str) -> dict:
    import requests
    for variant in ("consolidated/", ""):
        r = requests.get(f"https://www.screener.in/company/{ticker}/{variant}",
                         headers={"User-Agent": UA}, timeout=25)
        if r.status_code == 200:
            q = parse_quarters(r.text)
            if q:
                return q
    return {}


def main(tickers):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for t in tickers:
        q = fetch_quarters(t)
        (OUT_DIR / f"{t}.json").write_text(json.dumps(q, indent=1))
        print(f"{t}: {len(q)} quarters")
        print(f"   {'quarter':8s} {'revenue':>9s} {'ebitda':>9s} {'pbt':>9s} {'pat':>9s}")
        for period in list(q)[-6:]:
            r = q[period]
            print(f"   {period:8s} " + " ".join(f"{r.get(k) if r.get(k) is not None else '-':>9}"
                                                  for k in ("revenue", "ebitda", "pbt", "pat")))
        time.sleep(1.5)


if __name__ == "__main__":
    from pipeline.config import TICKERS
    main([a.upper() for a in sys.argv[1:]] or TICKERS)
