import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import export

QUOTE = "For the full year we expect OSAT and PCB together to deliver about 500 crores of revenue this year."


def row(outcome, quote=QUOTE, low=500, high=None, **extra):
    return {"made_in": "Q1FY27", "outcome": outcome, "delivered_text": extra.get("text"),
            "reason": extra.get("reason"),
            "claim": {"page": 14, "quote": quote, "target": "OSAT+PCB revenue 500 cr", "horizon": "FY27",
                      "low": low, "high": high}}


def test_mark_is_a_real_substring_around_the_numbers():
    m = export.mark_span(QUOTE, 500, None)
    assert m in QUOTE and "500" in m and len(m) < len(QUOTE)


def test_mark_falls_back_to_whole_quote_without_numbers():
    assert export.mark_span("We will grow at twice the market rate.", None, None) == "We will grow at twice the market rate."


def test_mark_survives_decimals_and_ranges():
    q = "We guide for 30-35% growth and about 12.5% margins in the coming year for sure."
    assert "12.5" in export.mark_span(q, 12.5, None)
    assert "30" in export.mark_span(q, 30, 35)


def test_quote_whitespace_is_normalised_but_text_unchanged():
    p = export.to_pledge(row("missed", quote="line one\n  line two with 500 crores"))
    assert p["quote"] == "line one line two with 500 crores" and p["mark"] in p["quote"]


def test_unclear_always_has_a_reason_and_checkable_ones_do_not():
    assert export.to_pledge(row("unclear"))["reason"]
    assert "reason" not in export.to_pledge(row("missed", text="3626 vs 4000"))


def test_company_sorted_missed_first_and_quarters_chronological():
    quarters = {q: {"revenue": 1, "ebitda": 1, "pbt": 1, "pat": 1} for q in ["Q1FY27", "Q4FY25", "Q4FY26", "Q1FY26"]}
    c = export.build_company("KAYNES", "Kaynes", "kaynes", [row("unclear"), row("pending"), row("missed")], quarters, "gemini")
    assert [p["outcome"] for p in c["promises"]] == ["missed", "pending", "unclear"]
    assert [q["quarter"] for q in c["quarters"]] == ["Q4FY25", "Q1FY26", "Q4FY26", "Q1FY27"]


def test_mark_finds_numbers_written_with_commas():
    q = "We will cross 4,000 crores of revenue in FY26 as a minimum, and we are confident about that."
    m = export.mark_span(q, 4000, None)
    assert "4,000" in m and m != q


def test_website_portfolio_matches_pipeline_config():
    import re
    from pipeline.config import PORTFOLIO
    ts = (Path(__file__).resolve().parent.parent / "frontend" / "lib" / "portfolio.ts").read_text()
    assert re.findall(r'ticker: "([A-Z0-9]+)", name: "([^"]+)"', ts) == [(t, n) for t, n, _ in PORTFOLIO]


def test_later_call_evidence_is_carried_to_the_page():
    r = row("delivered", text="310 cr vs 300 cr guided")
    r["evidence"] = {"period": "Q4FY26", "page": 2, "quote": "OSAT delivered 310 crore"}
    assert export.to_pledge(r)["evidence"]["page"] == 2
    assert "evidence" not in export.to_pledge(row("missed"))


def test_snapshot_is_attached_only_when_it_has_something_to_show():
    q = {"Q1FY27": {"revenue": 1, "ebitda": 1, "pbt": 1, "pat": 1}}
    snap = {"business": {"summary": "s", "segments": [{"name": "A", "page": 1, "quote": "q"}]}, "bull": [], "bear": [],
            "period": "Q1FY27", "provider": "gemini", "source_sha256": "x"}
    c = export.build_company("K", "K", None, [row("missed")], q, "gemini", snap)
    assert c["snapshot"]["period"] == "Q1FY27" and "source_sha256" not in c["snapshot"]
    empty = {**snap, "business": {"summary": "", "segments": []}}
    assert "snapshot" not in export.build_company("K", "K", None, [row("missed")], q, "gemini", empty)
    assert "snapshot" not in export.build_company("K", "K", None, [row("missed")], q, "gemini")
