# FINN: what I built, and why

FINN is a briefing for an investor, not a dashboard. It does three things and ties them together.

- **Push.** A short, ranked digest of what changed in the portfolio, plus alerts when a price or volume rule trips.
- **Pull.** Research on any NSE company, grounded only in primary sources: earnings call transcripts and filings. The headline feature is *promised vs delivered*: what management said it would do, and whether the reported numbers agree.
- **Network.** The investor's contacts. They are not a separate tab. Every feed card and every research page ends in a **Call Sheet**: who in your network could explain this, and why, in plain facts.

Live demo: https://finn-blush.vercel.app (works on a phone). Code: this repository.

## What I chose to build thin, and what I left out

I preferred a small thing that works over a broad thing that breaks.

Built: the three layers above, real accounts and connections, on-demand research for any ticker, and a mock network that overlaps the portfolio. Left out on purpose: free-form ask bar, push notifications (the digest is a page), and verdicts for segment-level claims. The limits section says exactly what that costs.

## Data pipelines

| Stream | Source | How it is processed |
|---|---|---|
| Filings | NSE announcements | Rule-based classifier gives each filing a priority. No model. |
| Prices and volume | End-of-day prices | Alert maths: volume at or above 2x the 20-day average, or a move of 5% or more. Both thresholds are settings. |
| Transcripts | screener.in links to the PDFs on BSE | Download, extract text page by page, cache by file hash. |
| Reported numbers | screener.in quarterly table | Revenue, EBITDA, PBT, PAT per quarter. Parsed, no model. |

**The Today feed.** The investor picks the window (24 hours, 3, 7 or 14 days) and sets what counts as unusual: the volume multiple, the price move, and which filing types to show. Settings live in a cookie on the device. Alerts are decided in the app from the price rows the feed ships, using the same maths as the pipeline (a shared test fixture keeps the two identical). Priority 0 is dropped. Priority 1 is counted ("14 routine filings hidden"), not shown. Priority 2 and up becomes cards, ranked by priority then recency. Results cards use the real reported quarters. Management-change cards quote the filing itself, and a check confirms the name, quote and previous employers appear in the filing text before the card is shown. Every event card links to the original filing.

**Refresh.** A scheduled GitHub Action (08:00 and 18:00 IST on weekdays) reads filings, prices and results numbers, asks the model only about management-change filings it has not read before (one call each, cached), and commits the new feed, which redeploys the site. Each source fails on its own: if NSE blocks the runner, the feed keeps its last filings, the page says when they were last read, and prices still update. `scripts/refresh_feed.py` does the same from a laptop.

**Promised vs delivered.**
1. A model reads a transcript and returns each forward-looking claim as JSON, with the **verbatim quote** and the page.
2. Code checks that the quote really exists on that page. If not, the claim is dropped. Any number must appear in the quote, or it is blanked.
3. The verdict is **arithmetic on the reported quarters**, not a model's opinion. FY26 revenue of 3,626 cr against a guided 4,000 cr or more is "missed", by subtraction. A future year is "pending", with year-to-date shown.
4. When a claim cannot be checked from the reported table (segment revenue, capex), it says so: "can't check yet". It never guesses.

**Works on any ticker.** `python -m pipeline.build_company TICKER` does everything from nothing. On the site, a signed-in user can type any NSE symbol and tap Build. TITAN and ASIANPAINT were built that way, with no code change.

## LLM routing and efficiency

The rule: use a model only where a rule cannot do the job, and never let it be the judge of a number.

| Step | Tool |
|---|---|
| Filing classification, alerts, verdicts, Call Sheet matching, feed ranking | Plain code. No model. |
| Claim extraction from transcripts | Gemini Flash, with quote verification |
| Management-change extraction from a filing | Gemini Flash, verified against the filing text |

- **One door** (`pipeline/llm.py`): every call goes through one wrapper. It caches each answer on disk by a hash of model, prompt and version, so a rerun costs nothing. It retries busy servers, and falls back through a list of models when one is overloaded or its daily quota is used up.
- **Quota awareness.** The free tier is small, so a build stops with a plain "API limit reached" message instead of failing. In the on-demand job, the cache is saved between runs, so a stopped build resumes without paying again.
- **A test model for drafts.** To fill the portfolio without spending Gemini quota, I built the draft research for most portfolio stocks with a separate test model (Hyde's GLM). That output is labelled **Draft** on the page. No deployed code ever calls that model. The website has no model calls at all, the on-demand job refuses any provider except Gemini, and the test key exists only on my machine. Kaynes, TITAN and ASIANPAINT were built with Gemini.

## Privacy and security

The network is the sensitive part, so the rules are in the database, not the website.

- **Row level security on every table.** The owner reads their own address book. Career details of another user are readable only by them and by their *accepted* connections. A pending request shows a name and headline only.
- **Connections can only be made through functions** (`request_connection`, `respond_connection`). A stranger can look up someone by *exact* username and gets a display name back, nothing else. There is no search and no browsing, so nobody can scan for people.
- **Notes stay private.** What you wrote about a contact is never shared with that contact.
- **The model never sees the network.** The Call Sheet is rules over rows. No contact data is sent to any model.
- **Demo accounts.** Three invented people (`demo_priya`, `demo_kabir`, `demo_meera`) accept connection requests instantly, so a reviewer can see the real connection flow alone. Nobody can sign in as them, and only the setup script can mark an account as a demo. The database tests check that a user cannot do it to themselves.
- **Signed-out visitors see an invented network**, labelled synthetic. Real users see only their own contacts and their accepted connections.
- **Secrets.** The Gemini key and the Supabase secret key live only in GitHub Actions secrets. The website holds the public anon key and one token that can start exactly one workflow. Per-user and global daily caps stop anyone burning the quota.
- **Tested on real Postgres.** 29 tests try to break these rules: a stranger reading careers, writing tables directly, and calling functions without signing in.

For a real deployment I would add: consent per data source, encryption at rest, retention limits, delete-on-request, and an audit log. The prototype only uses data users typed in themselves, or invented people.

## Cloud services

| Piece | Where | Why |
|---|---|---|
| Website | Vercel (Next.js, Tailwind) | Free, deploys from GitHub, mobile first |
| Database, sign-in, access rules | Supabase (Postgres, Auth) | Real row level security, which is where the privacy rules live |
| On-demand research builds | GitHub Actions | Free, runs the same Python as the CLI, holds the secrets, nothing to host |
| Model | Google AI Studio (Gemini), free tier | Cheap, structured output |

No servers to keep alive.

## The Network, woven in

The mock network has 120 invented people, 36 employers and 30 employer relations (competitor, supplier, customer), built to overlap the 17-stock portfolio and the research companies. A Call Sheet ranks people by rule: worked at the company, then at a competitor, supplier or customer, then overlapped with someone who did. Each line is a plain fact tagged by source ("public profile", "their profile", "your notes"). There is no strength score, because I could not defend one.

## Known limits (said plainly)

- Most promises read "can't check yet". Segment and capex claims need later transcripts, and I did not build that second tier. This weakens the headline feature, and it is the first thing I would build next.
- Research for most portfolio stocks is a draft from a test model. Treat the promise lists as indicative.
- The free Gemini quota allows about five companies a day, which is why on-demand building has daily caps.
- screener.in is a single point of dependency for documents and quarterly numbers.
- Matching a person's typed employer to a company is by name and first whole words. It is a heuristic and can miss.
- The digest is a page. Nothing is pushed to the phone.

## AI build history

I built this with Claude as a pair programmer, working in small steps with tests at each step. The conversation history is linked in the covering email.
