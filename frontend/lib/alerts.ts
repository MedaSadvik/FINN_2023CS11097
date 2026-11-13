/**
 * Triggered alerts on end-of-day data. A line-for-line port of pipeline/alerts.py: the same maths, so a threshold
 * means the same thing in the pipeline and in the app. lib/alerts.fixture.json (written from the Python) pins them together.
 * Rows are [day, close, volume], oldest first.
 */
export type Row = [string, number, number];
export type Rules = { volume_multiple?: number | null; price_move?: number | null }; // missing or null = rule off
export type Hit =
  | { kind: "volume_multiple"; day: string; ratio: number; volume: number; avg_volume: number; days_in_avg: number }
  | { kind: "price_move"; day: string; pct: number; close: number; prev_close: number };

const MIN_HISTORY = 10; // fewer prior days than this and an "average" means nothing
const round = (n: number, d: number) => Math.round(n * 10 ** d) / 10 ** d;

export function volumeSpike(rows: Row[], multiple = 2, window = 20): Hit | null {
  if (rows.length < MIN_HISTORY + 1) return null;
  const prior = rows.slice(-(window + 1), -1).map((r) => r[2]);
  const avg = prior.reduce((a, b) => a + b, 0) / prior.length;
  if (avg <= 0) return null;
  const last = rows[rows.length - 1];
  const ratio = last[2] / avg;
  return ratio >= multiple
    ? { kind: "volume_multiple", day: last[0], ratio: round(ratio, 2), volume: last[2], avg_volume: Math.round(avg), days_in_avg: prior.length }
    : null;
}

export function priceMove(rows: Row[], pct = 5): Hit | null {
  if (rows.length < 2 || rows[rows.length - 2][1] <= 0) return null;
  const [prev, last] = [rows[rows.length - 2], rows[rows.length - 1]];
  const change = ((last[1] - prev[1]) / prev[1]) * 100;
  return Math.abs(change) >= pct ? { kind: "price_move", day: last[0], pct: round(change, 2), close: last[1], prev_close: prev[1] } : null;
}

export function checkAll(rows: Row[], rules: Rules): Hit[] {
  const hits: Hit[] = [];
  const v = rules.volume_multiple != null ? volumeSpike(rows, rules.volume_multiple) : null;
  if (v) hits.push(v);
  const p = rules.price_move != null ? priceMove(rows, rules.price_move) : null;
  if (p) hits.push(p);
  return hits;
}

/** NSE closes at 15:30 IST. A day's numbers exist from then on. */
export const closeTime = (day: string) => new Date(`${day}T15:30:00+05:30`).getTime();

/**
 * Every trading day inside the window, checked against the 20 days before it.
 * Returns the days that tripped a rule, newest first. One card per company uses the first; the rest are "earlier days".
 */
export function hitsInWindow(rows: Row[], rules: Rules, fromMs: number, toMs: number): { day: string; hits: Hit[] }[] {
  const out: { day: string; hits: Hit[] }[] = [];
  for (let i = rows.length - 1; i >= 0; i--) {
    const t = closeTime(rows[i][0]);
    if (t > toMs) continue;
    if (t <= fromMs) break;
    const hits = checkAll(rows.slice(0, i + 1), rules);
    if (hits.length) out.push({ day: rows[i][0], hits });
  }
  return out;
}
