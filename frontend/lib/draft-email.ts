/**
 * A first-draft email to one contact. Plain template rules over facts already in the network: no model, and
 * nothing is sent anywhere. The investor edits it and sends it from their own mail app.
 * Only facts we hold are used (a role they had, when you last spoke). A tie is never claimed that the data does not show.
 */
import { employer, employerKeyFor, employerName } from "./network-core";
import { monthYear } from "./format";
import { monthsSince } from "./network-insights";
import type { Network, Person } from "./types";

const TITLES = new Set(["dr", "mr", "ms", "mrs", "prof", "shri", "smt"]);
export const firstName = (full: string) => {
  const parts = full.replace(/\./g, "").trim().split(/\s+/).filter(Boolean);
  const first = parts.find((p) => !TITLES.has(p.toLowerCase())) ?? parts[0] ?? "";
  return first;
};

export type Draft = { subject: string; body: string };

/** `about` is a tracked company's ticker, when the investor came from that company's page or a filing. */
export function draftEmail(net: Network, p: Person, opts: { about?: string | null; me?: string | null; now: Date }): Draft {
  const { about, me, now } = opts;
  const key = about ? employerKeyFor(net, about) : null;
  const company = key ? employerName(net, key) : null;
  const known = key ? employer(net, key) : undefined;
  const hasCompany = !!company && !!known;

  const months = monthsSince(p.last_spoke, now);
  const opening = p.last_spoke && months !== null && months >= 3
    ? `It has been a while since we last spoke, around ${monthYear(p.last_spoke)}. I hope you are well.`
    : "I hope you are well.";

  let context = "";
  if (hasCompany) {
    const mine = p.roles.find((r) => r.employer_key === key);
    const related = new Set(net.employer_relations.filter((r) => r.ticker === known!.ticker).map((r) => r.employer_key));
    const near = p.roles.find((r) => related.has(r.employer_key));
    if (mine) {
      const span = mine.end_year === null ? `since ${mine.start_year}` : `from ${mine.start_year} to ${mine.end_year}`;
      context = `I am reading up on ${company} and remembered you were ${mine.title} there ${span}.`;
    } else if (near) {
      context = `I am reading up on ${company} and remembered your time as ${near.title} at ${employerName(net, near.employer_key)}.`;
    } else {
      context = `I am reading up on ${company}.`;
    }
  }

  const ask = hasCompany
    ? "Would you be open to a 15 minute call in the next couple of weeks? I would value your view from the inside."
    : "Would you be open to a 15 minute call in the next couple of weeks? It would be good to catch up.";

  const body = [`Hi ${firstName(p.full_name)},`, opening, context, ask, `Best,\n${me?.trim() || "[Your name]"}`].filter(Boolean).join("\n\n");
  return { subject: hasCompany ? `${company}: a quick question` : "Catching up", body };
}

/** A mailto link with the draft filled in. There is no address: contacts here have none on file. */
export const mailtoHref = (d: Draft) => `mailto:?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`;
