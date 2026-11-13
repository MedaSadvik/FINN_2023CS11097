"""Read ONE management-change filing and pull out who joined or left, and their earlier employers.

The model only reads the filing text. Everything it returns is checked against that text:
  - the person's name must appear in the filing;
  - the quote must be a verbatim passage of the filing;
  - an earlier employer is kept only if its name appears in the filing.
Anything that fails the check is dropped, so the card can never show an invented career.
Employers are then matched to the ones in the investor's network by name (plain rules, no model).
"""
import re
from datetime import datetime, timedelta

from pipeline import llm
from pipeline.guidance import squash

VERSION = "people-v1"
EVENTS = ["appointment", "resignation", "cessation", "re-appointment", "other"]
SUFFIXES = r"\b(limited|ltd|pvt|private|technologies|technology|tech|india|inc|corporation|corp|services|group|the)\b"

SYSTEM = f"""You read ONE stock-exchange filing about a change in a company's management.
Use ONLY the text given. Never use outside knowledge about the person or companies.
Return JSON only:
{{"person": "full name of the person appointed or leaving, or null",
  "role": "their position as written in the filing, or null",
  "event": one of {EVENTS},
  "quote": "one EXACT verbatim passage (60-300 characters) from the filing that names this person and the change",
  "history": [{{"employer": "an earlier employer exactly as named in the filing",
               "title": "their title there if stated, else null",
               "start_year": a year or null, "end_year": a year or null}}]}}
If the filing is not about one named person, return {{"person": null, "history": []}}."""


def core(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(SUFFIXES, " ", name.lower()))


def match_employer(name: str, employers: list):
    """Key of the network employer this name refers to, or None. Needs a 4+ letter core to match."""
    n = core(name)
    if len(n) < 4:
        return None
    for e in employers:
        c = core(e["name"])
        if len(c) >= 4 and (n == c or n.startswith(c) or c.startswith(n)):
            return e["key"]
    return None


def verify(raw: dict, text: str, employers: list):
    """Return the checked person record, or None if the model's answer is not supported by the text."""
    body = squash(text)
    person = (raw or {}).get("person")
    if not person or squash(person) not in body:
        return None
    quote = " ".join((raw.get("quote") or "").split())
    out = {"person": person.strip(), "role": raw.get("role"), "event": raw.get("event") or "other",
           "quote": quote if len(squash(quote)) >= 25 and squash(quote) in body else None, "history": []}
    for h in raw.get("history") or []:
        emp = (h.get("employer") or "").strip()
        if emp and squash(emp) in body:
            out["history"].append({"employer": emp, "title": h.get("title"),
                                   "start_year": h.get("start_year"), "end_year": h.get("end_year"),
                                   "employer_key": match_employer(emp, employers)})
    return out


def extract_person(text: str, employers: list, call=None):
    kwargs = {"call": call} if call else {}
    raw = llm.generate_json(llm.flash_model(), SYSTEM, text[:12000], VERSION, **kwargs)
    return verify(raw if isinstance(raw, dict) else {}, text, employers)


def read_people(filings, employers, hours, now):
    """Management-change filings in the window -> verified person records (needs the PDF text and a model)."""
    from pipeline import fetch_pdf
    out = {}
    for f in filings:
        recent = datetime.fromisoformat(f["announced_at"]) >= now - timedelta(hours=hours)
        if f["category"] != "management_change" or not recent or not f.get("pdf_url"):
            continue
        try:
            path, _ = fetch_pdf.download(f["pdf_url"], referer="https://www.nseindia.com/")
            text = "\n".join(p["text"] for p in fetch_pdf.extract_pages(path))
            rec = extract_person(text, employers)
        except Exception as e:
            print(f"  {f['ticker']}: could not read filing ({type(e).__name__}: {e})")
            continue
        print(f"  {f['ticker']}: {rec['person'] if rec else 'no named person found'}")
        if rec:
            out[f["exchange_id"]] = rec
    return out
