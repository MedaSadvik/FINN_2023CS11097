import { Shell } from "@/components/Shell";
import { CompanyPicker } from "@/components/CompanyPicker";
import { getCompany } from "@/lib/data";
import { PORTFOLIO } from "@/lib/portfolio";

export default function Research() {
  const rows = PORTFOLIO.map((p) => ({ ...p, promises: getCompany(p.ticker)?.promises.length ?? null }));
  return (
    <Shell>
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">Research</h1>
        <p className="px-4 pt-1 pb-4 text-ink-2">What management promised on earnings calls, and whether it happened.</p>
        <CompanyPicker rows={rows} />
      </main>
    </Shell>
  );
}
