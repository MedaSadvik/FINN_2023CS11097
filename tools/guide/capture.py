"""Take the screenshots used by the user guide, from a running copy of the website.

    # 1. the pretend Supabase (only for the signed-in screens)
    python tools/guide/mock_supabase.py &
    # 2. the website, pointed at it
    cd frontend && NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321 NEXT_PUBLIC_SUPABASE_ANON_KEY=mock BUILD_GITHUB_TOKEN=mock NO_PROXY=127.0.0.1 npx next dev -p 3111 &
    # 3. the screenshots
    python tools/guide/capture.py

Needs: pip install playwright pillow, and a Chromium for Playwright. Pictures go to docs/guide/img/ (390 x 844 phone screens at 2x).
The signed-out screens use the real data in the repo. The signed-in screens use invented people on the pretend Supabase.
"""
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import Page, sync_playwright

BASE = "http://localhost:3111"
OUT = Path(__file__).resolve().parent.parent.parent / "docs" / "guide" / "img"
PASSWORD = "correct-horse-9"
MISSING = []


def save(page: Page, name: str, hl=None):
    """Screenshot the visible phone screen. `hl` outlines the element to tap, in red."""
    page.wait_for_timeout(350)
    if hl is not None:
        page.evaluate("""(el) => { el.dataset.o = el.style.outline; el.style.outline = '3px solid #e5322d'; el.style.outlineOffset = '3px'; el.style.borderRadius = '10px'; }""", hl.element_handle())
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path))
    if hl is not None:
        page.evaluate("(el) => { el.style.outline = el.dataset.o || ''; }", hl.element_handle())
    Image.open(path).convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)
    print("  saved", name)


def goto(page: Page, path: str):
    page.goto(BASE + path, wait_until="networkidle")


def top(page: Page, locator, offset=70):
    """Scroll so `locator` sits near the top of the screen."""
    locator.first.evaluate("e => e.scrollIntoView({block: 'start'})")
    page.evaluate(f"window.scrollBy(0, -{offset})")


def card(page: Page, word: str):
    """The Today card whose text contains `word`, or None."""
    items = page.locator("main article").filter(has_text=word)
    return items.first if items.count() else None


def fill_submit(page: Page, fields: dict, button: str):
    for name, value in fields.items():
        page.fill(f"input[name={name}]", value)
    page.get_by_role("button", name=button).last.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(900)


def sign_up(page: Page, name: str, username: str, email: str):
    goto(page, "/signin")
    page.get_by_role("tab", name="Create account").click()
    fill_submit(page, {"display_name": name, "username": username, "email": email, "password": PASSWORD}, "Create account")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        def ctx():
            c = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            # hide the developer badge that `next dev` draws in the corner
            c.add_init_script("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = 'nextjs-portal{display:none!important}'; document.head.appendChild(s); });")
            return c

        # ============================================================ signed out: Today
        a = ctx().new_page()
        print("Today")
        goto(a, "/")
        save(a, "today_top")
        goto(a, "/?w=14d")
        save(a, "today_14d", hl=a.get_by_role("link", name="14 days"))
        a.get_by_text("What counts as unusual").click()
        a.wait_for_timeout(400)
        top(a, a.get_by_text("What counts as unusual"), 100)
        save(a, "today_settings")
        a.reload(wait_until="networkidle")
        for word, name in (("Management change", "card_management"), ("Results,", "card_results"), ("Alert ·", "card_alert")):
            c = card(a, word)
            if c is None:
                MISSING.append(name); continue
            top(a, c, 20); save(a, name)
        who = a.get_by_role("button", name="Who to call").first
        if who.count():
            top(a, who, 300); who.click(); a.wait_for_timeout(700); save(a, "call_sheet")
            a.keyboard.press("Escape")
        goto(a, "/?w=14d")
        link = a.get_by_text("have a reason to hear from you").first
        if link.count(): top(a, link, 200); save(a, "today_reason", hl=link)

        # ============================================================ signed out: Research
        print("Research")
        goto(a, "/company")
        save(a, "research_list")
        a.fill("#company-q", "asain paint"); a.wait_for_timeout(500)
        save(a, "research_search")
        goto(a, "/company/KAYNES")
        save(a, "company_top")
        for id_, name in (("promises", "company_promises"), ("narrative", "company_narrative"), ("trajectory", "company_trajectory"),
                          ("balance", "company_balance"), ("cash", "company_cash"), ("quarters", "company_quarters"),
                          ("business", "company_business"), ("bullbear", "company_bullbear")):
            el = a.locator(f"#{id_}")
            if el.count(): top(a, el, 12); save(a, name)
            else: MISSING.append(name)
        goto(a, "/company/TITANCOMPANY")
        save(a, "company_notfound")
        goto(a, "/network")
        save(a, "network_signed_out")
        goto(a, "/signin")
        save(a, "signin")
        a.get_by_role("tab", name="Create account").click(); a.wait_for_timeout(300)
        a.fill("input[name=display_name]", "Asha Verma"); a.fill("input[name=username]", "asha_verma")
        a.fill("input[name=email]", "asha@example.com"); a.fill("input[name=password]", PASSWORD)
        save(a, "signup_form")

        # ============================================================ second person (Dev), signed up first so Asha can ask him
        print("Dev signs up")
        d = ctx().new_page()
        sign_up(d, "Dev Nair", "dev_nair", "dev@example.com")
        goto(d, "/me")
        d.locator("summary", has_text="Add a job").click()
        fill_submit(d, {"employer": "Dixon Technologies", "title": "Head of Finance", "start_year": "2016", "end_year": "2021"}, "Add job")

        # ============================================================ signed in: Asha
        print("Asha")
        sign_up(a, "Asha Verma", "asha_verma", "asha@example.com")
        save(a, "me_new")
        fill_submit(a, {"display_name": "Asha Verma", "headline": "Portfolio Manager, Ashoka Capital"}, "Save")
        save(a, "me_saved")
        a.locator("summary", has_text="Add a job").click()
        a.fill("input[name=employer]", "Kaynes Technology"); a.fill("input[name=title]", "Equity Analyst")
        a.fill("input[name=start_year]", "2017"); a.fill("input[name=end_year]", "2020")
        top(a, a.locator("summary", has_text="Add a job"), 60); save(a, "job_form")
        a.get_by_role("button", name="Add job").click(); a.wait_for_load_state("networkidle"); a.wait_for_timeout(900)
        top(a, a.get_by_role("heading", name="Career"), 40); save(a, "job_added")
        a.locator("summary", has_text="Add a school").click()
        a.fill("input[name=institution]", "IIT Delhi"); a.fill("input[name=start_year]:visible >> nth=0", "2010")
        a.locator("details", has_text="Add a school").locator("input[name=start_year]").fill("2010")
        a.locator("details", has_text="Add a school").locator("input[name=end_year]").fill("2014")
        a.locator("details", has_text="Add a school").get_by_role("button", name="Add school").click()
        a.wait_for_load_state("networkidle"); a.wait_for_timeout(900)
        top(a, a.get_by_role("heading", name="Education"), 40); save(a, "school_added")

        print("Connections")
        goto(a, "/network")
        save(a, "network_empty")
        fill_submit(a, {"username": "demo_priya"}, "Send request")
        top(a, a.locator("form").first, 60); save(a, "connect_demo")
        fill_submit(a, {"username": "dev_nair"}, "Send request")
        top(a, a.locator("form").first, 60); save(a, "connect_request")
        goto(a, "/network")
        top(a, a.get_by_role("heading", name="Connections"), 40); save(a, "connections_list")
        wait = a.get_by_role("heading", name="Waiting for an answer")
        if wait.count(): top(a, wait, 40); save(a, "waiting")

        print("Dev accepts")
        goto(d, "/network")
        asked = d.get_by_role("heading", name="Asked to connect with you")
        top(d, asked, 40); save(d, "incoming", hl=d.get_by_role("button", name="Accept"))
        d.get_by_role("button", name="Accept").click(); d.wait_for_load_state("networkidle"); d.wait_for_timeout(1200)
        goto(d, "/network")
        top(d, d.get_by_role("heading", name="Connections"), 40); save(d, "accepted")

        print("Sample contacts and insights")
        goto(a, "/network")
        top(a, a.get_by_role("heading", name="Sample contacts"), 40); save(a, "sample_load", hl=a.get_by_role("button", name="Load sample contacts"))
        a.get_by_role("button", name="Load sample contacts").click(); a.wait_for_load_state("networkidle"); a.wait_for_timeout(1500)
        goto(a, "/network")
        save(a, "network_insights")
        w = a.locator("#who-knows-what")
        if w.count(): top(a, w, 20); save(a, "who_knows_what")
        else: MISSING.append("who_knows_what")
        top(a, a.get_by_role("heading", name="Sample contacts"), 40); save(a, "sample_loaded")

        print("Profile and draft email")
        name_link = a.locator("#worth-a-call a[href^='/network/']").first
        if not name_link.count():
            name_link = a.locator("a[href^='/network/']").first
        href = name_link.get_attribute("href")
        goto(a, href)
        save(a, "person_top")
        print("Last spoke")
        a.locator("input[name=month]").scroll_into_view_if_needed()
        top(a, a.locator("input[name=month]"), offset=230)
        a.fill("input[name=month]", "2026-09")
        a.get_by_role("button", name="Save").last.click(); a.wait_for_timeout(1200)
        save(a, "last_spoke")
        a.evaluate("window.scrollTo(0, 0)")
        a.get_by_role("button", name="Draft an email").click(); a.wait_for_timeout(500)
        save(a, "draft_open")
        a.evaluate("window.scrollTo(0, 560)"); save(a, "draft_buttons")

        print("Call Sheet with a real connection")
        goto(a, "/company/KAYNES")
        sheet = a.get_by_role("button", name="Who in your network knows this company")
        if sheet.count():
            top(a, sheet, 200); sheet.click(); a.wait_for_timeout(800); save(a, "company_call_sheet")
        else: MISSING.append("company_call_sheet")
        print("Update a company")
        goto(a, "/company/TITAN")
        btn = a.get_by_role("button", name="Update TITAN with the new call")
        if btn.count():
            top(a, btn, 220); save(a, "update_offer", btn)
            # the test copy reuses another company's text below the button, so keep only the part that is about the update
            im = Image.open(OUT / "update_offer.png"); im.crop((0, 0, im.width, 800)).save(OUT / "update_offer.png", optimize=True)
        else: MISSING.append("update_offer")
        print("Build a company")
        goto(a, "/company/MARUTI"); save(a, "build_ask")
        goto(a, "/company/TATASTEEL"); save(a, "build_working")
        goto(a, "/me"); a.evaluate("window.scrollTo(0, document.body.scrollHeight)"); save(a, "sign_out", hl=a.get_by_role("button", name="Sign out"))
        browser.close()
    print("\nnot captured:", MISSING or "none")


if __name__ == "__main__":
    sys.exit(main())
