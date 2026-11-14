import Link from "next/link";
import { Suspense } from "react";
import { Shell } from "@/components/Shell";
import { NetworkInsights } from "@/components/NetworkInsights";
import { PersonLink } from "@/components/PersonLink";
import { ActionForm, Field } from "@/components/ActionForm";
import { monthYear } from "@/lib/format";
import { acceptRequest, clearSample, declineRequest, loadSample, removeConnection, requestConnection } from "@/app/actions";
import { getAccount, getNetwork } from "@/lib/account";
import { accountsEnabled } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";
import type { Person } from "@/lib/types";

type Conn = { id: number; requester_id: string; addressee_id: string; status: "pending" | "accepted" };
type Prof = { id: string; username: string; display_name: string; headline: string | null };
type Job = { profile_id: string; employer_name: string; title: string; start_year: number; end_year: number | null };

function Tiny({ action, id, label, strong }: { action: (f: FormData) => Promise<void>; id: number; label: string; strong?: boolean }) {
  return (
    <form action={action}>
      <input type="hidden" name="id" value={id} />
      <button type="submit" className={`min-h-11 rounded-full px-4 text-[0.95rem] font-semibold ${strong ? "bg-ink text-paper" : "border border-line text-ink-2 hover:border-ink hover:text-ink"}`}>{label}</button>
    </form>
  );
}

function SampleList({ title, people }: { title: string; people: Person[] }) {
  if (people.length === 0) return null;
  return (
    <section>
      <h3 className="px-4 pt-6 font-semibold">{title} <span className="font-normal text-ink-2">({people.length})</span></h3>
      <ul className="mt-2 divide-y divide-line border-y border-line">
        {people.map((p) => (
          <li key={p.id} className="px-4 py-2">
            <p><PersonLink id={p.id} name={p.full_name} /></p>
            <p className="text-sm text-ink-2">{p.headline}{p.last_spoke ? ` · last spoke ${monthYear(p.last_spoke)}` : ""}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SignedOut() {
  return (
    <div className="px-4 text-ink-2">
      <p>
        {accountsEnabled
          ? "Create an account to build your own network. Connect with people by their exact username and FINN shows, on every card, who among them has worked where."
          : "Accounts are not switched on in this build. Today and Research use a synthetic demo network."}
      </p>
      {accountsEnabled && (
        <Link href="/signin" className="mt-4 inline-flex min-h-11 items-center rounded-full bg-ink px-5 font-semibold text-paper">Sign in or create account</Link>
      )}
    </div>
  );
}

async function Body() {
  const account = await getAccount();
  if (!account) return <SignedOut />;
  if (!account.profile) {
    return (
      <div className="px-4">
        <p className="text-ink-2">Create your profile first, so people can find you by username.</p>
        <Link href="/me" className="mt-4 inline-flex min-h-11 items-center rounded-full bg-ink px-5 font-semibold text-paper">Create profile</Link>
      </div>
    );
  }
  const supabase = await createClient();
  const { data } = await supabase.from("connections").select("id, requester_id, addressee_id, status").order("created_at", { ascending: false });
  const conns = (data ?? []) as Conn[];
  const otherId = (c: Conn) => (c.requester_id === account.userId ? c.addressee_id : c.requester_id);
  const ids = conns.map(otherId);
  const [profs, jobs, view] = await Promise.all([
    ids.length ? supabase.from("profiles").select("id, username, display_name, headline").in("id", ids) : { data: [] },
    ids.length ? supabase.from("profile_roles").select("profile_id, employer_name, title, start_year, end_year").in("profile_id", ids).order("start_year", { ascending: false }) : { data: [] },
    getNetwork(account),
  ]);
  const byId = new Map(((profs.data ?? []) as Prof[]).map((p) => [p.id, p]));
  const who = (c: Conn) => byId.get(otherId(c));
  const incoming = conns.filter((c) => c.status === "pending" && c.addressee_id === account.userId);
  const outgoing = conns.filter((c) => c.status === "pending" && c.requester_id === account.userId);
  const connected = conns.filter((c) => c.status === "accepted");
  const samplePeople = view.net.people.filter((p) => !p.linked).sort((a, b) => a.full_name.localeCompare(b.full_name));
  const sample = samplePeople.length;

  return (
    <>
      <div className="px-4">
        <p className="text-ink-2">You are <span className="font-semibold text-ink">@{account.profile.username}</span>. Share it so people can find you.</p>
        <ActionForm action={requestConnection} submit="Send request">
          <Field label="Add a connection by exact username" name="username" required maxLength={21} placeholder="priya_iyer" autoComplete="off"
            hint="To try it alone, add demo_priya, demo_kabir or demo_meera. They accept at once." />
        </ActionForm>
      </div>

      {incoming.length > 0 && (
        <section>
          <h2 className="px-4 pt-8 text-lg font-bold">Asked to connect with you</h2>
          <ul className="mt-2 divide-y divide-line border-y border-line">
            {incoming.map((c) => (
              <li key={c.id} className="px-4 py-3">
                <p className="font-semibold">{who(c)?.display_name} <span className="font-normal text-ink-2">@{who(c)?.username}</span></p>
                {who(c)?.headline && <p className="text-sm text-ink-2">{who(c)?.headline}</p>}
                <div className="mt-2 flex gap-2"><Tiny action={acceptRequest} id={c.id} label="Accept" strong /><Tiny action={declineRequest} id={c.id} label="Decline" /></div>
              </li>
            ))}
          </ul>
          <p className="px-4 pt-2 text-sm text-ink-3">Accepting lets them see your jobs and schools, and you see theirs.</p>
        </section>
      )}

      <h2 className="px-4 pt-8 text-lg font-bold">Connections</h2>
      <ul className="mt-2 divide-y divide-line border-y border-line">
        {connected.map((c) => {
          const p = who(c);
          const theirJobs = ((jobs.data ?? []) as Job[]).filter((j) => j.profile_id === p?.id);
          const person = view.net.people.find((x) => x.profileId === p?.id);
          return (
            <li key={c.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-3">
                <p><span className="block font-semibold">{person ? <PersonLink id={person.id} name={p?.display_name ?? ""} /> : p?.display_name}</span>
                  <span className="block text-sm text-ink-2">@{p?.username}{p?.headline ? ` · ${p.headline}` : ""}</span></p>
                <Tiny action={removeConnection} id={c.id} label="Remove" />
              </div>
              {theirJobs.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-sm text-ink-2">
                  {theirJobs.map((j, i) => <li key={i}>{j.title}, {j.employer_name}, {j.start_year}–{j.end_year ?? "now"}</li>)}
                </ul>
              )}
            </li>
          );
        })}
        {connected.length === 0 && <li className="px-4 py-3 text-ink-2">No connections yet.</li>}
      </ul>

      {outgoing.length > 0 && (
        <section>
          <h2 className="px-4 pt-8 text-lg font-bold">Waiting for an answer</h2>
          <ul className="mt-2 divide-y divide-line border-y border-line">
            {outgoing.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-3 px-4 py-2">
                <span className="font-semibold">{who(c)?.display_name} <span className="font-normal text-ink-2">@{who(c)?.username}</span></span>
                <Tiny action={removeConnection} id={c.id} label="Cancel" />
              </li>
            ))}
          </ul>
        </section>
      )}

      <h2 className="px-4 pt-8 text-lg font-bold">Sample contacts</h2>
      <p className="px-4 pt-1 text-ink-2">
        {sample > 0
          ? `${sample} invented people are in your network so Today and Research have something to show. They are synthetic.`
          : "Your Call Sheets only use your connections. To try FINN before anyone accepts, load a set of invented contacts."}
      </p>
      <ActionForm action={sample > 0 ? clearSample : loadSample} submit={sample > 0 ? "Remove sample contacts" : "Load sample contacts"} className="px-4" />

      {sample > 0 && (
        <>
          <SampleList title="Close contacts" people={samplePeople.filter((p) => p.kind === "contact")} />
          <SampleList title="Wider network" people={samplePeople.filter((p) => p.kind !== "contact")} />
        </>
      )}
    </>
  );
}

export default function Network() {
  return (
    <Shell>
      <main className="pb-6">
        <h1 className="px-4 pt-6 pb-4 text-[1.7rem] leading-tight font-bold tracking-tight">Your network</h1>
        <Suspense fallback={<p className="px-4 text-ink-2">Loading…</p>}>
          <NetworkInsights />
          <div className="pt-10"><Body /></div>
        </Suspense>
      </main>
    </Shell>
  );
}
