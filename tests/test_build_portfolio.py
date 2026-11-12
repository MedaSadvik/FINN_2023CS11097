import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_portfolio as bp  # noqa: E402


def drive(tickers, existing, provider="openai_compat", fail=None):
    built = []

    def build(t):
        if fail and t in fail:
            raise fail[t]
        built.append(t)

    return bp.run(tickers, existing, build, lambda t: None, provider, say=lambda *_: None), built


def test_one_failure_does_not_stop_the_rest():
    res, built = drive(["A", "B", "C"], {}, fail={"B": ValueError("boom")})
    assert res == {"A": "built", "B": "failed", "C": "built"} and built == ["A", "C"]


def test_no_transcripts_and_exit_messages_are_classified():
    res, _ = drive(["A", "B"], {}, fail={"A": SystemExit("A: no transcripts found on screener.in"), "B": SystemExit("weird")})
    assert res == {"A": "no_data", "B": "failed"}


def test_quota_stops_the_run_and_later_companies_are_untouched():
    res, built = drive(["A", "B", "C"], {}, fail={"B": SystemExit("STOPPED: model quota used up")})
    assert res == {"A": "built", "B": "quota"} and built == ["A"]


def test_gemini_data_is_never_replaced_by_another_model():
    res, built = drive(["KAYNES", "TCS"], {"KAYNES": {"provider": "gemini"}})
    assert res == {"KAYNES": "skipped", "TCS": "built"} and built == ["TCS"]


def test_finished_companies_are_skipped_on_a_rerun():
    res, built = drive(["A", "B"], {"A": {"provider": "openai_compat"}})
    assert res == {"A": "skipped", "B": "built"} and built == ["B"]
