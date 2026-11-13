# FINN

Mobile-first financial investment agent. Built for the ENAM Founding AI Engineer Build Challenge (Nov 2026).

**Point of view:** FINN is a briefing, not a dashboard. A short ranked feed, a pinned ask-bar, and a *Call Sheet* on every card that says who in your network to call and why.

| Layer | What it does |
|---|---|
| **Push** | Windowed digest of filings, ranked. Alerts on volume, price move, filing type. |
| **Pull** | Company research grounded only in annual reports and concall transcripts. Star feature: promised vs delivered. |
| **Network** | Synthetic investor network. Woven into Push and Pull as Call Sheets. On its own tab it flags who is worth a call and who knows what. |

## Try it
Live: https://finn-blush.vercel.app (open it on a phone).
1. **Today** shows what changed, ranked. Tap *Who to call* on a card for the Call Sheet.
2. **Research** lists the companies read so far. Open one for promised vs delivered. Type any NSE symbol to build a new one (sign in first; a few builds per day).
3. **Network** needs an account. Sign up, then add `demo_priya`, `demo_kabir` or `demo_meera` by username. They accept at once, and their invented careers show up in Call Sheets ("their profile"). Real people accept by hand. *Load sample contacts* gives you a full invented network instead.

Signed out, you see an invented network. Research marked **Draft** was extracted by a test model; the rest by Gemini. Details: [docs/WRITEUP.md](docs/WRITEUP.md).

## Stack
Next.js 16 + Tailwind (Vercel) · Python pipeline · Supabase Postgres, Auth and row level security · Gemini Flash · GitHub Actions for on-demand builds.

## Run the pipeline on any ticker
```bash
pip install -r requirements.txt
cp .env.example .env                       # add GEMINI_API_KEY
python -m pipeline.build_company TITAN     # docs, quarterly numbers, guidance, verdicts (about 15 model calls)
python scripts/export_frontend.py TITAN    # writes frontend/data/companies.json
python scripts/build_portfolio.py          # every portfolio stock; resumable
python scripts/refresh_feed.py             # the Today feed: filings, prices, results numbers, new executives (--no-people skips the model)
```

## Run the website
```bash
cd frontend && npm install && npm run dev  # needs Node 22
```
Without Supabase keys the site runs signed-out, on the invented network. To switch on accounts, create a Supabase project, run these in its SQL editor in order: `db/schema.sql`, `db/seed_reference.sql`, `db/migrations/002` to `006`. Turn off "Confirm email" under Authentication, then copy `frontend/.env.local.example` to `.env.local` and fill it in.

Demo accounts: run `006`, set `DEMO_EMAIL_TEMPLATE` in `.env` (an address you control, with `{name}`, like `you+{name}@gmail.com`), then `python scripts/create_demo_accounts.py`.

On-demand builds also need three GitHub Actions secrets (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`) and a token in the website's environment (`BUILD_GITHUB_TOKEN`). The workflow file must be on the default branch.

## Tests
```bash
python -m pytest -q                                                     # 149 pass, 26 need a database
TEST_DATABASE_URL=postgresql://postgres:pw@localhost/finn_test python -m pytest tests/test_rls.py   # privacy rules on real Postgres
cd frontend && npx tsx --test lib/network.test.ts lib/build-state.test.ts
```
The privacy test drops and recreates the `public` schema. Never point it at a real database.

## Repo layout
```
db/schema.sql, db/migrations/    Postgres schema, row level security, accounts, connections, on-demand builds
pipeline/                        Python: fetchers, classifier, alerts, guidance extraction, verdicts, feed, export, llm.py
scripts/                         build_portfolio, export_frontend, export_feed, worker_build (GitHub Actions), probes
frontend/                        Next.js app (Today, Research, Network, profile)
.github/workflows/               build-company.yml: the on-demand research job
tests/                           Python tests, including privacy rules on real Postgres
docs/                            WRITEUP.md, architecture.md, interaction_model.md
data/network/                    the invented network (120 people, 36 employers)
```

## Data and privacy
The demo network is invented. Real company names appear only as employers. Accounts are real: privacy is enforced in the database, and no contact data goes to any model. See the privacy section of [docs/WRITEUP.md](docs/WRITEUP.md).

## Status
Built: Push (digest and alerts), Pull (promised vs delivered, any ticker), Network (accounts, connections, Call Sheet, worth-a-call, who-knows-what), on-demand builds with daily caps.
Not built: verdicts for segment-level claims (most promises read "can't check yet"), a free-form ask bar, phone push notifications.
