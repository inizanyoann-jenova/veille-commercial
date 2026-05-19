import hashlib
import logging
import re

import playwright.sync_api as _playwright_sync


def sync_playwright():
    return _playwright_sync.sync_playwright()

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import login
from credential_manager import CredentialManager
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

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


def _extract_from_comments(html: str) -> list[dict]:
    """MarchesOnline hides AO cards inside HTML comments for non-premium rendering."""
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
        loc_m = re.search(r'class="location"[^>]*>.*?<span>(97[46])</span>', block, re.DOTALL)
        dept = loc_m.group(1) if loc_m else ""
        publisher = _strip_tags(pub_m.group(1)) if pub_m else ""
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
    m = re.search(r'<a[^>]+href="([^"]+)"[^>]*(?:rel="next"|class="[^"]*next[^"]*")', html)
    if not m:
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


_DETAIL_PATTERNS = [
    r'itemprop=["\']description["\'][^>]*>(.*?)</(?:p|div|span|article)>',
    r'class=["\']ao-objet["\'][^>]*>(.*?)</(?:p|div|span)>',
    r'class=["\']objet-marche["\'][^>]*>(.*?)</(?:p|div|span)>',
    r'class=["\']description-lot["\'][^>]*>(.*?)</(?:p|div|span)>',
    r'class=["\']ao-description["\'][^>]*>(.*?)</(?:p|div|span)>',
]


def _parse_detail_html(html: str) -> str:
    """Extrait la description depuis le HTML brut d'une fiche détail."""
    for pattern in _DETAIL_PATTERNS:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            text = _strip_tags(m.group(1)).strip()
            if len(text) > 10:
                return text
    return ""


def _extract_detail(page, url: str) -> str:
    """Navigue vers la fiche détail et retourne la description complète.

    Retourne "" en cas d'erreur — ne propage pas l'exception pour ne pas
    interrompre la collecte.
    """
    if not url:
        return ""
    try:
        page.goto(url, timeout=20000)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        return _parse_detail_html(page.content())
    except Exception as exc:
        _log.warning("Marché Online : fiche détail inaccessible %s — %s", url, exc)
        return ""


def fetch_marcheonline_tenders() -> int:
    init_db()
    db       = SessionLocal()
    inserted = 0
    creds    = CredentialManager.get("marcheonline")
    _run_id  = start_scraper_run(db, "Marché Online")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    if creds:
                        login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS)

                    # ── Phase 1 : collecte des liens depuis les pages de liste ──
                    candidates = []
                    for base_url in _URLS:
                        current_url = base_url
                        page_count  = 0
                        while page_count < 10:
                            page.goto(current_url, timeout=30000)
                            page.wait_for_load_state("networkidle", timeout=30000)
                            html  = page.content()
                            for card in _extract_from_comments(html):
                                if card.get("title", "").strip():
                                    candidates.append(card)
                            next_url = _get_next_url(html, current_url)
                            if not next_url or next_url == current_url:
                                break
                            current_url = next_url
                            page_count += 1

                    # ── Phase 2 : enrichissement détail + filtre pertinence ────
                    for card in candidates:
                        title = card.get("title", "").strip()
                        url   = card.get("url", "")
                        tid   = f"MARCHEONLINE-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if tid in existing_ids:
                            continue

                        detail_desc = _extract_detail(page, url)
                        desc = detail_desc or card.get("description", "").strip()

                        relevant, extra_tags = classify_relevance(f"{title} {desc}")
                        if not relevant:
                            continue

                        t = Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=parse_date(card.get("date")),
                            deadline=parse_date(card.get("deadline")),
                            status="À qualifier", relevance_score=0,
                            is_maintenance=False, llm_analysis=None,
                            secteur="Public", type_opportunite="Marché Public",
                            tags=extra_tags,
                        )
                        if insert_if_new(db, t, existing_ids):
                            inserted += 1
                finally:
                    page.close()
            finally:
                browser.close()

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("Marché Online : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Marché Online : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Marché Online : %d AO insérés", fetch_marcheonline_tenders())
