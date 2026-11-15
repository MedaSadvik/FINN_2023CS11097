"""The daily staleness check, with the network replaced by fakes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_stale as c  # noqa: E402

from pipeline import staleness  # noqa: E402


def calls(*periods):
    return {"transcripts": [{"period": p, "url": "x"} for p in periods]}


def row(ticker, built=None, made_in=()):
    return {"ticker": ticker, "built_call": built, "data": {"promises": [{"made_in": m} for m in made_in]}}


def test_period_order_crosses_the_year():
    assert staleness.period_key("Q4FY26") < staleness.period_key("Q1FY27")
    assert staleness.newest_call([{"period": "Q3FY26"}, {"period": "Q1FY27"}, {"period": None}, {"period": "Q4FY26"}]) == "Q1FY27"
    assert staleness.newest_call([]) is None and staleness.newest_call([{"period": None}]) is None


def test_newer_only_when_strictly_newer():
    assert staleness.newer_call("Q1FY27", "Q2FY27") == "Q2FY27"
    assert staleness.newer_call("Q2FY27", "Q2FY27") is None
    assert staleness.newer_call("Q2FY27", "Q1FY27") is None
    assert staleness.newer_call(None, "Q1FY27") is None


def test_old_rows_use_their_newest_promise():
    assert staleness.built_call_of({"promises": [{"made_in": "Q3FY26"}, {"made_in": "Q1FY27"}]}) == "Q1FY27"
    assert staleness.built_call_of({"built_call": "Q2FY27", "promises": [{"made_in": "Q1FY27"}]}) == "Q2FY27"
    assert staleness.built_call_of({"promises": []}) is None


def test_marks_only_the_companies_behind():
    saved = {}
    docs = {"TITAN": calls("Q2FY27", "Q1FY27"), "SBIN": calls("Q1FY27", "Q4FY26")}
    report = c.run([row("TITAN", "Q1FY27"), row("SBIN", None, ["Q4FY26", "Q1FY27"])], docs.__getitem__,
                   lambda t, b: saved.update({t: b}))
    assert saved["TITAN"]["newer_call"] == "Q2FY27" and saved["TITAN"]["built_call"] == "Q1FY27"
    assert saved["SBIN"]["newer_call"] is None and saved["SBIN"]["built_call"] == "Q1FY27"   # old row got its label
    assert "newer call Q2FY27" in report[0] and "up to date" in report[1]


def test_an_unreadable_page_changes_nothing():
    saved = {}

    def fetch(t):
        if t == "A":
            raise ConnectionError("blocked")
        return {"annual_reports": [], "transcripts": [], "name": None}   # page read, but no call list

    report = c.run([row("A", "Q1FY27"), row("B", "Q1FY27")], fetch, lambda t, b: saved.update({t: b}))
    assert saved == {} and all("skipped" in r for r in report)
