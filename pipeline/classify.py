"""Rule-based announcement classifier. No LLM, free, deterministic.

Categories follow the ENAM reference document. First matching rule wins,
so ORDER MATTERS: narrow routine-paperwork rules come first, otherwise
"ESG Rating" would be read as a credit rating.

priority: 0 hide, 1 routine (collapsed in digest), 2 notable, 3 important.
Ambiguous subjects fall to 'unclassified'; an LLM can be asked later for those.
"""
import re

# (category, regex). Regexes are matched case-insensitively against the subject.
RULES = [
    # 1. results first: "newspaper publication of results" is results, not paperwork
    ("results", r"financial results|results for the (quarter|year|half)|unaudited|"
                r"audited (financial|standalone|consolidated)|board meeting.*results|results.*board meeting|"
                r"investor presentation|earnings presentation|results presentation|shareholder.?s? letter"),
    # 2. routine paperwork that must never be mistaken for something bigger
    ("unclassified", r"\besop\b|\besos\b|\besps\b|employee stock|\besg\b|auditor|company secretary|"
                     r"compliance officer|compliance certificate|certificate under|newspaper publication|"
                     r"trading window|shareholding pattern|share certificate|duplicate share|"
                     r"scrutinizer|reconciliation of share|statement of deviation|disclosure of voting"),
    ("management_change", r"resign|cessation|appointment of|re-?appointment|change in (management|directorate)|"
                          r"retire|\bceo\b|\bcfo\b|managing director|whole.?time director|key managerial|"
                          r"senior management"),
    ("earnings_call", r"transcript|earnings? call|conference call|con\.? call|audio recording|call recording"),
    ("investor_meetings", r"investor meet|analyst meet|institutional investor|investor conference|"
                          r"one.on.one|\bconference\b"),
    ("postal_ballot", r"postal ballot"),
    ("agm_egm", r"annual general meeting|\bagm\b|extraordinary general meeting|\begm\b|e-?voting|book closure"),
    ("pledging", r"pledge|invocation|encumbrance"),
    ("insider_trading", r"insider|\(pit\)|regulation 7\(|regulation 29|sast"),
    ("credit_rating", r"credit rating|rating (assigned|reaffirm|upgrad|downgrad|action)|crisil|\bicra\b|"
                      r"care ratings|india ratings|\brating\b"),
    ("bonus_split", r"\bbonus\b|stock split|sub-?division|split of"),
    ("dividend", r"dividend|record date"),
    ("fund_raise", r"rights issue|\bqip\b|qualified institutions? placement|preferential|buy-?back|"
                   r"commercial paper|non-?convertible|\bncd\b|fund ?raising|fund raise|raising of funds|"
                   r"issuance of (equity|debentures|warrants)"),
    ("M&A", r"acqui(re|sition)|merger|amalgamation|demerger|scheme of arrangement|joint venture|\bjv\b|"
            r"subsidiary|divest|slump sale|stake (sale|purchase)|investment in"),
    ("litigation", r"litigation|\bcourt\b|tribunal|\bnclt\b|penalty|\bfine\b|show cause|sebi order|"
                   r"insolvency|winding up|adjudicat|enforcement directorate|search and seizure|"
                   r"income.tax (order|demand|notice)|gst (order|demand|notice)|regulatory action|"
                   r"notice from (sebi|nclt|nclat|court|tribunal|income|gst|cci|rbi|stock exchange|authority)|"
                   r"order (passed |issued |received )?(by|from) (sebi|nclt|nclat|the (high|supreme) court|"
                   r"high court|supreme court|tribunal|income.tax|gst|cci|rbi|authority)"),
    ("capex", r"capex|capital expenditure|new plant|manufacturing (facility|plant|unit)|capacity expansion|"
              r"greenfield|brownfield|setting up of|expansion"),
    ("press_release", r"press release|order win|bagged|secures? order|receipt of order|awarded|new product|"
                      r"product launch|launch|partnership|collaboration|clarification|\bmou\b|tie-?up|"
                      r"inaugurat|general updates?|updates?"),
]
COMPILED = [(cat, re.compile(rx, re.I)) for cat, rx in RULES]

PRIORITY = {
    "results": 3, "M&A": 3, "management_change": 3, "litigation": 3, "capex": 3,
    "fund_raise": 2, "credit_rating": 2, "dividend": 2, "bonus_split": 2, "pledging": 2,
    "press_release": 1, "insider_trading": 1, "earnings_call": 1, "agm_egm": 1,
    "postal_ballot": 1, "investor_meetings": 0, "unclassified": 0,
}


def classify(subject: str) -> tuple[str, int]:
    """Return (category, priority) for an announcement subject line."""
    text = subject or ""
    for category, rx in COMPILED:
        if rx.search(text):
            return category, PRIORITY[category]
    return "unclassified", PRIORITY["unclassified"]
