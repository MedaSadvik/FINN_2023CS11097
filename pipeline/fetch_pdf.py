"""Download a transcript or annual report PDF and extract its text, page by page.

    python -m pipeline.fetch_pdf KAYNES Q1FY27        # concall transcript for that quarter
    python -m pipeline.fetch_pdf KAYNES AR2026        # annual report for that year

Needs the links from `python -m pipeline.fetch_docs KAYNES` first.
Output: data/cache/pdf/<sha256>.pdf and data/cache/text/<TICKER>_<WHAT>.json
Pages are kept separate on purpose: every claim FINN makes later cites a page, and
code checks the quoted text really appears on that page.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "cache"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MIN_CHARS_PER_PAGE = 100  # below this on average, the PDF is probably a scan (no text layer)


class NotAPdf(Exception):
    pass


def download(url: str, referer: str = "https://www.screener.in/") -> tuple:
    """Return (path, sha256). Cached by content hash, so the same file is never processed twice."""
    import requests
    r = requests.get(url, headers={"User-Agent": UA, "Referer": referer}, timeout=60, allow_redirects=True)
    r.raise_for_status()
    body = r.content
    if not body.startswith(b"%PDF"):  # exchange viewer pages return HTML, not the file
        raise NotAPdf(f"{url[:80]} returned {r.headers.get('content-type')} ({len(body)} bytes), "
                      f"starts with {body[:40]!r}")
    digest = hashlib.sha256(body).hexdigest()
    path = ROOT / "pdf" / f"{digest}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(body)
    return path, digest


def extract_pages(path) -> list:
    """Return [{'page': 1, 'text': '...'}, ...] (1-based pages)."""
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        return [{"page": i, "text": page.get_text("text")} for i, page in enumerate(doc, 1)]


def looks_scanned(pages: list) -> bool:
    if not pages:
        return True
    return sum(len(p["text"].strip()) for p in pages) / len(pages) < MIN_CHARS_PER_PAGE


def find_link(ticker: str, what: str) -> str:
    docs = json.loads((ROOT / "docs" / f"{ticker}.json").read_text())
    if what.upper().startswith("AR"):
        year = int(what[2:])
        hits = [a["url"] for a in docs["annual_reports"] if a["year"] == year]
    else:
        hits = [t["url"] for t in docs["transcripts"] if t["period"] == what.upper()]
    if not hits:
        raise SystemExit(f"no link for {ticker} {what}; run: python -m pipeline.fetch_docs {ticker}")
    return hits[0]  # screener lists newest first; first hit wins


def ensure_text(ticker: str, what: str, url: str) -> dict:
    """Download + extract once; later calls read the saved text. Returns the saved document dict."""
    out = ROOT / "text" / f"{ticker}_{what.upper()}.json"
    if out.exists():
        return json.loads(out.read_text())
    path, digest = download(url)
    doc = {"ticker": ticker, "what": what, "sha256": digest, "url": url, "pages": extract_pages(path)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc))
    return doc


def main(ticker: str, what: str):
    url = find_link(ticker, what)
    print("downloading", url[:100])
    path, digest = download(url)
    pages = extract_pages(path)
    total = sum(len(p["text"]) for p in pages)
    out = ROOT / "text" / f"{ticker}_{what.upper()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"ticker": ticker, "what": what, "sha256": digest, "url": url, "pages": pages}))
    print(f"{len(pages)} pages, {total:,} characters, scanned={looks_scanned(pages)}")
    print("--- page 1 (first 400 chars) ---")
    print(pages[0]["text"][:400] if pages else "(empty)")
    print(f"saved {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m pipeline.fetch_pdf TICKER Q1FY27|AR2026")
    main(sys.argv[1].upper(), sys.argv[2])
