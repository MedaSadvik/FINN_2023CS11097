"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Today" },
  { href: "/company", label: "Research" },
  { href: "/network", label: "Network" },
];

/** Three equal-width tabs; the current page gets an underline. */
export function NavTabs() {
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
  return (
    <nav aria-label="Main" className="flex">
      {TABS.map((t) => (
        <Link
          key={t.href} href={t.href} aria-current={active(t.href) ? "page" : undefined}
          className={`flex min-h-11 flex-1 items-center justify-center border-b-2 text-[0.95rem] ${
            active(t.href) ? "border-ink font-semibold text-ink" : "border-transparent text-ink-2 hover:text-ink"
          }`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
