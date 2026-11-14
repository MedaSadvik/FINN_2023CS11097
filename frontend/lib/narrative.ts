/**
 * "Narrative vs numbers": what management PROMISED set beside what the audited numbers SAY.
 * Pure rules over two things we already hold: checked promises and the multi-year financials. No model.
 */
import { balanceSheet, cashQuality, crore, isBank, trajectory, type Financials, type Flag } from "./financials";
import type { Pledge } from "./types";

export type Narrative = { headline: string; points: Flag[]; kept: number; missed: number };

export function narrativeVsNumbers(promises: Pledge[], f: Financials | null): Narrative | null {
  const kept = promises.filter((p) => p.outcome === "delivered" || p.outcome === "partly").length;
  const missed = promises.filter((p) => p.outcome === "missed").length;
  const decided = kept + missed;
  if (decided === 0 || !f) return null;

  const warns = [trajectory(f), balanceSheet(f), cashQuality(f)].flatMap((s) => (s ? s.flags : [])).filter((x) => x.tone === "warn");
  const points: Flag[] = [{ tone: missed > kept ? "warn" : "note", text: `Of ${decided} ${decided === 1 ? "promise" : "promises"} we could check, management kept ${kept} and missed ${missed}.` }];
  for (const w of warns) points.push({ tone: "warn", text: w.text });

  let headline: string;
  if (kept > 0 && warns.length > 0 && missed <= kept) headline = "Management mostly kept its word, but the filings add caution.";
  else if (missed > kept) headline = warns.length ? "More promises missed than kept, and the filings agree." : "More promises missed than kept.";
  else if (warns.length) headline = "The filings show strain behind the promises.";
  else {
    headline = "The promises and the numbers tell the same story.";
    points.push({ tone: "ok", text: isBank(f) ? "No warning signs in the multi-year numbers." : "No warning signs in profit, debt or cash over the years we have." });
  }
  return { headline, points, kept, missed };
}

export type Glance = { label: string; value: string; note?: string };

/** Headline numbers for the latest year: what a reader wants before the detail. */
export function atAGlance(f: Financials | null): { year: string; items: Glance[] } | null {
  if (!f || f.years.length === 0) return null;
  const year = f.years[f.years.length - 1];
  const r = f.rows[year];
  if (!r) return null;
  const num = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
  const items: Glance[] = [];
  if (num(r.revenue)) items.push({ label: isBank(f) ? "Income" : "Revenue", value: crore(r.revenue) });
  if (num(r.pat)) items.push({ label: "Profit after tax", value: crore(r.pat) });
  if (!isBank(f) && num(r.opm_pct)) items.push({ label: "Operating margin", value: `${Math.round(r.opm_pct)}%` });
  if (num(r.roce_pct)) items.push({ label: "Return on capital", value: `${Math.round(r.roce_pct)}%` });
  const bs = balanceSheet(f);
  if (bs?.deRatio != null) items.push({ label: "Debt to equity", value: `${bs.deRatio.toFixed(2)}×` });
  if (!isBank(f) && num(r.cfo)) items.push({ label: "Operating cash", value: crore(r.cfo) });
  return items.length ? { year, items } : null;
}
