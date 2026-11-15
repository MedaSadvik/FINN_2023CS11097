import { test } from "node:test";
import assert from "node:assert/strict";
import { panelFor } from "./build-state";

const on = { enabled: true, signedIn: true, now: Date.parse("2026-11-12T10:00:00Z") };

test("builds switched off: show the manual command", () => {
  assert.equal(panelFor({ state: "none" }, { ...on, enabled: false }).kind, "manual");
});
test("a fresh build shows progress to everyone, signed in or not", () => {
  const s = { state: "building" as const, updated_at: "2026-11-12T09:58:00Z" };
  assert.equal(panelFor(s, on).kind, "working");
  assert.equal(panelFor(s, { ...on, signedIn: false }).kind, "working");
});
test("a build that stopped updating is treated as stopped, matching the database", () => {
  const s = { state: "building" as const, updated_at: "2026-11-12T09:00:00Z" };
  assert.equal(panelFor(s, on).kind, "ask");
  assert.equal(panelFor(s, { ...on, signedIn: false }).kind, "signin");
});
test("no transcripts: nothing to retry", () => {
  const p = panelFor({ state: "no_data", message: "No transcripts." }, on);
  assert.deepEqual(p, { kind: "blocked", text: "No transcripts." });
});
test("limit and failure explain themselves and allow another try", () => {
  const p = panelFor({ state: "limit", message: "API limit reached for today. Try again later." }, on);
  assert.deepEqual(p, { kind: "ask", note: "API limit reached for today. Try again later." });
});
test("never asked before: plain button, or sign-in when signed out", () => {
  assert.deepEqual(panelFor({ state: "none" }, on), { kind: "ask", note: undefined });
  assert.equal(panelFor({ state: "none" }, { ...on, signedIn: false }).kind, "signin");
});

import { updatePanelFor } from "./build-state";

const stale = { enabled: true, signedIn: true, newer: "Q2FY27", built: "Q1FY27" };

test("a company behind the newest call offers an update, with the same warnings as a first build", () => {
  const p = updatePanelFor({ state: "done", updated_at: "2026-11-01T00:00:00Z" }, stale);
  assert.equal(p?.kind, "ask");
  assert.equal(p?.kind === "ask" && p.update, true);
  assert.match(p?.kind === "ask" ? p.note ?? "" : "", /newer earnings call \(Q2FY27\).*up to Q1FY27/);
});

test("signed-out visitors are asked to sign in; nothing is offered when builds are off", () => {
  assert.equal(updatePanelFor({ state: "none" }, { ...stale, signedIn: false })?.kind, "signin");
  assert.equal(updatePanelFor({ state: "none" }, { ...stale, enabled: false }), null);
});

test("an update that is running shows progress, and a stuck one offers the button again", () => {
  const now = Date.parse("2026-11-16T10:00:00Z");
  assert.equal(updatePanelFor({ state: "building", updated_at: "2026-11-16T09:55:00Z" }, { ...stale, now })?.kind, "working");
  assert.equal(updatePanelFor({ state: "building", updated_at: "2026-11-16T08:00:00Z" }, { ...stale, now })?.kind, "ask");
});

test("a failed or limited update says why and lets them try again", () => {
  const p = updatePanelFor({ state: "limit", message: "API limit reached for today. Try again later.", updated_at: "2026-11-16T09:00:00Z" }, stale);
  assert.equal(p?.kind, "ask");
  assert.match(p?.kind === "ask" ? p.note ?? "" : "", /API limit reached/);
});
