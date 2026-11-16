import "server-only";
import { accountsEnabled } from "./supabase/env";
import { createClient } from "./supabase/server";
import type { CompanyData } from "./data";
import type { BuildStatus } from "./build-state";

/** A company built on request (public filing data; anyone may read it). Null when absent or accounts are off. */
export async function getLiveCompany(ticker: string): Promise<CompanyData | null> {
  if (!accountsEnabled) return null;
  const supabase = await createClient();
  const { data } = await supabase.from("companies_live").select("data").eq("ticker", ticker.toUpperCase()).maybeSingle();
  return (data?.data as CompanyData | undefined) ?? null;
}

export type LiveRow = { ticker: string; name: string; promises: number };

export async function liveCompanies(): Promise<LiveRow[]> {
  if (!accountsEnabled) return [];
  const supabase = await createClient();
  const counted = await supabase.from("companies_live").select("ticker, name, promise_count").order("built_at", { ascending: false }).limit(200);
  if (!counted.error) return (counted.data ?? []).map((r) => ({ ticker: r.ticker as string, name: r.name as string, promises: (r.promise_count as number) ?? 0 }));
  // the database has not been updated with the count column yet: count here instead
  const { data } = await supabase.from("companies_live").select("ticker, name, data").order("built_at", { ascending: false }).limit(200);
  return (data ?? []).map((r) => ({ ticker: r.ticker as string, name: r.name as string, promises: ((r.data as CompanyData).promises ?? []).length }));
}

export async function getBuildStatus(ticker: string): Promise<BuildStatus> {
  if (!accountsEnabled) return { state: "none" };
  const supabase = await createClient();
  const { data, error } = await supabase.rpc("build_status", { p_ticker: ticker });
  return error || !data ? { state: "none" } : (data as BuildStatus);
}

/** For a company built on request: is a newer earnings call out than the research was built from? Null when not. */
export async function getStaleInfo(ticker: string): Promise<{ newer: string; built: string | null } | null> {
  if (!accountsEnabled) return null;
  const supabase = await createClient();
  const { data, error } = await supabase.from("companies_live").select("newer_call, built_call").eq("ticker", ticker.toUpperCase()).maybeSingle();
  if (error || !data?.newer_call) return null;   // an error also covers a database that has not been updated yet
  return { newer: data.newer_call as string, built: (data.built_call as string | null) ?? null };
}
