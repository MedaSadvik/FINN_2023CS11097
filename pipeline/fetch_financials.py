"""Multi-year financials (profit and loss, balance sheet, cash flow, ratios) from screener.in's annual tables.

    python -m pipeline.fetch_financials KAYNES

Plain HTML parsing, no model, no cost. These are the company's own audited numbers as standardised by screener.in,
so they stay within the "primary data only" rule for research. Row labels were checked against the live KAYNES page
(P&L has an extra TTM column with no date key; the other tables do not). Output is per fiscal year, in rupees crore.
"""
import re
import sys
import time

from pipeline.fetch_quarters import UA, Table, to_number

KEEP_YEARS = 8
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# section id on the page -> [(screener row label prefix, lowercase) -> our field]. First match wins.
SECTIONS = {
    "profit-loss": [("sales", "revenue"), ("revenue", "revenue"), ("operating profit", "ebitda"), ("financing profit", "ebitda"),
                    ("opm", "opm_pct"), ("financing margin", "opm_pct"), ("other income", "other_income"),
                    ("interest", "interest"), ("depreciation", "depreciation"), ("profit before tax", "pbt"),
                    ("tax", "tax_pct"), ("net profit", "pat"), ("eps", "eps"), ("dividend payout", "payout_pct")],
    "balance-sheet": [("equity capital", "equity_capital"), ("reserves", "reserves"), ("borrowing", "borrowings"),
                      ("deposits", "deposits"), ("other liabilities", "other_liabilities"),
                      ("total liabilities", "total_liabilities"), ("fixed assets", "fixed_assets"), ("cwip", "cwip"),
                      ("investments", "investments"), ("other assets", "other_assets"), ("total assets", "total_assets")],
    "cash-flow": [("cash from operating", "cfo"), ("cash from investing", "cfi"), ("cash from financing", "cff"),
                  ("net cash flow", "net_cash"), ("free cash flow", "fcf"), ("cfo/ebitda", "cfo_to_ebitda_pct")],
    "ratios": [("debtor days", "debtor_days"), ("inventory days", "inventory_days"), ("days payable", "payable_days"),
               ("cash conversion cycle", "ccc_days"), ("working capital days", "wc_days"), ("roce", "roce_pct")],
}


def year_label(date_key: str) -> str:
    """2026-03-31 -> FY26. A company with another year end keeps its month: 2026-09-30 -> Sep 26."""
    year, month = int(date_key[:4]), int(date_key[5:7])
    return f"FY{year % 100:02d}" if month == 3 else f"{MONTHS[month]} {year % 100:02d}"


class AnnualTable(Table):
    """Like the quarterly Table, but keeps header position: the P&L has a TTM column that carries no date key."""

    def __init__(self):
        super().__init__()
        self.cols = []            # one entry per data column: a date key, or None (TTM and the like)
        self._th_count, self._in_head = 0, False

    def handle_starttag(self, tag, attrs):
        if tag == "thead":
            self._in_head = True
        if tag == "th" and self._in_head:
            self._th_count += 1
            if self._th_count > 1:  # the first header cell is the empty label column
                self.cols.append(dict(attrs).get("data-date-key"))
            return
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "thead":
            self._in_head = False
        super().handle_endtag(tag)


def _section(html: str, section_id: str) -> str:
    start = html.find(f'id="{section_id}"')
    if start == -1:
        return ""
    end = html.find("</section>", start)
    return html[start:end if end != -1 else None]


def parse_financials(html: str) -> dict:
    """{'years': ['FY24', ...], 'rows': {'FY24': {'revenue': 2000.0, ...}}} . Empty dict if there is no profit and loss table."""
    rows: dict = {}
    order: list = []
    for section_id, mapping in SECTIONS.items():
        block = _section(html, section_id)
        if not block:
            continue
        t = AnnualTable()
        t.feed(block)
        for label, cells in t.rows:
            clean = re.sub(r"[+\s]+$", "", label).strip().lower()
            field = next((f for prefix, f in mapping if clean.startswith(prefix)), None)
            if field is None:
                continue
            for date_key, cell in zip(t.cols, cells):
                if not date_key:
                    continue
                y = year_label(date_key)
                if y not in order:
                    order.append(y)
                rows.setdefault(y, {}).setdefault(field, to_number(cell))  # first matching row wins
    if not any("revenue" in r for r in rows.values()):
        return {}
    years = sorted(order, key=lambda y: _sort_key(y))[-KEEP_YEARS:]
    return {"years": years, "rows": {y: rows[y] for y in years}}


def _sort_key(label: str):
    if label.startswith("FY"):
        return (2000 + int(label[2:]), 3)
    mon, yy = label.split()
    return (2000 + int(yy), MONTHS.index(mon))


def fetch_financials(ticker: str) -> dict:
    """Consolidated figures when screener has them, else standalone. Empty dict when nothing could be read."""
    import requests
    for basis, variant in (("consolidated", "consolidated/"), ("standalone", "")):
        r = requests.get(f"https://www.screener.in/company/{ticker}/{variant}", headers={"User-Agent": UA}, timeout=25)
        if r.status_code == 200:
            parsed = parse_financials(r.text)
            if parsed:
                return {"basis": basis, **parsed}
    return {}


def missing_fields(f: dict) -> list:
    """Fields that screener did not give for the latest year, so a changed label is noticed instead of silently ignored."""
    if not f:
        return ["everything"]
    latest = f["rows"][f["years"][-1]]
    wanted = [field for m in SECTIONS.values() for _, field in m]
    return sorted({x for x in wanted if latest.get(x) is None} - {"deposits", "payout_pct", "eps", "fcf", "cfo_to_ebitda_pct"})


if __name__ == "__main__":
    for t in [a.upper() for a in sys.argv[1:]] or ["KAYNES"]:
        f = fetch_financials(t)
        print(t, f.get("basis"), f.get("years"), "| missing:", missing_fields(f))
        time.sleep(1.5)
