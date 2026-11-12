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
  const { data } = await supabase.from("companies_live").select("ticker, name, data").order("built_at", { ascending: false }).limit(50);
  return (data ?? []).map((r) => ({ ticker: r.ticker as string, name: r.name as string, promises: ((r.data as CompanyData).promises ?? []).length }));
}

export async function getBuildStatus(ticker: string): Promise<BuildStatus> {
  if (!accountsEnabled) return { state: "none" };
  const supabase = await createClient();
  const { data, error } = await supabase.rpc("build_status", { p_ticker: ticker });
  return error || !data ? { state: "none" } : (data as BuildStatus);
}
