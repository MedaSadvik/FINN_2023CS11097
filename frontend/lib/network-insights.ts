/**
 * What the Network notices on its own, without being asked. Plain rules over the investor's contacts and the feed.
 * No model ever sees the network.
 *
 *  - reconnectIdeas: a contact used to work at a company that just filed something, and you have not spoken in a while.
 *  - expertiseMap:   who your go-to people are per sector, and where your portfolio is deeper than your network.
 *
 * Both only use employers FINN tracks (those with a ticker). A free-text employer is matched to a tracked company by
 * name, the same way the Call Sheet does it.
 */
import { sameCompany } from "./network-core";
import { monthYear, shortDate } from "./format";
import type { Employer, Evidence, FeedItem, Network, Person, Role } from "./types";

export const SECTOR_LABEL: Record<string, string> = {
  semis_electronics: "Semiconductors and electronics",
  ai_cloud: "AI and cloud",
  it_services: "IT services",
  pharma: "Pharma",
  financials: "Financials",
  energy_infra: "Energy and infrastructure",
};
export const sectorLabel = (s: string) => SECTOR_LABEL[s] ?? s.replace(/_/g, " ");

const DAY = 86_400_000;
const tracked = (net: Network) => net.employers.filter((e) => e.ticker);

/** The tracked company a role refers to: by key, else by the name the person wrote. */
export function trackedFor(net: Network, r: Role): Employer | undefined {
  const t = tracked(net);
  return t.find((e) => e.key === r.employer_key) ?? (r.employer_name ? t.find((e) => sameCompany(r.employer_name!, e.name)) : undefined);
}

export function monthsSince(iso: string | null, now: Date): number | null {
  if (!iso) return null;
  return Math.max(0, Math.floor((now.getTime() - new Date(`${iso}T00:00:00Z`).getTime()) / (30.44 * DAY)));
}

// ---------------------------------------------------------------- keep the network warm

export type FilingRef = { id: string; ticker: string; company: string; filed: string; priority: number; what: string; ask: string; pdf_url?: string | null };

const WHAT: Record<string, [string, string]> = {
  "M&A": ["announced a deal", "Ask what the deal means for the business day to day."],
  capex: ["announced a capex plan", "Ask what is driving the expansion, and how demand looks."],
  litigation: ["filed a legal update", "Ask how serious it is inside the company."],
  fund_raise: ["announced fund raising", "Ask why now, and who is likely to take it up."],
  credit_rating: ["had a credit rating action", "Ask what the rating agency picked up on."],
  dividend: ["declared a dividend", "Ask how management talks about cash internally."],
  bonus_split: ["announced a bonus or split", "Ask what is behind it."],
  pledging: ["reported a change in share pledges", "Ask what you would miss reading the filing alone."],
};

/** The feed's filings, reduced to what the Network needs. Alerts are price moves, not filings. */
export function filingRefs(items: FeedItem[]): FilingRef[] {
  const out: FilingRef[] = [];
  for (const i of items) {
    if (i.type === "alert") continue;
    const base = { id: i.id, ticker: i.ticker, company: i.company, filed: i.filed, pdf_url: i.pdf_url };
    if (i.type === "results") out.push({ ...base, priority: 3, what: `reported ${i.quarter} results`, ask: "Ask what the quarter looks like from the inside." });
    else if (i.type === "mgmt_change") out.push({ ...base, priority: 3, what: "announced a management change", ask: "Ask what they make of the change, and of the person arriving." });
    else {
      const [what, ask] = WHAT[i.category ?? ""] ?? ["filed an announcement", "Ask what they are hearing."];
      out.push({ ...base, priority: (i as { priority?: number }).priority ?? 2, what, ask });
    }
  }
  return out;
}

export type Reconnect = { person: Person; filing: FilingRef; tie: "now" | "formerly"; silentMonths: number | null; reasons: Evidence[]; ask: string };

/**
 * Contacts with a reason to hear from you: they worked at a company that just filed, and the silence is long.
 * Ranked: still there before formerly, then the weightier filing, then the longest silence. One idea per person.
 */
export function reconnectIdeas(net: Network, filings: FilingRef[], now: Date, opts: { minMonths?: number; limit?: number } = {}): Reconnect[] {
  const { minMonths = 6, limit = 5 } = opts;
  const byTicker = new Map<string, FilingRef>();
  for (const f of filings) {
    const cur = byTicker.get(f.ticker);
    if (!cur || f.priority > cur.priority || (f.priority === cur.priority && f.filed > cur.filed)) byTicker.set(f.ticker, f);
  }
  const ideas: Reconnect[] = [];
  for (const p of net.people.filter((x) => x.kind === "contact")) {
    const silent = monthsSince(p.last_spoke, now);
    if (silent !== null && silent < minMonths) continue;
    let best: Reconnect | null = null;
    for (const r of p.roles) {
      const emp = trackedFor(net, r);
      const filing = emp?.ticker ? byTicker.get(emp.ticker) : undefined;
      if (!emp || !filing) continue;
      const tie = r.end_year === null ? "now" : "formerly";
      const reasons: Evidence[] = [
        { text: `${r.title} at ${emp.name}, ${r.start_year}–${r.end_year ?? "now"}.`, source: p.linked ? "their profile" : "public profile" },
        { text: `${emp.name} ${filing.what} on ${shortDate(filing.filed)}.`, source: "NSE filing" },
        { text: silent === null ? "No conversation logged in your notes." : `You last spoke in ${monthYear(p.last_spoke!)}, ${silent} months ago.`, source: "your notes" },
      ];
      const idea: Reconnect = { person: p, filing, tie, silentMonths: silent, reasons, ask: filing.ask };
      if (!best || (tie === "now" && best.tie !== "now") || (tie === best.tie && filing.priority > best.filing.priority)) best = idea;
    }
    if (best) ideas.push(best);
  }
  const rank = (i: Reconnect) => (i.tie === "now" ? 1 : 0);
  return ideas
    .sort((a, b) => rank(b) - rank(a) || b.filing.priority - a.filing.priority || (b.silentMonths ?? 999) - (a.silentMonths ?? 999) || a.person.full_name.localeCompare(b.person.full_name))
    .slice(0, limit);
}

// ---------------------------------------------------------------- who knows what

export type Expert = { person: Person; years: number; where: string[]; current: boolean };
export type Theme = { sector: string; label: string; holdings: string[]; experts: Expert[]; expertCount: number; gap: boolean };

/** Whole years a person has spent in tracked companies of each sector (a stint counts at least one year). */
function yearsBySector(net: Network, p: Person, year: number) {
  const out = new Map<string, { years: number; where: Set<string>; current: boolean }>();
  for (const r of p.roles) {
    const emp = trackedFor(net, r);
    if (!emp || !emp.sector) continue;
    const e = out.get(emp.sector) ?? { years: 0, where: new Set<string>(), current: false };
    e.years += Math.max(1, (r.end_year ?? year) - r.start_year);
    e.where.add(emp.name);
    e.current ||= r.end_year === null;
    out.set(emp.sector, e);
  }
  return out;
}

/**
 * Your go-to people per sector, and where the portfolio is deeper than the network.
 * A go-to person has at least `minYears` in the sector. A gap is a sector you hold companies in and know no one in.
 */
export function expertiseMap(net: Network, now: Date, opts: { minYears?: number; perTheme?: number } = {}): Theme[] {
  const { minYears = 2, perTheme = 3 } = opts;
  const bySector = new Map<string, Theme>();
  const theme = (s: string) => {
    if (!bySector.has(s)) bySector.set(s, { sector: s, label: sectorLabel(s), holdings: [], experts: [], expertCount: 0, gap: false });
    return bySector.get(s)!;
  };
  for (const e of tracked(net)) if (e.sector) theme(e.sector).holdings.push(e.name);
  for (const p of net.people.filter((x) => x.kind === "contact")) {
    for (const [sector, v] of yearsBySector(net, p, now.getFullYear())) {
      if (v.years >= minYears) theme(sector).experts.push({ person: p, years: v.years, where: [...v.where], current: v.current });
    }
  }
  const themes = [...bySector.values()];
  for (const t of themes) {
    t.experts.sort((a, b) => b.years - a.years || Number(b.current) - Number(a.current) || a.person.full_name.localeCompare(b.person.full_name));
    t.expertCount = t.experts.length;
    t.gap = t.holdings.length > 0 && t.expertCount === 0;
    t.experts = t.experts.slice(0, perTheme);
  }
  return themes.sort((a, b) => Number(b.gap) - Number(a.gap) || b.holdings.length - a.holdings.length || a.label.localeCompare(b.label));
}
