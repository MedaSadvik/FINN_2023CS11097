import Link from "next/link";
import { requestCompany } from "@/app/actions";
import type { Panel } from "@/lib/build-state";
import { ActionForm } from "./ActionForm";
import { AutoRefresh } from "./AutoRefresh";

/** The "we have not read this company yet" area: start a build, watch it, or see why it cannot run. */
export function BuildPanel({ ticker, panel }: { ticker: string; panel: Panel }) {
  switch (panel.kind) {
    case "working":
      return (
        <div className="mt-4 rounded-lg bg-wash px-3 py-3">
          <AutoRefresh />
          <p role="status" className="font-semibold">{panel.update ? `Updating research for ${ticker}` : `Building research for ${ticker}`}</p>
          <p className="mt-1 text-ink-2">{panel.text}</p>
        </div>
      );
    case "blocked":
      return <p className="mt-4 rounded-lg bg-wash px-3 py-3 text-ink-2">{panel.text}</p>;
    case "signin":
      return (
        <div className="mt-4">
          {panel.note && <p className="mb-2 text-ink-2">{panel.note}</p>}
          <Link href="/signin" className="inline-flex min-h-11 items-center rounded-full bg-ink px-5 font-semibold text-paper">
            {panel.update ? `Sign in to update ${ticker}` : `Sign in to build ${ticker}`}
          </Link>
          <p className="mt-2 text-sm text-ink-3">Building reads the latest four earnings calls with a model. It takes a few minutes.</p>
        </div>
      );
    case "ask":
      return (
        <div className="mt-4">
          {panel.note && <p className="mb-1 text-ink-2">{panel.note}</p>}
          <ActionForm action={requestCompany} submit={panel.update ? `Update ${ticker} with the new call` : `Build research for ${ticker}`}>
            <input type="hidden" name="ticker" value={ticker} />
          </ActionForm>
          <p className="mt-2 text-sm text-ink-3">Reads the latest four earnings calls with a model. About 3 to 6 minutes. The number of builds per day is limited.</p>
        </div>
      );
    case "manual":
      return (
        <p className="mt-2 text-ink-2">
          Build it with <code className="rounded bg-wash px-1">python -m pipeline.build_company {ticker}</code>, then export it.
        </p>
      );
  }
}
