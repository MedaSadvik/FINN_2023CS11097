import { connection } from "next/server";
import { getFeed } from "@/lib/data";
import { getNetwork } from "@/lib/account";
import { expertiseMap, filingRefs, reconnectIdeas, type Reconnect, type Theme } from "@/lib/network-insights";
import type { Evidence } from "@/lib/types";
import { PersonLink } from "./PersonLink";

const tag = (s: Evidence["source"]) => (s === "your notes" ? "text-sm text-ink-3 italic" : "text-sm text-ink-3");
const plural = (n: number, one: string, many = one + "s") => `${n} ${n === 1 ? one : many}`;

function Idea({ idea }: { idea: Reconnect }) {
  const p = idea.person;
  return (
    <li className="px-4 py-4">
      <p><PersonLink id={p.id} name={p.full_name} about={idea.filing.ticker} /></p>
      <p className="text-sm text-ink-2">{p.headline}</p>
      <ul className="mt-2 space-y-1.5">
        {idea.reasons.map((r, i) => (
          <li key={i} className="text-[0.95rem] leading-snug">{r.text} <span className={tag(r.source)}>({r.source})</span></li>
        ))}
      </ul>
      <p className="mt-2 text-[0.95rem] font-medium">{idea.ask}</p>
    </li>
  );
}

function ThemeRow({ t }: { t: Theme }) {
  const note = t.gap ? "No one yet" : plural(t.expertCount, "go-to person", "go-to people");
  return (
    <li>
      <details className="group">
        <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 px-4 py-2">
          <span>
            <span className="block font-semibold">{t.label}</span>
            <span className={`block text-sm ${t.gap ? "font-medium text-ink" : "text-ink-3"}`}>{plural(t.holdings.length, "holding")}, {note.toLowerCase()}</span>
          </span>
          <span aria-hidden className="text-ink-3 group-open:rotate-180">⌄</span>
        </summary>
        <div className="px-4 pb-4">
          {t.gap ? (
            <p className="text-[0.95rem] leading-snug">No one in your network has worked in {t.label.toLowerCase()}. You hold {t.holdings.join(", ")}. Ask a trusted contact for an introduction.</p>
          ) : (
            <ul className="space-y-2.5">
              {t.expertCount > t.experts.length && <li className="text-sm text-ink-3">Top {t.experts.length} of {t.expertCount}, by years in the sector.</li>}
              {t.experts.map((e) => (
                <li key={e.person.id} className="text-[0.95rem] leading-snug">
                  <PersonLink id={e.person.id} name={e.person.full_name} />, {e.years} years{e.current ? ", still in it" : ""}.
                  <span className="block text-sm text-ink-2">{e.where.join(", ")}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </li>
  );
}

/** What the Network notices on its own: who to call now, and where your network is thin. Rules only. */
export async function NetworkInsights() {
  await connection(); // "months since you spoke" depends on today's date
  const { net, mode, contacts } = await getNetwork();
  if (contacts === 0) return null;
  const feed = getFeed();
  const items = feed.live ? feed.snapshot.items.filter((i) => new Date(i.filed.length <= 10 ? `${i.filed}T15:30:00+05:30` : i.filed).getTime() > feed.snapshot.endMs - 7 * 24 * 3_600_000) : feed.items;
  const now = new Date();
  const ideas = reconnectIdeas(net, filingRefs(items), now);
  const themes = expertiseMap(net, now);
  return (
    <>
      <section id="worth-a-call">
        <h2 className="px-4 text-lg font-bold">Worth a call</h2>
        <p className="px-4 pt-1 text-ink-2">
          Contacts who used to work at a company that just filed, and you have not spoken in six months or more.
          {mode === "demo" ? " This is a synthetic network." : ""}
        </p>
        {ideas.length ? (
          <ul className="mt-3 divide-y divide-line border-y border-line">{ideas.map((i) => <Idea key={i.person.id} idea={i} />)}</ul>
        ) : (
          <p className="px-4 pt-3 text-ink-2">No one right now. When a company you hold files something and an old colleague has gone quiet, they show up here.</p>
        )}
      </section>
      {themes.length > 0 && (
        <section id="who-knows-what" className="pt-8">
          <h2 className="px-4 text-lg font-bold">Who knows what</h2>
          <p className="px-4 pt-1 text-ink-2">Your go-to people by sector, counted from years spent at companies FINN tracks.</p>
          <ul className="mt-3 divide-y divide-line border-y border-line">{themes.map((t) => <ThemeRow key={t.sector} t={t} />)}</ul>
        </section>
      )}
    </>
  );
}
