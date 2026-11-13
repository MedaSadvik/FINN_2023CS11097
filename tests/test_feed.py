import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import alerts, feed, people

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 11, 10, 18, 0, tzinfo=IST)
EMPLOYERS = [{"key": "syrma", "name": "Syrma SGS", "ticker": "SYRMA"}, {"key": "dixon", "name": "Dixon", "ticker": "DIXON"}]


def filing(cat, prio, hours_ago, ticker="KAYNES", subject="s", i=[0]):
    i[0] += 1
    return {"ticker": ticker, "exchange_id": f"id{i[0]}", "category": cat, "priority": prio, "subject": subject,
            "detail": "detail text", "pdf_url": "http://x/f.pdf",
            "announced_at": (NOW - timedelta(hours=hours_ago)).isoformat()}


def build(filings, **kw):
    return feed.build_feed(filings, kw.pop("prices", {}), kw.pop("quarters", {}), {"KAYNES": "Kaynes"},
                           {"KAYNES": "kaynes"}, NOW, **kw)


def test_window_excludes_old_filings_and_hides_routine():
    out = build([filing("M&A", 3, 2), filing("M&A", 3, 100), filing("press_release", 1, 2), filing("unclassified", 0, 2)])
    assert len(out["items"]) == 1 and out["routine_hidden"] == 1  # priority 0 is dropped silently, 1 is counted


def test_ranked_by_priority_then_newest():
    out = build([filing("dividend", 2, 1), filing("M&A", 3, 10), filing("capex", 3, 3)])
    assert [i["category"] for i in out["items"]] == ["capex", "M&A", "dividend"]


def test_management_change_becomes_its_own_card_with_person():
    f = filing("management_change", 3, 1)
    rec = {"person": "A B", "history": []}
    item = build([f], people={f["exchange_id"]: rec})["items"][0]
    assert item["type"] == "mgmt_change" and item["person"] == rec


def test_results_card_uses_real_quarters_else_falls_back_to_event():
    q = lambda r: {"revenue": r, "ebitda": 1, "pbt": 1, "pat": 1}
    f = filing("results", 3, 1)
    full = build([f], quarters={"KAYNES": {"Q1FY27": q(9), "Q4FY26": q(8), "Q1FY26": q(7)}})["items"][0]
    assert full["type"] == "results" and full["qoq"]["revenue"] == 8 and full["yoy"]["revenue"] == 7
    assert build([f], quarters={"KAYNES": {"Q1FY27": q(9)}})["items"][0]["type"] == "event"
    assert build([f])["items"][0]["type"] == "event"


def test_alert_card_from_prices_and_none_when_quiet():
    quiet = [(f"2026-10-{d:02d}", 100.0, 1000) for d in range(1, 22)]
    loud = quiet[:-1] + [("2026-10-22", 90.0, 5000)]
    out = build([], prices={"KAYNES": loud, "OTHER": quiet})
    assert [i["type"] for i in out["items"]] == ["alert"]
    a = out["items"][0]
    assert a["volume_x"] == 5.0 and a["price_pct"] == -10.0


def test_person_must_be_in_filing_text():
    text = "The Board appointed Mr Anil Verma as Chief Operating Officer. He earlier worked at Syrma SGS Technology Limited as Head of Operations."
    raw = {"person": "Anil Verma", "role": "Chief Operating Officer", "event": "appointment",
           "quote": "The Board appointed Mr Anil Verma as Chief Operating Officer.",
           "history": [{"employer": "Syrma SGS Technology Limited", "title": "Head of Operations", "start_year": 2019, "end_year": 2023},
                       {"employer": "Made Up Corp", "title": "CEO", "start_year": 2010, "end_year": 2018}]}
    rec = people.verify(raw, text, EMPLOYERS)
    assert rec["person"] == "Anil Verma" and rec["quote"]
    assert [h["employer"] for h in rec["history"]] == ["Syrma SGS Technology Limited"]  # invented employer dropped
    assert rec["history"][0]["employer_key"] == "syrma"


def test_invented_person_or_quote_is_rejected():
    text = "The Board noted the resignation of the Company Secretary."
    assert people.verify({"person": "Ghost Person", "history": []}, text, EMPLOYERS) is None
    rec = people.verify({"person": "Company Secretary", "quote": "something never said in the filing at all", "history": []}, text, EMPLOYERS)
    assert rec["quote"] is None


def test_employer_matching_ignores_suffixes_and_rejects_short_names():
    assert people.match_employer("Dixon Technologies (India) Limited", EMPLOYERS) == "dixon"
    assert people.match_employer("Syrma", EMPLOYERS) == "syrma"
    assert people.match_employer("TI", EMPLOYERS) is None
    assert people.match_employer("Unrelated Industries", EMPLOYERS) is None


def test_extract_person_uses_model_and_verifies(monkeypatch, tmp_path):
    from pipeline import llm
    monkeypatch.setattr(llm, "CACHE", tmp_path)
    monkeypatch.setenv("GEMINI_FLASH_MODEL", "m")
    text = "Ms Ritu Rao has resigned as Chief Financial Officer with effect from 1 December."
    call = lambda m, s, p: '{"person": "Ritu Rao", "role": "Chief Financial Officer", "event": "resignation", "quote": "Ms Ritu Rao has resigned as Chief Financial Officer with effect from 1 December.", "history": []}'
    rec = people.extract_person(text, EMPLOYERS, call=call)
    assert rec["person"] == "Ritu Rao" and rec["event"] == "resignation"


def test_client_side_alerts_ship_price_rows_and_routine_times():
    quiet = [(f"2026-10-{d:02d}", 100.0, 1000) for d in range(1, 29)] + [(f"2026-11-{d:02d}", 100.0, 1000) for d in range(1, 21)]
    out = build([filing("press_release", 1, 2), filing("press_release", 1, 30)], prices={"KAYNES": quiet}, bake_alerts=False)
    assert out["items"] == [] and out["routine_hidden"] == 2 and len(out["routine_filed"]) == 2
    rows = out["market"]["KAYNES"]["rows"]
    assert len(rows) == feed.MARKET_ROWS and rows[-1] == ["2026-11-20", 100.0, 1000]
    assert out["market"]["KAYNES"]["company"] == "Kaynes" and out["market"]["KAYNES"]["employer_key"] == "kaynes"
    assert "market" not in build([], prices={"KAYNES": quiet})  # default keeps the old behaviour


def test_ts_alert_fixture_matches_python():
    """frontend/lib/alerts.fixture.json is what the TypeScript port is tested against. If this fails, the maths changed."""
    import json
    for c in json.loads((Path(__file__).resolve().parent.parent / "frontend" / "lib" / "alerts.fixture.json").read_text()):
        assert alerts.check_all([tuple(r) for r in c["rows"]], c["rules"]) == c["expect"], c["name"]
