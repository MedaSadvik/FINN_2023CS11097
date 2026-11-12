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
