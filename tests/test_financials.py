import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.fetch_financials import missing_fields, parse_financials, year_label

TH = lambda *keys: "".join(f'<th data-date-key="{k}">x</th>' if k else "<th>TTM</th>" for k in keys)


def row(label, *cells):
    return f'<tr><td class="text">{label}</td>' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def table(section, keys, rows):
    return (f'<section id="{section}"><table class="data-table"><thead><tr><th class="text"></th>{TH(*keys)}</tr></thead>'
            f"<tbody>{''.join(rows)}</tbody></table></section>")


# Labels and the TTM column as seen on the live KAYNES page (values invented).
HTML = (
    table("profit-loss", ["2024-03-31", "2025-03-31", "2026-03-31", None], [
        row("Sales&nbsp;<span>+</span>", "1,800", "2,722", "3,626", "3,899"),
        row("Expenses&nbsp;+", "1,500", "2,305", "3,048", "3,290"),
        row("Operating Profit", "300", "416", "578", "609"),
        row("OPM %", "17%", "15%", "16%", "16%"),
        row("Interest", "50", "106", "121", "126"),
        row("Profit before tax", "250", "372", "504", "496"),
        row("Tax %", "21%", "21%", "28%", ""),
        row("Net Profit&nbsp;+", "200", "293", "364", "346"),
        row("EPS in Rs", "40.1", "45.8", "54.28", "51.57"),
    ]) +
    table("balance-sheet", ["2024-03-31", "2025-03-31", "2026-03-31"], [
        row("Equity Capital", "64", "64", "67"), row("Reserves", "2,423", "2,776", "4,681"),
        row("Borrowings&nbsp;+", "323", "903", "913"), row("Other Liabilities&nbsp;+", "456", "898", "1,233"),
        row("Total Liabilities", "3,265", "4,641", "6,894"), row("Fixed Assets&nbsp;+", "319", "845", "1,594"),
        row("CWIP", "105", "391", "511"), row("Investments", "132", "132", "257"),
        row("Other Assets&nbsp;+", "2,709", "3,273", "4,532"), row("Total Assets", "3,265", "4,641", "6,894"),
    ]) +
    table("cash-flow", ["2024-03-31", "2025-03-31", "2026-03-31"], [
        row("Cash from Operating Activity&nbsp;+", "88", "-82", "-600"),
        row("Cash from Investing Activity&nbsp;+", "-1,523", "-355", "-917"),
        row("Cash from Financing Activity&nbsp;+", "1,429", "465", "1,580"),
        row("Net Cash Flow", "-7", "28", "62"), row("Free Cash Flow", "-295", "-1,031", "-1,841"),
        row("CFO/EBITDA <span>Share of operating profit converting into cash</span>", "53%", "-4%", "-80%"),
    ]) +
    table("ratios", ["2024-03-31", "2025-03-31", "2026-03-31"], [
        row("Debtor Days", "72", "77", "154"), row("Inventory Days", "150", "156", "169"),
        row("Days Payable", "99", "131", "131"), row("Cash Conversion Cycle", "123", "102", "193"),
        row("Working Capital Days", "66", "-7", "133"), row("ROCE %", "15%", "14%", "13%"),
    ])
)


def test_year_label():
    assert year_label("2026-03-31") == "FY26"
    assert year_label("2026-09-30") == "Sep 26"


def test_parse_reads_every_table_and_drops_ttm():
    f = parse_financials(HTML)
    assert f["years"] == ["FY24", "FY25", "FY26"]
    r = f["rows"]["FY26"]
    assert r["revenue"] == 3626.0 and r["ebitda"] == 578.0 and r["opm_pct"] == 16.0 and r["pat"] == 364.0
    assert r["borrowings"] == 913.0 and r["reserves"] == 4681.0 and r["total_assets"] == 6894.0
    assert r["cfo"] == -600.0 and r["cfi"] == -917.0 and r["fcf"] == -1841.0 and r["cfo_to_ebitda_pct"] == -80.0
    assert r["debtor_days"] == 154.0 and r["ccc_days"] == 193.0 and r["roce_pct"] == 13.0
    assert "TTM" not in f["years"]
    assert f["rows"]["FY24"]["cfo"] == 88.0


def test_blank_cells_are_none_not_zero():
    f = parse_financials(HTML)
    assert f["rows"]["FY26"]["tax_pct"] == 28.0
    html = HTML.replace("<td>28%</td>", "<td></td>")
    assert parse_financials(html)["rows"]["FY26"]["tax_pct"] is None


def test_banks_use_other_labels():
    html = table("profit-loss", ["2025-03-31", "2026-03-31"], [
        row("Revenue&nbsp;+", "300,000", "350,000"), row("Financing Profit", "90,000", "100,000"),
        row("Financing Margin %", "30%", "29%"), row("Net Profit&nbsp;+", "60,000", "66,000")])
    f = parse_financials(html)
    assert f["rows"]["FY26"]["revenue"] == 350000.0 and f["rows"]["FY26"]["ebitda"] == 100000.0


def test_no_profit_and_loss_means_nothing():
    assert parse_financials("<html></html>") == {}
    assert parse_financials(table("balance-sheet", ["2026-03-31"], [row("Borrowings", "1")])) == {}


def test_missing_fields_reports_a_changed_label():
    f = parse_financials(HTML)
    assert missing_fields(f) == ["depreciation", "other_income"]  # the fixture has no such rows
    assert "revenue" not in missing_fields(f) and "borrowings" not in missing_fields(f)
    assert missing_fields({}) == ["everything"]


# ---- found on the live site: TTM header, half-year columns, a stale consolidated page
def with_ttm_key(html):
    """screener's TTM header carries the text TTM as its date key, not a date."""
    return html.replace("<th>TTM</th>", '<th data-date-key="TTM">TTM</th>')


def test_ttm_with_a_literal_ttm_key_is_dropped_not_a_crash():
    html = with_ttm_key(HTML)
    assert 'data-date-key="TTM"' in html
    f = parse_financials(html)
    assert f["years"] == ["FY24", "FY25", "FY26"]


def test_a_half_year_column_is_not_a_fiscal_year():
    html = HTML.replace('<th data-date-key="2026-03-31">x</th></tr></thead><tbody><tr><td class="text">Equity Capital',
                        '<th data-date-key="2026-03-31">x</th><th data-date-key="2026-09-30">x</th></tr></thead><tbody><tr><td class="text">Equity Capital')
    html = html.replace("<td>67</td></tr>", "<td>67</td><td>70</td></tr>", 1)  # a September balance sheet cell
    assert 'data-date-key="2026-09-30"' in html and "<td>70</td>" in html
    f = parse_financials(html)
    assert f["years"] == ["FY24", "FY25", "FY26"] and "Sep 26" not in f["rows"]


def page(last_year):
    return table("profit-loss", [f"{y}-03-31" for y in range(last_year - 2, last_year + 1)],
                 [row("Sales", "1", "2", "3"), row("Net Profit", "1", "1", "1")])


def test_a_stale_consolidated_page_loses_to_a_current_standalone_one():
    pages = {"consolidated/": page(2015), "": page(2026)}
    f = fetch_financials_with(pages)
    assert f["basis"] == "standalone" and f["years"][-1] == "FY26"


def test_a_current_consolidated_page_is_used_without_asking_for_the_other():
    asked = []
    pages = {"consolidated/": page(2026), "": page(2026)}
    f = fetch_financials_with(pages, asked)
    assert f["basis"] == "consolidated" and asked == ["consolidated/"]


def test_consolidated_missing_falls_back_to_standalone():
    f = fetch_financials_with({"consolidated/": None, "": page(2026)})
    assert f["basis"] == "standalone"


def test_nothing_readable_is_empty():
    assert fetch_financials_with({"consolidated/": None, "": "<html></html>"}) == {}


def fetch_financials_with(pages, asked=None):
    from pipeline.fetch_financials import fetch_financials

    def get(ticker, variant):
        if asked is not None:
            asked.append(variant)
        return pages[variant]
    return fetch_financials("X", get=get, this_year=2026)
