/** What the "company not built yet" page should show, decided by plain rules (no React, easy to test). */
export type BuildStatus = {
  state: "none" | "queued" | "building" | "done" | "no_data" | "limit" | "failed" | "not_started";
  message?: string | null;
  updated_at?: string | null;
};

export type Panel =
  | { kind: "working"; text: string; update?: boolean } // a build is running: refresh the page every few seconds
  | { kind: "blocked"; text: string }                    // retrying will not help (no transcripts exist)
  | { kind: "ask"; note?: string; update?: boolean }     // signed in: show the button
  | { kind: "signin"; note?: string; update?: boolean }  // signed out: ask them to sign in first
  | { kind: "manual" };                            // builds are not switched on in this deployment

/** The database stops treating a build as running after this long, so the page must agree. */
export const STALE_MINUTES = 30;

export function panelFor(status: BuildStatus, ctx: { enabled: boolean; signedIn: boolean; now?: number }): Panel {
  if (!ctx.enabled) return { kind: "manual" };
  const running = status.state === "queued" || status.state === "building" || status.state === "done";
  if (running) {
    const age = status.updated_at ? ((ctx.now ?? Date.now()) - Date.parse(status.updated_at)) / 60000 : 0;
    if (status.state === "done" || age <= STALE_MINUTES) {
      return {
        kind: "working",
        text: status.state === "done" ? "Almost ready." : "Reading the earnings calls. This usually takes 3 to 6 minutes, and this page updates by itself.",
      };
    }
    return ctx.signedIn ? { kind: "ask", note: "The last build stopped before it finished." }
      : { kind: "signin", note: "The last build stopped before it finished." };
  }
  if (status.state === "no_data") return { kind: "blocked", text: status.message || "No earnings call transcripts were found for this company." };
  const note = status.state === "none" ? undefined : status.message ?? undefined;
  return ctx.signedIn ? { kind: "ask", note } : { kind: "signin", note };
}

/** A built company whose research is behind the newest earnings call: offer to update it, or show the update running. */
export function updatePanelFor(status: BuildStatus, ctx: { enabled: boolean; signedIn: boolean; newer: string; built: string | null; now?: number }): Panel | null {
  if (!ctx.enabled) return null;
  const age = status.updated_at ? ((ctx.now ?? Date.now()) - Date.parse(status.updated_at)) / 60000 : Infinity;
  if ((status.state === "queued" || status.state === "building") && age <= STALE_MINUTES) {
    return { kind: "working", update: true, text: `Reading the ${ctx.newer} call. This usually takes 3 to 6 minutes, and this page updates by itself.` };
  }
  const base = `A newer earnings call (${ctx.newer}) is out.` + (ctx.built ? ` This research uses calls up to ${ctx.built}.` : "");
  // a finished build is not mentioned: if it had worked, the newer call would no longer be flagged
  const why = status.state === "failed" || status.state === "limit" || status.state === "no_data" ? status.message : null;
  const note = why ? `${base} ${why}` : base;
  return ctx.signedIn ? { kind: "ask", note, update: true } : { kind: "signin", note, update: true };
}

export const TICKER_RE = /^[A-Z0-9&-]{1,20}$/;
