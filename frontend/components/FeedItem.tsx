import Link from "next/link";
import type { FeedItem as Item, Network, Quarter } from "@/lib/types";
import { callSheet, overlapWith, employerKeyFor } from "@/lib/network-core";
import { cr, change, pct, shortDate } from "@/lib/format";
import { CallSheet } from "./CallSheet";
import { LeadList } from "./LeadList";
import { SampleTag } from "./Shell";

const FIELDS: { key: keyof Omit<Quarter, "quarter">; label: string }[] = [
  { key: "revenue", label: "Revenue" }, { key: "ebitda", label: "EBITDA" },
  { key: "pbt", label: "PBT" }, { key: "pat", label: "PAT" },
];

function Delta({ v }: { v: number }) {
  return <span className={v >= 0 ? "text-ok" : "text-miss"}>{pct(v, 0)}</span>;
}

function summary(r: Extract<Item, { type: "results" }>) {
  const up = (b: Quarter) => r.cur.pat >= b.pat;
  if (!up(r.qoq) && !up(r.yoy)) return "Profit is down on both comparisons.";
  if (up(r.qoq) && up(r.yoy)) return "Profit is up on both comparisons.";
  return up(r.yoy) ? "Profit is up on last year, down on last quarter." : "Profit is down on last year, up on last quarter.";
}

function Head({ item, kind }: { item: Item; kind: string }) {
  const when = shortDate(item.filed);
  return (
    <div>
      <Link href={`/company/${item.ticker}`} className="font-bold hover:underline">{item.company}</Link>
      <p className="mt-0.5 flex items-center gap-2 text-sm text-ink-3">
        {item.sample && <SampleTag />}{kind}{when && ` · ${when}`}
      </p>
    </div>
  );
}

function FilingLink({ url }: { url?: string | null }) {
  if (!url) return null;
  return <a href={url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-sm text-ink-2 underline underline-offset-2 hover:text-ink">Open the filing</a>;
}

function WhoToCall({ net, employerKey, company, label }: { net: Network; employerKey: string | null; company: string; label: string }) {
  const leads = employerKey ? callSheet(net, employerKey, 2) : [];
  return (
    <CallSheet label={label} title={`Who can explain ${company}`}>
      <LeadList leads={leads} empty="No one in your contacts has worked there." />
    </CallSheet>
  );
}

const VERB: Record<string, string> = {
  appointment: "appointed", "re-appointment": "re-appointed", resignation: "resigned as", cessation: "ceased as", other: "named",
};

export function FeedItem({ item, net }: { item: Item; net: Network }) {
  if (item.type === "results") {
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
        <FilingLink url={item.pdf_url} />
        <div><WhoToCall net={net} employerKey={employerKeyFor(net, item.ticker)} company={item.company} label="Who to call" /></div>
      </article>
    );
  }
  if (item.type === "mgmt_change") {
    const p = item.person;
    const leads = p ? overlapWith(net, p.history) : [];
    return (
      <article className="px-4 py-5">
        <Head item={item} kind="Management change" />
        {p ? (
          <>
            <p className="mt-1 font-semibold">{p.person} {VERB[p.event] ?? "named"}{p.role ? ` ${p.role}` : ""}</p>
            {p.quote && <blockquote className="quote mt-3">“{p.quote}”</blockquote>}
            {p.history.length > 0 && (
              <ul className="mt-3 space-y-1 text-[0.95rem]">
                {p.history.map((h, i) => (
                  <li key={i}>
                    {h.title ? `${h.title}, ` : "Earlier at "}{h.employer}
                    {h.start_year ? `, ${h.start_year}–${h.end_year ?? "now"}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <>
            <p className="mt-1 font-semibold">{item.headline}</p>
            {item.detail && <p className="mt-2 text-ink-2">{item.detail}</p>}
          </>
        )}
        <FilingLink url={item.pdf_url} />
        <div>
          {leads.length > 0 ? (
            <CallSheet label={`${leads.length} of your contacts overlap`} title={`Overlap with ${p!.person}`}>
              <LeadList leads={leads} empty="" />
            </CallSheet>
          ) : (
            <WhoToCall net={net} employerKey={item.employer_key} company={item.company} label="Who knows this company" />
          )}
        </div>
      </article>
    );
  }
  if (item.type === "event") {
    return (
      <article className="px-4 py-5">
        <Head item={item} kind={item.label ?? "Material event"} />
        <p className="mt-1 font-semibold">{item.headline}</p>
        {item.detail && <p className="mt-2 text-ink-2">{item.detail}</p>}
        <FilingLink url={item.pdf_url} />
        <div><WhoToCall net={net} employerKey={item.employer_key} company={item.company} label="Best person to call" /></div>
      </article>
    );
  }
  const r = item.rules;
  const rule = [r?.volume_multiple && `volume above ${r.volume_multiple}×`, r?.price_move && `price move beyond ±${r.price_move}%`].filter(Boolean).join(", ");
  return (
    <article className="px-4 py-5">
      <Head item={item} kind="Alert" />
      <p className="mt-1 font-semibold">
        {item.volume_x !== null && <>Volume at {item.volume_x}× the 20-day average</>}
        {item.volume_x !== null && item.price_pct !== null && ", "}
        {item.price_pct !== null && <>price <Delta v={item.price_pct} /> on the day</>}.
      </p>
      {rule && <p className="mt-1 text-ink-2">Your rules: {rule}.{item.earlier ? ` ${item.earlier} earlier ${item.earlier === 1 ? "day" : "days"} in this window too.` : ""}</p>}
      <div><WhoToCall net={net} employerKey={item.employer_key} company={item.company} label="Who to call" /></div>
    </article>
  );
}
