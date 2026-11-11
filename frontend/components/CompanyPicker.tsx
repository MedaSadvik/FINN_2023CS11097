"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

type Row = { ticker: string; name: string; promises: number | null };

/** Pick a company from your portfolio, or type any NSE symbol. */
export function CompanyPicker({ rows }: { rows: Row[] }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const shown = rows.filter((r) => !needle || r.name.toLowerCase().includes(needle) || r.ticker.toLowerCase().includes(needle));
  const symbol = q.trim().toUpperCase().replace(/[^A-Z0-9&-]/g, "");
  return (
    <div>
      <form
        className="px-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (symbol) router.push(`/company/${encodeURIComponent(symbol)}`);
        }}
      >
        <label htmlFor="company-q" className="block text-sm text-ink-2">Search your stocks or type any NSE symbol</label>
        <div className="mt-1 flex gap-2">
          <input
            id="company-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            autoComplete="off"
            autoCapitalize="characters"
            placeholder="Kaynes, INFY, ZOMATO…"
            className="min-h-11 w-full rounded-lg border border-line bg-paper px-3 text-base outline-none focus-visible:border-ink"
          />
          <button type="submit" disabled={!symbol} className="min-h-11 rounded-lg bg-ink px-4 font-semibold text-paper disabled:opacity-40">
            Open
          </button>
        </div>
      </form>
      <ul className="mt-4 divide-y divide-line border-y border-line">
        {shown.map((r) => (
          <li key={r.ticker}>
            <Link href={`/company/${r.ticker}`} className="flex min-h-14 items-center justify-between gap-3 px-4 py-2 hover:bg-wash">
              <span>
                <span className="block font-semibold">{r.name}</span>
                <span className="block text-sm text-ink-3">{r.ticker}</span>
              </span>
              <span className={r.promises === null ? "text-sm text-ink-3" : "text-sm font-semibold text-ok"}>
                {r.promises === null ? "Not built yet" : `${r.promises} promises read`}
              </span>
            </Link>
          </li>
        ))}
        {shown.length === 0 && <li className="px-4 py-4 text-ink-2">No match in your stocks. Press Open to try “{symbol}” on NSE.</li>}
      </ul>
    </div>
  );
}
