import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Shell } from "@/components/Shell";
import { DraftEmail } from "@/components/DraftEmail";
import { draftEmail } from "@/lib/draft-email";
import { getAccount, getNetwork } from "@/lib/account";
import { callSheet, employerKeyFor, employerName } from "@/lib/network-core";
import { trackedFor } from "@/lib/network-insights";
import { monthYear, years } from "@/lib/format";
import type { Evidence } from "@/lib/types";

const TICKER = /^[A-Z0-9&-]{1,20}$/;

async function Body({ params, searchParams }: { params: PageProps<"/network/[id]">["params"]; searchParams: PageProps<"/network/[id]">["searchParams"] }) {
  await connection(); // "when you last spoke" depends on today's date
  const [{ id }, sp] = await Promise.all([params, searchParams]);
  const raw = Array.isArray(sp.about) ? sp.about[0] : sp.about;
  const about = raw && TICKER.test(raw.toUpperCase()) ? raw.toUpperCase() : null;

  const account = await getAccount();
  const { net, mode } = await getNetwork(account); // only this visitor's own people come back (row level security)
  const person = /^\d{1,9}$/.test(id) ? net.people.find((p) => p.id === Number(id)) : undefined;
  if (!person) notFound();

  const key = about ? employerKeyFor(net, about) : null;
  const lead = key ? callSheet(net, key, 200).find((l) => l.person.id === person.id) : undefined;
  const reasons: Evidence[] = lead?.reasons ?? [];
  const draft = draftEmail(net, person, { about, me: account?.profile?.display_name ?? null, now: new Date() });
  const companies = [...new Map(person.roles.flatMap((r) => { const e = trackedFor(net, r); return e ? [[e.ticker!, e.name] as const] : []; })).entries()];
  const synthetic = mode === "demo" || !person.linked;

  return (
    <main className="pb-8">
      <Link href="/network" className="block px-4 pt-4 text-sm text-ink-2 hover:text-ink">Your network</Link>
      <h1 className="px-4 pt-2 text-[1.7rem] leading-tight font-bold tracking-tight">{person.full_name}</h1>
      {person.headline && <p className="px-4 pt-1 text-ink-2">{person.headline}</p>}
      <div className="px-4">
        <DraftEmail name={person.full_name} subject={draft.subject} body={draft.body} />
      </div>

      <p className="px-4 pt-4 text-[0.95rem]">
        {person.last_spoke ? <>You last spoke in {monthYear(person.last_spoke)}. <span className="text-sm text-ink-3 italic">(your notes)</span></> : "No note on when you last spoke."}
      </p>

      {reasons.length > 0 && key && (
        <section className="px-4 pt-6">
          <h2 className="text-lg font-bold">On {employerName(net, key)}</h2>
          <ul className="mt-2 space-y-1.5">
            {reasons.map((r, i) => (
              <li key={i} className="text-[0.95rem] leading-snug">{r.text} <span className={r.source === "your notes" ? "text-sm text-ink-3 italic" : "text-sm text-ink-3"}>({r.source})</span></li>
            ))}
          </ul>
        </section>
      )}

      {person.roles.length > 0 && (
        <section className="px-4 pt-6">
          <h2 className="text-lg font-bold">Career</h2>
          <ul className="mt-2 divide-y divide-line border-y border-line">
            {person.roles.map((r, i) => (
              <li key={i} className="py-2.5">
                <p className="font-semibold">{r.title}</p>
                <p className="text-sm text-ink-2">{r.employer_name ?? employerName(net, r.employer_key)}, {years(r.start_year, r.end_year)}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {person.education.length > 0 && (
        <section className="px-4 pt-6">
          <h2 className="text-lg font-bold">Education</h2>
          <ul className="mt-2 divide-y divide-line border-y border-line">
            {person.education.map((e, i) => (
              <li key={i} className="py-2.5"><span className="font-semibold">{e.institution}</span> <span className="text-sm text-ink-2">{years(e.start_year, e.end_year)}</span></li>
            ))}
          </ul>
        </section>
      )}

      {companies.length > 0 && (
        <section className="px-4 pt-6">
          <h2 className="text-lg font-bold">Companies you track</h2>
          <p className="mt-1 text-ink-2">Places they have worked that FINN covers.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {companies.map(([ticker, name]) => (
              <Link key={ticker} href={`/company/${ticker}`} className="inline-flex min-h-11 items-center rounded-full border border-line px-4 text-[0.95rem] text-ink-2 hover:border-ink hover:text-ink">{name}</Link>
            ))}
          </div>
        </section>
      )}

      <p className="px-4 pt-6 text-sm text-ink-3">
        {synthetic ? "Invented person, part of the sample network." : "From their own profile. You can see it because they accepted your request."}
      </p>
    </main>
  );
}

export default function Person({ params, searchParams }: PageProps<"/network/[id]">) {
  return (
    <Shell>
      <Suspense fallback={<p className="px-4 pt-6 text-ink-2">Loading…</p>}>
        <Body params={params} searchParams={searchParams} />
      </Suspense>
    </Shell>
  );
}
