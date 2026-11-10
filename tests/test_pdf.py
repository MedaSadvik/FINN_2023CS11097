import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

pymupdf = pytest.importorskip("pymupdf")

import pipeline.fetch_pdf as fp


def make_pdf(path, pages):
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_extract_pages_keeps_pages_separate(tmp_path):
    p = tmp_path / "a.pdf"
    make_pdf(p, ["Revenue grew 22 percent in Q2.", "We expect margins of 14 percent."])
    pages = fp.extract_pages(p)
    assert [x["page"] for x in pages] == [1, 2]
    assert "Revenue grew 22 percent" in pages[0]["text"]
    assert "margins of 14 percent" in pages[1]["text"]
    assert "margins" not in pages[0]["text"]


def test_looks_scanned(tmp_path):
    p = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page()  # no text layer, like a scan
    doc.save(str(p))
    doc.close()
    assert fp.looks_scanned(fp.extract_pages(p)) is True
    q = tmp_path / "text.pdf"
    make_pdf(q, ["x " * 200])
    assert fp.looks_scanned(fp.extract_pages(q)) is False


class FakeResp:
    def __init__(self, body, ctype="application/pdf"):
        self.content, self.headers = body, {"content-type": ctype}

    def raise_for_status(self):
        pass


def test_download_rejects_html(monkeypatch, tmp_path):
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp(b"<html>viewer</html>", "text/html"))
    with pytest.raises(fp.NotAPdf):
        fp.download("https://example.com/AnnPdfOpen.aspx?Pname=x")


def test_download_caches_by_hash(monkeypatch, tmp_path):
    import requests
    src = tmp_path / "src.pdf"
    make_pdf(src, ["hello"])
    body = src.read_bytes()
    monkeypatch.setattr(fp, "ROOT", tmp_path / "cache")
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp(body))
    p1, h1 = fp.download("https://example.com/a")
    p2, h2 = fp.download("https://example.com/b")  # different URL, same bytes
    assert p1 == p2 and h1 == h2 and p1.exists()
