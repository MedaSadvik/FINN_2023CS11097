import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import create_demo_accounts as d  # noqa: E402

EMPLOYERS = {e["key"] for e in json.loads((ROOT / "data" / "network" / "synthetic_network.json").read_text())["employers"]}


def test_demo_data_fits_the_database_rules():
    names = set()
    for demo in d.DEMOS:
        assert re.fullmatch(r"[a-z0-9_]{3,20}", demo["username"]) and demo["username"] not in names
        names.add(demo["username"])
        assert 1 <= len(demo["display_name"]) <= 60 and len(demo["headline"]) <= 120
        assert "(demo)" in demo["display_name"]                      # visibly not a real person
        for name, key, title, start, end in demo["roles"]:
            assert key is None or key in EMPLOYERS, key              # a tracked employer key must exist (foreign key)
            assert 1 <= len(name) <= 80 and 1 <= len(title) <= 80
            assert 1960 <= start <= 2026 and (end is None or start <= end <= 2026)
        for school, start, end in demo["education"]:
            assert 1960 <= start <= end <= 2026


def test_demos_cover_the_portfolio_and_free_text_matching():
    keys = {k for demo in d.DEMOS for _, k, *_ in demo["roles"] if k}
    free = {n for demo in d.DEMOS for n, k, *_ in demo["roles"] if k is None}
    assert {"kaynes", "tcs", "infosys", "hdfcbank"} <= keys
    assert {"Titan Company", "Asian Paints"} <= free                 # companies built on request


def test_rows_are_marked_demo_and_owned_by_the_account():
    rows = d.rows_for(d.DEMOS[0], "uid-1")
    assert rows["profile"]["is_demo"] is True
    assert all(r["profile_id"] == "uid-1" for r in rows["roles"] + rows["education"])
    assert rows["roles"][-1]["end_year"] is None                     # current job


def test_email_template_is_checked():
    assert d.email_for("me+{name}@gmail.com", "demo_priya") == "me+demo_priya@gmail.com"
    with pytest.raises(SystemExit):
        d.email_for("me@gmail.com", "demo_priya")
