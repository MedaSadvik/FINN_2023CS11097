import { Shell } from "@/components/Shell";
import { FeedItem } from "@/components/FeedItem";
import { getFeed } from "@/lib/data";

export default function Today() {
  const { window, items } = getFeed();
  return (
    <Shell banner="Preview build. Results numbers are real. Cards marked Sample use placeholder content. Network is synthetic.">
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">What changed</h1>
        <p className="px-4 pt-1 text-ink-2">{window}</p>
        <div className="mt-4 divide-y divide-line border-y border-line">
          {items.map((it) => <FeedItem key={it.id} item={it} />)}
        </div>
      </main>
    </Shell>
  );
}
