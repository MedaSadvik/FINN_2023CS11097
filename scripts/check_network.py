"""Sanity-check the synthetic network: does it overlap the portfolio enough for a good demo?"""
import json
import sys
from collections import defaultdict
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "network" / "synthetic_network.json"
YEAR = 2026

data = json.loads(PATH.read_text())
emp = {e["key"]: e for e in data["employers"]}
people = {p["id"]: p for p in data["people"]}
contacts = [p for p in people.values() if p["kind"] == "contact"]
portfolio = sorted({e["ticker"] for e in data["employers"] if e["ticker"]})


def span(r):
    return r["start_year"], (r["end_year"] if r["end_year"] is not None else YEAR)


# 1. every portfolio ticker: how many contacts worked there?
ex_by_ticker = defaultdict(set)
for p in contacts:
    for r in p["roles"]:
        t = emp[r["employer_key"]]["ticker"]
        if t:
            ex_by_ticker[t].add(p["id"])
missing = [t for t in portfolio if not ex_by_ticker[t]]
print("tickers with 0 direct contacts:", missing or "none")

# 2. contacts per sector (expertise map needs >= 3 per theme)
by_sector = defaultdict(set)
for p in contacts:
    for r in p["roles"]:
        by_sector[emp[r["employer_key"]]["sector"]].add(p["id"])
for s, ids in sorted(by_sector.items()):
    print(f"  sector {s:18s} contacts: {len(ids)}")

# 3. overlaps (same logic as the SQL view `person_overlaps`, employer side)
roles = [(p["id"], r["employer_key"], *span(r)) for p in people.values() for r in p["roles"]]
by_emp = defaultdict(list)
for row in roles:
    by_emp[row[1]].append(row)
pairs = set()
for rows in by_emp.values():
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a[0] != b[0] and max(a[2], b[2]) <= min(a[3], b[3]):
                pairs.add(tuple(sorted((a[0], b[0]))))
contact_ids = {p["id"] for p in contacts}
c2e = defaultdict(int)
for a, b in pairs:
    if a in contact_ids and b not in contact_ids:
        c2e[a] += 1
    if b in contact_ids and a not in contact_ids:
        c2e[b] += 1
print(f"overlap pairs total: {len(pairs)} | contacts with >=1 extended overlap: {len(c2e)} of {len(contacts)}")
anchor = next(p for p in contacts if p["full_name"] == "Priya Iyer")
print(f"anchor Priya Iyer overlaps with {c2e[anchor['id']]} extended people")

# 4. sanity
bad = [p["full_name"] for p in people.values() for r in p["roles"]
       if r["end_year"] is not None and r["end_year"] < r["start_year"]]
if bad:
    print("BAD role dates:", bad)
    sys.exit(1)
print("ok")
