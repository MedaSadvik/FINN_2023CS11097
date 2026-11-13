import { redirect } from "next/navigation";
import { Suspense } from "react";
import { Shell } from "@/components/Shell";
import { AuthForm } from "@/components/AuthForm";
import { getAccount } from "@/lib/account";
import { accountsEnabled } from "@/lib/supabase/env";

async function Body() {
  if (!accountsEnabled) {
    return (
      <p className="px-4 pt-4 text-ink-2">
        Accounts are not switched on in this build. You are seeing the demo with a synthetic network. To switch them on, set the two
        Supabase variables in <code className="rounded bg-wash px-1">frontend/.env.local</code>.
      </p>
    );
  }
  if (await getAccount()) redirect("/network");
  return <AuthForm />;
}

export default function SignIn() {
  return (
    <Shell>
      <main>
        <h1 className="px-4 pt-6 pb-4 text-[1.7rem] leading-tight font-bold tracking-tight">Your account</h1>
        <Suspense fallback={<p className="px-4 text-ink-2">Loading…</p>}><Body /></Suspense>
      </main>
    </Shell>
  );
}
