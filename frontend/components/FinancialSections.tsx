import { BarChart, Legend } from "@/components/Charts";
import { balanceSheet, cashQuality, crore, isBank, trajectory, type Financials, type Flag } from "@/lib/financials";

const MARK: Record<Flag["tone"], string> = { warn: "Watch.", ok: "Good.", note: "Note." };

function Flags({ flags }: { flags: Flag[] }) {
  if (!flags.length) return null;
  return (
    <ul className="mt-3 space-y-1.5">
      {flags.map((f, i) => (
        <li key={i} className="text-[0.95rem] leading-snug"><span className={`font-semibold ${f.tone === "warn" ? "text-miss" : f.tone === "ok" ? "text-ok" : ""}`}>{MARK[f.tone]}</span> {f.text}</li>
      ))}
    </ul>
  );
}

function Section({ id, title, headline, children }: { id: string; title: string; headline: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-4 px-4 pt-8">
      <h2 className="text-lg font-bold">{title}</h2>
      <p className="mt-1 font-semibold">{headline}</p>
      {children}
    </section>
  );
}

const x = (v: number | null, d = 2) => (v === null ? "not available" : `${v.toFixed(d)}×`);

/** Which of the three sections have data. The page uses it to build its jump links. */
export const financialParts = (f: Financials | null) => ({
  trajectory: f ? trajectory(f) : null, balance: f ? balanceSheet(f) : null, cash: f ? cashQuality(f) : null,
});

export function FinancialSections({ f }: { f: Financials }) {
  const { trajectory: t, balance: b, cash: c } = financialParts(f);
  if (!t && !b && !c) return null;
  return (
    <>
      {t && (
        <Section id="trajectory" title="Trajectory" headline={t.headline}>
          <Legend items={[{ name: "Revenue, ₹ crore", swatch: "bg-ink" }]} />
          <BarChart labels={t.years} series={[{ name: "Revenue", values: t.revenue, tone: "ink" }]}
            under={t.opm.some((v) => v !== null) ? t.opm.map((v) => (v === null ? null : `${Math.round(v)}%`)) : undefined}
            summary={`Revenue by year: ${t.years.map((y, i) => `${y} ${t.revenue[i] ?? "n/a"}`).join(", ")}. Operating margin under each year.`} />
          {t.opm.some((v) => v !== null) && <p className="text-sm text-ink-3">Operating margin is shown under each year.</p>}
          <Flags flags={t.flags} />
          {isBank(f) && <p className="mt-3 text-[0.95rem] text-ink-2">Debt, operating margin, working capital and cash conversion are left out. They describe a business that sells goods, not a bank that lends deposits.</p>}
        </Section>
      )}
      {b && (
        <Section id="balance" title="Balance sheet" headline={b.headline}>
          {b.funding && (
            <>
              <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-wash" role="img"
                aria-label={`Funding: net worth ${Math.round(b.funding.equity)}%, borrowings ${Math.round(b.funding.debt)}%, other liabilities ${Math.round(b.funding.other)}%`}>
                <span className="bg-ink" style={{ width: `${b.funding.equity}%` }} />
                <span className="bg-miss" style={{ width: `${b.funding.debt}%` }} />
                <span className="bg-line" style={{ width: `${b.funding.other}%` }} />
              </div>
              <Legend items={[
                { name: `Net worth ${Math.round(b.funding.equity)}%`, swatch: "bg-ink" },
                { name: `Borrowings ${Math.round(b.funding.debt)}%`, swatch: "bg-miss" },
                { name: `Other ${Math.round(b.funding.other)}%`, swatch: "bg-line" },
              ]} />
            </>
          )}
          <dl className="mt-3 divide-y divide-line border-y border-line text-[0.95rem]">
            <Row k="Debt to equity" v={`${x(b.deRatio)}${b.deThen !== null && b.thenYear !== b.year ? ` (${x(b.deThen)} in ${b.thenYear})` : ""}`} />
            <Row k="Interest cover" v={x(b.interestCover, 1)} />
            <Row k="Cash conversion cycle" v={b.cccDays === null ? "not available" : `${Math.round(b.cccDays)} days${b.cccThen !== null && b.thenYear !== b.year ? ` (${Math.round(b.cccThen)} in ${b.thenYear})` : ""}`} />
            <Row k="Debtor days" v={b.debtorDays === null ? "not available" : `${Math.round(b.debtorDays)} days`} />
          </dl>
          <Flags flags={b.flags} />
        </Section>
      )}
      {c && (
        <Section id="cash" title="Cash quality" headline={c.headline}>
          <Legend items={[{ name: "Profit after tax", swatch: "bg-ink-3" }, { name: "Cash from operations", swatch: "bg-ink" }]} />
          <BarChart labels={c.years} series={[{ name: "Profit after tax", values: c.pat, tone: "mute" }, { name: "Cash from operations", values: c.cfo, tone: "ink" }]}
            summary={`Profit and operating cash by year: ${c.years.map((y, i) => `${y} profit ${c.pat[i]}, cash ${c.cfo[i]}`).join("; ")}. ₹ crore.`} />
          <p className="text-sm text-ink-3">₹ crore. Red bars are cash going out.</p>
          <Flags flags={c.flags} />
        </Section>
      )}
      <p className="px-4 pt-4 text-sm text-ink-3">
        From the company&rsquo;s audited annual numbers, as standardised by screener.in ({f.basis}, ₹ crore){f.fetched ? `, read ${f.fetched}` : ""}.
        {c?.fcfTotal != null ? ` Free cash flow over the same years: ${crore(c.fcfTotal)}.` : ""}
      </p>
    </>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return <div className="flex justify-between gap-4 py-2.5"><dt className="text-ink-2">{k}</dt><dd className="text-right font-semibold">{v}</dd></div>;
}
