import { Suspense } from "react";
import { notFound } from "next/navigation";
import { Shell } from "@/components/Shell";
import { PromiseRow } from "@/components/PromiseRow";
import { CallSheet } from "@/components/CallSheet";
import { LeadList } from "@/components/LeadList";
import { getCompany, knownTickers } from "@/lib/data";
import { callSheet } from "@/lib/network";

export function generateStaticParams() {
  return knownTickers().map((ticker) => ({ ticker }));
}

async function CompanyBody({ params }: { params: PageProps<"/company/[ticker]">["params"] }) {
  const { ticker } = await params;
  const c = getCompany(ticker);
  if (!c) notFound();
  const leads = callSheet(c.employer_key, 3);
  const order = ["missed", "partly", "delivered", "pending", "unclear"];
  const promises = [...c.promises].sort((a, b) => order.indexOf(a.outcome) - order.indexOf(b.outcome));
  return (
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">{c.name}</h1>
        <div className="px-4">
          <CallSheet label="Who in your network knows this company" title={`Who can explain ${c.name}`}>
            <LeadList leads={leads} empty="No one in your contacts has worked there." />
          </CallSheet>
        </div>

        <h2 className="px-4 pt-8 text-lg font-bold">Promised vs delivered</h2>
        <p className="px-4 pt-1 text-ink-2">Only what management said on earnings calls, checked against reported numbers.</p>
        <ul className="mt-3 divide-y divide-line border-y border-line">
          {promises.map((p) => <PromiseRow key={p.target} p={p} sample />)}
        </ul>

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
    <Shell banner="Preview build. Quarterly figures are real. Promise wording is placeholder until the verified export is wired in.">
      <Suspense fallback={<p className="px-4 pt-6 text-ink-2">Loading research…</p>}>
        <CompanyBody params={params} />
      </Suspense>
    </Shell>
  );
}
