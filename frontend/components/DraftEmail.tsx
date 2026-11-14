"use client";
import { useRef, useState } from "react";

const mailto = (subject: string, body: string) => `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

/**
 * A button that opens a first draft the investor can edit, then open in their own mail app or copy.
 * Nothing is sent from here, and the text never goes to a model.
 */
export function DraftEmail({ name, subject: s0, body: b0 }: { name: string; subject: string; body: string }) {
  const [open, setOpen] = useState(false);
  const [subject, setSubject] = useState(s0);
  const [body, setBody] = useState(b0);
  const [copied, setCopied] = useState(false);
  const area = useRef<HTMLTextAreaElement>(null);

  async function copy() {
    const text = `Subject: ${subject}\n\n${body}`;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      area.current?.select(); // older browsers: select the text so the person can copy it themselves
      return;
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mt-4">
      <button type="button" aria-expanded={open} aria-controls="draft-email" onClick={() => setOpen((o) => !o)}
        className="inline-flex min-h-11 items-center rounded-full bg-ink px-5 font-semibold text-paper">
        {open ? "Hide draft" : "Draft an email"}
      </button>
      {open && (
        <div id="draft-email" className="mt-3 rounded-lg border border-line p-3">
          <label className="block text-sm text-ink-3" htmlFor="draft-subject">Subject</label>
          <input id="draft-subject" value={subject} onChange={(e) => setSubject(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-line bg-paper px-3 text-[1rem]" />
          <label className="mt-3 block text-sm text-ink-3" htmlFor="draft-body">Message</label>
          <textarea id="draft-body" ref={area} value={body} onChange={(e) => setBody(e.target.value)} rows={12}
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 text-[1rem] leading-snug" />
          <div className="mt-3 flex flex-wrap gap-2">
            <a href={mailto(subject, body)} className="inline-flex min-h-11 items-center rounded-full bg-ink px-5 font-semibold text-paper">Open in mail app</a>
            <button type="button" onClick={copy} className="min-h-11 rounded-full border border-line px-5 font-semibold text-ink-2 hover:border-ink hover:text-ink">
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p className="mt-2 text-sm text-ink-3" role="status">
            Add {name.split(" ")[0]}&rsquo;s address in your mail app. FINN does not hold it, and nothing is sent from here.
          </p>
        </div>
      )}
    </div>
  );
}
