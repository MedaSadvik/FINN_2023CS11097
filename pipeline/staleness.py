"""Is the stored research behind the newest earnings call? Plain comparison of period labels, no model.

A period label looks like 'Q2FY27'. screener.in lists each call with the month it was held, and
pipeline.fetch_docs turns that into the quarter the call discusses.
"""
import re


def period_key(p):
    """'Q2FY27' -> (27, 2). None when it is not a quarter label."""
    m = re.fullmatch(r"Q([1-4])FY(\d{2})", p or "")
    return (int(m.group(2)), int(m.group(1))) if m else None


def newest_call(transcripts: list):
    """Label of the newest call in a list of {'period': ...} (or None if none has a usable period)."""
    periods = [t.get("period") for t in transcripts or [] if period_key(t.get("period"))]
    return max(periods, key=period_key) if periods else None


def built_call_of(data: dict):
    """Newest call a stored company was built from. Older rows have no label, so use its newest promise."""
    stored = data.get("built_call")
    if period_key(stored):
        return stored
    periods = [p.get("made_in") for p in data.get("promises") or [] if period_key(p.get("made_in"))]
    return max(periods, key=period_key) if periods else None


def newer_call(built, listed):
    """The listed call if it is newer than the one built from, else None."""
    if not period_key(built) or not period_key(listed):
        return None
    return listed if period_key(listed) > period_key(built) else None
