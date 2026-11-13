// Mirror of pipeline/config.py PORTFOLIO (a test keeps the two in step).
export const PORTFOLIO: { ticker: string; name: string }[] = [
  { ticker: "KAYNES", name: "Kaynes Technology" },
  { ticker: "CGPOWER", name: "CG Power" },
  { ticker: "DIXON", name: "Dixon Technologies" },
  { ticker: "SYRMA", name: "Syrma SGS" },
  { ticker: "TEJASNET", name: "Tejas Networks" },
  { ticker: "NETWEB", name: "Netweb Technologies" },
  { ticker: "E2E", name: "E2E Networks" },
  { ticker: "INFY", name: "Infosys" },
  { ticker: "TCS", name: "TCS" },
  { ticker: "WIPRO", name: "Wipro" },
  { ticker: "HCLTECH", name: "HCL Tech" },
  { ticker: "PERSISTENT", name: "Persistent Systems" },
  { ticker: "TATAELXSI", name: "Tata Elxsi" },
  { ticker: "SUNPHARMA", name: "Sun Pharma" },
  { ticker: "HDFCBANK", name: "HDFC Bank" },
  { ticker: "RELIANCE", name: "Reliance Industries" },
  { ticker: "LT", name: "Larsen & Toubro" },
];
export const nameFor = (ticker: string) => PORTFOLIO.find((p) => p.ticker === ticker.toUpperCase())?.name;
