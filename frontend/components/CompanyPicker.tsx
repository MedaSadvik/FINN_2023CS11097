"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import symbolData from "@/data/symbols.json";
import { isComplete, isKnown, searchSymbols, type SymbolList } from "@/lib/symbols";

type Row = { ticker: string; name: string; promises: number | null };
const LIST = symbolData as unknown as SymbolList;

/** Pick a company from your portfolio, or type any NSE symbol. */
export function CompanyPicker({ rows }: { rows: Row[] }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const shown = rows.filter((r) => !needle || r.name.toLowerCase().includes(needle) || r.ticker.toLowerCase().includes(needle));
  const symbol = q.trim().toUpperCase().replace(/[^A-Z0-9&-]/g, "");
  const have = new Set(rows.map((r) => r.ticker));
  const more = needle ? searchSymbols(LIST, q, 8).filter((m) => !have.has(m.symbol)).slice(0, 5) : [];
  const [note, setNote] = useState("");

  function open() {
    if (!symbol) return;
    if (!isComplete(LIST) || isKnown(LIST, symbol)) return router.push(`/company/${encodeURIComponent(symbol)}`);
    // The typed text is not a symbol: go straight to the only candidate, else ask the person to choose.
    const candidates = [...new Set([...shown.map((r) => r.ticker), ...more.map((m) => m.symbol)])];
    if (candidates.length === 1) return router.push(`/company/${encodeURIComponent(candidates[0])}`);
    setNote(candidates.length ? "Pick one of the matches below." : `No NSE company matches \u201c${q.trim()}\u201d. Check the spelling, or try the symbol.`);
  }
  return (
    <div>
      <form
        className="px-4"
        onSubmit={(e) => {
          e.preventDefault();
          open();
        }}
      >
        <label htmlFor="company-q" className="block text-sm text-ink-2">Search your stocks, or type any NSE symbol to build it</label>
        <div className="mt-1 flex gap-2">
          <input
            id="company-q"
            value={q}
            onChange={(e) => { setQ(e.target.value); setNote(""); }}
            autoComplete="off"
            autoCapitalize="characters"
            placeholder="Kaynes, INFY, ZOMATO…"
            className="min-h-11 w-full rounded-lg border border-line bg-paper px-3 text-base outline-none focus-visible:border-ink"
          />
          <button type="submit" disabled={!symbol} className="min-h-11 rounded-lg bg-ink px-4 font-semibold text-paper disabled:opacity-40">
            Open
          </button>
        </div>
        {note && <p className="mt-2 text-[0.95rem] text-miss" role="status">{note}</p>}
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
        {shown.length === 0 && more.length === 0 && (
          <li className="px-4 py-4 text-ink-2">
            {isComplete(LIST) ? <>No NSE company matches &ldquo;{q.trim()}&rdquo;. Check the spelling, or try the symbol.</> : <>No match in your stocks. Press Open to view or build &ldquo;{symbol}&rdquo;.</>}
          </li>
        )}
      </ul>
      {more.length > 0 && (
        <>
          <h2 className="px-4 pt-5 text-sm text-ink-2">{shown.length ? "Other NSE companies" : "Did you mean"}</h2>
          <ul className="mt-1 divide-y divide-line border-y border-line">
            {more.map((m) => (
              <li key={m.symbol}>
                <Link href={`/company/${m.symbol}`} className="flex min-h-14 items-center justify-between gap-3 px-4 py-2 hover:bg-wash">
                  <span>
                    <span className="block font-semibold">{m.name}</span>
                    <span className="block text-sm text-ink-3">{m.symbol}</span>
                  </span>
                  <span className="text-sm text-ink-3">Not built yet</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
