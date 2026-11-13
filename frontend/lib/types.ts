export type Role = { employer_key: string; employer_name?: string; title: string; start_year: number; end_year: number | null };
export type Education = { institution: string; start_year: number; end_year: number };
export type Person = {
  id: number;
  kind: "contact" | "extended";
  full_name: string;
  headline: string;
  last_spoke: string | null;
  roles: Role[];
  education: Education[];
  linked?: boolean; // a real connection (live profile), not a sample contact
};
export type Employer = { key: string; name: string; sector: string; ticker: string | null };
export type Relation = { employer_key: string; ticker: string; relation: "competitor" | "supplier" | "customer" };
export type Network = { employers: Employer[]; employer_relations: Relation[]; people: Person[] };

export type Evidence = { text: string; source: "public profile" | "their profile" | "your notes" | "NSE filing" };
export type Lead = { person: Person; reasons: Evidence[]; tier: "worked_there" | "adjacent" | "overlap" };

export type Quarter = { quarter: string; revenue: number; ebitda: number; pbt: number; pat: number };

export type Outcome = "delivered" | "partly" | "missed" | "pending" | "unclear";
export type Pledge = {
  made_in: string;
  call_month?: string;
  target: string;
  horizon: string;
  page: number;
  quote: string;
  mark: string;
  outcome: Outcome;
  result: string | null;
  reason?: string;
};

export type HistoryEntry = {
  employer: string; title: string | null; start_year: number | null; end_year: number | null; employer_key: string | null;
};
export type PersonRecord = {
  person: string; role: string | null; event: string; quote: string | null; history: HistoryEntry[];
};
export type AlertRules = { volume_multiple?: number; price_move?: number };

type Base = { id: string; ticker: string; company: string; filed: string; sample?: boolean; pdf_url?: string | null; category?: string };
export type FeedItem =
  | (Base & { type: "results"; quarter: string; cur: Quarter; qoq: Quarter; yoy: Quarter })
  | (Base & { type: "mgmt_change"; headline: string; detail?: string; person: PersonRecord | null; employer_key: string | null })
  | (Base & { type: "event"; label?: string; headline: string; detail: string; employer_key: string | null })
  | (Base & { type: "alert"; volume_x: number | null; price_pct: number | null; rules?: AlertRules; employer_key: string | null; earlier?: number });

export type Profile = { id: string; username: string; display_name: string; headline: string | null };
export type Account = { userId: string; email: string | null; profile: Profile | null };
