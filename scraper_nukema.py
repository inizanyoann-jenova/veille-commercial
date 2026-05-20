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

_URLS = [
    "https://marches-publics.nukema.com/seo/consultation/departement?departement=974",
    "https://marches-publics.nukema.com/seo/consultation/departement?departement=976",
]
_LOGIN_URL = "https://www.actu.nukema.com/connexion"
_LOGIN_SELECTORS = {
    "email": "input[type='email']",
    "password": "input[type='password']",
    "submit": "button[type='submit']",
}
_CARD = ".consultation-card, .card, article.consultation, li.consultation"
_FIELDS = {
    "title": "h3, h2, .card-title, .consultation-title",
    "description": ".card-text, .description, .organisme",
    "url": "a@href",
    "date": ".date, .card-date, time",
}
_NEXT = "a[aria-label='Next'], .pagination-next a, a.next"


def fetch_nukema_tenders() -> int:
    init_db()
    db       = SessionLocal()
    inserted = 0
    creds    = CredentialManager.get("nukema")
    _run_id  = start_scraper_run(db, "Nukema")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    if creds:
                        login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS)
                    for base_url in _URLS:
                        page.goto(base_url, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)
                        # Détection auth cross-subdomain : actu.nukema.com → marches-publics.nukema.com
                        if any(k in page.url for k in ("connexion", "login", "authentification")):
                            _log.warning(
                                "Nukema : session non maintenue après navigation (URL=%s) — "
                                "cookies cross-subdomain non partagés entre actu. et marches-publics.",
                                page.url,
                            )
                            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0,
                                               error="Auth cross-subdomain échouée")
                            return 0
                        page_count = 0
                        while page_count < 5:
                            for card in extract_cards(page, _CARD, _FIELDS):
                                title = card.get("title", "").strip()
                                desc  = card.get("description", "").strip()
                                relevant, extra_tags = classify_relevance(f"{title} {desc}")
                                if not relevant:
                                    continue
                                url = card.get("url", "") or base_url
                                if url and not url.startswith("http"):
                                    url = f"https://marches-publics.nukema.com{url}"
                                tid = f"NUKEMA-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                                t = Tender(
                                    id=tid, title=title, description=desc, source=url,
                                    publication_date=parse_date(card.get("date")),
                                    date_extraction=now_utc(),
                                    deadline=None, status="À qualifier",
                                    relevance_score=0, is_maintenance=False,
                                    llm_analysis=None, secteur="Public",
                                    type_opportunite="Marché Public",
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
        _log.info("Nukema : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Nukema : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Nukema : %d AO insérés", fetch_nukema_tenders())
