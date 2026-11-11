"use client";
import { useActionState } from "react";
import type { ActionState } from "@/app/actions";

/** A form that runs a server action and shows its one-line result. */
export function ActionForm({ action, children, submit, className }: {
  action: (prev: ActionState, f: FormData) => Promise<ActionState>;
  children: React.ReactNode;
  submit: string;
  className?: string;
}) {
  const [state, run, pending] = useActionState(action, null);
  return (
    <form action={run} className={className}>
      {children}
      <button type="submit" disabled={pending} className="mt-3 min-h-11 rounded-full bg-ink px-5 font-semibold text-paper disabled:opacity-50">
        {pending ? "Working…" : submit}
      </button>
      {state && <p role="status" className={`mt-2 text-[0.95rem] ${state.ok ? "text-ok" : "text-miss"}`}>{state.message}</p>}
    </form>
  );
}

export function Field({ label, name, type = "text", hint, required, defaultValue, list, maxLength, placeholder, autoComplete }: {
  label: string; name: string; type?: string; hint?: string; required?: boolean; defaultValue?: string | null;
  list?: string; maxLength?: number; placeholder?: string; autoComplete?: string;
}) {
  return (
    <label className="mt-3 block">
      <span className="block text-sm font-medium">{label}</span>
      <input
        name={name} type={type} required={required} defaultValue={defaultValue ?? undefined} list={list}
        maxLength={maxLength} placeholder={placeholder} autoComplete={autoComplete}
        className="mt-1 min-h-11 w-full rounded-lg border border-line bg-paper px-3 text-base outline-none focus-visible:border-ink"
      />
      {hint && <span className="mt-1 block text-sm text-ink-3">{hint}</span>}
    </label>
  );
}
