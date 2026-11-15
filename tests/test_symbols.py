import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline import symbols

HEAD = "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"


def csv_text(n=600, extra=""):
    body = "".join(f"SYM{i},Company {i} Limited,EQ,01-JAN-2000,1,1,INE{i:06d},1\n" for i in range(n))
    return "﻿" + HEAD + body + extra


def test_symbols_and_names_are_read_and_header_spaces_are_ignored():
    rows = symbols.parse_equity_csv(csv_text(extra="TITAN,Titan Company Limited,EQ,01-JAN-2000,1,1,INE280A01028,1\n"))
    assert ["TITAN", "Titan Company Limited"] in rows
    assert len(rows) == 601 and rows == sorted(rows, key=lambda r: r[0])


def test_duplicates_and_blank_rows_are_dropped():
    rows = symbols.parse_equity_csv(csv_text(extra="SYM1,Again,EQ,x,1,1,x,1\n,No symbol,EQ,x,1,1,x,1\n"))
    assert len(rows) == 600 and ["SYM1", "Company 1 Limited"] in rows


def test_a_short_list_is_refused_so_a_broken_download_cannot_replace_a_good_file():
    with pytest.raises(ValueError):
        symbols.parse_equity_csv(csv_text(n=20))
