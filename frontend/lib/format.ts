export const cr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")} cr`;
export const pct = (n: number, digits = 1) => `${n >= 0 ? "+" : "−"}${Math.abs(n).toFixed(digits)}%`;
export const change = (cur: number, base: number) => (base ? (cur / base - 1) * 100 : NaN);
export const monthYear = (iso: string) =>
  new Date(iso + "T00:00:00Z").toLocaleDateString("en-IN", { month: "short", year: "numeric", timeZone: "UTC" });
export const years = (a: number, b: number | null) => `${a}–${b ?? "now"}`;
export const shortDate = (iso: string) =>
  iso ? new Date(iso.length <= 10 ? iso + "T00:00:00+05:30" : iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }) : "";
export const at = (iso: string) => new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", hour12: true, timeZone: "Asia/Kolkata" });
export const windowLabel = (start: string, end: string) => `${at(start)} to ${at(end)}`;
