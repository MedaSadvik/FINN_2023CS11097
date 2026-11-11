import Link from "next/link";

export function Shell({ children, banner }: { children: React.ReactNode; banner?: string }) {
  return (
    <div className="mx-auto min-h-dvh w-full max-w-[34rem] pb-24">
      <header className="sticky top-0 z-10 flex items-baseline justify-between border-b border-line bg-paper/95 px-4 py-3 backdrop-blur">
        <Link href="/" className="text-[1.35rem] font-bold tracking-tight">FINN</Link>
        <nav className="flex gap-5 text-[0.95rem] text-ink-2">
          <Link href="/" className="hover:text-ink">Today</Link>
          <Link href="/company" className="hover:text-ink">Research</Link>
        </nav>
      </header>
      {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
      {children}
    </div>
  );
}

export function SampleTag({ children = "Sample" }: { children?: string }) {
  return <span className="rounded-sm bg-wash px-1.5 py-0.5 text-xs font-medium text-ink-2">{children}</span>;
}
