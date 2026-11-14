import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import enrich_live

SNAP = {"business": {"summary": "s", "segments": []}, "bull": [], "bear": [], "period": "Q1FY27"}
FIN = {"basis": "consolidated", "years": ["FY25", "FY26"], "rows": {}}


def test_only_companies_without_the_new_sections_are_listed():
    rows = [{"ticker": "TITAN", "data": {"promises": []}},
            {"ticker": "SBIN", "data": {"snapshot": SNAP}},
            {"ticker": "DONE", "data": {"snapshot": SNAP, "financials": FIN}},
            {"ticker": "ODD", "data": None}]
    assert enrich_live.missing(rows) == ["ODD", "SBIN", "TITAN"]


def test_nothing_to_do_gives_an_empty_list():
    assert enrich_live.missing([{"ticker": "A", "data": {"snapshot": SNAP, "financials": FIN}}]) == []
