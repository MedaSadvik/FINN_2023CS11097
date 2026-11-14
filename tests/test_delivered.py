import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline import delivered, llm

PAGES = [{"page": 1, "text": "Welcome to the call."},
         {"page": 2, "text": "In FY26 our OSAT business delivered revenue of Rs 310 crore, ahead of plan."},
         {"page": 3, "text": "Capex for FY26 was about 520 crore across the group."}]
QUARTERS = {f"Q{q}FY26": {"revenue": 100} for q in (1, 2, 3, 4)}


def row(scope="OSAT", metric="other_numeric", low=300, horizon="FY26", basis="absolute_crore", made_in="Q1FY26"):
    claim = {"metric": metric, "basis": basis, "low": low, "high": None, "horizon": horizon, "scope": scope,
             "target": f"{scope} revenue of {low} crore", "quote": "x"}
    return {"made_in": made_in, "claim": claim, "outcome": "unclear", "delivered_text": None, "reason": "segment claim"}


@pytest.fixture
def cache(tmp_path, monkeypatch):
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "KAYNES_Q4FY26.json").write_text(json.dumps({"pages": PAGES, "sha256": "x"}))
    monkeypatch.setattr(delivered, "ROOT", tmp_path)
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    return tmp_path


def answer(**over):
    f = {"id": 0, "page": 2, "quote": "our OSAT business delivered revenue of Rs 310 crore, ahead of plan",
         "actual": 310, "basis": "absolute_crore", "period": "FY26"}
    f.update(over)
    return lambda m, s, p: json.dumps({"findings": [f]})


def test_a_later_call_settles_a_segment_promise(cache):
    out = delivered.enrich("KAYNES", [row()], QUARTERS, call=answer())
    r = out[0]
    assert r["outcome"] == "delivered" and r["tier"] == "later_call" and r["actual"] == 310
    assert r["evidence"]["period"] == "Q4FY26" and r["evidence"]["page"] == 2 and "reason" not in r


def test_the_same_arithmetic_marks_a_miss(cache):
    out = delivered.enrich("KAYNES", [row(low=450)], QUARTERS, call=answer())
    assert out[0]["outcome"] == "missed"


@pytest.mark.parametrize("bad", [
    {"quote": "our OSAT business delivered revenue of Rs 999 crore, far ahead of plan", "actual": 999},  # invented quote
    {"actual": 311},                                  # number is not inside the quote
    {"basis": "yoy_growth_pct"},                      # wrong unit
    {"period": "FY27"},                               # wrong period
    {"page": 99, "quote": "short"},                   # unverifiable
])
def test_unverified_answers_are_thrown_away(cache, bad):
    out = delivered.enrich("KAYNES", [row()], QUARTERS, call=answer(**bad))
    assert out[0]["outcome"] == "unclear" and "evidence" not in out[0]


def test_wrong_cited_page_is_corrected_not_trusted(cache):
    out = delivered.enrich("KAYNES", [row()], QUARTERS, call=answer(page=3))
    assert out[0]["outcome"] == "delivered" and out[0]["evidence"]["page"] == 2


def test_only_ended_numeric_promises_are_tried(cache):
    running = {**QUARTERS, "Q1FY27": {"revenue": 1}}
    rows = [row(horizon="FY27"), row(low=None), row(basis="other"), row()]
    assert delivered.candidates(rows, running) == [3]
    rows[3]["outcome"] = "delivered"
    assert delivered.candidates(rows, running) == []


def test_a_call_before_the_period_ended_is_not_evidence(cache):
    assert delivered.later_transcripts("KAYNES", row()["claim"], "Q4FY26") == []   # made in the same call
    assert len(delivered.later_transcripts("KAYNES", row()["claim"], "Q1FY26")) == 1


def test_quota_exhaustion_leaves_promises_unclear(cache):
    def broke(m, s, p):
        raise RuntimeError("429 RESOURCE_EXHAUSTED PerDay quota")
    out = delivered.enrich("KAYNES", [row()], QUARTERS, call=broke)
    assert out[0]["outcome"] == "unclear"


def test_request_count_is_capped(cache, monkeypatch):
    monkeypatch.setattr(delivered, "MAX_CLAIMS", 1)
    n = []
    def counting(m, s, p):
        n.append(1)
        return json.dumps({"findings": []})
    delivered.enrich("KAYNES", [row(low=100 + i) for i in range(10)], QUARTERS, call=counting)
    assert len(n) == delivered.MAX_CALLS


def test_backfill_skips_a_company_that_was_never_built(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import importlib
    ep = importlib.import_module("scripts.enrich_portfolio")
    monkeypatch.setattr(llm, "ROOT", tmp_path)
    assert ep.enrich("NOPE").startswith("skipped")
