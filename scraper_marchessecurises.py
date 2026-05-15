import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_LOGIN_URL = "https://www.marches-securises.fr/entreprise/?page=connexion"
_SEARCH_URL = "https://www.marches-securises.fr/entreprise/?page=entreprise_dce_recherche"
_LOGIN_SELECTORS = {
    "email": "input[name='login'], input[type='email'], #login",
    "password": "input[name='pass'], input[type='password'], #password",
    "submit": "input[type='submit'], button[type='submit']",
}
_CARD = "table.tableau tr.ligneMarche, .liste-dce tr, tr[class*='ligne']"
_FIELDS = {
    "title": "td.objet, .objet, td:nth-child(2)",
    "description": "td.pa, .organisme-acheteur, td:nth-child(3)",
    "url": "a@href",
    "date": "td.date, .date-limite, td:last-child",
}
_NEXT = "a.suivant, a[title='Suivant'], .page-suivante"


def fetch_marchessecurises_tenders() -> int:
    creds = CredentialManager.get("marches_securises")
    if not creds:
        _log.warning("Marchés Sécurisés : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db       = SessionLocal()
    inserted = 0
    _run_id  = start_scraper_run(db, "Marchés Sécurisés")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                        _log.warning("Marchés Sécurisés : login échoué — vérifiez vos identifiants dans Paramètres")
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Login échoué")
                        return 0
                    page.goto(_SEARCH_URL, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc  = card.get("description", "").strip()
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or _SEARCH_URL
                            if url and not url.startswith("http"):
                                url = f"https://www.marches-securises.fr{url}"
                            tid = f"MARCHESSEC-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Privé",
                                type_opportunite="Marché Privé",
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
        _log.info("Marchés Sécurisés : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Marchés Sécurisés : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Marchés Sécurisés : %d AO insérés", fetch_marchessecurises_tenders())
