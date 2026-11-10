import type { Employer, Evidence, Lead, Network, Person, Role } from "./types";
import { monthYear } from "./format";
import raw from "@/data/network.json";

export const network = raw as unknown as Network;

const CURRENT = 9999;
const end = (r: Role) => r.end_year ?? CURRENT;
/** Two stints overlap if they share at least one year. */
const together = (a: Role, b: Role) => a.employer_key === b.employer_key && a.start_year <= end(b) && b.start_year <= end(a);

export const employer = (key: string): Employer | undefined => network.employers.find((e) => e.key === key);
export const employerName = (key: string) => employer(key)?.name ?? key;
const currentRole = (p: Person) => p.roles.find((r) => r.end_year === null);

function peopleWhoOverlapped(role: Role, except: number, limit = 3): Person[] {
  return network.people
    .filter((p) => p.id !== except && p.roles.some((r) => together(r, role)))
    .slice(0, limit);
}

/**
 * Call Sheet: who in your contacts can speak to this company, and why.
 * No score. Every line is a fact you can check, tagged with where it came from.
 * Plain rules, no model: the LLM never sees the network.
 */
export function callSheet(employerKey: string, limit = 3): Lead[] {
  const sector = employer(employerKey)?.sector;
  const ticker = employer(employerKey)?.ticker;
  const related = new Map(
    network.employer_relations.filter((r) => r.ticker === ticker).map((r) => [r.employer_key, r.relation]),
  );
  const leads: Lead[] = [];
  for (const p of network.people.filter((x) => x.kind === "contact")) {
    const mine = p.roles.filter((r) => r.employer_key === employerKey);
    const near = p.roles.filter((r) => related.has(r.employer_key));
    const reasons: Evidence[] = [];
    if (mine.length) {
      const r = mine[0];
      reasons.push({
        text: `${r.title} at ${employerName(employerKey)}, ${r.start_year}–${r.end_year ?? "now"}.`,
        source: "public profile",
      });
      const peers = peopleWhoOverlapped(r, p.id, 8).filter((q) => {
        const cr = currentRole(q);
        return cr && employer(cr.employer_key)?.sector === sector;
      });
      if (peers.length) {
        const names = peers.slice(0, 2).map((q) => {
          const at = currentRole(q)!.employer_key;
          return at === employerKey ? `${q.full_name} (still there)` : `${q.full_name} (now ${employerName(at)})`;
        });
        reasons.push({
          text: `Overlapped there with ${peers.length} ${peers.length === 1 ? "person" : "people"} still in the sector, including ${names.join(" and ")}.`,
          source: "public profile",
        });
      }
    } else if (near.length) {
      const r = near[0];
      reasons.push({
        text: `${r.title} at ${employerName(r.employer_key)}, ${r.start_year}–${r.end_year ?? "now"}. ${employerName(r.employer_key)} is a ${related.get(r.employer_key)} of ${employerName(employerKey)}.`,
        source: "public profile",
      });
    } else continue;
    const cr = currentRole(p);
    if (cr) reasons.push({ text: `Now ${p.headline}.`, source: "public profile" });
    if (p.last_spoke) reasons.push({ text: `You last spoke in ${monthYear(p.last_spoke)}.`, source: "your notes" });
    leads.push({ person: p, reasons, tier: mine.length ? "worked_there" : "adjacent" });
  }
  const recency = (l: Lead) => Math.max(...l.person.roles.filter((r) => r.employer_key === employerKey || related.has(r.employer_key)).map(end));
  return leads
    .sort((a, b) => (a.tier === b.tier ? recency(b) - recency(a) : a.tier === "worked_there" ? -1 : 1))
    .slice(0, limit);
}

/** For a newly named executive: which of your contacts overlapped with them at an earlier employer. */
export function overlapWith(history: Role[], limit = 3): Lead[] {
  const leads: Lead[] = [];
  for (const p of network.people.filter((x) => x.kind === "contact")) {
    const reasons: Evidence[] = [];
    for (const h of history) {
      const mine = p.roles.find((r) => together(r, h));
      if (mine) {
        const from = Math.max(mine.start_year, h.start_year);
        const to = Math.min(end(mine), end(h));
        reasons.push({
          text: `Both at ${employerName(h.employer_key)} in ${from}–${to === CURRENT ? "now" : to}. ${p.full_name} was there as ${mine.title}.`,
          source: "public profile",
        });
      }
    }
    if (!reasons.length) continue;
    if (p.last_spoke) reasons.push({ text: `You last spoke in ${monthYear(p.last_spoke)}.`, source: "your notes" });
    leads.push({ person: p, reasons, tier: "overlap" });
  }
  return leads.slice(0, limit);
}
