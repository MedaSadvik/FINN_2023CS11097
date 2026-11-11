import Link from "next/link";
import { Suspense } from "react";
import { getAccount } from "@/lib/account";
import { accountsEnabled } from "@/lib/supabase/env";

export function Shell({ children, banner }: { children: React.ReactNode; banner?: string }) {
  return (
    <div className="mx-auto min-h-dvh w-full max-w-[34rem] pb-24">
      <header className="sticky top-0 z-10 flex items-baseline justify-between border-b border-line bg-paper/95 px-4 py-3 backdrop-blur">
        <Link href="/" className="text-[1.35rem] font-bold tracking-tight">FINN</Link>
        <nav className="flex gap-4 text-[0.95rem] text-ink-2">
          <Link href="/" className="hover:text-ink">Today</Link>
          <Link href="/company" className="hover:text-ink">Research</Link>
          <Link href="/network" className="hover:text-ink">Network</Link>
          {accountsEnabled && <Suspense fallback={<span className="w-14" />}><AccountLink /></Suspense>}
        </nav>
      </header>
      {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
      {children}
    </div>
  );
}

async function AccountLink() {
  const a = await getAccount();
  return a?.profile
    ? <Link href="/me" className="font-semibold text-ink hover:underline">@{a.profile.username}</Link>
    : <Link href={a ? "/me" : "/signin"} className="font-semibold text-ink hover:underline">{a ? "Profile" : "Sign in"}</Link>;
}

export function SampleTag({ children = "Sample" }: { children?: string }) {
  return <span className="rounded-sm bg-wash px-1.5 py-0.5 text-xs font-medium text-ink-2">{children}</span>;
}
