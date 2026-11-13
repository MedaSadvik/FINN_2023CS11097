import "server-only";
import { demoNetwork } from "./network";
import { buildNetwork, type DbRows } from "./network-build";
import { accountsEnabled } from "./supabase/env";
import { createClient } from "./supabase/server";
import type { Account, Network, Profile } from "./types";

/** Who is signed in (validated with Supabase), or null. Always null when accounts are not configured. */
export async function getAccount(): Promise<Account | null> {
  if (!accountsEnabled) return null;
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return null;
  const { data: profile } = await supabase
    .from("profiles").select("id, username, display_name, headline").eq("id", data.user.id).maybeSingle();
  return { userId: data.user.id, email: data.user.email ?? null, profile: (profile as Profile | null) ?? null };
}

export type NetworkView = { net: Network; mode: "demo" | "mine"; contacts: number };

/**
 * The network the Call Sheet should use for this visitor.
 * Signed out: the synthetic demo network. Signed in: only their own address book plus the live careers of
 * their accepted connections. Row level security decides what comes back, not this code.
 * `target` is the company page being viewed, used to match people who wrote its name by hand.
 */
export async function getNetwork(account?: Account | null, target?: { key: string; name: string }): Promise<NetworkView> {
  const me = account === undefined ? await getAccount() : account;
  if (!me) return { net: demoNetwork, mode: "demo", contacts: demoNetwork.people.filter((p) => p.kind === "contact").length };
  const supabase = await createClient();
  const [people, roles, education] = await Promise.all([
    supabase.from("people").select("id, kind, full_name, headline, last_spoke, profile_id").limit(2000),
    supabase.from("network_roles").select("person_id, employer_key, employer_name, title, start_year, end_year").limit(10000),
    supabase.from("network_education").select("person_id, institution, start_year, end_year").limit(10000),
  ]);
  const rows: DbRows = {
    employers: demoNetwork.employers, // shared lookup, identical to the employers table seeded in the database
    relations: demoNetwork.employer_relations,
    people: (people.data ?? []) as DbRows["people"],
    roles: (roles.data ?? []) as DbRows["roles"],
    education: (education.data ?? []) as DbRows["education"],
  };
  const net = buildNetwork(rows, target);
  return { net, mode: "mine", contacts: net.people.filter((p) => p.kind === "contact").length };
}
