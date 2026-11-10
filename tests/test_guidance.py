import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline import guidance, llm

PAGES = [
    {"page": 1, "text": "Welcome to the Q1 FY27 call.\nOpening remarks by the CEO."},
    {"page": 2, "text": "We are confident of achieving revenue growth of 30-35% in FY27,\n"
                        "driven by our new OSAT facility and strong order book."},
    {"page": 3, "text": "On margins, we expect EBITDA margin to stay in the 14-15 % range\n"
                        "for the full year, even with the ramp-up costs."},
]

GOOD = "we are confident of achieving revenue growth of 30-35% in FY27, driven by our new OSAT facility"


def claim(quote, page=2, metric="revenue_growth"):
    return {"page": page, "quote": quote, "metric": metric, "target": "x", "horizon": "FY27"}


def test_verbatim_quote_kept():
    kept, dropped = guidance.verify_claims([claim(GOOD)], PAGES)
    assert len(kept) == 1 and not dropped and kept[0]["verified"] == "exact_page"


def test_pdf_line_breaks_and_spacing_forgiven():
    # page text has a newline and "14-15 %"; model returned it tidied up
    q = "we expect EBITDA margin to stay in the 14-15% range for the full year"
    kept, dropped = guidance.verify_claims([claim(q, page=3, metric="ebitda_margin")], PAGES)
    assert len(kept) == 1, dropped


def test_changed_number_dropped():
    fake = GOOD.replace("30-35%", "35-40%")  # the classic hallucination: plausible, wrong number
    kept, dropped = guidance.verify_claims([claim(fake)], PAGES)
    assert not kept and dropped[0]["reason"] == "quote not found in transcript"


def test_invented_quote_dropped():
    kept, dropped = guidance.verify_claims([claim("We will double our revenue within two years for sure")], PAGES)
    assert not kept and len(dropped) == 1


def test_wrong_page_is_corrected_not_trusted():
    kept, _ = guidance.verify_claims([claim(GOOD, page=1)], PAGES)
    assert kept[0]["page"] == 2 and kept[0]["verified"] == "page_corrected"


def test_short_and_duplicate_dropped():
    kept, dropped = guidance.verify_claims([claim("growth of 30-35%"), claim(GOOD), claim(GOOD)], PAGES)
    assert len(kept) == 1
    assert {d["reason"] for d in dropped} == {"quote too short", "duplicate"}


def test_extract_json_handles_fences_and_chatter():
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.extract_json('Here you go: {"a": [1, 2]} hope it helps') == {"a": [1, 2]}


def test_end_to_end_with_fake_llm_and_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    calls = []

    def fake(model, system, prompt):
        calls.append(prompt)
        return json.dumps({"claims": [claim(GOOD), claim("Management guided 90% growth next year, no doubt")]})

    r1 = guidance.extract_guidance(PAGES, call=fake)
    r2 = guidance.extract_guidance(PAGES, call=fake)  # second run must hit the cache
    assert len(r1["claims"]) == 1 and len(r1["dropped"]) == 1
    assert r1 == r2 and len(calls) == 1
    assert "[PAGE 2]" in calls[0]


def test_retry_on_rate_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    n = {"i": 0}

    def flaky(model, system, prompt):
        n["i"] += 1
        if n["i"] < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return '{"claims": []}'

    assert llm.generate_json("m", "s", "p", call=flaky) == {"claims": []} and n["i"] == 3


def test_real_errors_not_retried(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    with pytest.raises(ValueError):
        llm.generate_json("m", "s", "p", call=lambda *a: (_ for _ in ()).throw(ValueError("bad key")))


def test_falls_back_when_model_overloaded(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fb1,fb2")
    seen = []

    def call(model, system, prompt):
        seen.append(model)
        if model == "primary":
            raise RuntimeError("504 DEADLINE_EXCEEDED")
        if model == "fb1":
            raise RuntimeError("404 NOT_FOUND no longer available to new users")
        return '{"ok": true}'

    assert llm.generate_json("primary", "s", "p", call=call) == {"ok": True}
    assert llm.LAST_MODEL == "fb2"
    assert seen == ["primary", "fb1", "fb2"]  # hang and closed model both skipped without retries
    # second call: served from cache, no model is contacted, audit model still known
    seen.clear()
    assert llm.generate_json("primary", "s", "p", call=call) == {"ok": True}
    assert seen == [] and llm.LAST_MODEL == "fb2"


def test_all_models_failing_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fb1")
    with pytest.raises(RuntimeError, match="all models failed"):
        llm.generate_json("a", "s", "p", call=lambda *x: (_ for _ in ()).throw(RuntimeError("503 UNAVAILABLE")))


def test_busy_model_is_retried_before_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fb1")
    seen = []

    def call(model, system, prompt):
        seen.append(model)
        if model == "primary":
            raise RuntimeError("503 UNAVAILABLE high demand")
        return "[]"

    assert llm.generate_json("primary", "s", "p", call=call) == []
    assert seen == ["primary"] * 3 + ["fb1"]  # 503 = busy: 3 tries, then fall back
