import type { Lead } from "@/lib/types";
import { PersonLink } from "./PersonLink";

export function LeadList({ leads, empty, about }: { leads: Lead[]; empty: string; about?: string | null }) {
  if (!leads.length) return <p className="text-ink-2">{empty}</p>;
  return (
    <ul className="divide-y divide-line">
      {leads.map((l) => (
        <li key={l.person.id} className="py-4 first:pt-0">
          <p><PersonLink id={l.person.id} name={l.person.full_name} about={about} /></p>
          <p className="text-sm text-ink-2">{l.person.headline}</p>
          <ul className="mt-2 space-y-1.5">
            {l.reasons.map((r, i) => (
              <li key={i} className="text-[0.95rem] leading-snug">
                {r.text}{" "}
                <span className={r.source === "your notes" ? "text-sm text-ink-3 italic" : "text-sm text-ink-3"}>
                  ({r.source})
                </span>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}
