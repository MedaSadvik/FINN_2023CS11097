import test from "node:test";
import assert from "node:assert/strict";
import { isComplete, isKnown, searchSymbols, type SymbolList } from "./symbols";

const list: SymbolList = {
  asof: null, source: "test",
  rows: [
    ["TITAN", "Titan Company Limited"], ["TITAGARH", "Titagarh Rail Systems Limited"], ["ASIANPAINT", "Asian Paints Limited"],
    ["ASIANHOTNR", "Asian Hotels (North) Limited"], ["INFY", "Infosys Limited"], ["PERSISTENT", "Persistent Systems Limited"],
    ["TATAMOTORS", "Tata Motors Limited"], ["TCS", "Tata Consultancy Services Limited"], ["LT", "Larsen & Toubro Limited"],
    ["KAYNES", "Kaynes Technology India Limited"], ["OLAELEC", "Ola Electric Mobility Limited"],
  ],
};
const top = (q: string) => searchSymbols(list, q, 3).map((m) => m.symbol);

test("an exact symbol comes first", () => {
  assert.equal(top("titan")[0], "TITAN");
  assert.equal(top("INFY")[0], "INFY");
  assert.equal(top("lt")[0], "LT");
});

test("a company name, in full or in part, finds its symbol", () => {
  assert.equal(top("titan company")[0], "TITAN");
  assert.equal(top("asian paints")[0], "ASIANPAINT");
  assert.equal(top("asian paint")[0], "ASIANPAINT");
  assert.equal(top("larsen and toubro")[0], "LT");
  assert.equal(top("larsen & toubro")[0], "LT");
  assert.equal(top("tata consultancy")[0], "TCS");
  assert.equal(top("ola electric")[0], "OLAELEC");
});

test("a typing mistake still finds the company", () => {
  assert.equal(top("asain paint")[0], "ASIANPAINT");
  assert.equal(top("infosis")[0], "INFY");
  assert.equal(top("persistant")[0], "PERSISTENT");
  assert.equal(top("kaynes technologies")[0], "KAYNES");
});

test("a shared first word lists the candidates instead of guessing", () => {
  assert.deepEqual(top("tata").slice(0, 2).sort(), ["TATAMOTORS", "TCS"].sort());
  assert.ok(top("asian").includes("ASIANHOTNR") && top("asian").includes("ASIANPAINT"));
});

test("nonsense and empty input find nothing", () => {
  assert.deepEqual(searchSymbols(list, "qzxv"), []);
  assert.deepEqual(searchSymbols(list, "   "), []);
  assert.deepEqual(searchSymbols(list, "!!!"), []);
});

test("a short typo is not forgiven for a short word", () => {
  assert.deepEqual(searchSymbols(list, "tcz"), []);
  assert.ok(!top("tata").includes("TITAN")); // one letter off, but "tata" is too short to guess from
});

test("only a full list is allowed to say 'not found'", () => {
  assert.equal(isComplete(list), false);
  const big: SymbolList = { ...list, rows: Array.from({ length: 600 }, (_, i) => [`S${i}`, `Co ${i}`] as [string, string]) };
  assert.equal(isComplete(big), true);
  assert.equal(isKnown(big, "s7"), true);
  assert.equal(isKnown(big, "NOPE"), false);
});
