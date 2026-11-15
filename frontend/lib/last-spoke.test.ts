import test from "node:test";
import assert from "node:assert/strict";
import { monthValue, parseMonth } from "./last-spoke";

const now = new Date("2026-11-15T10:00:00Z");

test("a month is stored as the first day of that month", () => {
  assert.deepEqual(parseMonth("2026-05", now), { ok: true, date: "2026-05-01" });
  assert.deepEqual(parseMonth(" 2026-11 ", now), { ok: true, date: "2026-11-01" });
});

test("blank clears the date", () => {
  assert.deepEqual(parseMonth("", now), { ok: true, date: null });
});

test("future months, bad shapes and very old years are refused", () => {
  for (const bad of ["2026-12", "2027-01", "2026-13", "2026-00", "May 2026", "2026-5", "1980-01", "2026-05-01"]) {
    assert.equal(parseMonth(bad, now).ok, false, bad);
  }
});

test("monthValue feeds the picker", () => {
  assert.equal(monthValue("2026-05-01"), "2026-05");
  assert.equal(monthValue(null), "");
});
