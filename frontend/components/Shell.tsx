import Link from "next/link";
import { Suspense } from "react";
import { getAccount } from "@/lib/account";
import { NavTabs } from "./NavTabs";
import { accountsEnabled } from "@/lib/supabase/env";

export function Shell({ children, banner }: { children: React.ReactNode; banner?: string }) {
  return (
    <div className="mx-auto min-h-dvh w-full max-w-[34rem] pb-24">
      <header className="sticky top-0 z-10 border-b border-line bg-paper/95 backdrop-blur">
        <div className="flex items-center justify-between px-4 pt-3 pb-1">
          <Link href="/" className="text-[1.35rem] font-bold tracking-tight">FINN</Link>
          {accountsEnabled && <Suspense fallback={<span className="size-9" />}><AccountLink /></Suspense>}
        </div>
        <NavTabs />
      </header>
      {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
      {children}
    </div>
  );
}

async function AccountLink() {
  const a = await getAccount();
  if (!a) return <Link href="/signin" className="min-h-9 rounded-full bg-ink px-4 py-1.5 text-[0.95rem] font-semibold text-paper">Sign in</Link>;
  const name = a.profile?.display_name || a.profile?.username || "?";
  return (
    <Link
      href="/me" aria-label={a.profile ? `Your profile, @${a.profile.username}` : "Finish your profile"}
      className="flex size-9 items-center justify-center rounded-full bg-ink text-[1rem] font-semibold text-paper"
    >
      {name.trim().charAt(0).toUpperCase()}
    </Link>
  );
}

export function SampleTag({ children = "Sample" }: { children?: string }) {
  return <span className="rounded-sm bg-wash px-1.5 py-0.5 text-xs font-medium text-ink-2">{children}</span>;
}
