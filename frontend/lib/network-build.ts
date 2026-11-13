import type { Education, Employer, Network, Person, Relation, Role } from "./types";
import { sameCompany, tidyName } from "./network-core";

export type DbRows = {
  employers: Employer[];
  relations: Relation[];
  people: { id: number; kind: string; full_name: string; headline: string | null; last_spoke: string | null; profile_id: string | null }[];
  roles: { person_id: number; employer_key: string | null; employer_name?: string | null; title: string; start_year: number; end_year: number | null }[];
  education: { person_id: number; institution: string; start_year: number; end_year: number }[];
};

/**
 * Turn the rows the database returned for the signed-in user into the Network the Call Sheet reads.
 *
 * `target` is the company whose page is open. A role with no tracked employer (someone typed "Titan") is matched
 * to it by name right here, so it does not matter whether the profile or the company came first. Other untracked
 * employers get a key made from their tidied name, so two connections who both wrote "Acme Ltd" still overlap.
 */
export function buildNetwork(rows: DbRows, target?: { key: string; name: string }): Network {
  const employers: Employer[] = [...rows.employers];
  const known = new Set(employers.map((e) => e.key));
  const addEmployer = (key: string, name: string) => {
    if (!known.has(key)) { known.add(key); employers.push({ key, name, sector: "", ticker: null }); }
  };
  if (target) addEmployer(target.key, target.name);

  const roles = new Map<number, Role[]>();
  for (const r of rows.roles) {
    let key = r.employer_key;
    if (!key) {
      const written = (r.employer_name ?? "").trim();
      if (!tidyName(written)) continue;
      key = target && sameCompany(written, target.name) ? target.key : `name:${tidyName(written)}`;
      addEmployer(key, written);
    }
    const list = roles.get(r.person_id) ?? [];
    list.push({ employer_key: key, ...(r.employer_name ? { employer_name: r.employer_name } : {}), title: r.title, start_year: r.start_year, end_year: r.end_year });
    roles.set(r.person_id, list);
  }
  const edu = new Map<number, Education[]>();
  for (const e of rows.education) {
    const list = edu.get(e.person_id) ?? [];
    list.push({ institution: e.institution, start_year: e.start_year, end_year: e.end_year });
    edu.set(e.person_id, list);
  }
  const people: Person[] = rows.people.map((p) => ({
    id: p.id,
    kind: p.kind === "extended" ? "extended" : "contact",
    full_name: p.full_name,
    headline: p.headline ?? "",
    last_spoke: p.last_spoke,
    roles: (roles.get(p.id) ?? []).sort((a, b) => b.start_year - a.start_year),
    education: edu.get(p.id) ?? [],
    linked: p.profile_id !== null,
  }));
  return { employers, employer_relations: rows.relations, people };
}
