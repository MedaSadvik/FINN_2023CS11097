"""Triggered-alert maths on end-of-day data. Pure functions: no network, easy to test.

Input rows are (day, close, volume) sorted oldest to newest.
Thresholds come from the investor's settings (alert_rules table).
"""
from statistics import mean
from typing import Optional, Sequence

Row = tuple  # (day, close, volume)
MIN_HISTORY = 10  # fewer prior days than this and an "average" means nothing


def volume_spike(rows: Sequence[Row], multiple: float = 2.0, window: int = 20) -> Optional[dict]:
    """Latest volume vs the average of the `window` days before it."""
    if len(rows) < MIN_HISTORY + 1:
        return None
    prior = [r[2] for r in rows[-(window + 1):-1]]
    avg = mean(prior)
    if avg <= 0:
        return None
    ratio = rows[-1][2] / avg
    if ratio >= multiple:
        return {"kind": "volume_multiple", "day": rows[-1][0], "ratio": round(ratio, 2),
                "volume": rows[-1][2], "avg_volume": round(avg), "days_in_avg": len(prior)}
    return None


def price_move(rows: Sequence[Row], pct: float = 5.0) -> Optional[dict]:
    """Latest close vs previous close, either direction."""
    if len(rows) < 2 or rows[-2][1] <= 0:
        return None
    change = (rows[-1][1] - rows[-2][1]) / rows[-2][1] * 100
    if abs(change) >= pct:
        return {"kind": "price_move", "day": rows[-1][0], "pct": round(change, 2),
                "close": rows[-1][1], "prev_close": rows[-2][1]}
    return None


def check_all(rows: Sequence[Row], rules: dict) -> list:
    """rules example: {"volume_multiple": 2.0, "price_move": 5.0}. Missing key = rule off."""
    hits = []
    if "volume_multiple" in rules and (h := volume_spike(rows, rules["volume_multiple"])):
        hits.append(h)
    if "price_move" in rules and (h := price_move(rows, rules["price_move"])):
        hits.append(h)
    return hits
