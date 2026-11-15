/**
 * Find an NSE company from what a person types: a symbol, part of a name, or a near miss ("asain paint").
 * Plain matching over NSE's own list of listed companies (data/symbols.json). No model, no network call.
 */
export type SymbolRow = [string, string]; // [symbol, company name]
export type SymbolList = { asof: string | null; source: string; rows: SymbolRow[] };
export type Match = { symbol: string; name: string; score: number };

/** A real NSE list has about 2,000 rows. A shorter list is only a starter file, so it must never be used to say "not found". */
export const MIN_COMPLETE = 500;
export const isComplete = (l: SymbolList) => l.rows.length >= MIN_COMPLETE;
export const isKnown = (l: SymbolList, symbol: string) => l.rows.some((r) => r[0] === symbol.toUpperCase());

const STOP = new Set(["ltd", "limited", "the", "of", "co", "corp", "corporation", "company", "and", "pvt", "private"]);
const tokens = (s: string) =>
  s.toLowerCase().replace(/&/g, " and ").replace(/[^a-z0-9]+/g, " ").trim().split(" ").filter((t) => t && !STOP.has(t));

function distance(a: string, b: string): number {
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    prev = cur;
  }
  return prev[b.length];
}
const allowed = (len: number) => (len <= 4 ? 0 : len <= 7 ? 1 : 2); // typos forgiven grow with word length

const commonStart = (a: string, b: string) => { let i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++; return i; };

/** Distance of one typed word to the closest name word: also against the word's start ("pers" ~ "persistent"),
 *  and words that share most of their start count as one slip apart ("technologies" ~ "technology"). */
const wordDistance = (q: string, words: string[]) =>
  Math.min(...words.map((w) => {
    const near = commonStart(q, w) >= Math.max(4, Math.ceil(0.75 * Math.min(q.length, w.length))) ? 1 : 99;
    return Math.min(distance(q, w), distance(q, w.slice(0, q.length)), near);
  }), 99);

function score(q: string[], compact: string, sym: string, name: string): number {
  const nameWords = tokens(name);
  const nameCompact = nameWords.join("");
  if (sym === compact) return 100;
  if (sym.startsWith(compact)) return 90 - (sym.length - compact.length) * 0.1;
  if (q.every((t) => nameWords.some((w) => w.startsWith(t)))) return 80 - Math.max(0, nameWords.length - q.length) * 0.5;
  if (compact.length >= 3 && (nameCompact.includes(compact) || sym.includes(compact))) return 60;
  const d = q.map((t) => wordDistance(t, nameWords));
  if (q.every((t, i) => d[i] <= allowed(t.length))) return 50 - d.reduce((a, b) => a + b, 0) * 5;
  if (compact.length >= 6 && distance(compact, sym) <= 2) return 45;
  if (compact.length >= 6 && distance(compact, nameCompact.slice(0, compact.length)) <= 2) return 40;
  return 0;
}

export function searchSymbols(list: SymbolList, query: string, limit = 6): Match[] {
  const q = tokens(query);
  if (q.length === 0) return [];
  const compact = q.join("");
  const out: Match[] = [];
  for (const [symbol, name] of list.rows) {
    const s = score(q, compact, symbol.toLowerCase().replace(/[^a-z0-9]/g, ""), name);
    if (s > 0) out.push({ symbol, name, score: s });
  }
  return out.sort((a, b) => b.score - a.score || a.symbol.length - b.symbol.length || a.symbol.localeCompare(b.symbol)).slice(0, limit);
}
