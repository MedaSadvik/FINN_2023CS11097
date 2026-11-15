# Covering email (paste into the email body)

**To:** assessment@enam.com
**Subject:** IIT Delhi – Founding AI Engineer - 2027
**Attach:** docs/architecture.png

Fill in before sending: the AI build history link, and your name and entry number in the sign-off.

---

Hello,

My submission for the FINN build challenge is below.

Live prototype (phone friendly): https://finn-blush.vercel.app
Code: https://github.com/MedaSadvik/FINN_2023CS11097
AI build history: [PASTE LINK]
User guide with screenshots: https://github.com/MedaSadvik/FINN_2023CS11097/blob/main/docs/FINN_User_Guide.pdf
Architecture diagram: attached (also in the repo at docs/architecture.png)

FINN is a briefing for an investor, not a dashboard. Push is a ranked digest of what changed in the portfolio, plus alerts the investor can tune. Pull is research on any NSE company, grounded only in earnings-call transcripts and the company's own filings. The Network is the investor's contacts, woven into both: every feed card and every research page ends in a Call Sheet that says who could explain this company and why, in plain facts.

WHAT I BUILT, AND WHAT I LEFT OUT

I chose a small thing that works over a broad thing that breaks. Built: the three layers, real accounts and connections, and on-demand research for any ticker. Left out on purpose: a free-form ask bar, phone push notifications (the digest is a page), and reading annual reports as text. Multi-year numbers come from screener.in's standardised annual tables instead.

DATA PIPELINES

- Filings, prices, transcripts and reported numbers each have their own source and fail on their own. A scheduled GitHub Action runs twice each weekday. If NSE blocks it, the feed keeps its last filings, says when they were last read, and prices still update.
- Filings are classified by rule. Alerts are plain maths: volume at or above twice the 20-day average, or a price move of 5% or more. Both thresholds are settings the investor can change.
- Promised vs delivered: a model reads a transcript and returns each forward-looking claim with a verbatim quote and page. Code checks the quote is really on that page, and any number must appear inside the quote, or the claim is dropped. The verdict is arithmetic on reported quarters (FY26 revenue of 3,626 cr against a guided 4,000 cr is "missed" by subtraction). A year still running is "pending". For a finished year, a second step reads the later call that reports it, under the same checks. If nothing can be verified, the claim stays "can't check yet". It never guesses.
- Each research page also has a business snapshot and a bull and bear case, every line carrying its quote and page; trajectory, balance sheet and cash quality from the annual tables by rule; and a check that puts what management promised beside what the numbers say.

SECURITY AND PRIVACY

The network is the sensitive part, so the rules live in the database, not the website. Row level security is on every table. Career details of another user are visible only to them and their accepted connections. Connections can only be made through functions, and a stranger can look someone up only by exact username, so nobody can browse or scan for people. Notes stay private. The model never sees the network: the Call Sheet, "worth a call" and "who knows what" are plain rules over rows. 32 database tests try to break these rules against real Postgres. Secrets live only in GitHub Actions; the site holds a public key and one token that can start exactly one workflow, with per-user and daily caps. The demo network is invented and labelled synthetic. For real use I would add consent per data source, encryption at rest, retention limits, delete on request and an audit log.

LLMS AND AGENTS

A model is used only where a rule cannot do the job, and never as the judge of a number. Models do three things: extract claims from transcripts, extract details from management-change filings, and summarise the latest call. Every output is verified against the source text before it is shown. All calls go through one wrapper that caches by hash (a rerun costs nothing), retries when busy, falls back across models, and stops with a plain message when the free quota is used up. The website itself makes no model calls. I did not build an open-ended agent: a bounded, verified pipeline is easier to trust and to test.

CLOUD

Vercel for the website, Supabase for the database, sign-in and access rules, GitHub Actions for the scheduled and on-demand jobs, and Google's free Gemini tier. No servers to keep alive, and the whole thing runs on free tiers.

WHAT I WOULD DO NEXT

1. Read annual reports as text, so the business and risk sections come from the report itself.
2. Push notifications and a short bounded ask bar over the verified research.
3. Settle more promises: today many segment and capex claims read "can't check yet" because a later call often does not restate the number.
4. A second model provider as an automatic backup when the free quota runs out.
5. Second-degree reach in the Network, and consent and retention controls for real contact data.

LIMITS, SAID PLAINLY

Research for most portfolio stocks is a draft written by a test model and labelled Draft on the page; Kaynes, TITAN, ASIANPAINT, OLAELEC and SBIN were built with Gemini. The free Gemini quota allows only a few companies a day, so on-demand builds are capped. screener.in is a single point of dependency. Matching a contact's typed employer to a company is by name and can miss.

Thank you for the opportunity.

[Your name]
[Entry number]
