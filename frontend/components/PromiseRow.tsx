import type { Outcome, Pledge as P } from "@/lib/types";
import { SampleTag } from "./Shell";

const LABEL: Record<Outcome, { text: string; cls: string }> = {
  delivered: { text: "Delivered", cls: "text-ok" },
  partly: { text: "Partly", cls: "text-part" },
  missed: { text: "Missed", cls: "text-miss" },
  pending: { text: "Pending", cls: "text-pend" },
  unclear: { text: "Can't check yet", cls: "text-pend" },
};

function Quote({ text, mark }: { text: string; mark: string }) {
  const i = text.indexOf(mark);
  if (i < 0) return <>{text}</>;
  return <>{text.slice(0, i)}<mark>{mark}</mark>{text.slice(i + mark.length)}</>;
}

export function PromiseRow({ p, sample }: { p: P; sample?: boolean }) {
  const o = LABEL[p.outcome];
  return (
    <li className="px-4 py-5">
      <p className={`text-[0.95rem] font-bold ${o.cls}`}>{o.text}</p>
      <p className="mt-0.5 font-semibold">{p.target}</p>
      <blockquote className="quote mt-3">
        “<Quote text={p.quote} mark={p.mark} />”
      </blockquote>
      <p className="mt-1.5 flex items-center gap-2 text-sm text-ink-3">
        {sample && <SampleTag>Sample wording</SampleTag>}
        {p.made_in} call, {p.call_month}, page {p.page}
      </p>
      {(p.result || p.reason) && <p className="mt-3 text-[0.95rem]">{p.result ?? p.reason}</p>}
    </li>
  );
}
