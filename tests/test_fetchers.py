import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline.fetch_docs import parse_documents, period_from_call
from pipeline.fetch_filings import normalise, parse_nse_time

# Real shape, copied from the Day-1 probe of KAYNES (field names and values as returned by NSE).
NSE_ITEM = {
    "an_dt": "02-Nov-2026 20:37:31",
    "desc": "Acquisition",
    "attchmntText": "Kaynes Technology has incorporated a wholly owned subsidiary in Saudi Arabia.",
    "attchmntFile": "https://nsearchives.nseindia.com/corporate/KAYNESTECH_02112026203640_SEIncorporationKaynesArabia.pdf",
    "seq_id": "123456",
    "symbol": "KAYNES",
}


def test_normalise_nse_item():
    row = normalise(NSE_ITEM, "KAYNES")
    assert row["category"] == "M&A" and row["priority"] == 3
    assert row["exchange"] == "NSE" and row["exchange_id"] == "123456"
    assert row["announced_at"] == "2026-11-02T20:37:31+05:30"
    assert row["pdf_url"].endswith(".pdf")


def test_normalise_missing_fields():
    row = normalise({"an_dt": "07-Oct-2026 15:10:27", "desc": "Trading Window"}, "KAYNES")
    assert row["category"] == "unclassified" and row["pdf_url"] is None
    assert row["exchange_id"]  # falls back to a synthetic id, never empty


def test_parse_nse_time():
    assert parse_nse_time(" 18-Sep-2026 17:10:36 ").hour == 17


@pytest.mark.parametrize("month,year,expected", [
    (10, 2026, "Q2FY27"), (11, 2026, "Q2FY27"), (8, 2025, "Q1FY26"),
    (1, 2026, "Q3FY26"), (2, 2026, "Q3FY26"), (5, 2026, "Q4FY26"), (6, 2026, "Q4FY26"),
])
def test_period_from_call(month, year, expected):
    assert period_from_call(month, year) == expected


# Annual-report markup is REAL (pasted from screener.in/company/KAYNES). The concall block is
# an ASSUMED shape: replace with real HTML once seen.
HTML = """
<ul class="list-links">
  <li>
    <a href="https://www.bseindia.com/xml-data/corpfiling/AttachHis/aaa.pdf"
       class="plausible-event-name=Annual+Report" target="_blank">Annual Report 2026</a>
    <div class="flex"><span class="ink-600 smaller">from bse</span>
      <button type="button" data-url="/annual-reports/1/summary/">AI Summary</button></div>
  </li>
  <li><a href="https://x/bbb.pdf">Annual Report 2025</a></li>
</ul>
<ul class="list-links">
  <li><div class="ink-600">Oct 2026</div>
      <a href="https://x/ccc.pdf">Transcript</a> <a href="https://x/ppt.pdf">PPT</a></li>
  <li><div>Aug 2026</div><a href="https://x/ddd.pdf">Transcript</a></li>
  <li><div>Jun 2026</div><a href="https://x/eee.pdf">Notes</a></li>
</ul>
"""


def test_parse_documents():
    d = parse_documents(HTML)
    assert [a["year"] for a in d["annual_reports"]] == [2026, 2025]
    assert d["annual_reports"][0]["source"] == "from bse"
    assert [(t["label"], t["period"]) for t in d["transcripts"]] == [("Oct 2026", "Q2FY27"), ("Aug 2026", "Q1FY27")]
    assert all(t["url"].startswith("https://") for t in d["transcripts"])
