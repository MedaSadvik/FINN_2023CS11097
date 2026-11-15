import { redirect } from "next/navigation";
import { Suspense } from "react";
import { Shell } from "@/components/Shell";
import { ActionForm, Field } from "@/components/ActionForm";
import { addEducation, addRole, createProfile, removeEducation, removeRole, signOut, updateProfile } from "@/app/actions";
import { getAccount } from "@/lib/account";
import { createClient } from "@/lib/supabase/server";
import { demoNetwork } from "@/lib/network";

type Role = { id: number; employer_name: string; title: string; start_year: number; end_year: number | null };
type School = { id: number; institution: string; start_year: number; end_year: number };

function Remove({ action, id, label }: { action: (f: FormData) => Promise<void>; id: number; label: string }) {
  return (
    <form action={action}>
      <input type="hidden" name="id" value={id} />
      <button type="submit" aria-label={`Remove ${label}`} className="min-h-11 px-2 text-sm text-ink-2 underline underline-offset-2 hover:text-miss">Remove</button>
    </form>
  );
}

async function Body({ notice }: { notice?: string }) {
  const account = await getAccount();
  if (!account) redirect("/signin");
  const p = account.profile;
  if (!p) {
    return (
      <div className="px-4">
        <p className="text-ink-2">Choose a username so people can find you. This can&apos;t be changed later.</p>
        {notice && <p className="mt-2 text-miss">{notice}</p>}
        <ActionForm action={createProfile} submit="Create profile">
          <Field label="Your name" name="display_name" required maxLength={60} />
          <Field label="Username" name="username" required maxLength={20} placeholder="priya_iyer" hint="Lowercase letters, numbers and underscore." />
          <Field label="Headline" name="headline" maxLength={120} placeholder="Head of Operations, Kaynes Technology" />
        </ActionForm>
      </div>
    );
  }
  const supabase = await createClient();
  const [roles, schools] = await Promise.all([
    supabase.from("profile_roles").select("id, employer_name, title, start_year, end_year").eq("profile_id", p.id).order("start_year", { ascending: false }),
    supabase.from("profile_education").select("id, institution, start_year, end_year").eq("profile_id", p.id).order("start_year", { ascending: false }),
  ]);
  return (
    <>
      <div className="px-4">
        <p className="text-ink-2">@{p.username}</p>
        <ActionForm action={updateProfile} submit="Save">
          <Field label="Your name" name="display_name" required maxLength={60} defaultValue={p.display_name} />
          <Field label="Headline" name="headline" maxLength={120} defaultValue={p.headline} placeholder="Head of Operations, Kaynes Technology" />
        </ActionForm>
      </div>

      <h2 className="px-4 pt-8 text-lg font-bold">Career</h2>
      <p className="px-4 pt-1 text-ink-2">Connections see this. It is how FINN finds who has worked where.</p>
      <ul className="mt-2 divide-y divide-line border-y border-line">
        {((roles.data ?? []) as Role[]).map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-3 px-4 py-2">
            <span>
              <span className="block font-semibold">{r.title}</span>
              <span className="block text-sm text-ink-2">{r.employer_name}, {r.start_year}–{r.end_year ?? "now"}</span>
            </span>
            <Remove action={removeRole} id={r.id} label={`${r.title} at ${r.employer_name}`} />
          </li>
        ))}
        {(roles.data ?? []).length === 0 && <li className="px-4 py-3 text-ink-2">No jobs added yet.</li>}
      </ul>
      <details className="px-4 pt-3">
        <summary className="min-h-11 cursor-pointer font-semibold">Add a job</summary>
        <ActionForm action={addRole} submit="Add job">
          <Field label="Company" name="employer" required list="employers" maxLength={80} hint="Pick a company FINN tracks to get overlaps, or type any name." />
          <datalist id="employers">{demoNetwork.employers.map((e) => <option key={e.key} value={e.name} />)}</datalist>
          <Field label="Title" name="title" required maxLength={80} />
          <div className="flex gap-3">
            <div className="flex-1"><Field label="From year" name="start_year" type="number" required /></div>
            <div className="flex-1"><Field label="To year" name="end_year" type="number" hint="Blank if current." /></div>
          </div>
        </ActionForm>
      </details>

      <h2 className="px-4 pt-8 text-lg font-bold">Education</h2>
      <ul className="mt-2 divide-y divide-line border-y border-line">
        {((schools.data ?? []) as School[]).map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-3 px-4 py-2">
            <span>
              <span className="block font-semibold">{s.institution}</span>
              <span className="block text-sm text-ink-2">{s.start_year}–{s.end_year}</span>
            </span>
            <Remove action={removeEducation} id={s.id} label={s.institution} />
          </li>
        ))}
        {(schools.data ?? []).length === 0 && <li className="px-4 py-3 text-ink-2">No schools added yet.</li>}
      </ul>
      <details className="px-4 pt-3">
        <summary className="min-h-11 cursor-pointer font-semibold">Add a school</summary>
        <ActionForm action={addEducation} submit="Add school">
          <Field label="School" name="institution" required maxLength={80} />
          <div className="flex gap-3">
            <div className="flex-1"><Field label="From year" name="start_year" type="number" required /></div>
            <div className="flex-1"><Field label="To year" name="end_year" type="number" required /></div>
          </div>
        </ActionForm>
      </details>

      <form action={signOut} className="px-4 pt-10">
        <button type="submit" className="min-h-11 rounded-full border border-ink px-5 font-semibold hover:bg-ink hover:text-paper">Sign out</button>
      </form>
    </>
  );
}

export default function Me({ searchParams }: PageProps<"/me">) {
  return (
    <Shell>
      <main className="pb-6">
        <h1 className="px-4 pt-6 pb-4 text-[1.7rem] leading-tight font-bold tracking-tight">Your profile</h1>
        <Suspense fallback={<p className="px-4 text-ink-2">Loading…</p>}>
          <Notice searchParams={searchParams} />
        </Suspense>
      </main>
    </Shell>
  );
}

async function Notice({ searchParams }: { searchParams: PageProps<"/me">["searchParams"] }) {
  const q = await searchParams;
  return <Body notice={typeof q.notice === "string" ? q.notice : undefined} />;
}
