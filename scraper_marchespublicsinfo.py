import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_URL = "https://www.marches-publics.info/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnouncement[query]=SSI+incendie+CMSI+videosurveillance&searchAnnouncement[dptList][]=974&searchAnnouncement[dptList][]=976"
_CARD = "tr.annonce, .annonce-row, li.annonce, .search-result-item"
_FIELDS = {
    "title": "td.objet, .objet, h3, .titre",
    "description": "td.pa, .organisme, .acheteur",
    "url": "a@href",
    "date": "td.date, .date, time",
}
_NEXT = "a.next, a[title='Page suivante'], .pagination-next a"


def fetch_marchespublicsinfo_tenders() -> int:
    init_db()
    db       = SessionLocal()
    inserted = 0
    _run_id  = start_scraper_run(db, "Marchés Public Info")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    try:
                        page.goto(_URL, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception as exc:
                        _log.warning("Marchés Public Info inaccessible : %s", type(exc).__name__)
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
                        return 0
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc  = card.get("description", "").strip()
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or _URL
                            if url and not url.startswith("http"):
                                url = f"https://www.marches-publics.info{url}"
                            tid = f"MARCHESPUBLICSINFO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
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
        _log.info("Marchés Public Info : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Marchés Public Info : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Marchés Public Info : %d AO insérés", fetch_marchespublicsinfo_tenders())
