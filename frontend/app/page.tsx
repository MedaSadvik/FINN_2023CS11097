import { Shell } from "@/components/Shell";
import { FeedItem } from "@/components/FeedItem";
import { getFeed } from "@/lib/data";

export default function Today() {
  const feed = getFeed();
  const banner = feed.live
    ? feed.provider && feed.provider !== "gemini"
      ? "Draft. Executive details were read by a test model, not the shipped Gemini run. Network is synthetic."
      : "Network is synthetic."
    : "Preview build. Results numbers are real. Cards marked Sample use placeholder content. Network is synthetic.";
  return (
    <Shell banner={banner}>
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">What changed</h1>
        <p className="px-4 pt-1 text-ink-2">{feed.window}</p>
        {feed.items.length === 0 ? (
          <p className="px-4 pt-8 text-ink-2">Nothing important in the last {feed.hours} hours.</p>
        ) : (
          <div className="mt-4 divide-y divide-line border-y border-line">
            {feed.items.map((it) => <FeedItem key={it.id} item={it} />)}
          </div>
        )}
        {feed.routineHidden > 0 && (
          <p className="px-4 pt-4 text-sm text-ink-3">{feed.routineHidden} routine {feed.routineHidden === 1 ? "filing" : "filings"} hidden.</p>
        )}
      </main>
    </Shell>
  );
}
