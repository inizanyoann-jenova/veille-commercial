import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager

log = logging.getLogger(__name__)

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


def fetch_marchessecurises_tenders() -> int:
    creds = CredentialManager.get("marches_securises")
    if not creds:
        log.warning("Marchés Sécurisés : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                    log.warning("Marchés Sécurisés : login échoué — vérifiez vos identifiants dans Paramètres")
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
                            url = f"https://www.marches-securises.fr{url}"
                        tid = f"MARCHESSEC-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="Privé",
                            type_opportunite="Marché Public",
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
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Marchés Sécurisés : {fetch_marchessecurises_tenders()} AO insérés")
