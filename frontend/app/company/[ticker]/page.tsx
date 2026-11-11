import { Suspense } from "react";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import { PromiseRow } from "@/components/PromiseRow";
import { CallSheet } from "@/components/CallSheet";
import { LeadList } from "@/components/LeadList";
import { getCompany, knownTickers } from "@/lib/data";
import { callSheet } from "@/lib/network-core";
import { getNetwork } from "@/lib/account";
import { nameFor } from "@/lib/portfolio";

export function generateStaticParams() {
  return knownTickers().map((ticker) => ({ ticker }));
}

function NotBuilt({ ticker }: { ticker: string }) {
  return (
    <main className="px-4 pt-6">
      <h1 className="text-[1.7rem] leading-tight font-bold tracking-tight">{nameFor(ticker) ?? ticker}</h1>
      <p className="mt-3">We have not read {ticker}&apos;s earnings calls yet.</p>
      <p className="mt-2 text-ink-2">
        In this prototype a company appears after its transcripts are read and checked. Build it with
        {" "}<code className="rounded bg-wash px-1">python -m pipeline.build_company {ticker}</code>, then export it.
      </p>
      <Link href="/company" className="mt-4 inline-flex min-h-11 items-center rounded-full border border-ink px-4 font-semibold hover:bg-ink hover:text-paper">
        Choose another company
      </Link>
    </main>
  );
}

async function CompanyBody({ params }: { params: PageProps<"/company/[ticker]">["params"] }) {
  const { ticker } = await params;
  const c = getCompany(ticker);
  if (!c) return <NotBuilt ticker={decodeURIComponent(ticker).toUpperCase()} />;
  const { net } = await getNetwork();
  const leads = c.employer_key ? callSheet(net, c.employer_key, 3) : [];
  const checked = c.promises.filter((p) => p.outcome !== "unclear");
  const unclear = c.promises.filter((p) => p.outcome === "unclear");
  const count = (o: string) => c.promises.filter((p) => p.outcome === o).length;
  const parts = ["missed", "partly", "delivered", "pending"].map((o) => [o, count(o)] as const).filter(([, n]) => n);
  const summary = `${c.promises.length} ${c.promises.length === 1 ? "promise" : "promises"}. ` + [...parts.map(([o, n]) => `${n} ${o}`), `${unclear.length} can't be checked yet`].join(", ") + ".";
  const banner = c.sample
    ? "Preview. Quarterly figures are real. Promise wording is placeholder."
    : c.provider && c.provider !== "gemini"
      ? "Draft. Promises were extracted by a test model, not the shipped Gemini run."
      : null;
  return (
      <main>
        {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
        <Link href="/company" className="block px-4 pt-4 text-sm text-ink-2 hover:text-ink">All companies</Link>
        <h1 className="px-4 pt-2 text-[1.7rem] leading-tight font-bold tracking-tight">{c.name}</h1>
        <div className="px-4">
          <CallSheet label="Who in your network knows this company" title={`Who can explain ${c.name}`}>
            <LeadList leads={leads} empty="No one in your contacts has worked there." />
          </CallSheet>
        </div>

        <h2 className="px-4 pt-8 text-lg font-bold">Promised vs delivered</h2>
        <p className="px-4 pt-1 text-ink-2">Only what management said on earnings calls, checked against reported numbers.</p>
        <p className="px-4 pt-1 font-semibold">{summary}</p>
        <ul className="mt-3 divide-y divide-line border-y border-line">
          {checked.map((p, i) => <PromiseRow key={`${p.made_in}-${i}`} p={p} sample={c.sample} />)}
        </ul>
        {unclear.length > 0 && (
          <details className="border-b border-line">
            <summary className="flex min-h-12 cursor-pointer items-center px-4 font-semibold">
              {unclear.length} {unclear.length === 1 ? "promise" : "promises"} we can't check yet
            </summary>
            <ul className="divide-y divide-line border-t border-line">
              {unclear.map((p, i) => <PromiseRow key={`${p.made_in}-u${i}`} p={p} sample={c.sample} />)}
            </ul>
          </details>
        )}

        <h2 className="px-4 pt-8 text-lg font-bold">Reported quarters</h2>
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
