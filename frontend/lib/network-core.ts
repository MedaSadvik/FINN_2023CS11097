import type { Employer, Evidence, HistoryEntry, Lead, Network, Person, Role } from "./types";
import { monthYear } from "./format";

const CURRENT = 9999;
const end = (r: Role) => r.end_year ?? CURRENT;
/** Two stints overlap if they share at least one year. */
const together = (a: Role, b: Role) => a.employer_key === b.employer_key && a.start_year <= end(b) && b.start_year <= end(a);

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
  const sector = employer(net, employerKey)?.sector;
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
        text: `${r.title} at ${employerName(net, employerKey)}, ${r.start_year}–${r.end_year ?? "now"}.`,
        source: src(p),
      });
      const peers = peopleWhoOverlapped(net, r, p.id, 8).filter((q) => {
        const cr = currentRole(q);
        return cr && employer(net, cr.employer_key)?.sector === sector;
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
