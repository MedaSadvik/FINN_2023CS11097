import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline.alerts import check_all, price_move, volume_spike
from pipeline.classify import classify

# Subjects modelled on real exchange headlines (several seen on Netweb's feed).
CASES = [
    ("Outcome of Board Meeting - Approval of Unaudited Financial Results for the quarter ended 30 Sep 2026", "results"),
    ("Investor Presentation Q2 FY27", "results"),
    ("Copy of Newspaper Publication of Financial Results", "results"),
    ("Copy of Newspaper Publication", "unclassified"),
    ("Announcement under Regulation 30 (LODR)-Change in Management", "management_change"),
    ("Resignation of Chief Financial Officer", "management_change"),
    ("Appointment of Statutory Auditors", "unclassified"),
    ("Appointment of Company Secretary and Compliance Officer", "unclassified"),
    ("Announcement under Regulation 30 (LODR)-Earnings Call Transcript", "earnings_call"),
    ("Intimation of Conference", "investor_meetings"),
    ("Analysts/Institutional Investor Meet/Con. Call Updates", "earnings_call"),
    ("ESG Rating", "unclassified"),
    ("Allotment of 286819 Shares under ESOP", "unclassified"),
    ("Credit Rating reaffirmed by CRISIL", "credit_rating"),
    ("Pledge created by promoter", "pledging"),
    ("Intimation of Postal Ballot Notice", "postal_ballot"),
    ("Notice of 30th Annual General Meeting", "agm_egm"),
    ("Declaration of Interim Dividend and Record Date", "dividend"),
    ("Issue of Bonus Shares", "bonus_split"),
    ("Approval of Rights Issue", "fund_raise"),
    ("Acquisition of 51% stake in XYZ Pvt Ltd", "M&A"),
    ("Incorporation of wholly owned subsidiary", "M&A"),
    ("Receipt of order from SEBI", "litigation"),
    ("Receipt of order worth Rs 500 crore from a customer", "press_release"),
    ("Order received from Income Tax authority", "litigation"),
    ("Board approves capex for new manufacturing facility", "capex"),
    ("Product Launch", "press_release"),
    ("Press Release", "press_release"),
    ("Certificate under SEBI (Depositories and Participants) Regulations, 2018", "unclassified"),
    ("", "unclassified"),
]


@pytest.mark.parametrize("subject,expected", CASES)
def test_classify(subject, expected):
    assert classify(subject)[0] == expected, subject


def test_priority_ordering():
    assert classify("Change in Management")[1] == 3
    assert classify("ESG Rating")[1] == 0
    assert classify("Declaration of Dividend")[1] == 2


def rows(volumes, closes=None):
    closes = closes or [100.0] * len(volumes)
    return [(f"d{i}", c, v) for i, (c, v) in enumerate(zip(closes, volumes))]


def test_volume_spike_fires():
    r = rows([1000] * 20 + [2500])
    hit = volume_spike(r, multiple=2.0)
    assert hit and hit["ratio"] == 2.5 and hit["days_in_avg"] == 20


def test_volume_spike_below_threshold():
    assert volume_spike(rows([1000] * 20 + [1500]), multiple=2.0) is None


def test_volume_needs_history():
    assert volume_spike(rows([1000] * 5), multiple=2.0) is None


def test_volume_average_excludes_today():
    # if today were in the average, 20x spike would be diluted below 2x
    hit = volume_spike(rows([100] * 20 + [20000]), multiple=2.0)
    assert hit and hit["ratio"] == 200.0


def test_price_move_both_directions():
    assert price_move(rows([1, 1], [100, 106]), pct=5)["pct"] == 6.0
    assert price_move(rows([1, 1], [100, 94]), pct=5)["pct"] == -6.0
    assert price_move(rows([1, 1], [100, 103]), pct=5) is None


def test_check_all_respects_rules():
    r = rows([1000] * 20 + [3000], [100] * 20 + [110])
    assert {h["kind"] for h in check_all(r, {"volume_multiple": 2, "price_move": 5})} == {"volume_multiple", "price_move"}
    assert check_all(r, {}) == []
