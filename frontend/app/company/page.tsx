import { Suspense } from "react";
import { Shell } from "@/components/Shell";
import { CompanyPicker } from "@/components/CompanyPicker";
import { getCompany } from "@/lib/data";
import { liveCompanies } from "@/lib/live";
import { PORTFOLIO } from "@/lib/portfolio";

const base = PORTFOLIO.map((p) => ({ ...p, promises: getCompany(p.ticker)?.promises.length ?? null }));

async function Picker() {
  const mine = new Set(base.map((r) => r.ticker));
  const extra = (await liveCompanies()).filter((r) => !mine.has(r.ticker) && !getCompany(r.ticker));
  return <CompanyPicker rows={[...base, ...extra]} />;
}

export default function Research() {
  return (
    <Shell>
      <main>
        <h1 className="px-4 pt-6 text-[1.7rem] leading-tight font-bold tracking-tight">Research</h1>
        <p className="px-4 pt-1 pb-4 text-ink-2">What management promised on earnings calls, and whether it happened.</p>
        <Suspense fallback={<CompanyPicker rows={base} />}><Picker /></Suspense>
      </main>
    </Shell>
  );
}
