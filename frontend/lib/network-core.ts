import type { Employer, Evidence, HistoryEntry, Lead, Network, Person, Role } from "./types";
import { monthYear } from "./format";

const CURRENT = 9999;
const end = (r: Role) => r.end_year ?? CURRENT;
/** Two stints overlap if they share at least one year. */
const together = (a: Role, b: Role) => a.employer_key === b.employer_key && a.start_year <= end(b) && b.start_year <= end(a);

const STOP = new Set(["ltd", "limited", "pvt", "private", "inc", "corp", "corporation", "llp", "india", "the", "co"]);
/** A company name reduced to what identifies it: lowercase, no punctuation, no "Ltd", "India" and the like. */
export const tidyName = (s: string) =>
  s.toLowerCase().replace(/&/g, " and ").replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter((w) => w && !STOP.has(w)).join(" ");

/**
 * Do two employer names mean the same company? Equal after tidying, or one is the other's first whole words
 * ("Titan" and "Titan Company"). The shorter name must have 5+ letters so "Tata" does not match every Tata company.
 */
export function sameCompany(a: string, b: string): boolean {
  const x = tidyName(a), y = tidyName(b);
  if (!x || !y) return false;
  if (x === y) return true;
  const [short, long] = x.length <= y.length ? [x, y] : [y, x];
  return short.length >= 5 && long.startsWith(short + " ");
}

/** Where the person said they worked, when it differs from the company we matched it to. */
const atName = (net: Network, r: Role, key: string) => {
  const name = employerName(net, key);
  return r.employer_name && tidyName(r.employer_name) !== tidyName(name) ? `${name} (they wrote \u201c${r.employer_name}\u201d)` : name;
};

export const employer = (net: Network, key: string): Employer | undefined => net.employers.find((e) => e.key === key);
export const employerKeyFor = (net: Network, ticker: string) => net.employers.find((e) => e.ticker === ticker)?.key ?? ticker.toLowerCase();
export const employerName = (net: Network, key: string) => employer(net, key)?.name ?? key;
/** Where a fact came from: a connection's own profile, or the sample/public data. */
const src = (p: Person): Evidence["source"] => (p.linked ? "their profile" : "public profile");
const currentRole = (p: Person) => p.roles.find((r) => r.end_year === null);

function peopleWhoOverlapped(net: Network, role: Role, except: number, limit = 3): Person[] {
  return net.people
    .filter((p) => p.id !== except && p.roles.some((r) => together(r, role)))
    .slice(0, limit);
}

/**
 * Call Sheet: who in your contacts can speak to this company, and why.
 * No score. Every line is a fact you can check, tagged with where it came from.
 * Plain rules, no model: the LLM never sees the network.
 */
export function callSheet(net: Network, employerKey: string, limit = 3): Lead[] {
  const sector = employer(net, employerKey)?.sector || null; // untracked companies have no sector: never match on it
  const ticker = employer(net, employerKey)?.ticker;
  const related = new Map(
    net.employer_relations.filter((r) => r.ticker === ticker).map((r) => [r.employer_key, r.relation]),
  );
  const leads: Lead[] = [];
  for (const p of net.people.filter((x) => x.kind === "contact")) {
    const mine = p.roles.filter((r) => r.employer_key === employerKey);
    const near = p.roles.filter((r) => related.has(r.employer_key));
    const reasons: Evidence[] = [];
    if (mine.length) {
      const r = mine[0];
      reasons.push({
        text: `${r.title} at ${atName(net, r, employerKey)}, ${r.start_year}–${r.end_year ?? "now"}.`,
        source: src(p),
      });
      const peers = peopleWhoOverlapped(net, r, p.id, 8).filter((q) => {
        const cr = currentRole(q);
        return cr && sector !== null && employer(net, cr.employer_key)?.sector === sector;
      });
      if (peers.length) {
        const names = peers.slice(0, 2).map((q) => {
          const at = currentRole(q)!.employer_key;
          return at === employerKey ? `${q.full_name} (still there)` : `${q.full_name} (now ${employerName(net, at)})`;
        });
        reasons.push({
          text: `Overlapped there with ${peers.length} ${peers.length === 1 ? "person" : "people"} still in the sector, including ${names.join(" and ")}.`,
          source: src(p),
        });
      }
    } else if (near.length) {
      const r = near[0];
      reasons.push({
        text: `${r.title} at ${employerName(net, r.employer_key)}, ${r.start_year}–${r.end_year ?? "now"}. ${employerName(net, r.employer_key)} is a ${related.get(r.employer_key)} of ${employerName(net, employerKey)}.`,
        source: src(p),
      });
    } else continue;
    const cr = currentRole(p);
    if (cr) reasons.push({ text: `Now ${p.headline}.`, source: src(p) });
    if (p.last_spoke) reasons.push({ text: `You last spoke in ${monthYear(p.last_spoke)}.`, source: "your notes" });
    leads.push({ person: p, reasons, tier: mine.length ? "worked_there" : "adjacent" });
  }
  const recency = (l: Lead) => Math.max(...l.person.roles.filter((r) => r.employer_key === employerKey || related.has(r.employer_key)).map(end));
  return leads
    .sort((a, b) => (a.tier === b.tier ? recency(b) - recency(a) : a.tier === "worked_there" ? -1 : 1))
    .slice(0, limit);
}

/** For a newly named executive: which of your contacts overlapped with them at an earlier employer. */
export function overlapWith(net: Network, history: HistoryEntry[], limit = 3): Lead[] {
  const leads: Lead[] = [];
  for (const p of net.people.filter((x) => x.kind === "contact")) {
    const reasons: Evidence[] = [];
    for (const h of history) {
      if (!h.employer_key) continue; // employer is not in your network, so nobody to compare with
      const mine = p.roles.find((r) => r.employer_key === h.employer_key && (h.start_year === null || together(r, { ...r, ...h, employer_key: h.employer_key, title: h.title ?? "", start_year: h.start_year, end_year: h.end_year })));
      if (!mine) continue;
      if (h.start_year === null) {
        reasons.push({ text: `${p.full_name} worked at ${employerName(net, h.employer_key)} as ${mine.title}, ${mine.start_year}–${mine.end_year ?? "now"}. The filing does not say when they were there.`, source: src(p) });
      } else {
        const from = Math.max(mine.start_year, h.start_year);
        const to = Math.min(end(mine), h.end_year ?? CURRENT);
        reasons.push({ text: `Both at ${employerName(net, h.employer_key)} in ${from}–${to === CURRENT ? "now" : to}. ${p.full_name} was there as ${mine.title}.`, source: src(p) });
      }
    }
    if (!reasons.length) continue;
    if (p.last_spoke) reasons.push({ text: `You last spoke in ${monthYear(p.last_spoke)}.`, source: "your notes" });
    leads.push({ person: p, reasons, tier: "overlap" });
  }
  return leads.slice(0, limit);
}
