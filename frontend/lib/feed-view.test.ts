import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_PREFS, encodePrefs, parsePrefs, pickWindow, selectFeed, type FeedSnapshot } from "./feed-view";
import type { FeedItem } from "./types";

const END = new Date("2026-11-11T16:00:00+05:30").getTime();
const hoursAgo = (h: number) => new Date(END - h * 3_600_000).toISOString();
const ev = (id: string, category: string, h: number, priority = 3): FeedItem =>
  ({ id, type: "event", ticker: "KAYNES", company: "Kaynes", filed: hoursAgo(h), category, headline: id, detail: "", employer_key: null, priority }) as FeedItem;

const quiet = (n: number): [string, number, number][] =>
  Array.from({ length: n }, (_, i) => [`2026-10-${String(i + 1).padStart(2, "0")}`, 100, 1000]);

const snap = (over: Partial<FeedSnapshot> = {}): FeedSnapshot => ({
  endMs: END, maxHours: 336, routineTotal: 5, routineFiled: [hoursAgo(2), hoursAgo(50), hoursAgo(200)],
  items: [ev("new", "M&A", 3), ev("mid", "capex", 40), ev("old", "litigation", 150)], market: null, ...over,
});

test("window keeps only what is inside it, and counts routine filings for that window", () => {
  const a = selectFeed(snap(), 24, DEFAULT_PREFS);
  assert.deepEqual(a.items.map((i) => i.id), ["new"]);
  assert.equal(a.routineHidden, 1);
  const b = selectFeed(snap(), 72, DEFAULT_PREFS);
  assert.deepEqual(b.items.map((i) => i.id), ["new", "mid"]);
  assert.equal(b.routineHidden, 2);
  assert.equal(selectFeed(snap(), 336, DEFAULT_PREFS).items.length, 3);
});

test("hidden filing types are removed and counted", () => {
  const v = selectFeed(snap(), 336, { ...DEFAULT_PREFS, off: ["capex"] });
  assert.deepEqual(v.items.map((i) => i.id), ["new", "old"]);
  assert.equal(v.hiddenByYou, 1);
});

test("an older export without routine times only knows the total for the full window", () => {
  const s = snap({ routineFiled: null });
  assert.equal(selectFeed(s, 24, DEFAULT_PREFS).routineHidden, null);
  assert.equal(selectFeed(s, 336, DEFAULT_PREFS).routineHidden, 5);
});

test("alerts follow the investor's thresholds", () => {
  const rows = quiet(28);
  rows[27][2] = 3000; rows[27][1] = 90; // 28 Oct: volume 3x, price -10%
  const market = { KAYNES: { company: "Kaynes", employer_key: "kaynes", rows } };
  const end = new Date("2026-10-29T10:00:00+05:30").getTime();
  const s = snap({ endMs: end, items: [], market, routineFiled: [] });
  const alerts = (p = DEFAULT_PREFS, h = 72) => selectFeed(s, h, p).items.filter((i) => i.type === "alert");
  assert.equal(alerts().length, 1);
  assert.equal(alerts({ ...DEFAULT_PREFS, volume: 5, move: 15 }).length, 0); // stricter: nothing
  const only = alerts({ ...DEFAULT_PREFS, volume: null })[0];                 // volume rule off
  assert.ok(only.type === "alert" && only.volume_x === null && only.price_pct === -10);
  assert.equal(alerts({ ...DEFAULT_PREFS, volume: null, move: null }).length, 0);
});

test("one alert card per company, newest day, with a count of earlier days", () => {
  const rows = quiet(28);
  rows[22][2] = 3000; rows[27][2] = 4000;
  const s = snap({ endMs: new Date("2026-10-29T10:00:00+05:30").getTime(), items: [], routineFiled: [], market: { KAYNES: { company: "Kaynes", employer_key: null, rows } } });
  const a = selectFeed(s, 336, { ...DEFAULT_PREFS, move: null }).items;
  assert.equal(a.length, 1);
  assert.ok(a[0].type === "alert" && a[0].filed === "2026-10-28" && a[0].earlier === 1);
});

test("an old export with baked alerts keeps them", () => {
  const baked = { id: "alert-X", type: "alert", ticker: "X", company: "X", filed: "2026-11-11", volume_x: 3, price_pct: null, employer_key: null, priority: 2 } as FeedItem;
  const v = selectFeed(snap({ items: [baked] }), 24, DEFAULT_PREFS);
  assert.equal(v.items.length, 1);
});

test("results cards and management changes follow their own switches", () => {
  const results = { id: "r", type: "results", ticker: "K", company: "K", filed: hoursAgo(1), quarter: "Q2FY27" } as unknown as FeedItem;
  assert.equal(selectFeed(snap({ items: [results] }), 24, { ...DEFAULT_PREFS, off: ["results"] }).items.length, 0);
  const mc = { id: "m", type: "mgmt_change", ticker: "K", company: "K", filed: hoursAgo(1), category: "management_change", priority: 3 } as unknown as FeedItem;
  assert.equal(selectFeed(snap({ items: [mc] }), 24, { ...DEFAULT_PREFS, off: ["management_change"] }).items.length, 0);
});

test("prefs cookie: round trip, off rules, and garbage", () => {
  const p = { volume: null, move: 7, off: ["capex", "dividend"] };
  assert.deepEqual(parsePrefs(encodePrefs(p)), p);
  assert.deepEqual(parsePrefs(undefined), DEFAULT_PREFS);
  assert.deepEqual(parsePrefs("not json"), DEFAULT_PREFS);
  assert.deepEqual(parsePrefs(JSON.stringify({ v: 999, m: "x", off: ["nope", 3, "capex"] })), { volume: 2, move: 5, off: ["capex"] });
});

test("window choice never exceeds the export", () => {
  assert.equal(pickWindow("7d", 336).hours, 168);
  assert.equal(pickWindow("14d", 48).key, "24h"); // not offered; falls back to the default or the largest usable
  assert.equal(pickWindow(undefined, 336).key, "3d");
});
