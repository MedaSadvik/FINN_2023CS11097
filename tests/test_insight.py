import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline import insight, llm

PAGES = [{"page": 1, "text": "We make electronics systems and run an OSAT plant for chips."},
         {"page": 2, "text": "Order book stands at 8,000 crore and demand from railways is strong this quarter."},
         {"page": 3, "text": "Working capital remains a concern and receivables days rose to 120 days."}]


def good():
    return {"business": {"summary": "Electronics maker with an OSAT chip plant.",
                         "segments": [{"name": "OSAT", "page": 1, "quote": "We make electronics systems and run an OSAT plant for chips."}]},
            "bull": [{"point": "Order book at 8,000 crore", "page": 2, "quote": "Order book stands at 8,000 crore and demand from railways is strong"}],
            "bear": [{"point": "Receivables rose to 120 days", "page": 3, "quote": "Working capital remains a concern and receivables days rose to 120 days."}]}


def test_verified_items_are_kept():
    out = insight.check(good(), PAGES)
    assert out["business"]["summary"] and out["business"]["segments"][0]["name"] == "OSAT"
    assert out["bull"][0]["page"] == 2 and out["bear"][0]["point"].startswith("Receivables")


def test_invented_quote_is_dropped():
    d = good()
    d["bull"][0]["quote"] = "Order book stands at 12,000 crore and demand is booming everywhere"
    assert insight.check(d, PAGES)["bull"] == []


def test_a_number_not_in_the_quote_is_dropped():
    d = good()
    d["bull"][0]["point"] = "Order book at 9,000 crore"
    assert insight.check(d, PAGES)["bull"] == []


def test_summary_needs_a_supported_segment():
    d = good()
    d["business"]["segments"][0]["quote"] = "We are the biggest chip maker in the whole world today"
    out = insight.check(d, PAGES)
    assert out["business"]["segments"] == [] and out["business"]["summary"] == ""


def test_garbage_from_the_model_does_not_crash():
    for bad in (None, [], {"bull": "x"}, {"business": 3, "bull": [{"quote": None}]}):
        out = insight.check(bad, PAGES)
        assert out["bull"] == [] and out["bear"] == []


def test_limits_apply():
    d = good()
    d["bull"] = [{"point": "Order book strong", "page": 2, "quote": "Order book stands at 8,000 crore and demand from railways is strong"} for i in range(5)]
    assert len(insight.check(d, PAGES)["bull"]) == 1  # same quote only counts once


def test_page_picker_keeps_opening_and_signal_pages():
    pages = [{"page": i, "text": "filler " * 5} for i in range(1, 30)]
    pages[20]["text"] = "demand margin risk concern demand"
    got = [p["page"] for p in insight.pick_pages(pages)]
    assert got[:3] == [1, 2, 3] and 21 in got and len(got) <= insight.MAX_PAGES


def test_build_uses_latest_transcript(tmp_path, monkeypatch):
    (tmp_path / "text").mkdir()
    for p in ("Q3FY26", "Q1FY27"):
        (tmp_path / "text" / f"K_{p}.json").write_text(json.dumps({"pages": PAGES, "sha256": p}))
    monkeypatch.setattr(insight, "ROOT", tmp_path)
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    out = insight.build("K", call=lambda m, s, p: json.dumps(good()))
    assert out["period"] == "Q1FY27" and out["source_sha256"] == "Q1FY27"
    assert insight.build("NOPE") is None
