import { Suspense } from "react";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import { PromiseRow } from "@/components/PromiseRow";
import { CallSheet } from "@/components/CallSheet";
import { LeadList } from "@/components/LeadList";
import { getCompany, getFinancials, knownTickers } from "@/lib/data";
import { FinancialSections, financialParts } from "@/components/FinancialSections";
import { AtAGlance, BullBear, BusinessSnapshot, NarrativeVsNumbers } from "@/components/PullInsights";
import { atAGlance, narrativeVsNumbers } from "@/lib/narrative";
import symbolData from "@/data/symbols.json";
import { isComplete, isKnown, searchSymbols, type SymbolList } from "@/lib/symbols";
import { callSheet, tidyName } from "@/lib/network-core";
import { nameFor } from "@/lib/portfolio";
import { getAccount, getNetwork } from "@/lib/account";
import { getBuildStatus, getLiveCompany } from "@/lib/live";
import { buildsEnabled } from "@/lib/github";
import { panelFor, TICKER_RE } from "@/lib/build-state";
import { BuildPanel } from "@/components/BuildPanel";

export function generateStaticParams() {
  return knownTickers().map((ticker) => ({ ticker }));
}

const LIST = symbolData as unknown as SymbolList;

/** The typed symbol is not on NSE's list: say so and offer the closest companies. */
function NotListed({ ticker }: { ticker: string }) {
  const near = searchSymbols(LIST, ticker, 5);
  return (
    <main className="px-4 pt-6">
      <h1 className="text-[1.7rem] leading-tight font-bold tracking-tight">No NSE company &ldquo;{ticker}&rdquo;</h1>
      <p className="mt-3">We could not find that symbol on NSE&rsquo;s list of listed companies.</p>
      {near.length > 0 && (
        <>
          <h2 className="mt-5 text-sm text-ink-2">Did you mean</h2>
          <ul className="mt-1 divide-y divide-line border-y border-line">
            {near.map((m) => (
              <li key={m.symbol}>
                <Link href={`/company/${m.symbol}`} className="flex min-h-14 flex-col justify-center py-2 hover:bg-wash">
                  <span className="font-semibold">{m.name}</span>
                  <span className="text-sm text-ink-3">{m.symbol}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
      <Link href="/company" className="mt-6 inline-flex min-h-11 items-center rounded-full border border-ink px-4 font-semibold hover:bg-ink hover:text-paper">
        Search again
      </Link>
    </main>
  );
}

async function NotBuilt({ ticker }: { ticker: string }) {
  const valid = TICKER_RE.test(ticker);
  if (isComplete(LIST) && !(valid && isKnown(LIST, ticker))) return <NotListed ticker={ticker} />;
  const [status, account] = valid ? await Promise.all([getBuildStatus(ticker), getAccount()]) : [{ state: "none" as const }, null];
  const panel = valid ? panelFor(status, { enabled: buildsEnabled, signedIn: account !== null }) : null;
  return (
    <main className="px-4 pt-6">
      <h1 className="text-[1.7rem] leading-tight font-bold tracking-tight">{nameFor(ticker) ?? LIST.rows.find((r) => r[0] === ticker)?.[1] ?? ticker}</h1>
      <p className="mt-3">We have not read {valid ? `${ticker}\u2019s` : "this company\u2019s"} earnings calls yet.</p>
      {panel ? <BuildPanel ticker={ticker} panel={panel} />
        : <p className="mt-2 text-ink-2">Use the NSE symbol, such as INFY or ZOMATO.</p>}
      <Link href="/company" className="mt-6 inline-flex min-h-11 items-center rounded-full border border-ink px-4 font-semibold hover:bg-ink hover:text-paper">
        Choose another company
      </Link>
    </main>
  );
}

async function CompanyBody({ params }: { params: PageProps<"/company/[ticker]">["params"] }) {
  const { ticker } = await params;
  const c = getCompany(ticker) ?? (await getLiveCompany(ticker));
  if (!c) return <NotBuilt ticker={decodeURIComponent(ticker).toUpperCase()} />;
  const key = c.employer_key ?? `name:${tidyName(c.name)}`;
  const { net } = await getNetwork(undefined, { key, name: c.name });
  const leads = callSheet(net, key, 3);
  const fin = getFinancials(c);
  const parts = financialParts(fin);
  const snap = c.snapshot ?? null;
  const glance = atAGlance(fin);
  const narrative = narrativeVsNumbers(c.promises, fin);
  const draft = !c.sample && !!c.provider && c.provider !== "gemini";
  const jumps = [
    { id: "business", label: "Business", show: !!snap?.business.segments.length },
    { id: "promises", label: "Promises", show: true },
    { id: "narrative", label: "Words vs numbers", show: !!narrative },
    { id: "bullbear", label: "Bull and bear", show: !!(snap?.bull.length || snap?.bear.length) },
    { id: "quarters", label: "Quarters", show: true },
    { id: "trajectory", label: "Trajectory", show: !!parts.trajectory }, { id: "balance", label: "Balance sheet", show: !!parts.balance },
    { id: "cash", label: "Cash", show: !!parts.cash },
  ].filter((j) => j.show);
  const checked = c.promises.filter((p) => p.outcome !== "unclear");
  const unclear = c.promises.filter((p) => p.outcome === "unclear");
  const count = (o: string) => c.promises.filter((p) => p.outcome === o).length;
  const tally = ["missed", "partly", "delivered", "pending"].map((o) => [o, count(o)] as const).filter(([, n]) => n);
  const summary = `${c.promises.length} ${c.promises.length === 1 ? "promise" : "promises"}. ` + [...tally.map(([o, n]) => `${n} ${o}`), `${unclear.length} can't be checked yet`].join(", ") + ".";
  const banner = c.sample
    ? "Preview. Quarterly figures are real. Promise wording is placeholder."
    : c.provider && c.provider !== "gemini"
      ? "Draft. Promises and summaries were written by a test model, not the shipped Gemini run."
      : null;
  return (
      <main>
        {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
        <Link href="/company" className="block px-4 pt-4 text-sm text-ink-2 hover:text-ink">All companies</Link>
        <h1 className="px-4 pt-2 text-[1.7rem] leading-tight font-bold tracking-tight">{c.name}</h1>
        <div className="px-4">
          <CallSheet label="Who in your network knows this company" title={`Who can explain ${c.name}`}>
            <LeadList leads={leads} empty="No one in your contacts has worked there." about={c.ticker} />
          </CallSheet>
        </div>

        {jumps.length > 2 && (
          <nav aria-label="On this page" className="mt-3 flex gap-2 overflow-x-auto px-4 pb-1">
            {jumps.map((j) => (
              <a key={j.id} href={`#${j.id}`} className="inline-flex min-h-11 flex-none items-center rounded-full border border-line px-4 text-[0.95rem] text-ink-2 hover:border-ink hover:text-ink">{j.label}</a>
            ))}
          </nav>
        )}

        {glance && <AtAGlance {...glance} />}
        {snap && <BusinessSnapshot s={snap} draft={draft} />}

        <h2 id="promises" className="scroll-mt-4 px-4 pt-8 text-lg font-bold">Promised vs delivered</h2>
        <p className="px-4 pt-1 text-ink-2">Only what management said on earnings calls, checked against reported numbers.</p>
        <p className="px-4 pt-1 font-semibold">{summary}</p>
        <ul className="mt-3 divide-y divide-line border-y border-line">
          {checked.map((p, i) => <PromiseRow key={`${p.made_in}-${i}`} p={p} sample={c.sample} />)}
        </ul>
        {unclear.length > 0 && (
          <details className="border-b border-line">
            <summary className="flex min-h-12 cursor-pointer items-center px-4 font-semibold">
              {unclear.length} {unclear.length === 1 ? "promise" : "promises"} we can&apos;t check yet
            </summary>
            <ul className="divide-y divide-line border-t border-line">
              {unclear.map((p, i) => <PromiseRow key={`${p.made_in}-u${i}`} p={p} sample={c.sample} />)}
            </ul>
          </details>
        )}

        {narrative && <NarrativeVsNumbers n={narrative} />}
        {snap && <BullBear s={snap} draft={draft} />}

        <h2 id="quarters" className="scroll-mt-4 px-4 pt-8 text-lg font-bold">Reported quarters</h2>
        <p className="px-4 pt-1 text-ink-2">₹ crore</p>
        <div className="overflow-x-auto px-4 pt-3">
          <table className="w-full text-[0.95rem] tabular-nums">
            <thead className="text-sm text-ink-3">
              <tr><th className="pb-1 text-left font-medium">Quarter</th>
                {["Revenue", "EBITDA", "PBT", "PAT"].map((h) => <th key={h} className="pb-1 text-right font-medium">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-line">
              {[...c.quarters].reverse().map((q) => (
                <tr key={q.quarter}>
                  <th scope="row" className="py-2 text-left font-medium">{q.quarter}</th>
                  <td className="py-2 text-right">{q.revenue.toLocaleString("en-IN")}</td><td className="py-2 text-right">{q.ebitda}</td>
                  <td className="py-2 text-right">{q.pbt}</td><td className="py-2 text-right">{q.pat}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {fin && <FinancialSections f={fin} />}
      </main>
  );
}

// The page shell is static; the company data streams in behind a placeholder.
export default function Company({ params }: PageProps<"/company/[ticker]">) {
  return (
    <Shell>
      <Suspense fallback={<p className="px-4 pt-6 text-ink-2">Loading research…</p>}>
        <CompanyBody params={params} />
      </Suspense>
    </Shell>
  );
}
