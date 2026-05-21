import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager
from scraper_utils import parse_date, load_existing_ids, insert_if_new, now_utc

_log = logging.getLogger(__name__)

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


def fetch_tendersgo_tenders() -> int:
    creds = CredentialManager.get("tendersgo")
    if not creds:
        _log.warning("Tenders Go : aucun identifiant configuré — scraper ignoré")
        init_db()
        db = SessionLocal()
        try:
            _run_id = start_scraper_run(db, "Tenders Go")
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Pas d'identifiants configurés")
        finally:
            db.close()
        return 0
    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "Tenders Go")
    try:
        existing_ids = load_existing_ids(db)
        nb_found     = 0

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                        _log.warning("Tenders Go : login échoué — vérifiez vos identifiants dans Paramètres")
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Login échoué")
                        return 0
                    page.goto(_SEARCH_URL, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    page_count = 0
                    while page_count < 5:
                        cards = extract_cards(page, _CARD, _FIELDS)
                        nb_found += len(cards)
                        for card in cards:
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            relevant, extra_tags = classify_relevance(f"{title} {desc}")
                            if not relevant:
                                continue
                            url = card.get("url", "") or _SEARCH_URL
                            if url and not url.startswith("http"):
                                url = f"https://app.tendersgo.com{url}"
                            tid = f"TENDERSGO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                date_extraction=now_utc(),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="International",
                                type_opportunite="Marché International",
                                tags=extra_tags,
                            )
                            if insert_if_new(db, t, existing_ids):
                                inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                finally:
                    page.close()
            finally:
                browser.close()

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=nb_found, nb_new=inserted)
        _log.info("Tenders Go : %d trouvés, %d inséré(s)", nb_found, inserted)
    except Exception as exc:
        _log.exception("Tenders Go : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Tenders Go : %d AO insérés", fetch_tendersgo_tenders())
