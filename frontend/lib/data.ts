import sample from "@/data/kaynes.json";
import realCompanies from "@/data/companies.json";
import feed from "@/data/feed.json";
import type { FeedItem, Pledge, Quarter } from "./types";

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

/** Newest reported quarter against the previous quarter and the same quarter a year earlier. */
function resultsItem(c: CompanyData): FeedItem | null {
  const by = new Map(c.quarters.map((q) => [q.quarter, q]));
  const cur = c.quarters[c.quarters.length - 1];
  if (!cur) return null;
  const n = Number(cur.quarter[1]);
  const fy = Number(cur.quarter.slice(-2));
  const prev = by.get(n > 1 ? `Q${n - 1}FY${String(fy).padStart(2, "0")}` : `Q4FY${String(fy - 1).padStart(2, "0")}`);
  const yoy = by.get(`Q${n}FY${String(fy - 1).padStart(2, "0")}`);
  if (!prev || !yoy) return null;
  return { id: `r-${c.ticker}`, type: "results", ticker: c.ticker, company: c.name, priority: "high",
    filed: "", quarter: cur.quarter, cur, qoq: prev, yoy };
}

export function getFeed() {
  const results = Object.values(companies).map(resultsItem).filter((x): x is FeedItem => x !== null);
  return { window: feed.window, items: [...results, ...(feed.items as unknown as FeedItem[])] };
}
