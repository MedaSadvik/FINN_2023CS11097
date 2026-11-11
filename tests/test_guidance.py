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


def make_pages(n):
    return [{"page": i, "text": f"page {i} text " * 5} for i in range(1, n + 1)]


def test_chunk_pages_cover_everything_with_overlap():
    pages = make_pages(20)
    chunks = guidance.chunk_pages(pages, size=8)
    assert len(chunks) == 3
    assert [p["page"] for p in chunks[0]][0] == 1 and chunks[-1][-1]["page"] == 20
    assert {p["page"] for c in chunks for p in c} == set(range(1, 21))
    assert chunks[0][-1]["page"] == chunks[1][0]["page"]  # one page of overlap
    assert len(guidance.chunk_pages(make_pages(10))) == 1  # short documents stay whole
    two = guidance.chunk_pages(make_pages(20))             # default size 10: two even halves, not 10+10+tiny
    assert [len(c) for c in two] == [10, 11] and two[0][-1]["page"] == two[1][0]["page"]


def test_check_numbers():
    ok = guidance.check_numbers({"quote": "we expect growth of 30%-35% this year", "low": 30, "high": 35})
    assert ok["numbers"] == "verified" and ok["low"] == 30
    bad = guidance.check_numbers({"quote": "we expect growth of 30%-35% this year", "low": 30, "high": 40, "basis": "yoy_growth_pct"})
    assert bad["numbers"] == "unverified_in_quote" and bad["low"] is None and bad["basis"] == "other"
    assert guidance.check_numbers({"quote": "INR 1,200 crores of capex", "low": 1200})["numbers"] == "verified"
    assert guidance.check_numbers({"quote": "twice the market", "low": None})["numbers"] == "none"


def test_extract_guidance_chunks_and_dedupes(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    pages = make_pages(20)
    pages[9]["text"] = "We expect revenue growth of 30-35% in FY27 given the order book and capacity ramp."
    calls = []

    def fake(model, system, prompt):
        calls.append(prompt)
        if "[PAGE 10]" in prompt:  # page 10 sits in the overlap of chunks 1 and 2
            return json.dumps({"claims": [{"page": 10, "quote": "We expect revenue growth of 30-35% in FY27 given the order book",
                                           "metric": "revenue_growth", "target": "t", "basis": "yoy_growth_pct",
                                           "low": 30, "high": 35, "horizon": "FY27", "scope": "company"}]})
        return '{"claims": []}'

    r = guidance.extract_guidance(pages, call=fake)
    assert len(calls) == 2
    assert len(r["claims"]) == 1 and not r["dropped"]  # seen twice, kept once, no noise in dropped
    assert r["claims"][0]["numbers"] == "verified"


def test_merge_same_promise_keeps_first_and_attaches_evidence():
    a = {"page": 5, "quote": "q1", "metric": "revenue_target", "target": "FY26 revenue of at least INR4,000 crore",
         "low": 4000, "high": None, "horizon": "FY26", "scope": "company"}
    b = {**a, "page": 9, "quote": "q2", "target": "FY26 revenue of minimum 4000 crore"}   # same promise, other words
    c = {**a, "page": 11, "quote": "q3", "low": 1500, "target": "OSAT 1,500", "scope": "OSAT"}  # different promise
    merged = guidance.merge_same_promise([a, b, c])
    assert len(merged) == 2 and merged[0]["also_quoted"] == [{"page": 9, "quote": "q2"}]
    x = {"page": 1, "quote": "x1", "metric": "revenue_growth", "target": "doubling the market growth", "low": None,
         "high": None, "horizon": "FY27", "scope": "company"}
    y = {**x, "page": 2, "quote": "x2", "target": "double the market growth"}
    z = {**x, "page": 3, "quote": "x3", "target": "rail margin stays strong"}
    assert len(guidance.merge_same_promise([x, y, z])) == 2


def test_fiscal_context_resolves_this_year():
    assert "FY27" in guidance.fiscal_context("May 2026") and "next year' means FY28" in guidance.fiscal_context("May 2026")
    assert "'this year' and 'current year' mean FY26" in guidance.fiscal_context("Feb 2026")
    assert guidance.fiscal_context(None) == "" and guidance.fiscal_context("soon") == ""


def test_daily_quota_skips_model_without_waiting(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("must not wait")))
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fb1")
    seen = []

    def call(model, system, prompt):
        seen.append(model)
        if model == "primary":
            raise RuntimeError("429 RESOURCE_EXHAUSTED quota metric GenerateRequestsPerDayPerProjectPerModel")
        return "{}"

    assert llm.generate_json("primary", "s", "p", call=call) == {} and seen == ["primary", "fb1"]


def test_rate_limit_waits_as_long_as_google_says(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    waits = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    n = {"i": 0}

    def call(model, system, prompt):
        n["i"] += 1
        if n["i"] == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED {'retryDelay': '34s'}")
        return "{}"

    llm.generate_json("m", "s", "p", call=call)
    assert waits == [36]


def test_think_tags_are_stripped():
    assert llm.extract_json('<think>maybe {"x": 1} or not</think>{"claims": []}') == {"claims": []}


def test_openai_compat_provider(monkeypatch, tmp_path):
    import requests
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OPENAI_MODEL", "glm-test")
    sent = {}

    class R:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    def post(url, headers, json, timeout):
        sent.update(url=url, auth=headers["Authorization"], body=json)
        return R()

    monkeypatch.setattr(requests, "post", post)
    assert llm.flash_model() == "glm-test" and llm.fallback_models() == []
    assert llm.generate_json(llm.flash_model(), "sys", "hi") == {"ok": True}
    assert sent["url"] == "https://example.test/v1/chat/completions" and sent["auth"] == "Bearer k"
    assert sent["body"]["model"] == "glm-test" and sent["body"]["messages"][0]["role"] == "system"
    assert llm.LAST_MODEL == "glm-test"


def test_dev_provider_output_never_touches_shipped_folders(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm.derived("guidance") == "guidance" and llm.derived("verdicts") == "verdicts"
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    assert llm.derived("guidance") == "guidance_dev" and llm.derived("llm") == "llm_dev"


def test_all_models_out_of_daily_quota_raises_quota_exhausted(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm, "USAGE", tmp_path / "usage.json")
    monkeypatch.setattr(llm.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("must not wait")))
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "fb1")

    def call(model, system, prompt):
        raise RuntimeError("429 RESOURCE_EXHAUSTED requests per day limit exceeded. Please retry in 20h35m48.4s.")

    with pytest.raises(llm.QuotaExhausted, match="resets in about 20h35m"):
        llm.generate_json("primary", "s", "p", call=call)


def test_usage_counter_counts_per_model_and_resets_daily(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    f = tmp_path / "usage.json"
    assert [llm.count_call("a", f), llm.count_call("a", f), llm.count_call("b", f)] == [1, 2, 1]
    day = next(iter(json.loads(f.read_text())))
    f.write_text(json.dumps({"1999-01-01": {"a": 19}, day: {"a": 2}}))  # yesterday's numbers must vanish
    assert llm.count_call("a", f) == 3 and list(json.loads(f.read_text())) == [day]
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    assert llm.count_call("a", f) == 0  # dev provider is not counted against Gemini


def test_fake_calls_never_touch_the_real_usage_file(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm, "USAGE", tmp_path / "usage.json")
    llm.generate_json("m", "s", "p", call=lambda *a: "{}")
    assert not (tmp_path / "usage.json").exists()


def test_empty_model_reply_is_retried_not_crashed(monkeypatch, tmp_path):
    """A reasoning model can answer with null content. That must be retried, never a TypeError."""
    monkeypatch.setattr(llm, "CACHE", tmp_path / "llm")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://x")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    replies = iter([None, '{"ok": true}'])

    class R:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": next(replies)}, "finish_reason": "length"}]}

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: R())
    assert llm.generate_json("glm", "s", "p") == {"ok": True}
