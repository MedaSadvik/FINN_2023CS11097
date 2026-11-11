"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/**
 * Button plus a bottom sheet (centred on wide screens).
 * Built from plain elements in a portal on <body>, not <dialog>, so it behaves the same in every browser:
 * the page behind is locked, and only the sheet's own body scrolls.
 * Content is rendered on the server and passed in as children.
 */
export function CallSheet({ label, title, children }: { label: string; title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const { body, documentElement: html } = document;
    const prev = [body.style.overflow, html.style.overflow];
    body.style.overflow = html.style.overflow = "hidden";
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    const opener = trigger.current;
    return () => {
      [body.style.overflow, html.style.overflow] = prev;
      window.removeEventListener("keydown", onKey);
      opener?.focus();
    };
  }, [open]);

  return (
    <>
      <button
        ref={trigger}
        type="button"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
        className="mt-3 inline-flex min-h-11 items-center rounded-full border border-ink px-4 text-[0.95rem] font-semibold hover:bg-ink hover:text-paper"
      >
        {label}
      </button>
      {open &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 sm:items-center"
            style={{ overscrollBehavior: "contain", touchAction: "none" }}
            onClick={(e) => e.target === e.currentTarget && setOpen(false)}
          >
            <div
              ref={panel}
              role="dialog"
              aria-modal="true"
              aria-label={title}
              tabIndex={-1}
              className="flex w-full max-w-[34rem] flex-col overflow-hidden rounded-t-[1.25rem] bg-paper text-ink outline-none sm:rounded-[1.25rem]"
              style={{ maxHeight: "min(85vh, 40rem)" }}
            >
              <div className="flex flex-none items-center justify-between border-b border-line px-5 py-3">
                <h2 className="text-lg font-bold">{title}</h2>
                <button type="button" onClick={() => setOpen(false)} className="min-h-11 px-2 text-ink-2 hover:text-ink">
                  Close
                </button>
              </div>
              <div
                className="min-h-0 flex-1 overflow-y-auto px-5 py-4"
                style={{ overscrollBehavior: "contain", touchAction: "pan-y", WebkitOverflowScrolling: "touch" }}
              >
                {children}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
