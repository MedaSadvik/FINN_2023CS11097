"use client";
import { useRef } from "react";

/** Button plus a bottom sheet. Content is rendered on the server and passed in as children. */
export function CallSheet({ label, title, children }: { label: string; title: string; children: React.ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button
        type="button"
        onClick={() => ref.current?.showModal()}
        className="mt-3 inline-flex min-h-11 items-center rounded-full border border-ink px-4 text-[0.95rem] font-semibold hover:bg-ink hover:text-paper"
      >
        {label}
      </button>
      <dialog
        ref={ref}
        className="sheet"
        aria-label={title}
        onClick={(e) => e.target === ref.current && ref.current?.close()}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={() => ref.current?.close()} className="min-h-11 px-2 text-ink-2 hover:text-ink">
            Close
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
      </dialog>
    </>
  );
}
