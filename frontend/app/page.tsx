import Link from "next/link";
import { Suspense } from "react";
import { Shell } from "@/components/Shell";
import { FeedItem } from "@/components/FeedItem";
import { getFeed } from "@/lib/data";
import { getNetwork } from "@/lib/account";

async function TodayBody() {
  const feed = getFeed();
  const { net, mode, contacts } = await getNetwork();
  const banner = feed.live
    ? feed.provider && feed.provider !== "gemini"
      ? `Draft. Executive details were read by a test model, not the shipped Gemini run.${mode === "demo" ? " Network is synthetic." : ""}`
      : mode === "demo" ? "Network is synthetic." : null
    : `Preview build. Results numbers are real. Cards marked Sample use placeholder content.${mode === "demo" ? " Network is synthetic." : ""}`;
  return (
    <>
      {banner && <p className="bg-wash px-4 py-2 text-sm text-ink-2">{banner}</p>}
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">What changed</h1>
        <p className="px-4 pt-1 text-ink-2">{feed.window}</p>
        {mode === "mine" && contacts === 0 && (
          <p className="mx-4 mt-4 rounded-lg bg-wash px-3 py-2 text-[0.95rem]">
            Your network is empty, so Call Sheets have no one to suggest. <Link href="/network" className="font-semibold underline underline-offset-2">Add connections or load sample contacts.</Link>
          </p>
        )}
        {feed.items.length === 0 ? (
          <p className="px-4 pt-8 text-ink-2">Nothing important in the last {feed.hours} hours.</p>
        ) : (
          <div className="mt-4 divide-y divide-line border-y border-line">
            {feed.items.map((it) => <FeedItem key={it.id} item={it} net={net} />)}
          </div>
        )}
        {feed.routineHidden > 0 && (
          <p className="px-4 pt-4 text-sm text-ink-3">{feed.routineHidden} routine {feed.routineHidden === 1 ? "filing" : "filings"} hidden.</p>
        )}
      </main>
    </>
  );
}

export default function Today() {
  return (
    <Shell>
      <Suspense fallback={<p className="px-4 pt-6 text-ink-2">Loading…</p>}>
        <TodayBody />
      </Suspense>
    </Shell>
  );
}
