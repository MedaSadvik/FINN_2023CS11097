import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import seed_portfolio as sp  # noqa: E402


def test_rows_carry_the_file_data_and_the_newest_call():
    companies = {"kaynes": {"name": "Kaynes Technology", "provider": "gemini", "promises": [{"made_in": "Q4FY26"}, {"made_in": "Q1FY27"}]},
                 "INFY": {"name": "Infosys", "provider": "openai_compat", "promises": []}}
    rows = {r["ticker"]: r for r in sp.rows_from(companies)}
    assert set(rows) == {"KAYNES", "INFY"}
    assert rows["KAYNES"]["built_call"] == "Q1FY27" and rows["KAYNES"]["newer_call"] is None
    assert rows["KAYNES"]["provider"] == "gemini" and rows["INFY"]["provider"] == "openai_compat"
    assert rows["INFY"]["built_call"] is None


def test_the_real_file_seeds_every_portfolio_company():
    import json
    real = json.loads(sp.FILE.read_text())
    rows = sp.rows_from(real)
    assert len(rows) == len(real) >= 15
    assert all(r["data"].get("promises") is not None and r["name"] for r in rows)
