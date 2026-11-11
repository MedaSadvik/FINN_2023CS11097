import assert from "node:assert/strict";
import { test } from "node:test";
import { buildNetwork } from "./network-build";
import { callSheet, overlapWith } from "./network-core";

const employers = [
  { key: "kaynes", name: "Kaynes", sector: "semis", ticker: "KAYNES" },
  { key: "syrma", name: "Syrma SGS", sector: "semis", ticker: "SYRMA" },
  { key: "dixon", name: "Dixon", sector: "semis", ticker: "DIXON" },
];
const relations = [{ employer_key: "syrma", ticker: "KAYNES", relation: "competitor" as const }];
const net = buildNetwork({
  employers, relations,
  people: [
    { id: 1, kind: "contact", full_name: "Asha", headline: "VP at Dixon", last_spoke: "2026-05-01", profile_id: null },
    { id: 2, kind: "contact", full_name: "Bala", headline: "Head at Syrma", last_spoke: null, profile_id: "uuid-b" },
    { id: 3, kind: "extended", full_name: "Chitra", headline: "At Dixon", last_spoke: null, profile_id: null },
  ],
  roles: [
    { person_id: 1, employer_key: "kaynes", title: "Ops", start_year: 2016, end_year: 2020 },
    { person_id: 1, employer_key: "dixon", title: "VP", start_year: 2020, end_year: null },
    { person_id: 2, employer_key: "syrma", title: "Head", start_year: 2019, end_year: null },
    { person_id: 3, employer_key: "kaynes", title: "Analyst", start_year: 2017, end_year: 2019 },
    { person_id: 3, employer_key: "dixon", title: "Lead", start_year: 2019, end_year: null },
  ],
  education: [],
});

test("buildNetwork links roles to people and marks real connections", () => {
  assert.equal(net.people.length, 3);
  assert.equal(net.people[1].linked, true);
  assert.equal(net.people[0].linked, false);
  assert.equal(net.people[0].roles[0].employer_key, "dixon"); // newest first
});

test("call sheet: worked there ranks above competitor, with sources and no score", () => {
  const leads = callSheet(net, "kaynes", 5);
  assert.deepEqual(leads.map((l) => l.person.full_name), ["Asha", "Bala"]);
  assert.equal(leads[0].tier, "worked_there");
  assert.equal(leads[1].tier, "adjacent");
  assert.ok(leads[0].reasons.some((r) => r.source === "your notes"));
  assert.ok(leads[0].reasons.some((r) => /Overlapped there with 1 person/.test(r.text)));
});

test("a connection's career is tagged as their profile, sample data as public profile", () => {
  const bala = callSheet(net, "kaynes", 5).find((l) => l.person.full_name === "Bala")!;
  assert.ok(bala.reasons.every((r) => r.source === "their profile"));
  const asha = callSheet(net, "kaynes", 5).find((l) => l.person.full_name === "Asha")!;
  assert.ok(asha.reasons.filter((r) => r.source !== "your notes").every((r) => r.source === "public profile"));
});

test("extended people never appear as leads", () => {
  assert.ok(!callSheet(net, "kaynes", 5).some((l) => l.person.full_name === "Chitra"));
});

test("overlap needs shared years; unknown years are said plainly", () => {
  const hit = overlapWith(net, [{ employer: "Kaynes", title: null, start_year: 2018, end_year: 2019, employer_key: "kaynes", }]);
  assert.equal(hit.length, 1);
  const miss = overlapWith(net, [{ employer: "Kaynes", title: null, start_year: 2021, end_year: 2022, employer_key: "kaynes" }]);
  assert.equal(miss.length, 0);
  const vague = overlapWith(net, [{ employer: "Kaynes", title: null, start_year: null, end_year: null, employer_key: "kaynes" }]);
  assert.match(vague[0].reasons[0].text, /does not say when/);
  assert.equal(overlapWith(net, [{ employer: "Unknown Co", title: null, start_year: 2018, end_year: 2019, employer_key: null }]).length, 0);
});

test("empty network gives empty answers, not errors", () => {
  const empty = buildNetwork({ employers, relations, people: [], roles: [], education: [] });
  assert.deepEqual(callSheet(empty, "kaynes"), []);
});
