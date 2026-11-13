import Link from "next/link";
import { Suspense } from "react";
import { cookies } from "next/headers";
import { Shell } from "@/components/Shell";
import { FeedItem } from "@/components/FeedItem";
import { AlertSettings, WindowPicker } from "@/components/FeedControls";
import { getFeed } from "@/lib/data";
import { getNetwork } from "@/lib/account";
import { PREFS_COOKIE, parsePrefs, pickWindow, selectFeed } from "@/lib/feed-view";
import { windowLabel } from "@/lib/format";

async function TodayBody({ searchParams }: { searchParams: PageProps<"/">["searchParams"] }) {
  const feed = getFeed();
  const { net, mode, contacts } = await getNetwork();
  const syn = mode === "demo" ? " Network is synthetic." : "";
  const banner = feed.live
    ? feed.provider && feed.provider !== "gemini"
      ? `Draft. Executive details were read by a test model, not the shipped Gemini run.${syn}`
      : mode === "demo" ? "Network is synthetic." : null
    : `Preview build. Results numbers are real. Cards marked Sample use placeholder content.${syn}`;

  let items, windowText, picker = null, hiddenLine: string | null = null, emptyText: string;
  if (feed.live) {
    const [{ w }, jar] = await Promise.all([searchParams, cookies()]);
    const prefs = parsePrefs(jar.get(PREFS_COOKIE)?.value);
    const win = pickWindow(typeof w === "string" ? w : undefined, feed.snapshot.maxHours);
    const view = selectFeed(feed.snapshot, win.hours, prefs);
    items = view.items;
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
  } else {
    items = feed.items;
    windowText = feed.note;
    emptyText = "Nothing to show yet.";
  }

  return (
    <>
      {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">What changed</h1>
        <p className="px-4 pt-1 text-ink-2">{windowText}</p>
        {picker}
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
