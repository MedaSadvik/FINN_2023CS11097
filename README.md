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
data/network/                 generated synthetic_network.json
docs/                         architecture, interaction model, decisions
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
- [ ] Data pipelines (prices, filings, documents)
- [ ] Push, Pull, Call Sheet UI
