"""Build one company on request and publish it. Runs inside GitHub Actions, never in the website.

    python scripts/worker_build.py TICKER REQUEST_ID

Needs (as secrets in the job, never in the website):  SUPABASE_URL, SUPABASE_SERVICE_KEY, GEMINI_API_KEY.
Writes the result to the companies_live table and reports progress in build_requests, which is what the
website shows. Only Gemini output is ever published; any other provider aborts the build.
Failures are reported in plain words. Details go to the job log, never to the website.
"""
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TICKER = re.compile(r"^[A-Z0-9&-]{1,20}$")
MESSAGES = {
    "no_data": "No earnings call transcripts were found for this company.",
    "limit": "API limit reached for today. Try again later.",
    "failed": "The build failed. Try again later.",
}


class Api:
    """The smallest possible Supabase REST client: update a request, upsert a company."""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        # new-style secret keys (sb_secret_...) go in `apikey` only; old JWT service keys also need Authorization
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        if not key.startswith("sb_"):
            self.headers["Authorization"] = f"Bearer {key}"

    def set_status(self, request_id: int, status: str, message: str | None = None):
        body = {"status": status, "message": message, "updated_at": datetime.now(timezone.utc).isoformat()}
        r = requests.patch(f"{self.url}/rest/v1/build_requests?id=eq.{int(request_id)}",
                           headers=self.headers, json=body, timeout=30)
        r.raise_for_status()

    def publish(self, company: dict):
        row = {"ticker": company["ticker"], "name": company["name"], "provider": company["provider"], "data": company}
        r = requests.post(f"{self.url}/rest/v1/companies_live?on_conflict=ticker",
                          headers={**self.headers, "Prefer": "resolution=merge-duplicates"}, json=row, timeout=60)
        r.raise_for_status()


def employer_key_for(ticker: str):
    net = json.loads((ROOT / "data" / "network" / "synthetic_network.json").read_text())
    return next((e["key"] for e in net["employers"] if e.get("ticker") == ticker), None)


def run(ticker: str, request_id: int, api, steps=None) -> str:
    """Returns the final status. `steps` lets tests replace the network and the model."""
    from pipeline import build_company, export, fetch_docs, fetch_financials, llm
    steps = steps or {}
    find_docs = steps.get("fetch_docs", fetch_docs.fetch_docs)
    build = steps.get("build", lambda t: build_company.build(t, 4, exit_on_quota=False))
    read_outputs = steps.get("read_outputs", lambda t: _read_outputs(t, llm))
    provider = steps.get("provider", llm.provider)
    quota_error = llm.QuotaExhausted

    if not TICKER.match(ticker):
        api.set_status(request_id, "failed", MESSAGES["failed"])
        return "failed"
    api.set_status(request_id, "building", "Reading the earnings calls. This takes a few minutes.")
    try:
        if provider() != "gemini":
            raise RuntimeError(f"refusing to publish output from provider {provider()!r}")
        docs = find_docs(ticker)
        if not docs.get("transcripts"):
            api.set_status(request_id, "no_data", MESSAGES["no_data"])
            return "no_data"
        build(ticker)
        verdicts, quarters = read_outputs(ticker)
        company = export.build_company(ticker, docs.get("name") or ticker, employer_key_for(ticker),
                                       verdicts, quarters, provider())
        try:  # multi-year numbers are an extra: the research is still worth publishing without them
            fin = steps.get("financials", fetch_financials.fetch_financials)(ticker)
            if fin:
                company["financials"] = {**fin, "fetched": date.today().isoformat()}
        except Exception as e:
            print(f"financials skipped: {type(e).__name__}: {e}")
        api.publish(company)
        api.set_status(request_id, "done", None)
        return "done"
    except quota_error as e:
        print(f"quota: {e}")
        api.set_status(request_id, "limit", MESSAGES["limit"])
        return "limit"
    except Exception as e:  # log the detail here; the website only ever shows a plain sentence
        print(f"FAILED {type(e).__name__}: {e}")
        try:
            api.set_status(request_id, "failed", MESSAGES["failed"])
        except Exception as e2:
            print(f"could not report the failure: {e2}")
        return "failed"


def _read_outputs(ticker, llm):
    cache = ROOT / "data" / "cache"
    verdicts = json.loads((cache / llm.derived("verdicts") / f"{ticker}.json").read_text())
    quarters = json.loads((cache / "quarters" / f"{ticker}.json").read_text())
    return verdicts, quarters


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("usage: python scripts/worker_build.py TICKER REQUEST_ID [--fail]")
    api = Api(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    if len(sys.argv) == 4 and sys.argv[3] == "--fail":
        # last step of the job when it crashed before the worker could report (install error, timeout)
        api.set_status(int(sys.argv[2]), "failed", MESSAGES["failed"])
        raise SystemExit(0)
    status = run(sys.argv[1].upper(), int(sys.argv[2]), api)
    print(f"RESULT: {status}")
    sys.exit(0 if status in ("done", "no_data", "limit") else 1)
