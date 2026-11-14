/**
 * Multi-year reading of a company's own numbers: trajectory, balance sheet, cash quality.
 * Arithmetic on the annual tables only (rupees crore). No model, nothing from outside the company's filings.
 * Every function returns null when the table does not have what it needs, and the page then leaves that section out.
 */
export type FinRow = Partial<Record<
  "revenue" | "deposits" | "ebitda" | "opm_pct" | "interest" | "pbt" | "pat" | "equity_capital" | "reserves" | "borrowings" | "other_liabilities" |
  "total_liabilities" | "cfo" | "cfi" | "fcf" | "debtor_days" | "inventory_days" | "payable_days" | "ccc_days" | "roce_pct", number | null>>;
export type Financials = { basis: string; years: string[]; rows: Record<string, FinRow>; fetched?: string };

export type Flag = { tone: "warn" | "ok" | "note"; text: string };

const n = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);
const at = (f: Financials, back: number): FinRow | undefined => f.rows[f.years[f.years.length - 1 - back]];
const yr = (f: Financials, back: number) => f.years[f.years.length - 1 - back];
export const crore = (v: number) => `${v < 0 ? "-" : ""}₹${Math.abs(Math.round(v)).toLocaleString("en-IN")} cr`;
const pct = (v: number, d = 0) => `${v.toFixed(d)}%`;

/** Compound annual growth between two positive values. Null when either is zero or negative (a growth rate would mislead). */
export function cagr(from: number | null | undefined, to: number | null | undefined, years: number): number | null {
  if (!n(from) || !n(to) || from <= 0 || to <= 0 || years <= 0) return null;
  return (Math.pow(to / from, 1 / years) - 1) * 100;
}

/** A bank lends what it takes in as deposits, so debt, operating margin, working capital and operating cash flow do not describe it. */
export const isBank = (f: Financials) => n(at(f, 0)?.deposits) && (at(f, 0)!.deposits as number) > 0;

// ---------------------------------------------------------------- trajectory

export type Trajectory = {
  years: string[]; revenue: (number | null)[]; opm: (number | null)[];
  revenueCagr: number | null; patCagr: number | null; opmNow: number | null; opmThen: number | null;
  span: number; margin: "expanding" | "compressing" | "steady" | null; headline: string; flags: Flag[];
};

export function trajectory(f: Financials): Trajectory | null {
  const span = Math.min(3, f.years.length - 1);
  if (span < 2) return null;
  const now = at(f, 0)!, then = at(f, span)!;
  if (!n(now.revenue) || !n(then.revenue)) return null;
  const revenueCagr = cagr(then.revenue, now.revenue, span);
  const patCagr = cagr(then.pat, now.pat, span);
  const opmNow = n(now.opm_pct) ? now.opm_pct : null, opmThen = n(then.opm_pct) ? then.opm_pct : null;
  const diff = opmNow !== null && opmThen !== null ? opmNow - opmThen : null;
  const bank = isBank(f);
  const margin = bank || diff === null ? null : diff >= 1 ? "expanding" : diff <= -1 ? "compressing" : "steady";

  const parts: string[] = [];
  if (revenueCagr !== null) parts.push(`Revenue grew ${pct(revenueCagr, 0)} a year over ${span} years, to ${crore(now.revenue)}`);
  else parts.push(`Revenue was ${crore(now.revenue)} in ${yr(f, 0)}, against ${crore(then.revenue)} in ${yr(f, span)}`);
  if (bank && patCagr !== null) parts.push(`profit after tax grew ${pct(patCagr)} a year`);
  if (margin && opmNow !== null && opmThen !== null) {
    parts.push(margin === "steady" ? `operating margin held near ${pct(opmNow)}` : `operating margin ${margin === "expanding" ? "rose" : "fell"} from ${pct(opmThen)} to ${pct(opmNow)}`);
  }
  const flags: Flag[] = [];
  if (n(now.pat) && n(then.pat) && !bank) {
    if (patCagr !== null && revenueCagr !== null && patCagr < revenueCagr - 5) flags.push({ tone: "warn", text: `Profit grew ${pct(patCagr)} a year, slower than revenue.` });
    else if (patCagr !== null && revenueCagr !== null && patCagr > revenueCagr + 5) flags.push({ tone: "ok", text: `Profit grew ${pct(patCagr)} a year, faster than revenue.` });
    else if (now.pat <= 0) flags.push({ tone: "warn", text: `The company made a loss in ${yr(f, 0)}.` });
  }
  if (n(now.roce_pct) && n(then.roce_pct) && now.roce_pct - then.roce_pct <= -3) flags.push({ tone: "warn", text: `Return on capital fell from ${pct(then.roce_pct)} to ${pct(now.roce_pct)}.` });

  return {
    years: f.years, revenue: f.years.map((y) => f.rows[y]?.revenue ?? null), opm: f.years.map((y) => (bank ? null : f.rows[y]?.opm_pct ?? null)),
    revenueCagr, patCagr, opmNow, opmThen, span, margin, headline: parts.join("; ") + ".", flags,
  };
}

// ---------------------------------------------------------------- balance sheet

export type BalanceSheet = {
  year: string; debt: number; netWorth: number; deRatio: number | null; deThen: number | null; thenYear: string;
  interestCover: number | null; cccDays: number | null; cccThen: number | null; debtorDays: number | null;
  funding: { equity: number; debt: number; other: number } | null; headline: string; flags: Flag[];
};

export function balanceSheet(f: Financials): BalanceSheet | null {
  if (isBank(f)) return null;
  const now = at(f, 0);
  if (!now || !n(now.borrowings) || !n(now.equity_capital) || !n(now.reserves)) return null;
  const netWorth = now.equity_capital + now.reserves;
  const deRatio = netWorth > 0 ? now.borrowings / netWorth : null;
  const back = Math.min(2, f.years.length - 1);
  const then = at(f, back);
  const thenWorth = then && n(then.equity_capital) && n(then.reserves) ? then.equity_capital + then.reserves : null;
  const deThen = then && n(then.borrowings) && thenWorth && thenWorth > 0 ? then.borrowings / thenWorth : null;
  const interestCover = n(now.ebitda) && n(now.interest) && now.interest > 0 ? now.ebitda / now.interest : null;
  const totalL = n(now.total_liabilities) && now.total_liabilities > 0 ? now.total_liabilities : null;
  const funding = totalL ? { equity: (netWorth / totalL) * 100, debt: (now.borrowings / totalL) * 100, other: Math.max(0, 100 - (netWorth / totalL) * 100 - (now.borrowings / totalL) * 100) } : null;
  const cccDays = n(now.ccc_days) ? now.ccc_days : null, cccThen = then && n(then.ccc_days) ? then.ccc_days : null;

  const flags: Flag[] = [];
  if (deRatio !== null && deThen !== null && back > 0) {
    if (deRatio - deThen >= 0.15) flags.push({ tone: "warn", text: `Debt to equity rose from ${deThen.toFixed(2)} to ${deRatio.toFixed(2)} in ${back} years.` });
    else if (deThen - deRatio >= 0.15) flags.push({ tone: "ok", text: `Debt to equity fell from ${deThen.toFixed(2)} to ${deRatio.toFixed(2)} in ${back} years.` });
  }
  if (interestCover !== null && interestCover < 3) flags.push({ tone: "warn", text: `Operating profit covers interest only ${interestCover.toFixed(1)} times.` });
  if (cccDays !== null && cccThen !== null && back > 0 && cccDays - cccThen >= 15) flags.push({ tone: "warn", text: `The cash conversion cycle lengthened from ${Math.round(cccThen)} to ${Math.round(cccDays)} days, so more cash is tied up in stock and unpaid bills.` });
  else if (cccDays !== null && cccThen !== null && back > 0 && cccThen - cccDays >= 15) flags.push({ tone: "ok", text: `The cash conversion cycle shortened from ${Math.round(cccThen)} to ${Math.round(cccDays)} days.` });

  const headline = `Borrowings are ${crore(now.borrowings)} against a net worth of ${crore(netWorth)}` + (deRatio !== null ? `, a debt to equity of ${deRatio.toFixed(2)}.` : ".");
  return { year: yr(f, 0), debt: now.borrowings, netWorth, deRatio, deThen, thenYear: yr(f, back), interestCover, cccDays, cccThen, debtorDays: n(now.debtor_days) ? now.debtor_days : null, funding, headline, flags };
}

// ---------------------------------------------------------------- cash quality

export type CashQuality = {
  years: string[]; cfo: (number | null)[]; pat: (number | null)[];
  span: number; sumCfo: number; sumPat: number; conversion: number | null; fcfTotal: number | null; headline: string; flags: Flag[];
};

export function cashQuality(f: Financials): CashQuality | null {
  if (isBank(f)) return null;
  const span = Math.min(3, f.years.length);
  const recent = f.years.slice(-span);
  const rows = recent.map((y) => f.rows[y]);
  if (span < 2 || rows.some((r) => !n(r?.cfo) || !n(r?.pat))) return null;
  const sumCfo = rows.reduce((a, r) => a + (r!.cfo as number), 0);
  const sumPat = rows.reduce((a, r) => a + (r!.pat as number), 0);
  const conversion = sumPat > 0 ? (sumCfo / sumPat) * 100 : null;
  const fcfTotal = rows.every((r) => n(r!.fcf)) ? rows.reduce((a, r) => a + (r!.fcf as number), 0) : null;

  const flags: Flag[] = [];
  const last = rows[rows.length - 1]!;
  if (conversion !== null && conversion <= 0) flags.push({ tone: "warn", text: `Profit is not turning into cash: ${crore(sumPat)} reported, ${crore(sumCfo)} of operating cash, over ${span} years.` });
  else if (conversion !== null && conversion < 50) flags.push({ tone: "warn", text: `Only ${pct(conversion)} of reported profit turned into operating cash in ${span} years.` });
  else if (conversion !== null && conversion >= 80) flags.push({ tone: "ok", text: `Profit is turning into cash: ${pct(conversion)} over ${span} years.` });
  if ((last.cfo as number) < 0) flags.push({ tone: "warn", text: `Operating cash flow was negative in ${recent[recent.length - 1]}, at ${crore(last.cfo as number)}.` });
  if (fcfTotal !== null && fcfTotal < 0) flags.push({ tone: "note", text: `After capital spending, the company used ${crore(-fcfTotal)} of cash over ${span} years. It was funded by borrowing or raising equity.` });

  const headline = `Over ${span} years the company reported ${crore(sumPat)} of profit and generated ${crore(sumCfo)} of operating cash` + (conversion !== null ? ` (${pct(conversion)}).` : ".");
  return { years: recent, cfo: rows.map((r) => r!.cfo as number), pat: rows.map((r) => r!.pat as number), span, sumCfo, sumPat, conversion, fcfTotal, headline, flags };
}
