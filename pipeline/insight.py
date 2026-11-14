"""Business snapshot and bull vs bear, from the LATEST concall only. One model request per company.

    python -m pipeline.insight KAYNES

Every line shown to the user carries a verbatim quote from the transcript and its page number.
Anything whose quote is not really on that page is dropped, and a number in a point must appear
in its quote. So the model can choose and phrase, but it cannot invent evidence.
"""
import json
import re
import sys
from pathlib import Path

from pipeline import guidance, llm
from pipeline.delivered import period_key

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"
VERSION = "insight-v1"
MAX_PAGES = 12
MAX_SEGMENTS, MAX_POINTS = 5, 3
OPENING_PAGES = 3      # prepared remarks usually describe the business
SIGNALS = ["demand", "order", "margin", "growth", "guidance", "capex", "capacity", "customer", "pipeline",
           "headwind", "challenge", "pressure", "delay", "risk", "concern", "competition", "working capital",
           "debt", "slow", "decline", "outlook"]

SYSTEM = """You read pages of ONE earnings-call transcript and summarise the company for an investor.
Use ONLY the pages given. Never use outside knowledge.

Return JSON:
{"business": {"summary": "<one sentence, under 30 words, what the company does and how it earns>",
              "segments": [{"name": "<segment or business line>", "page": n, "quote": "<verbatim>"}]},
 "bull": [{"point": "<under 20 words>", "page": n, "quote": "<verbatim>"}],
 "bear": [{"point": "<under 20 words>", "page": n, "quote": "<verbatim>"}]}

Rules:
- 3 bull points: reasons the story could work, from management's statements of demand, wins, margins, capacity.
- 3 bear points: risks, delays, pressure on margins or cash, dependence on a customer, or doubts raised by analysts
  and not fully answered. Use management's or analysts' own words; never invent a risk.
- Each quote is ONE exact passage copied from a single page, 40-300 characters.
- A number in `point` must also appear in its quote.
- Fewer items are better than weak ones. Up to 5 segments."""


def latest_transcript(ticker: str):
    best = None
    for path in (ROOT / "text").glob(f"{ticker}_*.json"):
        period = path.stem[len(ticker) + 1:]
        k = period_key(period)
        if k and (best is None or k > best[0]):
            best = (k, period, path)
    return best


def pick_pages(pages: list, limit: int = MAX_PAGES) -> list:
    """The opening pages, plus the pages that talk most about demand, margins and risks."""
    head = pages[:OPENING_PAGES]
    rest = []
    for p in pages[OPENING_PAGES:]:
        text = p["text"].lower()
        rest.append((sum(text.count(s) for s in SIGNALS), p))
    best = [p for score, p in sorted(rest, key=lambda s: -s[0])[:max(0, limit - len(head))] if score]
    return sorted(head + best, key=lambda p: p["page"])


def _numbers(text: str) -> set:
    return {float(t) for t in re.findall(r"\d+(?:\.\d+)?", (text or "").replace(",", ""))}


def verified(item: dict, pages: list, need_numbers: bool):
    """{'page','quote'} when the quote is really on a page (and its numbers are in the quote), else None."""
    if not isinstance(item, dict):
        return None
    quote = item.get("quote") or ""
    kept, _ = guidance.verify_claims([{"quote": quote, "page": item.get("page")}], pages)
    if not kept:
        return None
    if need_numbers and not _numbers(item.get("point")) <= _numbers(quote):
        return None
    return {"page": kept[0]["page"], "quote": " ".join(quote.split())}


def check(data: dict, pages: list) -> dict:
    data = data if isinstance(data, dict) else {}
    biz = data.get("business") if isinstance(data.get("business"), dict) else {}
    segments, seen = [], set()
    for s in biz.get("segments") or []:
        v = verified(s, pages, False)
        name = str(s.get("name") or "").strip() if isinstance(s, dict) else ""
        if v and name and name.lower() not in seen and len(segments) < MAX_SEGMENTS:
            seen.add(name.lower())
            segments.append({"name": name, **v})
    summary = str(biz.get("summary") or "").strip() if segments else ""
    out = {"business": {"summary": summary, "segments": segments}}
    for side in ("bull", "bear"):
        items, quotes = [], set()
        for it in data.get(side) or []:
            v, point = verified(it, pages, True), str(it.get("point") or "").strip() if isinstance(it, dict) else ""
            if v and point and guidance.squash(v["quote"]) not in quotes and len(items) < MAX_POINTS:
                quotes.add(guidance.squash(v["quote"]))
                items.append({"point": point, **v})
        out[side] = items
    return out


def build(ticker: str, call=None):
    """The snapshot dict for the company's latest call, or None when there is no transcript."""
    latest = latest_transcript(ticker)
    if not latest:
        return None
    _, period, path = latest
    doc = json.loads(path.read_text())
    pages = pick_pages(doc["pages"])
    kwargs = {"call": call} if call else {}
    prompt = "\n\n".join(f"[PAGE {p['page']}]\n{p['text'].strip()}" for p in pages)
    data = llm.generate_json(llm.flash_model(), SYSTEM, prompt, VERSION, **kwargs)
    out = check(data, pages)
    out.update(period=period, source_sha256=doc.get("sha256"), provider=llm.provider(), prompt_version=VERSION)
    return out


def main(ticker: str):
    out = build(ticker)
    if out is None:
        raise SystemExit(f"{ticker}: no transcript in the cache; run build_company first")
    path = ROOT / llm.derived("insight") / f"{ticker}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    print(f"{ticker} {out['period']}: {len(out['business']['segments'])} segments, "
          f"{len(out['bull'])} bull, {len(out['bear'])} bear -> {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m pipeline.insight TICKER")
    main(sys.argv[1].upper())
