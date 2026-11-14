import test from "node:test";
import assert from "node:assert/strict";
import { balanceSheet, cagr, cashQuality, trajectory, type Financials } from "./financials";

// Shaped like KAYNES (the last three years are real; earlier years are rounded stand-ins for the test).
const kaynes: Financials = {
  basis: "consolidated", years: ["FY23", "FY24", "FY25", "FY26"],
  rows: {
    FY23: { revenue: 1000, opm_pct: 14, pat: 100, ebitda: 140, interest: 20, equity_capital: 60, reserves: 800, borrowings: 200, total_liabilities: 1400, cfo: 60, fcf: -50, ccc_days: 110, roce_pct: 16 },
    FY24: { revenue: 1800, opm_pct: 17, pat: 200, ebitda: 300, interest: 50, equity_capital: 64, reserves: 2423, borrowings: 323, total_liabilities: 3265, cfo: 88, fcf: -295, ccc_days: 123, roce_pct: 15 },
    FY25: { revenue: 2722, opm_pct: 15, pat: 293, ebitda: 416, interest: 106, equity_capital: 64, reserves: 2776, borrowings: 903, total_liabilities: 4641, cfo: -82, fcf: -1031, ccc_days: 102, roce_pct: 14 },
    FY26: { revenue: 3626, opm_pct: 16, pat: 364, ebitda: 578, interest: 121, equity_capital: 67, reserves: 4681, borrowings: 913, total_liabilities: 6894, cfo: -600, fcf: -1841, ccc_days: 193, roce_pct: 13 },
  },
};

test("cagr refuses a growth rate when a value is not positive", () => {
  assert.equal(Math.round(cagr(100, 200, 1)!), 100);
  assert.equal(cagr(-5, 20, 3), null);
  assert.equal(cagr(0, 20, 3), null);
  assert.equal(cagr(null, 20, 3), null);
});

test("trajectory: growth, margin and a profit-versus-revenue flag", () => {
  const t = trajectory(kaynes)!;
  assert.equal(t.span, 3);
  assert.equal(Math.round(t.revenueCagr!), 54);
  assert.equal(t.margin, "expanding"); // 14% to 16%
  assert.match(t.headline, /Revenue grew 54% a year over 3 years, to ₹3,626 cr; operating margin rose from 14% to 16%\./);
  assert.ok(t.flags.some((f) => /Return on capital fell from 16% to 13%/.test(f.text)));
  assert.equal(t.flags.some((f) => /slower than revenue/.test(f.text)), false); // profit and revenue grew alike here
});

test("trajectory: a thin history is left out", () => {
  assert.equal(trajectory({ basis: "x", years: ["FY25", "FY26"], rows: { FY25: { revenue: 1 }, FY26: { revenue: 2 } } }), null);
});

test("balance sheet: debt, net worth, ratio, funding mix, and the cycle that lengthened", () => {
  const b = balanceSheet(kaynes)!;
  assert.equal(b.netWorth, 4748);
  assert.equal(b.deRatio!.toFixed(2), "0.19");
  assert.equal(b.deThen!.toFixed(2), "0.13"); // FY24: 323 / 2487
  assert.equal(b.interestCover!.toFixed(1), "4.8");
  assert.equal(Math.round(b.funding!.equity + b.funding!.debt + b.funding!.other), 100);
  assert.ok(b.flags.some((f) => f.tone === "warn" && /lengthened from 123 to 193 days/.test(f.text)));
  assert.match(b.headline, /Borrowings are ₹913 cr against a net worth of ₹4,748 cr, a debt to equity of 0\.19\./);
});

test("balance sheet: weak interest cover is flagged; missing data returns null", () => {
  const weak = structuredClone(kaynes);
  weak.rows.FY26.ebitda = 200;
  assert.ok(balanceSheet(weak)!.flags.some((f) => /covers interest only 1\.7 times/.test(f.text)));
  assert.equal(balanceSheet({ basis: "x", years: ["FY26"], rows: { FY26: { revenue: 1 } } }), null);
});

test("cash quality: profit that does not turn into cash", () => {
  const c = cashQuality(kaynes)!;
  assert.equal(c.sumPat, 857);
  assert.equal(c.sumCfo, -594);
  assert.equal(c.conversion!.toFixed(0), "-69");
  assert.equal(c.fcfTotal, -3167);
  assert.equal(c.headline, "Over 3 years the company reported ₹857 cr of profit and generated -₹594 cr of operating cash (-69%).");
  assert.ok(c.flags.some((f) => f.tone === "warn" && /Profit is not turning into cash: ₹857 cr reported, -₹594 cr of operating cash/.test(f.text)));
  assert.ok(c.flags.some((f) => /Operating cash flow was negative in FY26/.test(f.text)));
  assert.ok(c.flags.some((f) => f.tone === "note" && /used ₹3,167 cr of cash/.test(f.text)));
});

test("cash quality: thin but positive conversion", () => {
  const thin: Financials = { basis: "x", years: ["FY24", "FY25", "FY26"], rows: {
    FY24: { cfo: 30, pat: 100 }, FY25: { cfo: 40, pat: 120 }, FY26: { cfo: 50, pat: 150 } } };
  assert.match(cashQuality(thin)!.flags[0].text, /Only 32% of reported profit turned into operating cash in 3 years\./);
});

test("cash quality: a healthy company gets a good flag and no warning", () => {
  const ok: Financials = { basis: "x", years: ["FY24", "FY25", "FY26"], rows: {
    FY24: { cfo: 90, pat: 100, fcf: 20 }, FY25: { cfo: 110, pat: 120, fcf: 30 }, FY26: { cfo: 140, pat: 150, fcf: 40 } } };
  const c = cashQuality(ok)!;
  assert.equal(Math.round(c.conversion!), 92);
  assert.deepEqual(c.flags.map((f) => f.tone), ["ok"]);
});

test("cash quality needs cash flow and profit for each year", () => {
  assert.equal(cashQuality({ basis: "x", years: ["FY25", "FY26"], rows: { FY25: { cfo: 1, pat: 1 }, FY26: { pat: 1 } } }), null);
});

test("trajectory: profit growing much slower than revenue is flagged", () => {
  const slow: Financials = { basis: "x", years: ["FY23", "FY24", "FY25", "FY26"], rows: {
    FY23: { revenue: 1000, pat: 100, opm_pct: 15 }, FY24: { revenue: 1500, pat: 105, opm_pct: 12 },
    FY25: { revenue: 2000, pat: 110, opm_pct: 10 }, FY26: { revenue: 2600, pat: 115, opm_pct: 9 } } };
  const t = trajectory(slow)!;
  assert.equal(t.margin, "compressing");
  assert.ok(t.flags.some((f) => f.tone === "warn" && /slower than revenue/.test(f.text)));
  assert.match(t.headline, /operating margin fell from 15% to 9%/);
});
