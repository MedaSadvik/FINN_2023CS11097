"""Generate the synthetic investor network. Deterministic: same seed, same output.

Output: data/network/synthetic_network.json
Everything here is FAKE. Names are random combinations. Employers are real
companies so the overlap with the portfolio works; the people are invented.

Shape of the output:
  employers, employer_relations, people (with roles + education)
  people.kind = 'contact'  -> the investor knows them (about 50)
  people.kind = 'extended' -> people they overlapped with (about 70), no direct tie
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 2026
TODAY = date(2026, 11, 10)
CURRENT_YEAR = TODAY.year
OUT = Path(__file__).resolve().parent.parent / "data" / "network" / "synthetic_network.json"

# key, display name, sector, ticker if in our portfolio
EMPLOYERS = [
    # semiconductors / electronics manufacturing
    ("kaynes", "Kaynes Technology", "semis_electronics", "KAYNES"),
    ("cgpower", "CG Power", "semis_electronics", "CGPOWER"),
    ("dixon", "Dixon Technologies", "semis_electronics", "DIXON"),
    ("syrma", "Syrma SGS", "semis_electronics", "SYRMA"),
    ("tejas", "Tejas Networks", "semis_electronics", "TEJASNET"),
    ("micron", "Micron India", "semis_electronics", None),
    ("ti", "Texas Instruments India", "semis_electronics", None),
    ("qualcomm", "Qualcomm India", "semis_electronics", None),
    ("intel", "Intel India", "semis_electronics", None),
    ("tataelec", "Tata Electronics", "semis_electronics", None),
    # AI / cloud / compute
    ("netweb", "Netweb Technologies", "ai_cloud", "NETWEB"),
    ("e2e", "E2E Networks", "ai_cloud", "E2E"),
    ("nvidia", "Nvidia India", "ai_cloud", None),
    ("aws", "AWS India", "ai_cloud", None),
    ("microsoft", "Microsoft India", "ai_cloud", None),
    ("yotta", "Yotta Data Services", "ai_cloud", None),
    # IT services
    ("infosys", "Infosys", "it_services", "INFY"),
    ("tcs", "TCS", "it_services", "TCS"),
    ("wipro", "Wipro", "it_services", "WIPRO"),
    ("hcltech", "HCL Tech", "it_services", "HCLTECH"),
    ("persistent", "Persistent Systems", "it_services", "PERSISTENT"),
    ("tataelxsi", "Tata Elxsi", "it_services", "TATAELXSI"),
    ("accenture", "Accenture India", "it_services", None),
    ("cognizant", "Cognizant", "it_services", None),
    # pharma
    ("sunpharma", "Sun Pharma", "pharma", "SUNPHARMA"),
    ("drreddys", "Dr Reddy's", "pharma", None),
    ("cipla", "Cipla", "pharma", None),
    # financials
    ("hdfcbank", "HDFC Bank", "financials", "HDFCBANK"),
    ("icicibank", "ICICI Bank", "financials", None),
    ("axisbank", "Axis Bank", "financials", None),
    ("goldman", "Goldman Sachs India", "financials", None),
    # energy / infra / industrials
    ("reliance", "Reliance Industries", "energy_infra", "RELIANCE"),
    ("lt", "Larsen & Toubro", "energy_infra", "LT"),
    ("siemens", "Siemens India", "energy_infra", None),
    ("abb", "ABB India", "energy_infra", None),
    ("ntpc", "NTPC", "energy_infra", None),
]
EMP = {e[0]: e for e in EMPLOYERS}
BY_SECTOR = {}
for key, _, sector, _ in EMPLOYERS:
    BY_SECTOR.setdefault(sector, []).append(key)

# "relation to this company": competitor / supplier / customer
RELATIONS = [
    ("syrma", "KAYNES", "competitor"), ("dixon", "KAYNES", "competitor"),
    ("tataelec", "KAYNES", "competitor"), ("micron", "KAYNES", "customer"),
    ("ti", "KAYNES", "supplier"), ("qualcomm", "DIXON", "supplier"),
    ("nvidia", "NETWEB", "supplier"), ("intel", "NETWEB", "supplier"),
    ("yotta", "E2E", "competitor"), ("aws", "E2E", "competitor"),
    ("nvidia", "E2E", "supplier"), ("microsoft", "E2E", "competitor"),
    ("siemens", "CGPOWER", "competitor"), ("abb", "CGPOWER", "competitor"),
    ("ntpc", "CGPOWER", "customer"), ("ntpc", "LT", "customer"),
    ("tcs", "INFY", "competitor"), ("wipro", "INFY", "competitor"),
    ("hcltech", "INFY", "competitor"), ("accenture", "INFY", "competitor"),
    ("cognizant", "TCS", "competitor"), ("accenture", "TCS", "competitor"),
    ("tataelxsi", "PERSISTENT", "competitor"), ("cognizant", "PERSISTENT", "competitor"),
    ("drreddys", "SUNPHARMA", "competitor"), ("cipla", "SUNPHARMA", "competitor"),
    ("icicibank", "HDFCBANK", "competitor"), ("axisbank", "HDFCBANK", "competitor"),
    ("qualcomm", "TEJASNET", "supplier"), ("tataelec", "TEJASNET", "supplier"),
]

INSTITUTIONS = [
    "IIT Delhi", "IIT Bombay", "IIT Madras", "BITS Pilani", "NIT Trichy",
    "IIM Ahmedabad", "IIM Bangalore", "ISB Hyderabad", "SRCC Delhi", "VJTI Mumbai",
]
FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Neha", "Karthik", "Meera", "Arjun",
         "Divya", "Siddharth", "Kavya", "Rahul", "Isha", "Manish", "Pooja", "Nikhil", "Shreya",
         "Amit", "Tanvi", "Harsh", "Lakshmi", "Gaurav", "Sneha", "Varun", "Ritu", "Deepak", "Nisha"]
LAST = ["Iyer", "Sharma", "Menon", "Kapoor", "Reddy", "Nair", "Banerjee", "Gupta", "Rao",
        "Joshi", "Chawla", "Pillai", "Desai", "Bhatt", "Malhotra", "Kulkarni", "Singh",
        "Mehta", "Verma", "Krishnan", "Sethi", "Agarwal", "Bose", "Patil"]
TITLES = {  # by seniority 0 (junior) to 3 (senior)
    "semis_electronics": ["Design Engineer", "Plant Manager", "Head of Operations", "VP Supply Chain"],
    "ai_cloud": ["Solutions Engineer", "Product Manager", "Director Engineering", "VP Infrastructure"],
    "it_services": ["Consultant", "Delivery Manager", "Account Head", "Business Unit Head"],
    "pharma": ["Analyst", "Regulatory Manager", "Head of Business Development", "VP Commercial"],
    "financials": ["Analyst", "Credit Manager", "Head of Corporate Banking", "Group Treasurer"],
    "energy_infra": ["Project Engineer", "Project Manager", "Head of Projects", "VP Strategy"],
}

# Hand-written anchors: guarantee a few demo moments. Everything else is random.
# (name, kind, [(employer, title, start, end)], [(school, start, end)], months_since_last_spoke)
ANCHORS = [
    ("Priya Iyer", "contact", [("ti", "Design Engineer", 2010, 2014), ("kaynes", "Head of Operations", 2017, 2019),
                               ("micron", "VP Supply Chain", 2019, None)], [("IIT Delhi", 2006, 2010)], 14),
    ("Rohan Kapoor", "contact", [("infosys", "Delivery Manager", 2009, 2016), ("wipro", "Account Head", 2016, 2022),
                                 ("accenture", "Business Unit Head", 2022, None)], [("IIM Ahmedabad", 2007, 2009)], 5),
    ("Meera Nair", "contact", [("dixon", "Plant Manager", 2013, 2018), ("syrma", "Head of Operations", 2018, 2023),
                               ("tataelec", "VP Supply Chain", 2023, None)], [("NIT Trichy", 2008, 2012)], 9),
    ("Karthik Reddy", "contact", [("nvidia", "Solutions Engineer", 2015, 2020), ("e2e", "Director Engineering", 2020, 2023),
                                  ("yotta", "VP Infrastructure", 2023, None)], [("IIT Madras", 2011, 2015)], 3),
    ("Divya Menon", "contact", [("hdfcbank", "Credit Manager", 2012, 2018), ("icicibank", "Head of Corporate Banking", 2018, None)],
     [("IIM Bangalore", 2010, 2012)], 22),
    ("Siddharth Joshi", "contact", [("lt", "Project Manager", 2008, 2015), ("siemens", "Head of Projects", 2015, 2021),
                                    ("ntpc", "VP Strategy", 2021, None)], [("IIT Bombay", 2004, 2008)], 7),
    ("Neha Banerjee", "contact", [("sunpharma", "Regulatory Manager", 2011, 2017), ("drreddys", "Head of Business Development", 2017, None)],
     [("BITS Pilani", 2007, 2011)], 11),
    ("Vikram Sethi", "contact", [("tejas", "Design Engineer", 2012, 2016), ("qualcomm", "Product Manager", 2016, 2021),
                                 ("netweb", "Head of Operations", 2021, 2024)], [("IIT Delhi", 2008, 2012)], 2),
]


def make_name(rng, used):
    for _ in range(200):
        n = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if n not in used:
            used.add(n)
            return n
    raise RuntimeError("name pool exhausted")


def make_career(rng, sector):
    """2-3 consecutive roles; first one in `sector`, later ones may drift."""
    start = rng.randint(2005, 2016)
    roles, year = [], start
    n_roles = rng.choice([2, 2, 3])
    for i in range(n_roles):
        sec = sector if i == 0 or rng.random() < 0.65 else rng.choice(list(BY_SECTOR))
        emp = rng.choice(BY_SECTOR[sec])
        length = rng.randint(2, 7)
        last = i == n_roles - 1
        end = None if last or year + length >= CURRENT_YEAR else year + length
        if end is None and not last:
            break
        seniority = min(3, i + rng.choice([0, 1]))
        roles.append((emp, TITLES[sec][seniority], year, end))
        if end is None:
            break
        year = end
    # a role list that ended with a closed role means the person is "between roles"; reopen last
    if roles and roles[-1][3] is not None and rng.random() < 0.8:
        e, t, s, _ = roles[-1]
        roles[-1] = (e, t, s, None)
    return roles, start


def make_education(rng, career_start):
    school = rng.choice(INSTITUTIONS)
    end = career_start
    return [(school, end - rng.choice([2, 4]), end)]


def person_dict(pid, name, kind, roles, edu, months_ago):
    return {
        "id": pid,
        "kind": kind,
        "full_name": name,
        "headline": None,
        "last_spoke": (TODAY - timedelta(days=30 * months_ago)).isoformat() if months_ago is not None else None,
        "synthetic": True,
        "roles": [{"employer_key": e, "title": t, "start_year": s, "end_year": en} for e, t, s, en in roles],
        "education": [{"institution": i, "start_year": s, "end_year": en} for i, s, en in edu],
    }


def set_headline(p):
    cur = [r for r in p["roles"] if r["end_year"] is None]
    if cur:
        p["headline"] = f'{cur[0]["title"]}, {EMP[cur[0]["employer_key"]][1]}'
    else:
        last = p["roles"][-1]
        p["headline"] = f'Formerly {last["title"]}, {EMP[last["employer_key"]][1]}'


def main():
    rng = random.Random(SEED)
    used, people, pid = set(), [], 1

    for name, kind, roles, edu, months in ANCHORS:
        used.add(name)
        people.append(person_dict(pid, name, kind, roles, edu, months))
        pid += 1

    sectors = list(BY_SECTOR)
    # fill to 50 contacts: weight toward semis / AI (the portfolio tilt)
    weights = {"semis_electronics": 4, "ai_cloud": 3, "it_services": 3, "pharma": 1, "financials": 2, "energy_infra": 2}
    pool = [s for s in sectors for _ in range(weights[s])]
    while sum(p["kind"] == "contact" for p in people) < 50:
        sector = rng.choice(pool)
        roles, start = make_career(rng, sector)
        people.append(person_dict(pid, make_name(rng, used), "contact", roles,
                                  make_education(rng, start), rng.randint(1, 30)))
        pid += 1
    # about 70 extended people: colleagues and classmates of contacts, no direct tie
    while sum(p["kind"] == "extended" for p in people) < 70:
        sector = rng.choice(pool)
        roles, start = make_career(rng, sector)
        people.append(person_dict(pid, make_name(rng, used), "extended", roles,
                                  make_education(rng, start), None))
        pid += 1

    for p in people:
        set_headline(p)

    out = {
        "_note": "SYNTHETIC DATA. Invented people. Real company names are used only as employers.",
        "seed": SEED,
        "generated_for": TODAY.isoformat(),
        "employers": [{"key": k, "name": n, "sector": s, "ticker": t} for k, n, s, t in EMPLOYERS],
        "employer_relations": [{"employer_key": e, "ticker": t, "relation": r} for e, t, r in RELATIONS],
        "people": people,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT} | {len(people)} people")


if __name__ == "__main__":
    main()
