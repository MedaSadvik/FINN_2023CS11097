/**
 * What the investor sees on Today: the feed snapshot, cut to the window they picked and shaped by their own settings.
 * Pure functions, so they are tested without a browser. The page only passes data in.
 */
import { hitsInWindow, type Row, type Rules } from "./alerts";
import type { FeedItem } from "./types";

export const WINDOWS = [
  { key: "24h", hours: 24, label: "24 hours" },
  { key: "3d", hours: 72, label: "3 days" },
  { key: "7d", hours: 168, label: "7 days" },
  { key: "14d", hours: 336, label: "14 days" },
] as const;
export const DEFAULT_WINDOW = "3d";

/** Filing types the investor can switch on or off. Alerts are governed by the two thresholds instead. */
export const CATEGORIES = [
  { key: "results", label: "Results" },
  { key: "management_change", label: "Management change" },
  { key: "M&A", label: "Deals" },
  { key: "litigation", label: "Legal" },
  { key: "capex", label: "Capex" },
  { key: "fund_raise", label: "Fund raising" },
  { key: "credit_rating", label: "Credit rating" },
  { key: "dividend", label: "Dividends" },
  { key: "bonus_split", label: "Bonus or split" },
  { key: "pledging", label: "Share pledges" },
] as const;

export const VOLUME_CHOICES = [1.5, 2, 3, 5] as const; // times the 20-day average
export const MOVE_CHOICES = [2, 3, 5, 7, 10] as const; // percent in a day

/** null means the rule is off. `off` lists filing types the investor has hidden. */
export type Prefs = { volume: number | null; move: number | null; off: string[] };
export const DEFAULT_PREFS: Prefs = { volume: 2, move: 5, off: [] };
export const PREFS_COOKIE = "finn_prefs";

const oneOf = <T extends number>(v: unknown, allowed: readonly T[], fallback: number | null) =>
  v === null ? null : typeof v === "number" && (allowed as readonly number[]).includes(v) ? v : fallback;

/** Read the cookie defensively: anything unexpected falls back to the defaults. */
export function parsePrefs(raw: string | undefined | null): Prefs {
  if (!raw) return DEFAULT_PREFS;
  try {
    const o = JSON.parse(raw) as { v?: unknown; m?: unknown; off?: unknown };
    const keys = new Set<string>(CATEGORIES.map((c) => c.key));
    return {
      volume: o.v === undefined ? DEFAULT_PREFS.volume : oneOf(o.v, VOLUME_CHOICES, DEFAULT_PREFS.volume),
      move: o.m === undefined ? DEFAULT_PREFS.move : oneOf(o.m, MOVE_CHOICES, DEFAULT_PREFS.move),
      off: Array.isArray(o.off) ? o.off.filter((k): k is string => typeof k === "string" && keys.has(k)) : [],
    };
  } catch {
    return DEFAULT_PREFS;
  }
}
export const encodePrefs = (p: Prefs) => JSON.stringify({ v: p.volume, m: p.move, off: p.off });

export type Market = Record<string, { company: string; employer_key: string | null; rows: Row[] }>;
export type FeedSnapshot = {
  endMs: number;
  maxHours: number;
  items: FeedItem[];
  routineFiled: string[] | null; // null: an older export that only has a total
  routineTotal: number;
  market: Market | null; // null: an older export with alerts already decided
  filingsAsOfMs: number | null; // when NSE was last read successfully; null in older exports
};

export function pickWindow(key: string | undefined, maxHours: number) {
  const usable = WINDOWS.filter((w) => w.hours <= maxHours);
  const list = usable.length ? usable : [{ key: "all", hours: maxHours, label: `${maxHours} hours` }];
  return list.find((w) => w.key === key) ?? list.find((w) => w.key === DEFAULT_WINDOW) ?? list[list.length - 1];
}
export const windowChoices = (maxHours: number) => WINDOWS.filter((w) => w.hours <= maxHours);

const ms = (iso: string) => new Date(iso.length <= 10 ? `${iso}T15:30:00+05:30` : iso).getTime();
const categoryOf = (i: FeedItem) => (i.type === "results" ? "results" : i.type === "alert" ? "alert" : i.category ?? "");

export type View = { items: FeedItem[]; routineHidden: number | null; hiddenByYou: number };

export function selectFeed(s: FeedSnapshot, hours: number, prefs: Prefs): View {
  const from = s.endMs - hours * 3_600_000;
  const inWindow = (i: FeedItem) => ms(i.filed) > from && ms(i.filed) <= s.endMs;

  const filings = s.items.filter((i) => (s.market ? i.type !== "alert" : true) && inWindow(i));
  const shown = filings.filter((i) => !prefs.off.includes(categoryOf(i)));
  const items: FeedItem[] = [...shown];

  if (s.market) {
    const rules: Rules = { volume_multiple: prefs.volume, price_move: prefs.move };
    for (const [ticker, m] of Object.entries(s.market)) {
      const days = hitsInWindow(m.rows, rules, from, s.endMs);
      if (!days.length) continue;
      const vol = days[0].hits.find((h) => h.kind === "volume_multiple");
      const px = days[0].hits.find((h) => h.kind === "price_move");
      items.push({
        id: `alert-${ticker}-${days[0].day}`, type: "alert", ticker, company: m.company, filed: days[0].day,
        employer_key: m.employer_key,
        volume_x: vol && vol.kind === "volume_multiple" ? vol.ratio : null,
        price_pct: px && px.kind === "price_move" ? px.pct : null,
        rules: { volume_multiple: prefs.volume ?? undefined, price_move: prefs.move ?? undefined },
        earlier: days.length - 1,
      });
    }
  }
  const prio = (i: FeedItem) => (i.type === "alert" ? 2 : ((i as { priority?: number }).priority ?? 3));
  items.sort((a, b) => prio(b) - prio(a) || ms(b.filed) - ms(a.filed));

  const routineHidden = s.routineFiled ? s.routineFiled.filter((t) => ms(t) > from && ms(t) <= s.endMs).length
    : hours >= s.maxHours ? s.routineTotal : null;
  return { items, routineHidden, hiddenByYou: filings.length - shown.length };
}

/** Filings older than this at the time of the snapshot are called out, so a quiet feed is never mistaken for a quiet market. */
export const STALE_HOURS = 30;
export const filingsStale = (s: FeedSnapshot) => s.filingsAsOfMs !== null && s.endMs - s.filingsAsOfMs > STALE_HOURS * 3_600_000;
