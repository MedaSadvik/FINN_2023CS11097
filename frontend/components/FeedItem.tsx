import Link from "next/link";
import type { FeedItem as Item, Quarter } from "@/lib/types";
import { callSheet, overlapWith, employerName, employerKeyFor } from "@/lib/network";
import { cr, change, pct } from "@/lib/format";
import { CallSheet } from "./CallSheet";
import { LeadList } from "./LeadList";
import { SampleTag } from "./Shell";

const FIELDS: { key: keyof Omit<Quarter, "quarter">; label: string }[] = [
  { key: "revenue", label: "Revenue" }, { key: "ebitda", label: "EBITDA" },
  { key: "pbt", label: "PBT" }, { key: "pat", label: "PAT" },
];

function Delta({ v }: { v: number }) {
  const up = v >= 0;
  return <span className={up ? "text-ok" : "text-miss"}>{pct(v, 0)}</span>;
}

function summary(r: Extract<Item, { type: "results" }>) {
  const up = (b: Quarter) => r.cur.pat >= b.pat;
  if (!up(r.qoq) && !up(r.yoy)) return "Profit is down on both comparisons.";
  if (up(r.qoq) && up(r.yoy)) return "Profit is up on both comparisons.";
  return up(r.yoy) ? "Profit is up on last year, down on last quarter." : "Profit is down on last year, up on last quarter.";
}

function Head({ item, kind, sample }: { item: Item; kind: string; sample?: boolean }) {
  return (
    <div>
      <Link href={`/company/${item.ticker}`} className="font-bold hover:underline">{item.company}</Link>
      <p className="mt-0.5 flex items-center gap-2 text-sm text-ink-3">
        {sample && <SampleTag />}{kind}
      </p>
    </div>
  );
}

export function FeedItem({ item }: { item: Item }) {
  if (item.type === "results") {
    const leads = callSheet(employerKeyFor(item.ticker), 2);
    return (
      <article className="px-4 py-5">
        <Head item={item} kind={`Results, ${item.quarter}`} />
        <p className="mt-1 text-ink-2">{summary(item)}</p>
        <table className="mt-4 w-full text-[0.95rem] tabular-nums">
          <thead className="text-sm text-ink-3">
            <tr><th className="pb-1 text-left font-medium"><span className="sr-only">Line</span></th>
              <th className="pb-1 text-right font-medium">{item.quarter}</th>
              <th className="pb-1 text-right font-medium">vs {item.qoq.quarter}</th>
              <th className="pb-1 text-right font-medium">vs {item.yoy.quarter}</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {FIELDS.map(({ key, label }) => (
              <tr key={key}>
                <th scope="row" className="py-2 text-left font-medium">{label}</th>
                <td className="py-2 text-right font-semibold">{cr(item.cur[key])}</td>
                <td className="py-2 text-right"><Delta v={change(item.cur[key], item.qoq[key])} /></td>
                <td className="py-2 text-right"><Delta v={change(item.cur[key], item.yoy[key])} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <CallSheet label="Who to call" title={`Who can explain ${item.company}`}>
          <LeadList leads={leads} empty="No one in your contacts has worked there." />
        </CallSheet>
      </article>
    );
  }
  if (item.type === "mgmt_change") {
    const leads = overlapWith(item.history);
    return (
      <article className="px-4 py-5">
        <Head item={item} kind="Management change" sample />
        <p className="mt-1 font-semibold">{item.headline}</p>
        <p className="mt-2 text-ink-2">{item.bio}</p>
        <ul className="mt-3 space-y-1 text-[0.95rem]">
          {item.history.map((h) => (
            <li key={h.employer_key}>{h.title}, {employerName(h.employer_key)}, {h.start_year}–{h.end_year ?? "now"}</li>
          ))}
        </ul>
        <CallSheet label={`${leads.length} of your contacts overlap`} title={`Overlap with ${item.person}`}>
          <LeadList leads={leads} empty="None of your contacts overlapped with them." />
        </CallSheet>
      </article>
    );
  }
  if (item.type === "event") {
    const leads = callSheet(item.employer_key, 2);
    return (
      <article className="px-4 py-5">
        <Head item={item} kind="Material event" sample />
        <p className="mt-1 font-semibold">{item.headline}</p>
        <p className="mt-2 text-ink-2">{item.detail}</p>
        <CallSheet label="Best person to call" title={`Who can explain ${item.company}`}>
          <LeadList leads={leads} empty="No one in your contacts has worked there." />
        </CallSheet>
      </article>
    );
  }
  const leads = callSheet(item.employer_key, 2);
  return (
    <article className="px-4 py-5">
      <Head item={item} kind="Alert" sample />
      <p className="mt-1 font-semibold">
        Volume at {item.volume_x}× the 20-day average, price <Delta v={item.price_pct} /> today.
      </p>
      <p className="mt-1 text-ink-2">Your rules: volume above 2×, price move beyond ±5%.</p>
      <CallSheet label="Who to call" title={`Who can explain ${item.company}`}>
        <LeadList leads={leads} empty="No one in your contacts has worked there." />
      </CallSheet>
    </article>
  );
}
