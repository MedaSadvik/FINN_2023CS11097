import { ActionForm } from "@/components/ActionForm";
import { setLastSpoke } from "@/app/actions";
import { monthValue } from "@/lib/last-spoke";

/** Lets a signed-in investor record, or clear, the month they last spoke to this contact. Private to them. */
export function LastSpoke({ personId, current, max }: { personId: number; current: string | null; max: string }) {
  return (
    <ActionForm action={setLastSpoke} submit="Save" className="mt-2">
      <input type="hidden" name="person_id" value={personId} />
      <label className="block">
        <span className="block text-sm font-medium">Last spoke</span>
        <input type="month" name="month" defaultValue={monthValue(current)} min="1990-01" max={max}
          className="mt-1 min-h-11 w-full rounded-lg border border-line bg-paper px-3 text-base outline-none focus-visible:border-ink" />
        <span className="mt-1 block text-sm text-ink-3">Only you can see this. Leave it blank to clear it.</span>
      </label>
    </ActionForm>
  );
}
