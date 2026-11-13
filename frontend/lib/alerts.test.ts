import test from "node:test";
import assert from "node:assert/strict";
import fixture from "./alerts.fixture.json" with { type: "json" };
import { checkAll, hitsInWindow, closeTime, type Row } from "./alerts";

for (const c of fixture as { name: string; rows: Row[]; rules: object; expect: unknown[] }[]) {
  test(`same answer as the Python: ${c.name}`, () => assert.deepEqual(checkAll(c.rows, c.rules), c.expect));
}

const quiet = (n: number): Row[] => Array.from({ length: n }, (_, i) => [`2026-10-${String(i + 1).padStart(2, "0")}`, 100, 1000]);

test("window checks each day and returns the tripped days newest first", () => {
  const rows = quiet(28);
  rows[24][2] = 3000; // 25 Oct
  rows[27][1] = 90;   // 28 Oct, -10%
  const hits = hitsInWindow(rows, { volume_multiple: 2, price_move: 5 }, closeTime("2026-10-20"), closeTime("2026-10-28"));
  assert.deepEqual(hits.map((h) => h.day), ["2026-10-28", "2026-10-25"]);
});

test("days outside the window are ignored", () => {
  const rows = quiet(28);
  rows[24][2] = 3000;
  assert.equal(hitsInWindow(rows, { volume_multiple: 2 }, closeTime("2026-10-26"), closeTime("2026-10-28")).length, 0);
});
