import type { Snapshot } from "@/lib/types";
import type { Flag } from "@/lib/financials";
import type { Glance, Narrative } from "@/lib/narrative";

const MARK: Record<Flag["tone"], string> = { warn: "Watch.", ok: "Good.", note: "Note." };

function Source({ page, period }: { page: number; period: string }) {
  return <p className="mt-1.5 text-sm text-ink-3">{period} call, page {page}</p>;
}

function Points({ items, period }: { items: Snapshot["bull"]; period: string }) {
  return (
    <ul className="mt-2 divide-y divide-line border-y border-line">
      {items.map((it, i) => (
        <li key={i} className="py-3">
          <p className="font-semibold">{it.point}</p>
          <blockquote className="quote mt-2">&ldquo;{it.quote}&rdquo;</blockquote>
          <Source page={it.page} period={period} />
        </li>
      ))}
    </ul>
  );
}

export function AtAGlance({ year, items }: { year: string; items: Glance[] }) {
  return (
    <section className="px-4 pt-6" aria-label={`Key numbers for ${year}`}>
      <h2 className="text-lg font-bold">Key numbers, {year}</h2>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 border-y border-line">
        {items.map((g) => (
          <div key={g.label} className="border-b border-line py-3 last:border-b-0 odd:[&:nth-last-child(2)]:border-b-0">
            <dt className="text-sm text-ink-3">{g.label}</dt>
            <dd className="text-[1.15rem] font-bold tabular-nums">{g.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function BusinessSnapshot({ s, draft }: { s: Snapshot; draft: boolean }) {
  if (!s.business.segments.length) return null;
  return (
    <section id="business" className="scroll-mt-4 px-4 pt-8">
      <h2 className="text-lg font-bold">What the company does</h2>
      {draft && <p className="mt-1 text-sm text-ink-3">Draft. Written by a test model.</p>}
      {s.business.summary && <p className="mt-1 font-semibold">{s.business.summary}</p>}
      <ul className="mt-2 divide-y divide-line border-y border-line">
        {s.business.segments.map((seg) => (
          <li key={seg.name} className="py-3">
            <p className="font-semibold">{seg.name}</p>
            <blockquote className="quote mt-2">&ldquo;{seg.quote}&rdquo;</blockquote>
            <Source page={seg.page} period={s.period} />
          </li>
        ))}
      </ul>
    </section>
  );
}

export function BullBear({ s, draft }: { s: Snapshot; draft: boolean }) {
  if (!s.bull.length && !s.bear.length) return null;
  return (
    <section id="bullbear" className="scroll-mt-4 px-4 pt-8">
      <h2 className="text-lg font-bold">Bull case and bear case</h2>
      <p className="mt-1 text-ink-2">From the {s.period} call only. Each point carries the words it rests on.{draft ? " Draft: written by a test model." : ""}</p>
      {s.bull.length > 0 && (<><h3 className="mt-4 font-bold text-ok">For</h3><Points items={s.bull} period={s.period} /></>)}
      {s.bear.length > 0 && (<><h3 className="mt-5 font-bold text-miss">Against</h3><Points items={s.bear} period={s.period} /></>)}
    </section>
  );
}

export function NarrativeVsNumbers({ n }: { n: Narrative }) {
  return (
    <section id="narrative" className="scroll-mt-4 px-4 pt-8">
      <h2 className="text-lg font-bold">What they said, against the numbers</h2>
      <p className="mt-1 font-semibold">{n.headline}</p>
      <ul className="mt-3 space-y-1.5">
        {n.points.map((f, i) => (
          <li key={i} className="text-[0.95rem] leading-snug">
            <span className={`font-semibold ${f.tone === "warn" ? "text-miss" : f.tone === "ok" ? "text-ok" : ""}`}>{MARK[f.tone]}</span> {f.text}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-sm text-ink-3">Promises come from earnings calls. Numbers come from the annual tables.</p>
    </section>
  );
}
