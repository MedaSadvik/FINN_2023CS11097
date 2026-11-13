import Link from "next/link";
import { Suspense } from "react";
import { connection } from "next/server";
import { cookies } from "next/headers";
import { Shell } from "@/components/Shell";
import { FeedItem } from "@/components/FeedItem";
import { AlertSettings, WindowPicker } from "@/components/FeedControls";
import { getFeed } from "@/lib/data";
import { getNetwork } from "@/lib/account";
import { PREFS_COOKIE, filingsStale, parsePrefs, pickWindow, selectFeed } from "@/lib/feed-view";
import { at, windowLabel } from "@/lib/format";
import { filingRefs, reconnectIdeas } from "@/lib/network-insights";

async function TodayBody({ searchParams }: { searchParams: PageProps<"/">["searchParams"] }) {
  const feed = getFeed();
  const { net, mode, contacts } = await getNetwork();
  const syn = mode === "demo" ? " Network is synthetic." : "";
  const banner = feed.live
    ? feed.provider && feed.provider !== "gemini"
      ? `Draft. Executive details were read by a test model, not the shipped Gemini run.${syn}`
      : mode === "demo" ? "Network is synthetic." : null
    : `Preview build. Results numbers are real. Cards marked Sample use placeholder content.${syn}`;

  let items, windowText, picker = null, warm = 0, hiddenLine: string | null = null, emptyText: string, stale: string | null = null;
  if (feed.live) {
    const [{ w }, jar] = await Promise.all([searchParams, cookies()]);
    const prefs = parsePrefs(jar.get(PREFS_COOKIE)?.value);
    const win = pickWindow(typeof w === "string" ? w : undefined, feed.snapshot.maxHours);
    const view = selectFeed(feed.snapshot, win.hours, prefs);
    items = view.items;
    await connection();
    warm = reconnectIdeas(net, filingRefs(view.items), new Date()).length;
    windowText = windowLabel(new Date(feed.snapshot.endMs - win.hours * 3_600_000).toISOString(), feed.end);
    picker = (
      <>
        <WindowPicker current={win.key} maxHours={feed.snapshot.maxHours} />
        <AlertSettings prefs={prefs} canTune={feed.snapshot.market !== null} />
      </>
    );
    const bits = [
      view.routineHidden !== null && view.routineHidden > 0 && `${view.routineHidden} routine ${view.routineHidden === 1 ? "filing" : "filings"} hidden`,
      view.hiddenByYou > 0 && `${view.hiddenByYou} hidden by your settings`,
    ].filter(Boolean);
    hiddenLine = bits.length ? bits.join(". ") + "." : null;
    emptyText = `Nothing important in the last ${win.label}.`;
    if (filingsStale(feed.snapshot) && feed.snapshot.filingsAsOfMs !== null) {
      stale = `Filings were last read ${at(new Date(feed.snapshot.filingsAsOfMs).toISOString())}. The latest refresh could not reach NSE, so newer filings are missing.`;
    }
  } else {
    items = feed.items;
    windowText = feed.note;
    emptyText = "Nothing to show yet.";
  }

  return (
    <>
      {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
      {stale && <p role="status" className="bg-wash px-4 py-2 text-sm font-medium">{stale}</p>}
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">What changed</h1>
        <p className="px-4 pt-1 text-ink-2">{windowText}</p>
        {picker}
        {warm > 0 && (
          <Link href="/network#worth-a-call" className="mx-4 mt-3 flex min-h-11 items-center justify-between rounded-lg border border-line px-3 text-[0.95rem] hover:border-ink">
            <span><span className="font-semibold">{warm} {warm === 1 ? "contact has" : "contacts have"} a reason to hear from you</span> <span className="text-ink-3">in this window</span></span>
            <span aria-hidden>›</span>
          </Link>
        )}
        {mode === "mine" && contacts === 0 && (
          <p className="mx-4 mt-4 rounded-lg bg-wash px-3 py-2 text-[0.95rem]">
            Your network is empty, so Call Sheets have no one to suggest. <Link href="/network" className="font-semibold underline underline-offset-2">Add connections or load sample contacts.</Link>
          </p>
        )}
        {items.length === 0 ? (
          <p className="px-4 pt-8 text-ink-2">{emptyText}</p>
        ) : (
          <div className="mt-4 divide-y divide-line border-y border-line">
            {items.map((it) => <FeedItem key={it.id} item={it} net={net} />)}
          </div>
        )}
        {hiddenLine && <p className="px-4 pt-4 text-sm text-ink-3">{hiddenLine}</p>}
      </main>
    </>
  );
}

export default function Today({ searchParams }: PageProps<"/">) {
  return (
    <Shell>
      <Suspense fallback={<p className="px-4 pt-6 text-ink-2">Loading…</p>}>
        <TodayBody searchParams={searchParams} />
      </Suspense>
    </Shell>
  );
}
