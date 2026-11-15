"""Build docs/FINN_User_Guide.pdf from docs/USER_GUIDE.md and docs/guide/img/*.png.

    python3 tools/guide/build_pdf.py

The Markdown file is the single source. Rules it must follow:
  ## Section          starts a new page
  ### N. Step title   one step; the paragraphs and ![](img) lines under it belong to it
Text before a step in a section (lists, notes) is printed once above that section's steps.
Needs: pip install markdown playwright (and `playwright install chromium`).
"""
import html
import re
import sys
import tempfile
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parent.parent.parent / "docs"
SRC = DOCS / "USER_GUIDE.md"
OUT = DOCS / "FINN_User_Guide.pdf"
STEPS_PER_PAGE = 2
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def md(text: str) -> str:
    return markdown.markdown(text, extensions=["tables"])


def parse(text: str) -> dict:
    """{'note': str, 'sections': [{'title', 'intro', 'steps': [{'title', 'body', 'images'}]}]}"""
    pre, *chunks = re.split(r"^## ", text, flags=re.M)
    note = "\n".join(l[2:] for l in pre.splitlines() if l.startswith("> "))
    sections = []
    for ch in chunks:
        title, _, rest = ch.partition("\n")
        rest = rest.replace("\n---\n", "\n").strip()
        intro, *steps = re.split(r"^### ", rest, flags=re.M)
        out = []
        for s in steps:
            st, _, body = s.partition("\n")
            images = IMG.findall(body)
            out.append({"title": st.strip(), "body": IMG.sub("", body).strip(), "images": images})
        sections.append({"title": title.strip(), "intro": intro.strip(), "steps": out})
    return {"note": note, "sections": sections}


def step_html(s: dict) -> str:
    imgs = "".join(f'<figure><img src="{(DOCS / src).as_uri()}" alt="{html.escape(alt)}"></figure>' for alt, src in s["images"])
    return f'<div class="step n{len(s["images"])}"><div class="shots">{imgs}</div><div class="words"><h3>{html.escape(s["title"])}</h3>{md(s["body"])}</div></div>'


def build_html(doc: dict) -> str:
    # The intro section ("What FINN is") has no steps: it rides on the cover page.
    cover_sec = [s for s in doc["sections"] if not s["steps"]]
    body_secs = [s for s in doc["sections"] if s["steps"]]
    toc = "".join(f"<li>{html.escape(s['title'])}</li>" for s in doc["sections"])
    pages = [f"""<section class="page cover">
      <h1>FINN</h1><p class="sub">User guide: every screen, step by step</p>
      <p class="url">finn-blush.vercel.app &nbsp;(open it on a phone)</p>
      <div class="note">{md(doc['note'])}</div>
      {''.join(f'<h2>{html.escape(s["title"])}</h2>' + md(s['intro']) for s in cover_sec)}
      <h2>In this guide</h2><ol class="toc">{toc}</ol></section>"""]
    for sec in body_secs:
        chunks = [sec["steps"][i:i + STEPS_PER_PAGE] for i in range(0, len(sec["steps"]), STEPS_PER_PAGE)]
        for n, chunk in enumerate(chunks):
            head = f"<h2>{html.escape(sec['title'])}</h2>" if n == 0 else f'<h2 class="cont">{html.escape(sec["title"])} (continued)</h2>'
            intro = md(sec["intro"]) if n == 0 and sec["intro"] else ""
            pages.append(f'<section class="page">{head}<div class="intro">{intro}</div>{"".join(step_html(s) for s in chunk)}</section>')
    css = """
    @page { size: A4; margin: 0 }
    * { box-sizing: border-box }
    body { margin: 0; font: 11pt/1.45 "Helvetica Neue", Arial, sans-serif; color: #17202e }
    .page { width: 210mm; height: 297mm; padding: 14mm 16mm 18mm; page-break-after: always; overflow: hidden }
    h1 { font-size: 44pt; margin: 0; letter-spacing: -1px }
    h2 { font-size: 18pt; margin: 0 0 4mm; padding-bottom: 2mm; border-bottom: 2px solid #17202e }
    h2.cont { font-size: 13pt; color: #5b6676; border-bottom-width: 1px }
    .cover h2 { margin-top: 9mm }
    .sub { font-size: 16pt; margin: 2mm 0 }
    .url { color: #5b6676 }
    .note { background: #eef1f5; padding: 3mm 5mm; border-radius: 3mm; margin: 6mm 0 }
    .note p { margin: 0; font-size: 10pt }
    table { border-collapse: collapse; width: 100% }
    th, td { border-bottom: 1px solid #d5dae1; text-align: left; padding: 2mm 3mm; font-size: 10pt }
    .toc { columns: 2; margin: 0; padding-left: 6mm }
    .toc li { margin: 1mm 0 }
    .cover { padding-top: 10mm }
    .intro ul { margin: 0 0 4mm 5mm; padding: 0; font-size: 10pt }
    .step { display: flex; gap: 7mm; margin-bottom: 7mm; break-inside: avoid; align-items: flex-start }
    .shots { display: flex; gap: 3mm; flex: none }
    figure { margin: 0 }
    img { width: 52mm; display: block; border: 1px solid #c9cfd8; border-radius: 3mm }
    .n2 img { width: 44mm }
    .n3 { flex-direction: column; gap: 3mm }
    .n3 img { width: 42mm }
    .words { flex: 1 }
    .words h3 { font-size: 13pt; margin: 0 0 2mm }
    .words p { margin: 0 0 2.5mm }
    .words ul { margin: 0 0 2mm 5mm; padding: 0 }
    code { background: #eef1f5; padding: 0 1mm; border-radius: 1mm }
    """
    return f"<!doctype html><meta charset=utf-8><title>FINN user guide</title><style>{css}</style>{''.join(pages)}"


def main() -> int:
    doc = parse(SRC.read_text())
    steps = sum(len(s["steps"]) for s in doc["sections"])
    missing = [src for s in doc["sections"] for st in s["steps"] for _, src in st["images"] if not (DOCS / src).exists()]
    if missing:
        print("missing images:", missing)
        return 1
    with tempfile.TemporaryDirectory() as d:
        page_file = Path(d) / "guide.html"
        page_file.write_text(build_html(doc))
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.goto(page_file.as_uri(), wait_until="load")
            pg.pdf(path=str(OUT), format="A4", print_background=True, prefer_css_page_size=True,
                   display_header_footer=True, header_template="<span></span>",
                   footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#5b6676">FINN user guide · page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
                   margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            b.close()
    print(f"{OUT.name}: {steps} steps, {OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
