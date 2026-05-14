import hashlib
import re
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from playwright_base import login
from credential_manager import CredentialManager

_LOGIN_URL = "https://www.marchesonline.com/connexion"
_LOGIN_SELECTORS = {
    "email": "#email-input",
    "password": "input[type='password'].modal_connexion_input",
    "submit": "button.primary-dark-btn",
}

_URLS = [
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101",
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/mayotte-D976",
]
_BASE = "https://www.marchesonline.com"


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def _extract_from_comments(html: str) -> list[dict]:
    """MarchesOnline hides AO cards inside HTML comments for non-premium rendering.
    The data (title, URL, dates, organisme) is fully present in the comment markup."""
    comments = re.findall(r"<!--(.*?)-->", html, re.DOTALL)
    results = []
    for block in comments:
        if "blockNotice" not in block:
            continue
        url_m = re.search(r'<a[^>]+href="(/appels-offres/avis/[^"]+)"[^>]*class="blockContentResults', block)
        title_m = re.search(r'<h2[^>]*itemprop="about"[^>]*>(.*?)</h2>', block, re.DOTALL)
        pub_m = re.search(r'<span[^>]*itemprop="publisher"[^>]*>(.*?)</span>', block, re.DOTALL)
        date_pub_m = re.search(r'itemprop="datePublished" content="([^"]+)"', block)
        date_ans_m = re.search(r'class="answerDate"[^>]*>.*?<span[^>]*class="dateColor"[^>]*>(.*?)</span>', block, re.DOTALL)
        # Extract department code (974, 976) from location to improve territory detection
        loc_m = re.search(r'class="location"[^>]*>.*?<span>(97[46])</span>', block, re.DOTALL)
        dept = loc_m.group(1) if loc_m else ""
        publisher = _strip_tags(pub_m.group(1)) if pub_m else ""
        # Append dept code to description so detect_territoire() picks it up
        description = f"{dept} — {publisher}" if dept else publisher
        results.append({
            "url": f"{_BASE}{url_m.group(1)}" if url_m else "",
            "title": _strip_tags(title_m.group(1)) if title_m else "",
            "description": description,
            "date": date_pub_m.group(1) if date_pub_m else "",
            "deadline": date_ans_m.group(1).strip() if date_ans_m else "",
        })
    return results


def _get_next_url(html: str, current_url: str) -> str | None:
    """Return the absolute URL of the next page, or None."""
    m = re.search(r'<a[^>]+href="([^"]+)"[^>]*(?:rel="next"|class="[^"]*next[^"]*")', html)
    if not m:
        # Try pagination pattern: look for current page number and increment
        page_m = re.search(r'/page-(\d+)', current_url)
        if page_m:
            current_page = int(page_m.group(1))
        else:
            current_page = 1
        # Check if there's a next page link in pagination
        next_m = re.search(
            r'<li[^>]*class="[^"]*active[^"]*"[^>]*>.*?</li>\s*<li[^>]*>\s*<a[^>]+href="([^"]+)"',
            html, re.DOTALL
        )
        if next_m:
            href = next_m.group(1)
            return f"{_BASE}{href}" if href.startswith("/") else href
        return None
    href = m.group(1)
    return f"{_BASE}{href}" if href.startswith("/") else href


def fetch_marcheonline_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    creds = CredentialManager.get("marcheonline")
    seen_ids: set[str] = set()
    _run_id = start_scraper_run(db, "Marché Online")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if creds:
                    login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS)
                for base_url in _URLS:
                    current_url = base_url
                    page_count = 0
                    while page_count < 5:
                        page.goto(current_url, timeout=15000)
                        page.wait_for_load_state("networkidle", timeout=15000)
                        html = page.content()
                        cards = _extract_from_comments(html)
                        for card in cards:
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            if not title:
                                continue
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or current_url
                            tid = f"MARCHEONLINE-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            if tid in seen_ids:
                                continue
                            seen_ids.add(tid)
                            if db.query(Tender).filter(Tender.id == tid).first():
                                continue
                            db.add(Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=_parse_date(card.get("date")),
                                deadline=_parse_date(card.get("deadline")),
                                status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
                            ))
                            inserted += 1
                        next_url = _get_next_url(html, current_url)
                        if not next_url or next_url == current_url:
                            break
                        current_url = next_url
                        page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
    except Exception as _e:
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Marché Online : {fetch_marcheonline_tenders()} AO insérés")
