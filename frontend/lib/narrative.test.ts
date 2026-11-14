import test from "node:test";
import assert from "node:assert/strict";
import { atAGlance, narrativeVsNumbers } from "./narrative";
import type { Financials } from "./financials";
import type { Pledge } from "./types";

const p = (outcome: Pledge["outcome"]): Pledge => ({ made_in: "Q1FY26", target: "t", horizon: "FY26", page: 1, quote: "q", mark: "q", outcome, result: null });

const strained: Financials = {
  basis: "consolidated", years: ["FY24", "FY25", "FY26"],
  rows: {
    FY24: { revenue: 1000, pat: 100, opm_pct: 15, cfo: 20, fcf: -50, equity_capital: 10, reserves: 500, borrowings: 100, total_liabilities: 900, roce_pct: 15 },
    FY25: { revenue: 1500, pat: 150, opm_pct: 15, cfo: -50, fcf: -200, equity_capital: 10, reserves: 600, borrowings: 300, total_liabilities: 1100, roce_pct: 14 },
    FY26: { revenue: 2200, pat: 200, opm_pct: 15, cfo: -100, fcf: -400, equity_capital: 10, reserves: 700, borrowings: 500, total_liabilities: 1400, roce_pct: 13 },
  },
};
const healthy: Financials = {
  basis: "consolidated", years: ["FY24", "FY25", "FY26"],
  rows: Object.fromEntries(["FY24", "FY25", "FY26"].map((y, i) => [y, { revenue: 1000 * (1 + i * 0.2), pat: 100 * (1 + i * 0.2), opm_pct: 15, cfo: 110 * (1 + i * 0.2), fcf: 60, equity_capital: 10, reserves: 500, borrowings: 50, ebitda: 200, interest: 5, total_liabilities: 700, roce_pct: 20 }])),
};

test("kept promises with poor cash conversion get a cautionary headline and the cash warning", () => {
  const n = narrativeVsNumbers([p("delivered"), p("delivered"), p("missed")], strained)!;
  assert.match(n.headline, /filings add caution/);
  assert.ok(n.points.some((x) => x.tone === "warn" && /cash/i.test(x.text)));
  assert.equal(n.kept, 2); assert.equal(n.missed, 1);
});

test("clean numbers and kept promises say so", () => {
  const n = narrativeVsNumbers([p("delivered")], healthy)!;
  assert.match(n.headline, /same story/);
  assert.ok(n.points.some((x) => x.tone === "ok"));
});

test("more misses than kept promises is stated plainly", () => {
  const n = narrativeVsNumbers([p("missed"), p("missed"), p("partly")], healthy)!;
  assert.match(n.headline, /More promises missed/);
});

test("nothing to compare means no section", () => {
  assert.equal(narrativeVsNumbers([p("unclear"), p("pending")], strained), null);
  assert.equal(narrativeVsNumbers([p("delivered")], null), null);
});

test("pending and unclear promises are not counted as kept or missed", () => {
  const n = narrativeVsNumbers([p("delivered"), p("pending"), p("unclear")], healthy)!;
  assert.match(n.points[0].text, /Of 1 promise we/);
});

test("at a glance reads the latest year and skips what a bank does not have", () => {
  const g = atAGlance(healthy)!;
  assert.equal(g.year, "FY26");
  assert.deepEqual(g.items.map((i) => i.label), ["Revenue", "Profit after tax", "Operating margin", "Return on capital", "Debt to equity", "Operating cash"]);
  const bank: Financials = { basis: "consolidated", years: ["FY25", "FY26"], rows: { FY25: { revenue: 100, pat: 20, deposits: 900 }, FY26: { revenue: 120, pat: 25, deposits: 1000, opm_pct: -12, roce_pct: 7 } } };
  assert.deepEqual(atAGlance(bank)!.items.map((i) => i.label), ["Income", "Profit after tax", "Return on capital"]);
  assert.equal(atAGlance(null), null);
});
