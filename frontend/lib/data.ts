import kaynes from "@/data/kaynes.json";
import feed from "@/data/feed.json";
import type { FeedItem, Pledge, Quarter } from "./types";

export type CompanyData = { ticker: string; employer_key: string; name: string; quarters: Quarter[]; promises: Pledge[] };
const companies: Record<string, CompanyData> = { KAYNES: kaynes as unknown as CompanyData };

export const getCompany = (t: string) => companies[t.toUpperCase()];
export const getFeed = () => ({ window: feed.window, items: feed.items as unknown as FeedItem[] });
export const knownTickers = () => Object.keys(companies);
