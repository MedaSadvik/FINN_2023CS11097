import test from "node:test";
import assert from "node:assert/strict";
import { expertiseMap, filingRefs, monthsSince, reconnectIdeas, trackedFor } from "./network-insights";
import { demoNetwork } from "./network";
import type { FeedItem, Network, Person } from "./types";

const NOW = new Date("2026-11-14T10:00:00Z");
const net = (people: Person[]): Network => ({
  employers: [
    { key: "kaynes", name: "Kaynes Technology", sector: "semis_electronics", ticker: "KAYNES" },
    { key: "dixon", name: "Dixon Technologies", sector: "semis_electronics", ticker: "DIXON" },
    { key: "sunpharma", name: "Sun Pharma", sector: "pharma", ticker: "SUNPHARMA" },
    { key: "acme", name: "Acme", sector: "", ticker: null },
  ],
  employer_relations: [], people,
});
const person = (id: number, name: string, roles: Person["roles"], last: string | null, kind: Person["kind"] = "contact"): Person =>
  ({ id, kind, full_name: name, headline: "", last_spoke: last, roles, education: [] });
const role = (key: string, a: number, b: number | null, name?: string) => ({ employer_key: key, title: "Head", start_year: a, end_year: b, ...(name ? { employer_name: name } : {}) });
const results = { id: "r1", type: "results", ticker: "KAYNES", company: "Kaynes", filed: "2026-11-11T16:00:00+05:30", quarter: "Q2FY27" } as unknown as FeedItem;
const capex = { id: "c1", type: "event", ticker: "DIXON", company: "Dixon", filed: "2026-11-10T10:00:00+05:30", category: "capex", priority: 2, headline: "h", detail: "", employer_key: "dixon" } as unknown as FeedItem;
const alert = { id: "a1", type: "alert", ticker: "KAYNES", company: "Kaynes", filed: "2026-11-11", volume_x: 3, price_pct: null, employer_key: null } as FeedItem;

test("months since", () => {
  assert.equal(monthsSince("2025-09-14", NOW), 14);
  assert.equal(monthsSince(null, NOW), null);
});

test("a free-text employer is matched to the tracked company by name", () => {
  const n = net([]);
  assert.equal(trackedFor(n, role("name:kaynes", 2015, 2018, "Kaynes Technology India Pvt Ltd"))?.key, "kaynes");
  assert.equal(trackedFor(n, role("name:acme", 2015, 2018, "Acme"))?.key, undefined);
});

test("filings: alerts are not filings; results and events get plain wording", () => {
  const refs = filingRefs([results, capex, alert]);
  assert.deepEqual(refs.map((r) => r.what), ["reported Q2FY27 results", "announced a capex plan"]);
});

test("reconnect: former employer filed and the silence is long", () => {
  const n = net([person(1, "Asha", [role("kaynes", 2015, 2019)], "2025-01-10")]);
  const [idea] = reconnectIdeas(n, filingRefs([results]), NOW);
  assert.equal(idea.person.full_name, "Asha");
  assert.equal(idea.tie, "formerly");
  assert.equal(idea.silentMonths, 22);
  assert.deepEqual(idea.reasons.map((r) => r.source), ["public profile", "NSE filing", "your notes"]);
  assert.match(idea.ask, /quarter/);
});

test("reconnect: someone you spoke to recently is left alone", () => {
  const n = net([person(1, "Asha", [role("kaynes", 2015, 2019)], "2026-09-01")]);
  assert.equal(reconnectIdeas(n, filingRefs([results]), NOW).length, 0);
});

test("reconnect: no filing from their employer means no idea", () => {
  const n = net([person(1, "Asha", [role("sunpharma", 2015, 2019)], "2024-01-01")]);
  assert.equal(reconnectIdeas(n, filingRefs([results]), NOW).length, 0);
});

test("reconnect: never-logged counts as silent; wider-network people are not suggested", () => {
  const n = net([person(1, "Asha", [role("kaynes", 2015, 2019)], null), person(2, "Ravi", [role("kaynes", 2015, 2019)], "2024-01-01", "extended")]);
  const ideas = reconnectIdeas(n, filingRefs([results]), NOW);
  assert.deepEqual(ideas.map((i) => i.person.full_name), ["Asha"]);
  assert.match(ideas[0].reasons[2].text, /No conversation logged/);
});

test("reconnect ranking: still there first, then weightier filing, then longer silence; one idea per person", () => {
  const n = net([
    person(1, "Former", [role("kaynes", 2015, 2019)], "2023-01-01"),
    person(2, "Current", [role("dixon", 2020, null)], "2026-01-01"),
    person(3, "Both", [role("kaynes", 2010, 2012), role("dixon", 2015, null)], "2025-01-01"),
  ]);
  const ideas = reconnectIdeas(n, filingRefs([results, capex]), NOW);
  assert.deepEqual(ideas.map((i) => i.person.full_name), ["Both", "Current", "Former"]);
  assert.equal(ideas.filter((i) => i.person.full_name === "Both").length, 1);
  assert.equal(ideas[0].filing.ticker, "DIXON"); // the role that is current wins
});

test("reconnect honours the limit", () => {
  const ppl = Array.from({ length: 8 }, (_, i) => person(i + 1, `P${i}`, [role("kaynes", 2015, 2019)], "2023-01-01"));
  assert.equal(reconnectIdeas(net(ppl), filingRefs([results]), NOW, { limit: 3 }).length, 3);
});

test("expertise: ranked by years in the sector; one-year stints below the bar are left out; gaps are flagged", () => {
  const n = net([
    person(1, "Long", [role("kaynes", 2010, 2016), role("dixon", 2016, null)], null), // 6 + 10 = 16
    person(2, "Short", [role("kaynes", 2024, 2026)], null),                            // 2
    person(3, "Brief", [role("kaynes", 2025, 2025)], null),                            // counts 1, under the bar
    person(4, "Wider", [role("kaynes", 2000, 2020)], null, "extended"),                // not a contact
  ]);
  const map = expertiseMap(n, NOW);
  const semis = map.find((t) => t.sector === "semis_electronics")!;
  assert.deepEqual(semis.experts.map((e) => [e.person.full_name, e.years]), [["Long", 16], ["Short", 2]]);
  assert.deepEqual(semis.holdings, ["Kaynes Technology", "Dixon Technologies"]);
  assert.equal(semis.gap, false);
  assert.equal(semis.expertCount, 2);
  const pharma = map.find((t) => t.sector === "pharma")!;
  assert.equal(pharma.gap, true);
  assert.equal(map[0].sector, "pharma"); // gaps first
});

test("expertise: the count is the whole network, the list is only the top few", () => {
  const ppl = Array.from({ length: 5 }, (_, i) => person(i + 1, `P${i}`, [role("kaynes", 2010, 2016 + i)], null));
  const t = expertiseMap(net(ppl), NOW).find((x) => x.sector === "semis_electronics")!;
  assert.equal(t.expertCount, 5);
  assert.equal(t.experts.length, 3);
});

test("the synthetic demo network produces real ideas and a map", () => {
  const map = expertiseMap(demoNetwork, NOW);
  assert.ok(map.length >= 5 && map.some((t) => t.experts.length >= 2));
  const ideas = reconnectIdeas(demoNetwork, filingRefs([results, capex]), NOW);
  assert.ok(ideas.length >= 1, "the demo network overlaps the portfolio, so at least one contact has a reason");
});
