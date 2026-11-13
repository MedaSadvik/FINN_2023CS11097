"""Create (or refresh) the demo accounts evaluators can connect with in one tap. Run once on your own machine.

    python scripts/create_demo_accounts.py

Needs in the root .env:
    SUPABASE_URL=...
    SUPABASE_SERVICE_KEY=...                 the Supabase *secret* key. Stays on your machine.
    DEMO_EMAIL_TEMPLATE=you+{name}@gmail.com  any address you control; {name} is replaced by demo_priya, etc.

Run db/migrations/006_demo_accounts.sql in Supabase first. Safe to run again: it updates what is there.
Each account gets a random password that is never shown or saved, because nobody signs in as a demo.
People and careers are invented. Connecting to a demo username is accepted instantly by the database.
"""
import os
import re
import secrets
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# Careers are built to overlap the portfolio and the companies built on request:
#   priya: Kaynes; kabir: Titan and Asian Paints, written by hand (free text, matched by name); meera: Infosys, TCS, HDFC Bank.
DEMOS = [
    {"username": "demo_priya", "display_name": "Priya Iyer (demo)", "headline": "VP Supply Chain, Micron India",
     "roles": [("Texas Instruments India", "ti", "Design Engineer", 2010, 2014),
               ("Kaynes Technology", "kaynes", "Head of Operations", 2017, 2019),
               ("Micron India", "micron", "VP Supply Chain", 2019, None)],
     "education": [("IIT Delhi", 2006, 2010)]},
    {"username": "demo_kabir", "display_name": "Kabir Shah (demo)", "headline": "Strategy Lead, Bajaj Finance",
     "roles": [("Titan Company", None, "Analyst", 2016, 2020),
               ("Asian Paints", None, "Brand Manager", 2020, 2023),
               ("Bajaj Finance", None, "Strategy Lead", 2023, None)],
     "education": [("XLRI Jamshedpur", 2012, 2014)]},
    {"username": "demo_meera", "display_name": "Meera Nair (demo)", "headline": "Head of Digital Banking, HDFC Bank",
     "roles": [("Infosys", "infosys", "Senior Consultant", 2012, 2016),
               ("TCS", "tcs", "Engagement Manager", 2016, 2019),
               ("HDFC Bank", "hdfcbank", "Head of Digital Banking", 2019, None)],
     "education": [("IIM Bangalore", 2010, 2012)]},
]


def email_for(template: str, username: str) -> str:
    if "{name}" not in template or "@" not in template:
        raise SystemExit("DEMO_EMAIL_TEMPLATE must look like you+{name}@gmail.com")
    return template.replace("{name}", username)


def rows_for(demo: dict, user_id: str) -> dict:
    """The database rows for one demo account."""
    return {
        "profile": {"id": user_id, "username": demo["username"], "display_name": demo["display_name"],
                    "headline": demo["headline"], "is_demo": True},
        "roles": [{"profile_id": user_id, "employer_name": n, "employer_key": k, "title": t, "start_year": a, "end_year": b}
                  for n, k, t, a, b in demo["roles"]],
        "education": [{"profile_id": user_id, "institution": i, "start_year": a, "end_year": b} for i, a, b in demo["education"]],
    }


class Supabase:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.h = {"apikey": key, "Content-Type": "application/json"}
        if not key.startswith("sb_"):
            self.h["Authorization"] = f"Bearer {key}"

    def user_id(self, email: str):
        r = requests.get(f"{self.url}/auth/v1/admin/users", headers=self.h, params={"per_page": 200}, timeout=30)
        r.raise_for_status()
        return next((u["id"] for u in r.json().get("users", []) if (u.get("email") or "").lower() == email.lower()), None)

    def create_user(self, email: str) -> str:
        r = requests.post(f"{self.url}/auth/v1/admin/users", headers=self.h, timeout=30,
                          json={"email": email, "password": secrets.token_urlsafe(24), "email_confirm": True})
        r.raise_for_status()
        return r.json()["id"]

    def rest(self, method: str, path: str, **kw):
        r = requests.request(method, f"{self.url}/rest/v1/{path}", headers={**self.h, **kw.pop("headers", {})}, timeout=30, **kw)
        r.raise_for_status()


def main():
    for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
        k, _, v = line.partition("=")
        if k.strip() and not line.lstrip().startswith("#"):
            os.environ.setdefault(k.strip(), re.sub(r"\s+#.*$", "", v).strip())
    need = [k for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "DEMO_EMAIL_TEMPLATE") if not os.environ.get(k)]
    if need:
        raise SystemExit("Add to .env: " + ", ".join(need))
    db = Supabase(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    for demo in DEMOS:
        email = email_for(os.environ["DEMO_EMAIL_TEMPLATE"], demo["username"])
        uid = db.user_id(email) or db.create_user(email)
        rows = rows_for(demo, uid)
        db.rest("POST", "profiles?on_conflict=id", json=rows["profile"], headers={"Prefer": "resolution=merge-duplicates"})
        for table in ("profile_roles", "profile_education"):
            db.rest("DELETE", f"{table}?profile_id=eq.{uid}")
        db.rest("POST", "profile_roles", json=rows["roles"])
        db.rest("POST", "profile_education", json=rows["education"])
        print(f"ok  @{demo['username']}  {demo['display_name']}")
    print("Done. Anyone can now add these usernames from the Network tab.")


if __name__ == "__main__":
    main()
