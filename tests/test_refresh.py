import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.refresh import Fetchers, refresh

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 11, 14, 18, 0, tzinfo=IST)
OLD_END = datetime(2026, 11, 13, 18, 0, tzinfo=IST)
NAMES = {"KAYNES": "Kaynes", "DIXON": "Dixon"}
EMP = {"KAYNES": "kaynes", "DIXON": "dixon"}
TICKERS = ["KAYNES", "DIXON"]


def filing(ticker, cat, prio, hours_ago, i=[0]):
    i[0] += 1
    return {"ticker": ticker, "exchange_id": f"id{i[0]}", "category": cat, "priority": prio, "subject": "s", "detail": "d",
            "pdf_url": "http://x/f.pdf", "announced_at": (NOW - timedelta(hours=hours_ago)).isoformat()}


def rows(close=100.0, n=30, last_day="2026-11-14"):
    return [(f"2026-10-{d:02d}", close, 1000) for d in range(1, n + 1)][:-1] + [(last_day, close, 1000)]


def boom(*a, **k):
    raise RuntimeError("blocked")


OLD = {"window": {"start": "x", "end": OLD_END.isoformat(), "hours": 336}, "routine_hidden": 3, "routine_filed": ["t1", "t2", "t3"],
       "filings_as_of": OLD_END.isoformat(), "provider": "gemini",
       "items": [{"id": "old1", "type": "event", "ticker": "KAYNES", "company": "Kaynes", "filed": "2026-11-12T10:00:00+05:30", "priority": 3},
                 {"id": "oldalert", "type": "alert", "ticker": "X", "company": "X", "filed": "2026-11-12", "priority": 2},
                 {"id": "mg1", "type": "mgmt_change", "ticker": "DIXON", "company": "Dixon", "filed": "2026-11-12T11:00:00+05:30",
                  "priority": 3, "person": {"person": "A B", "history": []}}],
       "market": {"KAYNES": {"company": "Kaynes", "employer_key": "kaynes", "rows": [["2026-11-13", 90.0, 500]]},
                  "DIXON": {"company": "Dixon", "employer_key": "dixon", "rows": [["2026-11-13", 50.0, 700]]}}}


def run(old=OLD, **over):
    f = dict(filings=lambda d: [filing("KAYNES", "capex", 3, 2), filing("DIXON", "press_release", 1, 5)],
             prices=lambda t: rows(), quarters=lambda t: {}, people=None)
    f.update(over)
    return refresh(old, NOW, 336, TICKERS, NAMES, EMP, [], Fetchers(**f))


def test_everything_works():
    out, rep = run()
    assert not rep.failed
    assert [i["category"] for i in out["items"]] == ["capex"] and out["routine_hidden"] == 1
    assert out["filings_as_of"] == NOW.isoformat() and set(out["market"]) == {"KAYNES", "DIXON"}
    assert out["provider"] == "gemini"


def test_nse_down_keeps_old_filings_and_still_refreshes_prices():
    out, rep = run(filings=boom)
    assert rep.failed == {"filings"}
    assert [i["id"] for i in out["items"]] == ["old1", "mg1"]          # old cards kept, old baked alert dropped
    assert out["routine_hidden"] == 3 and out["routine_filed"] == ["t1", "t2", "t3"]
    assert out["filings_as_of"] == OLD_END.isoformat()                 # says plainly how stale the filings are
    assert out["window"]["end"] == NOW.isoformat()
    assert out["market"]["KAYNES"]["rows"][-1][0] == "2026-11-14"       # prices are fresh


def test_one_company_price_failure_keeps_its_old_rows():
    out, rep = run(prices=lambda t: boom() if t == "DIXON" else rows())
    assert rep.failed == {"prices"}
    assert out["market"]["DIXON"]["rows"] == [["2026-11-13", 50.0, 700]] or out["market"]["DIXON"]["rows"] == [("2026-11-13", 50.0, 700)]
    assert out["market"]["KAYNES"]["rows"][-1][0] == "2026-11-14"


def test_price_failure_with_no_old_rows_leaves_the_company_out_rather_than_inventing_it():
    out, _ = run(old={}, prices=lambda t: boom() if t == "DIXON" else rows())
    assert set(out["market"]) == {"KAYNES"}


def test_quarters_failure_only_loses_the_numbers():
    f = [filing("KAYNES", "results", 3, 2)]
    out, rep = run(filings=lambda d: f, quarters=boom)
    assert out["items"][0]["type"] == "event" and not rep.failed        # falls back to a plain filing card


def test_people_failure_keeps_the_last_known_person():
    f = [filing("DIXON", "management_change", 3, 2)]
    f[0]["exchange_id"] = "mg1"
    out, rep = run(filings=lambda d: f, people=boom)
    assert rep.failed == {"people"}
    assert out["items"][0]["type"] == "mgmt_change" and out["items"][0]["person"] == {"person": "A B", "history": []}


def test_new_person_beats_old():
    f = [filing("DIXON", "management_change", 3, 2)]
    f[0]["exchange_id"] = "mg1"
    new = {"person": "C D", "history": []}
    out, _ = run(filings=lambda d: f, people=lambda *a: {"mg1": new})
    assert out["items"][0]["person"] == new


def test_first_ever_run_with_nse_down_gives_an_empty_but_valid_feed():
    out, rep = run(old={}, filings=boom)
    assert out["items"] == [] and out["filings_as_of"] is None and "market" in out


def test_no_prices_at_all_is_a_failure_not_a_success():
    out, rep = run(old={}, prices=boom)
    assert "prices" in rep.failed and out["market"] == {}


def test_nan_prices_never_reach_the_feed():
    """A NaN close made feed_live.json invalid JSON and broke the website build."""
    import json, math
    nan = float("nan")
    bad = rows()[:-1] + [("2026-11-14", nan, 500)]
    out, rep = run(prices=lambda t: bad)
    assert all(math.isfinite(x) for m in out["market"].values() for r in m["rows"] for x in r[1:])
    assert out["market"]["KAYNES"]["rows"][-1][0] == "2026-11-13" or out["market"]["KAYNES"]["rows"][-1][0].startswith("2026-10")
    json.dumps(out, allow_nan=False)  # strict: raises on NaN


def test_a_company_with_only_nan_rows_keeps_its_old_rows():
    nan = float("nan")
    out, rep = run(prices=lambda t: [("2026-11-14", nan, nan)] if t == "DIXON" else rows())
    assert "prices" in rep.failed
    assert out["market"]["DIXON"]["rows"][-1][0] == "2026-11-13"
