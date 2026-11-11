import sample from "@/data/kaynes.json";
import realCompanies from "@/data/companies.json";
import feed from "@/data/feed.json";
import live from "@/data/feed_live.json";
import type { FeedItem, Pledge, Quarter } from "./types";
import { windowLabel } from "./format";

export type CompanyData = {
  ticker: string;
  employer_key: string | null;
  name: string;
  quarters: Quarter[];
  promises: Pledge[];
  sample?: boolean;   // placeholder wording, shown with a label
  provider?: string;  // "gemini" is the shipped run; anything else is a test model
};

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

type LiveFeed = { window?: { start: string; end: string; hours: number }; routine_hidden?: number; provider?: string | null; items: FeedItem[] };

/** Real feed (scripts/export_feed.py) when exported, otherwise the labelled sample. */
export function getFeed() {
  const real = live as unknown as LiveFeed;
  if (real.items.length || real.window) {
    return {
      live: true,
      window: real.window ? windowLabel(real.window.start, real.window.end) : "",
      hours: real.window?.hours ?? 48,
      routineHidden: real.routine_hidden ?? 0,
      provider: real.provider ?? null,
      items: real.items,
    };
  }
  const results = Object.values(companies).map(resultsItem).filter((x): x is FeedItem => x !== null);
  return { live: false, window: feed.window, hours: 48, routineHidden: 0, provider: null,
    items: [...results, ...(feed.items as unknown as FeedItem[])] };
}
