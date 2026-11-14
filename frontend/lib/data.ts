import sample from "@/data/kaynes.json";
import realCompanies from "@/data/companies.json";
import feed from "@/data/feed.json";
import live from "@/data/feed_live.json";
import type { FeedItem, Pledge, Quarter, Snapshot } from "./types";
import type { FeedSnapshot, Market } from "./feed-view";
import type { Financials } from "./financials";
import financialsFile from "@/data/financials.json";

export type CompanyData = {
  ticker: string;
  employer_key: string | null;
  name: string;
  quarters: Quarter[];
  promises: Pledge[];
  sample?: boolean;   // placeholder wording, shown with a label
  provider?: string;  // "gemini" is the shipped run; anything else is a test model
  financials?: Financials; // multi-year numbers read with an on-demand build
  snapshot?: Snapshot;     // business summary and bull/bear, each line with a quote from the latest call
};

/** Multi-year numbers: from the build itself, else the portfolio file (scripts/export_financials.py). Null when neither has them. */
export const getFinancials = (c: CompanyData): Financials | null =>
  c.financials ?? (financialsFile as unknown as Record<string, Financials>)[c.ticker.toUpperCase()] ?? null;

// Real exports (scripts/export_frontend.py) win over the built-in sample.
const companies: Record<string, CompanyData> = {
  KAYNES: sample as unknown as CompanyData,
  ...(realCompanies as unknown as Record<string, CompanyData>),
};

export const getCompany = (t: string) => companies[t.toUpperCase()];
export const knownTickers = () => Object.keys(companies);

/** Sample results card from a company's reported quarters (only used before a real feed is exported). */
function resultsItem(c: CompanyData): FeedItem | null {
  const by = new Map(c.quarters.map((q) => [q.quarter, q]));
  const cur = c.quarters[c.quarters.length - 1];
  if (!cur) return null;
  const n = Number(cur.quarter[1]);
  const fy = Number(cur.quarter.slice(-2));
  const prev = by.get(n > 1 ? `Q${n - 1}FY${String(fy).padStart(2, "0")}` : `Q4FY${String(fy - 1).padStart(2, "0")}`);
  const yoy = by.get(`Q${n}FY${String(fy - 1).padStart(2, "0")}`);
  if (!prev || !yoy) return null;
  return { id: `r-${c.ticker}`, type: "results", ticker: c.ticker, company: c.name, filed: "", quarter: cur.quarter,
    cur, qoq: prev, yoy };
}

type LiveFeed = {
  window?: { start: string; end: string; hours: number };
  routine_hidden?: number; routine_filed?: string[]; market?: Market; filings_as_of?: string | null; provider?: string | null; items: FeedItem[];
};

/** Real feed (scripts/export_feed.py) when exported, otherwise the labelled sample. */
export function getFeed() {
  const real = live as unknown as LiveFeed;
  if (real.items.length || real.window) {
    const end = real.window ? real.window.end : new Date().toISOString();
    const snapshot: FeedSnapshot = {
      endMs: new Date(end).getTime(),
      maxHours: real.window?.hours ?? 48,
      items: real.items,
      routineFiled: real.routine_filed ?? null,
      routineTotal: real.routine_hidden ?? 0,
      market: real.market ?? null,
      filingsAsOfMs: real.filings_as_of ? new Date(real.filings_as_of).getTime() : null,
    };
    return { live: true as const, provider: real.provider ?? null, end, snapshot };
  }
  const results = Object.values(companies).map(resultsItem).filter((x): x is FeedItem => x !== null);
  return { live: false as const, provider: null, note: feed.window,
    items: [...results, ...(feed.items as unknown as FeedItem[])] };
}
