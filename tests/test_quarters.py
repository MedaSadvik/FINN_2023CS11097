import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline.fetch_quarters import parse_quarters, quarter_label, to_number


@pytest.mark.parametrize("date,expected", [
    ("2026-06-30", "Q1FY27"), ("2026-09-30", "Q2FY27"), ("2025-12-31", "Q3FY26"), ("2026-03-31", "Q4FY26"),
])
def test_quarter_label(date, expected):
    assert quarter_label(date) == expected


def test_to_number():
    assert to_number("1,234") == 1234.0
    assert to_number("-12") == -12.0
    assert to_number("15.6 %") == 15.6
    assert to_number("") is None and to_number("-") is None


# Header and the Sales row are REAL (pasted from screener.in/company/KAYNES). The remaining
# row labels are ASSUMED; replace with real HTML once seen.
HTML = """
<section id="quarters" class="card card-large"><h2>Quarterly Results</h2>
<table class="data-table"><thead><tr><th class="text"></th>
  <th class="highlight-cell" data-date-key="2025-06-30">Jun 2025</th>
  <th class="" data-date-key="2025-09-30">Sep 2025</th>
  <th class="highlight-cell" data-date-key="2026-06-30">Jun 2026</th></tr></thead>
<tbody>
<tr class="stripe"><td class="text"><button class="button-plain">Sales&nbsp;<span class="blue-icon">+</span></button></td>
  <td class="highlight-cell">1,297</td><td class="">1,361</td><td class="">2,046</td></tr>
<tr><td class="text">Expenses&nbsp;+</td><td>1,100</td><td>1,150</td><td>1,700</td></tr>
<tr><td class="text">Operating Profit</td><td>197</td><td>211</td><td></td></tr>
<tr><td class="text">OPM %</td><td>15%</td><td>16%</td><td>15.6%</td></tr>
<tr><td class="text">Profit before tax</td><td>150</td><td>160</td><td>260</td></tr>
<tr><td class="text">Net Profit&nbsp;+</td><td>-12</td><td>120</td><td>204</td></tr>
</tbody></table></section>
<section id="profit-loss"><table><thead><tr><th data-date-key="2020-03-31">Mar 2020</th></tr></thead>
<tbody><tr><td class="text">Sales</td><td>1</td></tr></tbody></table></section>
"""


def test_parse_quarters():
    q = parse_quarters(HTML)
    assert list(q) == ["Q1FY26", "Q2FY26", "Q1FY27"]
    assert q["Q1FY27"]["revenue"] == 2046.0
    assert q["Q1FY26"] == {"revenue": 1297.0, "ebitda": 197.0, "opm_pct": 15.0, "pbt": 150.0, "pat": -12.0}
    assert q["Q1FY27"]["ebitda"] is None          # blank cell, not zero
    assert q["Q1FY27"]["pat"] == 204.0
    assert "expenses" not in str(q).lower()        # unmapped rows ignored


def test_parse_ignores_other_sections_and_missing_section():
    assert parse_quarters("<section id='profit-loss'></section>") == {}
    assert "Q4FY20" not in parse_quarters(HTML)    # annual table after the quarterly one is not read
