import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_LOGIN_URL = "https://www.instao.fr/connexion"
_SEARCH_URL = "https://www.instao.fr/bids?c=&l=974%2C976"
_LOGIN_SELECTORS = {
    "email": "input[type='email'], input[name='email'], #email",
    "password": "input[type='password'], input[name='password'], #password",
    "submit": "button[type='submit'], input[type='submit']",
}
_CARD = ".bid-card, article.bid, .tender-card, li.bid"
_FIELDS = {
    "title": "h3, h2, .bid-title, .card-title",
    "description": ".bid-description, .card-text, .organisme",
    "url": "a@href",
    "date": ".bid-date, .card-date, time, .date",
}
_NEXT = "a[aria-label='Page suivante'], .pagination-next a, button.next"


def fetch_instao_tenders() -> int:
    creds = CredentialManager.get("instao")
    if not creds:
        _log.warning("Instao : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db       = SessionLocal()
    inserted = 0
    _run_id  = start_scraper_run(db, "Instao")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                        _log.warning("Instao : login échoué — vérifiez vos identifiants dans Paramètres")
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Login échoué")
                        return 0
                    page.goto(_SEARCH_URL, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc  = card.get("description", "").strip()
                            relevant, extra_tags = classify_relevance(f"{title} {desc}")
                            if not relevant:
                                continue
                            url = card.get("url", "") or _SEARCH_URL
                            if url and not url.startswith("http"):
                                url = f"https://www.instao.fr{url}"
                            tid = f"INSTAO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Privé",
                                type_opportunite="Marché Privé",
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
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("Instao : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Instao : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Instao : %d AO insérés", fetch_instao_tenders())
