"use server";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { accountsEnabled } from "@/lib/supabase/env";
import { demoNetwork } from "@/lib/network";

export type ActionState = { ok: boolean; message: string } | null;
const ok = (message: string): ActionState => ({ ok: true, message });
const fail = (message: string): ActionState => ({ ok: false, message });

const USERNAME = /^[a-z0-9_]{3,20}$/;
const text = (f: FormData, k: string) => String(f.get(k) ?? "").trim();
const year = (f: FormData, k: string) => {
  const v = text(f, k);
  return v === "" ? null : Number(v);
};

/** Turn a database error into something a person can act on. */
function explain(error: { code?: string; message: string }): string {
  if (error.code === "23505") return "That username is already taken.";
  if (error.code === "23514") return "Check the values: years must be between 1960 and 2100, and the end year can't be before the start.";
  if (error.code === "42501" || error.code === "PGRST301") return "You need to sign in again.";
  return error.message;
}

async function me() {
  if (!accountsEnabled) return null;
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  return data.user ? { supabase, user: data.user } : null;
}

// ---------------------------------------------------------------- sign in and out
export async function signUp(_: ActionState, f: FormData): Promise<ActionState> {
  if (!accountsEnabled) return fail("Accounts are not switched on in this build.");
  const email = text(f, "email"), password = String(f.get("password") ?? "");
  const username = text(f, "username").toLowerCase(), display = text(f, "display_name");
  if (!USERNAME.test(username)) return fail("Username: 3 to 20 characters, lowercase letters, numbers or underscore.");
  if (!display) return fail("Enter your name.");
  if (password.length < 8) return fail("Password must be at least 8 characters.");
  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) return fail(error.message);
  if (!data.session) return ok("Check your email to confirm your account, then sign in.");
  const { error: pe } = await supabase.from("profiles").insert({ id: data.user!.id, username, display_name: display });
  if (pe) redirect(`/me?notice=${encodeURIComponent(explain(pe))}`); // account exists; finish the profile there
  redirect("/me");
}

export async function signIn(_: ActionState, f: FormData): Promise<ActionState> {
  if (!accountsEnabled) return fail("Accounts are not switched on in this build.");
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email: text(f, "email"), password: String(f.get("password") ?? "") });
  if (error) return fail("Wrong email or password.");
  redirect("/network");
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/");
}

// ---------------------------------------------------------------- profile
export async function createProfile(_: ActionState, f: FormData): Promise<ActionState> {
  const s = await me();
  if (!s) return fail("Sign in first.");
  const username = text(f, "username").toLowerCase();
  if (!USERNAME.test(username)) return fail("Username: 3 to 20 characters, lowercase letters, numbers or underscore.");
  if (!text(f, "display_name")) return fail("Enter your name.");
  const { error } = await s.supabase.from("profiles")
    .insert({ id: s.user.id, username, display_name: text(f, "display_name"), headline: text(f, "headline") || null });
  if (error) return fail(explain(error));
  redirect("/me");
}

export async function updateProfile(_: ActionState, f: FormData): Promise<ActionState> {
  const s = await me();
  if (!s) return fail("Sign in first.");
  if (!text(f, "display_name")) return fail("Enter your name.");
  const { error } = await s.supabase.from("profiles")
    .update({ display_name: text(f, "display_name"), headline: text(f, "headline") || null }).eq("id", s.user.id);
  if (error) return fail(explain(error));
  revalidatePath("/", "layout");
  return ok("Saved.");
}

export async function addRole(_: ActionState, f: FormData): Promise<ActionState> {
  const s = await me();
  if (!s) return fail("Sign in first.");
  const name = text(f, "employer"), start = year(f, "start_year");
  if (!name || !text(f, "title") || start === null) return fail("Add the company, your title and the year you started.");
  const known = demoNetwork.employers.find((e) => e.name.toLowerCase() === name.toLowerCase());
  const { error } = await s.supabase.from("profile_roles").insert({
    profile_id: s.user.id, employer_name: known?.name ?? name, employer_key: known?.key ?? null,
    title: text(f, "title"), start_year: start, end_year: year(f, "end_year"),
  });
  if (error) return fail(explain(error));
  revalidatePath("/me");
  return ok(known ? "Added." : "Added. FINN doesn't track this company yet, so it won't produce overlaps.");
}

export async function addEducation(_: ActionState, f: FormData): Promise<ActionState> {
  const s = await me();
  if (!s) return fail("Sign in first.");
  const start = year(f, "start_year"), end = year(f, "end_year");
  if (!text(f, "institution") || start === null || end === null) return fail("Add the school and both years.");
  const { error } = await s.supabase.from("profile_education")
    .insert({ profile_id: s.user.id, institution: text(f, "institution"), start_year: start, end_year: end });
  if (error) return fail(explain(error));
  revalidatePath("/me");
  return ok("Added.");
}

async function removeRow(table: "profile_roles" | "profile_education", f: FormData) {
  const s = await me();
  if (!s) return;
  await s.supabase.from(table).delete().eq("id", Number(f.get("id")));
  revalidatePath("/me");
}
export async function removeRole(f: FormData) { return removeRow("profile_roles", f); }
export async function removeEducation(f: FormData) { return removeRow("profile_education", f); }

// ---------------------------------------------------------------- connections
const REQUEST_RESULT: Record<string, string> = {
  requested: "Request sent. They need to accept before you can see each other's careers.",
  connected: "You are now connected.",
  already_connected: "You are already connected.",
  already_requested: "You already asked them. Waiting for their answer.",
};

export async function requestConnection(_: ActionState, f: FormData): Promise<ActionState> {
  const s = await me();
  if (!s) return fail("Sign in first.");
  const username = text(f, "username").toLowerCase().replace(/^@/, "");
  if (!USERNAME.test(username)) return fail("Type their exact username, for example priya_iyer.");
  const { data, error } = await s.supabase.rpc("request_connection", { p_username: username });
  if (error) return fail(error.message.includes("create your profile") ? "Create your profile first." : error.message);
  revalidatePath("/network");
  revalidatePath("/", "layout");
  return ok(REQUEST_RESULT[data as string] ?? "Done.");
}

async function respond(accept: boolean, f: FormData) {
  const s = await me();
  if (!s) return;
  await s.supabase.rpc("respond_connection", { p_id: Number(f.get("id")), p_accept: accept });
  revalidatePath("/", "layout");
}
export async function acceptRequest(f: FormData) { return respond(true, f); }
export async function declineRequest(f: FormData) { return respond(false, f); }

export async function removeConnection(f: FormData) {
  const s = await me();
  if (!s) return;
  await s.supabase.from("connections").delete().eq("id", Number(f.get("id")));
  revalidatePath("/", "layout");
}

// ---------------------------------------------------------------- sample contacts
export async function loadSample(): Promise<void> {
  const s = await me();
  if (!s) return;
  await s.supabase.rpc("load_sample_network", { p: { people: demoNetwork.people } });
  revalidatePath("/", "layout");
}
export async function clearSample(): Promise<void> {
  const s = await me();
  if (!s) return;
  await s.supabase.rpc("clear_sample_network");
  revalidatePath("/", "layout");
}
