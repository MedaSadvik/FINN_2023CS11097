type Series = { name: string; values: (number | null)[]; tone: "ink" | "mute" };

const W = 320, TOP = 18, PLOT = 104;

/**
 * Grouped bars per year, drawn as plain SVG: no library, scales to the screen width.
 * A negative value hangs below the zero line and is drawn in the loss colour, so "cash went out" reads at a glance.
 * Only the latest year carries a number on the bar. `under` adds a small second line beneath each year (for example margin).
 */
export function BarChart({ labels, series, under, summary, unit = "" }: { labels: string[]; series: Series[]; under?: (string | null)[]; summary: string; unit?: string }) {
  const all = series.flatMap((s) => s.values).filter((v): v is number => v !== null);
  const hi = Math.max(0, ...all), lo = Math.min(0, ...all);
  const span = hi - lo || 1;
  const y = (v: number) => TOP + ((hi - v) / span) * PLOT;
  const zero = y(0);
  const group = W / labels.length;
  const bar = Math.min(26, (group - 8) / series.length);
  const fmt = (v: number) => `${v < 0 ? "-" : ""}${Math.abs(Math.round(v)).toLocaleString("en-IN")}${unit}`;
  const LABEL = lo < 0 ? 26 : 12; // leave room under a hanging bar for its number
  const h = TOP + PLOT + LABEL + (under ? 14 : 0) + 6;
  return (
    <svg viewBox={`0 0 ${W} ${h}`} role="img" aria-label={summary} className="mt-3 block w-full">
      <line x1="0" x2={W} y1={zero} y2={zero} className="stroke-line" strokeWidth="1" />
      {labels.map((label, i) => {
        const gx = i * group + (group - bar * series.length) / 2;
        const latest = i === labels.length - 1;
        return (
          <g key={label}>
            {series.map((s, j) => {
              const v = s.values[i];
              if (v === null || v === undefined) return null;
              const top = Math.min(y(v), zero), height = Math.max(1.5, Math.abs(y(v) - zero));
              const fill = v < 0 ? "fill-miss" : s.tone === "ink" ? (latest ? "fill-ink" : "fill-ink-2") : latest ? "fill-ink-3" : "fill-ink-3/55";
              return (
                <g key={s.name}>
                  <rect x={gx + j * bar} y={top} width={bar - 2} height={height} rx="1.5" className={fill} />
                  {latest && (
                    <text x={gx + j * bar + (bar - 2) / 2} y={v < 0 ? top + height + 10 : top - 4} textAnchor="middle" className={`text-[9px] font-semibold ${v < 0 ? "fill-miss" : "fill-ink"}`}>{fmt(v)}</text>
                  )}
                </g>
              );
            })}
            <text x={i * group + group / 2} y={TOP + PLOT + LABEL} textAnchor="middle" className={`text-[9px] ${latest ? "fill-ink font-semibold" : "fill-ink-3"}`}>{label}</text>
            {under && <text x={i * group + group / 2} y={TOP + PLOT + LABEL + 12} textAnchor="middle" className="fill-ink-3 text-[9px]">{under[i] ?? ""}</text>}
          </g>
        );
      })}
    </svg>
  );
}

export function Legend({ items }: { items: { name: string; swatch: string }[] }) {
  return (
    <p className="mt-2 flex flex-wrap gap-x-4 text-sm text-ink-2">
      {items.map((i) => <span key={i.name} className="inline-flex items-center gap-1.5"><span aria-hidden className={`inline-block size-2.5 rounded-sm ${i.swatch}`} />{i.name}</span>)}
    </p>
  );
}
