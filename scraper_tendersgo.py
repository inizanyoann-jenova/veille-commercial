import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager

log = logging.getLogger(__name__)

_LOGIN_URL = "https://app.tendersgo.com/login"
_SEARCH_URL = "https://app.tendersgo.com/tenders?country=FR&keywords=SSI+incendie+videosurveillance+CCTV+CMSI"
_LOGIN_SELECTORS = {
    "email": "input[type='email'], input[name='email'], #email",
    "password": "input[type='password'], input[name='password'], #password",
    "submit": "button[type='submit'], input[type='submit']",
}
_CARD = ".tender-card, .tender-item, article.tender, li.tender, tr.tender-row"
_FIELDS = {
    "title": "h3, h2, .tender-title, .title",
    "description": ".tender-description, .description, .country",
    "url": "a@href",
    "date": ".tender-date, .date, time",
}
_NEXT = "a[aria-label='Next page'], .pagination-next a, button.next-page"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_tendersgo_tenders() -> int:
    creds = CredentialManager.get("tendersgo")
    if not creds:
        log.warning("Tenders Go : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db = SessionLocal()
    inserted = 0
    seen_ids: set[str] = set()
    _run_id = start_scraper_run(db, "Tenders Go")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                    log.warning("Tenders Go : login échoué — vérifiez vos identifiants dans Paramètres")
                    finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Login échoué")
                    return 0
                page.goto(_SEARCH_URL, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=15000)
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _SEARCH_URL
                        if url and not url.startswith("http"):
                            url = f"https://app.tendersgo.com{url}"
                        tid = f"TENDERSGO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if tid in seen_ids:
                            continue
                        seen_ids.add(tid)
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="International",
                            type_opportunite="Marché International",
                        ))
                        inserted += 1
                    if not paginate(page, _NEXT):
                        break
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
    print(f"Tenders Go : {fetch_tendersgo_tenders()} AO insérés")
