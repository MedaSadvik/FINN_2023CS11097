# FINN

Mobile-first financial investment agent. Built for the ENAM Founding AI Engineer Build Challenge (Nov 2026).

**Point of view:** FINN is a briefing, not a dashboard. A short ranked feed, a pinned ask-bar, and a *Call Sheet* on every card that says who in your network to call and why.

| Layer | What it does |
|---|---|
| **Push** | Windowed digest of filings, ranked. Alerts on volume, price move, filing type. |
| **Pull** | Company research grounded only in annual reports and concall transcripts. Star feature: promised vs delivered. |
| **Network** | Synthetic investor network. Woven into Push and Pull as Call Sheets. Also answers direct questions. |

## Stack
Next.js + Tailwind (Vercel) · Python pipeline · Supabase Postgres (RLS) · Gemini Flash/Pro · GitHub Actions cron.

## Repo layout
```
db/schema.sql                 Postgres schema + row level security
scripts/seed_network.py       builds the synthetic network (deterministic)
scripts/check_network.py      checks the network overlaps the portfolio
scripts/probe_sources.py      Day-1 check: which data sources work from your machine
pipeline/classify.py          rule-based announcement classifier (no LLM)
pipeline/alerts.py            volume-spike and price-move alert maths
pipeline/fetch_prices.py      end-of-day prices via yfinance (untested live)
pipeline/fetch_filings.py     NSE announcements -> classified rows (shape verified by probe)
pipeline/fetch_docs.py        screener.in annual report + transcript links
pipeline/fetch_pdf.py         download PDF (hash-cached), extract text per page
tests/                        unit tests
data/network/                 generated synthetic_network.json
docs/                         architecture, interaction model, decisions
```

## Day-1 data probe (run on your own machine)
```bash
pip install -r requirements.txt
python scripts/probe_sources.py        # tests Yahoo, NSE, screener.in for all 17 tickers
python -m pytest -q tests              # classifier + alert logic
```

## Try the network generator
```bash
python3 scripts/seed_network.py
python3 scripts/check_network.py
```

## Data and privacy note
All network data is **synthetic**. People are invented. Real company names appear only as employers. Real people named in filings are described only from what the filing itself discloses. See `docs/architecture.md`.

## Status
- [x] Architecture, interaction model
- [x] Schema, synthetic network
- [x] Classifier and alert logic (unit tested)
- [x] Live probe: NSE and screener.in work from a home connection
- [ ] Filings + docs fetchers run live (written, tests pass)
- [x] Docs fetcher parses real screener HTML (Kaynes: 18 transcripts, 4 ARs)
- [ ] PDF download + extraction run live (written, tests pass)
- [ ] LLM steps: results extraction, guidance claims, promised vs delivered
- [ ] Push, Pull, Call Sheet UI
