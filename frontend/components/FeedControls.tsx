import Link from "next/link";
import { ActionForm } from "@/components/ActionForm";
import { resetPrefs, savePrefs } from "@/app/actions";
import { CATEGORIES, MOVE_CHOICES, VOLUME_CHOICES, windowChoices, type Prefs } from "@/lib/feed-view";

const select = "mt-1 min-h-11 w-full rounded-lg border border-line bg-paper px-3 text-base outline-none focus-visible:border-ink";

/** Pick the period. Plain links, so it works without script and the choice can be shared as a URL. */
export function WindowPicker({ current, maxHours }: { current: string; maxHours: number }) {
  return (
    <nav aria-label="Time window" className="flex gap-2 px-4 pt-3">
      {windowChoices(maxHours).map((w) => (
        <Link
          key={w.key} href={w.key === current ? "/" : `/?w=${w.key}`} replace
          aria-current={w.key === current ? "true" : undefined}
          className={`flex min-h-11 flex-1 items-center justify-center rounded-full border text-[0.95rem] ${
            w.key === current ? "border-ink bg-ink font-semibold text-paper" : "border-line text-ink-2 hover:border-ink hover:text-ink"
          }`}
        >
          {w.label}
        </Link>
      ))}
    </nav>
  );
}

/** What counts as unusual, and which filing types to show. */
export function AlertSettings({ prefs, canTune }: { prefs: Prefs; canTune: boolean }) {
  const custom = prefs.volume !== 2 || prefs.move !== 5 || prefs.off.length > 0;
  const summary = [
    prefs.volume ? `volume ${prefs.volume}×` : "volume off",
    prefs.move ? `price ±${prefs.move}%` : "price off",
    prefs.off.length ? `${prefs.off.length} type${prefs.off.length === 1 ? "" : "s"} hidden` : null,
  ].filter(Boolean).join(", ");
  return (
    <details className="group mx-4 mt-3 rounded-lg border border-line">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-3 text-[0.95rem]">
        <span className="py-1.5">
          <span className="block font-semibold">What counts as unusual</span>
          <span className="block text-sm text-ink-3">{summary}</span>
        </span>
        <span aria-hidden className="text-ink-3 group-open:rotate-180">⌄</span>
      </summary>
      <div className="border-t border-line px-3 pb-3">
        <ActionForm action={savePrefs} submit="Save">
          {canTune ? (
            <div className="grid grid-cols-2 gap-3">
              <label className="mt-3 block">
                <span className="block text-sm font-medium">Volume above</span>
                <select name="volume" defaultValue={prefs.volume ?? "off"} className={select}>
                  {VOLUME_CHOICES.map((v) => <option key={v} value={v}>{v}× average</option>)}
                  <option value="off">Off</option>
                </select>
              </label>
              <label className="mt-3 block">
                <span className="block text-sm font-medium">Price move in a day</span>
                <select name="move" defaultValue={prefs.move ?? "off"} className={select}>
                  {MOVE_CHOICES.map((v) => <option key={v} value={v}>±{v}%</option>)}
                  <option value="off">Off</option>
                </select>
              </label>
            </div>
          ) : (
            <p className="mt-3 text-sm text-ink-3">Price and volume alerts are fixed in this build of the feed.</p>
          )}
          <fieldset className="mt-4">
            <legend className="text-sm font-medium">Show these filings</legend>
            <div className="mt-1 grid grid-cols-2 gap-x-3">
              {CATEGORIES.map((c) => (
                <label key={c.key} className="flex min-h-11 items-center gap-2 text-[0.95rem]">
                  <input type="checkbox" name="show" value={c.key} defaultChecked={!prefs.off.includes(c.key)} className="size-5 accent-ink" />
                  {c.label}
                </label>
              ))}
            </div>
          </fieldset>
        </ActionForm>
        {custom && (
          <form action={resetPrefs}>
            <button type="submit" className="mt-2 min-h-11 text-sm text-ink-2 underline underline-offset-2 hover:text-ink">Back to defaults</button>
          </form>
        )}
        <p className="mt-1 text-sm text-ink-3">Saved on this device.</p>
      </div>
    </details>
  );
}
