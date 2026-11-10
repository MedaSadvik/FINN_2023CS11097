export type Role = { employer_key: string; title: string; start_year: number; end_year: number | null };
export type Education = { institution: string; start_year: number; end_year: number };
export type Person = {
  id: number;
  kind: "contact" | "extended";
  full_name: string;
  headline: string;
  last_spoke: string | null;
  roles: Role[];
  education: Education[];
};
export type Employer = { key: string; name: string; sector: string; ticker: string | null };
export type Relation = { employer_key: string; ticker: string; relation: "competitor" | "supplier" | "customer" };
export type Network = { employers: Employer[]; employer_relations: Relation[]; people: Person[] };

export type Evidence = { text: string; source: "public profile" | "your notes" };
export type Lead = { person: Person; reasons: Evidence[]; tier: "worked_there" | "adjacent" | "overlap" };

export type Quarter = { quarter: string; revenue: number; ebitda: number; pbt: number; pat: number };

export type Outcome = "delivered" | "partly" | "missed" | "pending" | "unclear";
export type Pledge = {
  made_in: string;
  call_month: string;
  target: string;
  horizon: string;
  page: number;
  quote: string;
  mark: string;
  outcome: Outcome;
  result: string | null;
  reason?: string;
};

export type FeedItem =
  | { id: string; type: "results"; ticker: string; company: string; priority: "high"; filed: string; quarter: string;
      cur: Quarter; qoq: Quarter; yoy: Quarter }
  | { id: string; type: "mgmt_change"; ticker: string; company: string; priority: "high"; filed: string;
      headline: string; person: string; role: string; bio: string;
      history: { employer_key: string; title: string; start_year: number; end_year: number | null }[] }
  | { id: string; type: "event"; ticker: string; company: string; priority: "medium"; filed: string;
      headline: string; detail: string; employer_key: string }
  | { id: string; type: "alert"; ticker: string; company: string; priority: "medium"; filed: string;
      trigger: string; volume_x: number; price_pct: number; employer_key: string };
