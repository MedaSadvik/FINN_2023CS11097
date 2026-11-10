import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline.verdicts import evaluate, parse_horizon, quarter_labels


@pytest.mark.parametrize("text,expected", [
    ("FY27", {"kind": "FY", "fy": 27}), ("FY 2027", {"kind": "FY", "fy": 27}),
    ("H1 FY26", {"kind": "H1", "fy": 26}), ("Q3FY27", {"kind": "Q3", "fy": 27}),
    ("Q3 FY'27", {"kind": "Q3", "fy": 27}), ("unspecified", None), ("next 3 years", None), (None, None),
])
def test_parse_horizon(text, expected):
    assert parse_horizon(text) == expected


def test_quarter_labels():
    assert quarter_labels({"kind": "FY", "fy": 26}) == ["Q1FY26", "Q2FY26", "Q3FY26", "Q4FY26"]
    assert quarter_labels({"kind": "H2", "fy": 26}) == ["Q3FY26", "Q4FY26"]
    assert quarter_labels({"kind": "Q3", "fy": 26}) == ["Q3FY26"]
    assert quarter_labels({"kind": "Q1", "fy": 27}, fy_offset=-1) == ["Q1FY26"]


def year(fy, rev, ebitda=None):
    return {f"Q{q}FY{fy}": {"revenue": rev, "ebitda": ebitda if ebitda is not None else rev * 0.15} for q in (1, 2, 3, 4)}


QUARTERS = {**year(25, 100), **year(26, 120)}  # FY26 revenue +20%, EBITDA margin 15%


def growth(low, high=None, horizon="FY26", **kw):
    return {"metric": "revenue_growth", "basis": "yoy_growth_pct", "low": low, "high": high,
            "horizon": horizon, "scope": "company", **kw}


def test_real_kaynes_numbers_q1fy27_yoy():
    # Real screener figures: Q1FY26 revenue 673, Q1FY27 946. Transcript said "40% year-on-year".
    q = {"Q1FY26": {"revenue": 673.0}, "Q1FY27": {"revenue": 946.0}}
    r = evaluate(growth(30, 35, horizon="Q1FY27"), q)
    assert r["outcome"] == "delivered" and r["actual"] == 40.6 and r["note"] == "above the promised range"


@pytest.mark.parametrize("low,high,expected", [(15, None, "delivered"), (22, None, "partly"), (25, 30, "missed")])
def test_growth_judging(low, high, expected):
    r = evaluate(growth(low, high), QUARTERS)
    assert r["outcome"] == expected and r["actual"] == 20.0


@pytest.mark.parametrize("low,high,expected", [(14, 15, "delivered"), (16, None, "partly"), (17, None, "missed")])
def test_margin_judging(low, high, expected):
    c = {"metric": "ebitda_margin", "basis": "margin_pct", "low": low, "high": high, "horizon": "FY26", "scope": "company"}
    r = evaluate(c, QUARTERS)
    assert r["outcome"] == expected and r["actual"] == 15.0


def test_revenue_target_absolute():
    c = {"metric": "revenue_target", "basis": "absolute_crore", "low": 450, "high": 500, "horizon": "FY26", "scope": "company"}
    assert evaluate(c, QUARTERS)["outcome"] == "delivered"  # FY26 revenue 480
    assert evaluate({**c, "low": 600, "high": 650}, QUARTERS)["outcome"] == "missed"


def test_future_period_is_pending_with_year_to_date():
    q = {**year(26, 100), "Q1FY27": {"revenue": 140.0, "ebitda": 20.0}}  # only Q1FY27 reported
    r = evaluate(growth(30, 35, horizon="FY27"), q)
    assert r["outcome"] == "pending" and r["actual"] == 40.0
    assert "so far Q1FY27" in r["delivered_text"]


@pytest.mark.parametrize("claim,why", [
    (growth(None), "no verified number"),
    (growth(30, horizon="unspecified"), "no fiscal period"),
    (growth(30, scope="OSAT"), "segment claim"),
    ({"metric": "capex", "basis": "absolute_crore", "low": 300, "horizon": "FY26", "scope": "company"}, "not computable"),
])
def test_unclear_cases(claim, why):
    r = evaluate(claim, QUARTERS)
    assert r["outcome"] == "unclear" and why in r["reason"]


def test_missing_prior_year_is_not_a_guess():
    q = year(26, 120)  # no FY25 quarters to compare against
    assert evaluate(growth(20), q)["outcome"] == "unclear"


def test_kaynes_real_fy26_revenue_miss():
    # Real: FY26 quarterly revenue 673 + 906 + 804 + 1243 = 3626 vs "at least INR 4,000 crore".
    q = {"Q1FY26": {"revenue": 673.0}, "Q2FY26": {"revenue": 906.0}, "Q3FY26": {"revenue": 804.0},
         "Q4FY26": {"revenue": 1243.0}}
    c = {"metric": "revenue_target", "basis": "absolute_crore", "low": 4000, "high": None, "horizon": "FY26", "scope": "company"}
    r = evaluate(c, q)
    assert r["outcome"] == "missed" and r["actual"] == 3626.0  # 9% short: more than the 5% allowance


def test_far_future_promise_is_pending_not_unclear():
    c = {"metric": "revenue_target", "basis": "other", "low": 1, "horizon": "FY28", "scope": "company"}
    r = evaluate(c, QUARTERS)
    assert r["outcome"] == "pending" and "due FY28" in r["delivered_text"]
