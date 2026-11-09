"""Portfolio and research universe. Single source of truth for tickers."""

# (NSE symbol, display name, sector tag matching db/schema.sql employers.sector)
PORTFOLIO = [
    ("KAYNES", "Kaynes Technology", "semis_electronics"),
    ("CGPOWER", "CG Power", "semis_electronics"),
    ("DIXON", "Dixon Technologies", "semis_electronics"),
    ("SYRMA", "Syrma SGS", "semis_electronics"),      # replaces MosChip; transcripts unchecked
    ("TEJASNET", "Tejas Networks", "semis_electronics"),
    ("NETWEB", "Netweb Technologies", "ai_cloud"),
    ("E2E", "E2E Networks", "ai_cloud"),
    ("INFY", "Infosys", "it_services"),
    ("TCS", "TCS", "it_services"),                    # replaces Tata Motors
    ("WIPRO", "Wipro", "it_services"),                # replaces Bharti Airtel
    ("HCLTECH", "HCL Tech", "it_services"),
    ("PERSISTENT", "Persistent Systems", "it_services"),
    ("TATAELXSI", "Tata Elxsi", "it_services"),
    ("SUNPHARMA", "Sun Pharma", "pharma"),
    ("HDFCBANK", "HDFC Bank", "financials"),
    ("RELIANCE", "Reliance Industries", "energy_infra"),
    ("LT", "Larsen & Toubro", "energy_infra"),
]

TICKERS = [t for t, _, _ in PORTFOLIO]


def yahoo_symbol(ticker: str, exchange: str = "NS") -> str:
    """RELIANCE -> RELIANCE.NS (NSE) or RELIANCE.BO (BSE)."""
    return f"{ticker}.{exchange}"
