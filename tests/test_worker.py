"""The on-demand worker, with the network and the model replaced by fakes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import worker_build as w  # noqa: E402

from pipeline import llm  # noqa: E402


class FakeApi:
    def __init__(self):
        self.statuses, self.published = [], []

    def set_status(self, rid, status, message=None):
        self.statuses.append((status, message))

    def publish(self, company):
        self.published.append(company)


ROW = {"made_in": "Q1FY27", "outcome": "pending", "delivered_text": None, "reason": None,
       "claim": {"page": 3, "quote": "we expect revenue of 100 crore", "target": "FY27 revenue 100 cr",
                 "horizon": "FY27", "low": 100, "high": None}}
QUARTERS = {"Q1FY27": {"revenue": 90, "ebitda": 10, "pbt": 8, "pat": 6}}


def steps(**over):
    base = {"fetch_docs": lambda t: {"transcripts": [{"url": "x"}], "name": "Acme Ltd"},
            "build": lambda t: None, "read_outputs": lambda t: ([ROW], QUARTERS), "provider": lambda: "gemini",
            "financials": lambda t: {}}
    return {**base, **over}


def test_success_publishes_and_marks_done():
    api = FakeApi()
    assert w.run("ACME", 7, api, steps()) == "done"
    assert [s for s, _ in api.statuses] == ["building", "done"]
    assert api.published[0]["name"] == "Acme Ltd" and api.published[0]["provider"] == "gemini"


def test_multi_year_numbers_are_attached_when_found():
    api = FakeApi()
    fin = {"basis": "consolidated", "years": ["FY26"], "rows": {"FY26": {"revenue": 100.0}}}
    assert w.run("ACME", 7, api, steps(financials=lambda t: fin)) == "done"
    assert api.published[0]["financials"]["rows"]["FY26"]["revenue"] == 100.0 and "fetched" in api.published[0]["financials"]


def test_a_financials_failure_does_not_stop_the_research_being_published():
    def boom(t):
        raise RuntimeError("screener down")
    api = FakeApi()
    assert w.run("ACME", 7, api, steps(financials=boom)) == "done"
    assert "financials" not in api.published[0]


def test_no_transcripts_stops_before_any_model_call():
    api = FakeApi()
    called = []
    st = steps(fetch_docs=lambda t: {"transcripts": []}, build=lambda t: called.append(t))
    assert w.run("NOPE", 1, api, st) == "no_data"
    assert not called and not api.published
    assert api.statuses[-1] == ("no_data", w.MESSAGES["no_data"])


def test_quota_exhausted_says_so_in_plain_words():
    def boom(t):
        raise llm.QuotaExhausted("daily quota used")
    api = FakeApi()
    assert w.run("ACME", 1, api, steps(build=boom)) == "limit"
    assert api.statuses[-1] == ("limit", "API limit reached for today. Try again later.")
    assert not api.published


def test_unexpected_error_is_hidden_from_the_website():
    def boom(t):
        raise ValueError("secret detail: key=abc123")
    api = FakeApi()
    assert w.run("ACME", 1, api, steps(build=boom)) == "failed"
    status, message = api.statuses[-1]
    assert status == "failed" and "abc123" not in message and "secret" not in message


def test_never_publishes_a_test_model():
    api = FakeApi()
    assert w.run("ACME", 1, api, steps(provider=lambda: "openai_compat")) == "failed"
    assert not api.published


def test_bad_ticker_is_rejected():
    api = FakeApi()
    assert w.run("a;b", 1, api, steps()) == "failed"
    assert not api.published


def test_secret_key_header_style():
    assert "Authorization" not in w.Api("https://x.supabase.co", "sb_secret_abc").headers
    assert w.Api("https://x.supabase.co", "eyJabc").headers["Authorization"] == "Bearer eyJabc"
