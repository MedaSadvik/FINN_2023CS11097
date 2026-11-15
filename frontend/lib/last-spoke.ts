/**
 * "When did you last speak?" is typed by the investor as a month (YYYY-MM, what a phone month picker gives).
 * We store the first day of that month. Blank clears it. A month in the future is refused.
 */
export type MonthResult = { ok: true; date: string | null } | { ok: false; message: string };

export function parseMonth(value: string, now: Date): MonthResult {
  const v = value.trim();
  if (v === "") return { ok: true, date: null };
  const m = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(v);
  if (!m) return { ok: false, message: "Pick a month and year." };
  const year = Number(m[1]), month = Number(m[2]);
  if (year < 1990) return { ok: false, message: "That date looks too old. Pick a month after 1990." };
  if (year * 12 + month > now.getUTCFullYear() * 12 + now.getUTCMonth() + 1) return { ok: false, message: "That month is in the future." };
  return { ok: true, date: `${m[1]}-${m[2]}-01` };
}

/** The value for a month picker's current setting, from a stored date. */
export const monthValue = (iso: string | null): string => (iso ? iso.slice(0, 7) : "");
