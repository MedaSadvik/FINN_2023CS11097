# FINN architecture v1 (the original plan)

This is the plan I wrote before building. What was built, and why it differs, is in [WRITEUP.md](WRITEUP.md), with the final diagram in [architecture.png](architecture.png).

Principle: thin-but-working beats broad-but-broken.

## Two paths
- **Hot path:** demo set (portfolio + 3-5 research names) precomputed. Instant.
- **Cold path:** any other NSE ticker is ingested on first request, then cached. Same code.

## Diagram
```
 Sources                Python pipeline                        Supabase Postgres              Next.js on Vercel
 yfinance (EOD)   -->   fetch_prices      ---------------->    prices_eod                     Push: digest + alerts
 BSE/NSE filings  -->   fetch_filings --> classify (rules)-->  filings (+priority, summary)    Pull: company view
 screener.in docs -->   fetch_docs --> chunk --> extract -->   documents, chunks, quarters,    Call Sheet chips
 (transcripts, AR)                       (Flash) -> verify     guidance_claims, verdicts       Ask-bar (bounded agent)
 Synthetic network --> seed_network ----------------------->  people, roles, education (RLS)
                        link_people (filing name -> person)--> filing_people
 Triggers: GitHub Actions cron (daily after close) + on-demand worker (cold path)
```

## Pipelines
| Stream | Fetch | Refresh | Store |
|---|---|---|---|
| Prices/volume | yfinance `.NS` | daily | `prices_eod` |
| Filings | BSE first, NSE second | daily | `filings` |
| Transcripts / annual reports | screener.in links, else company IR | on first need | `documents`, `chunks` |
| Network | synthetic seed | static | `people`, `roles`, `education` |

Filing priority comes from rules on exchange category and subject. An LLM is used only for vague categories.
Name matching (filing person to network person): normalise name, then employer and tenure overlap. LLM breaks ties only. Evidence is stored.
NSE often blocks cloud IPs. Fallback: BSE first, plus a cached snapshot in the repo.

## Privacy and security
- Prototype network is fully synthetic and labelled so.
- Row Level Security on every personal table: `owner_id = auth.uid()`. Service key stays server-side.
- **The LLM never sees the whole network.** SQL finds matches. The model gets 2-3 facts to phrase one sentence.
- Real deployment: public-profile data or user-uploaded contacts only; consent per source; encryption at rest; store only role, employer, school, dates; retention limit; delete on request; audit log.
- Real people in filings: only the bio the company discloses.

## LLM routing
| Step | Tool |
|---|---|
| Announcement classify | Rules |
| Ambiguous classify, one-line summaries | Gemini Flash |
| Results extraction (Revenue, EBITDA, PBT, PAT) | Flash + JSON schema + arithmetic check |
| Guidance claim extraction | Flash on section-targeted pages |
| Promised vs delivered, bull vs bear | Gemini Pro, offline, cached |
| "Why this person" sentence | Flash |
| Ask-bar | Flash agent, 3 tools, max 4 steps |

Every claim stores a verbatim quote and page. Code checks the quote exists on the page. Failed check means the claim is dropped.
Cache key: hash(document + prompt version). No vector DB in the MVP.

## Cloud
Vercel (frontend, thin API) · Supabase (DB, auth, RLS, storage) · GitHub Actions (daily jobs) · Render free tier (Python worker, cold path) · Google AI Studio (models).

## "Knows" definition
Two people overlapped at the same employer or school in the same years. Computed by the `person_overlaps` view in `db/schema.sql`. No numeric strength score: the Call Sheet shows plain facts.
