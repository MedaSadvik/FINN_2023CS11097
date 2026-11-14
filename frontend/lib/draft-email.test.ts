import test from "node:test";
import assert from "node:assert/strict";
import { buildNetwork } from "./network-build";
import { draftEmail, firstName, mailtoHref } from "./draft-email";

const net = buildNetwork({
  employers: [
    { key: "kaynes", name: "Kaynes Technology", sector: "semis", ticker: "KAYNES" },
    { key: "syrma", name: "Syrma SGS", sector: "semis", ticker: "SYRMA" },
  ],
  relations: [{ employer_key: "syrma", ticker: "KAYNES", relation: "competitor" }],
  people: [
    { id: 1, kind: "contact", full_name: "Dr. Asha Rao", headline: "VP", last_spoke: "2026-01-10", profile_id: null },
    { id: 2, kind: "contact", full_name: "Bala", headline: "Head", last_spoke: null, profile_id: null },
    { id: 3, kind: "contact", full_name: "Chitra Nair", headline: "Analyst", last_spoke: "2026-10-20", profile_id: null },
  ],
  roles: [
    { person_id: 1, employer_key: "kaynes", title: "Operations Head", start_year: 2016, end_year: 2020 },
    { person_id: 2, employer_key: "syrma", title: "Head of Sales", start_year: 2019, end_year: null },
  ],
  education: [],
});
const now = new Date("2026-11-15T00:00:00Z");
const [asha, bala, chitra] = net.people;

test("first name skips a title", () => {
  assert.equal(firstName("Dr. Asha Rao"), "Asha");
  assert.equal(firstName("Bala"), "Bala");
});

test("a former employee is reminded of their role and the silence is named", () => {
  const d = draftEmail(net, asha, { about: "KAYNES", me: "Priya", now });
  assert.equal(d.subject, "Kaynes Technology: a quick question");
  assert.match(d.body, /^Hi Asha,/);
  assert.match(d.body, /Operations Head there from 2016 to 2020/);
  assert.match(d.body, /last spoke, around Jan 2026/);
  assert.match(d.body, /Best,\nPriya$/);
});

test("a competitor's employee gets the role they had, with no invented tie to the company", () => {
  const d = draftEmail(net, bala, { about: "KAYNES", now });
  assert.match(d.body, /your time as Head of Sales at Syrma SGS/);
  assert.match(d.body, /\[Your name\]/);
  assert.doesNotMatch(d.body, /last spoke/);
});

test("no tie at all: only the company is named, nothing is claimed", () => {
  const d = draftEmail(net, chitra, { about: "KAYNES", now });
  assert.match(d.body, /I am reading up on Kaynes Technology\.\n/);
  assert.doesNotMatch(d.body, /remembered/);
  assert.doesNotMatch(d.body, /while since/); // spoke 3 weeks ago
});

test("without a company it is a plain catch-up", () => {
  const d = draftEmail(net, asha, { now });
  assert.equal(d.subject, "Catching up");
  assert.doesNotMatch(d.body, /reading up/);
  const unknown = draftEmail(net, asha, { about: "NOPE", now });
  assert.equal(unknown.subject, "Catching up");
});

test("the mailto link carries the whole draft and no address", () => {
  const d = draftEmail(net, asha, { about: "KAYNES", now });
  const h = mailtoHref(d);
  assert.ok(h.startsWith("mailto:?subject="));
  const body = new URLSearchParams(h.slice("mailto:?".length)).get("body");
  assert.equal(body, d.body);
});
