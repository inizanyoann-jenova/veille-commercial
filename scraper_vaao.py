import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_URLS = [
    "https://www.vaao.fr/departement/la-reunion",
    "https://www.vaao.fr/departement/mayotte",
]
_CARD   = ".views-row, article.node--type-appel-offre, .appel-offre-item, article"
_FIELDS = {
    "title":       "h3, h2, .node__title, .title",
    "description": ".field--name-body, .description, .body",
    "url":         "a@href",
    "date":        "time, .date, .field--name-field-date",
}
_NEXT = "a[rel='next'], li.pager__item--next > a, .pager-next a"


def fetch_vaao_tenders() -> int:
    init_db()
    db       = SessionLocal()
    inserted = 0
    _run_id  = start_scraper_run(db, "VAAO")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for base_url in _URLS:
                    page = browser.new_page()
                    try:
                        page.goto(base_url, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)
                        page_count = 0
                        while page_count < 5:
                            for card in extract_cards(page, _CARD, _FIELDS):
                                title = card.get("title", "").strip()
                                desc  = card.get("description", "").strip()
                                if not is_relevant_def(f"{title} {desc}"):
                                    continue
                                url = card.get("url", "") or base_url
                                if url and not url.startswith("http"):
                                    url = f"https://www.vaao.fr{url}"
                                tid = f"VAAO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
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
        _log.info("VAAO : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("VAAO : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("VAAO : %d AO insérés", fetch_vaao_tenders())
