import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import extract_cards, paginate
from scraper_utils import parse_date, load_existing_ids, insert_if_new, now_utc

_log = logging.getLogger(__name__)

_URL = "https://www.isdb.org/project-procurement"
_CARD = "tr.views-row, .views-row, article.tender, li.tender, .procurement-item, table tbody tr"
_FIELDS = {
    "title": "td.views-field-title, .views-field-title, h3, h2, td:first-child",
    "description": "td.views-field-body, .views-field-body, .description, td:nth-child(2)",
    "url": "a@href",
    "date": "td.views-field-field-date, .date, time",
}
_NEXT = "a[title='Go to next page'], li.pager__item--next a, .pager-next a"


def fetch_isdb_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "IsDB — Banque Islamique de Développement")
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
                        _log.warning("IsDB inaccessible : %s", type(exc).__name__)
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
                        return 0
                    page_count = 0
                    nb_found   = 0
                    while page_count < 5:
                        cards = extract_cards(page, _CARD, _FIELDS)
                        nb_found += len(cards)
                        for card in cards:
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            relevant, extra_tags = classify_relevance(f"{title} {desc}")
                            if not relevant:
                                continue
                            url = card.get("url", "") or _URL
                            if url and not url.startswith("http"):
                                url = f"https://www.isdb.org{url}"
                            tid = f"ISDB-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                date_extraction=now_utc(),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Banque Dev.",
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
        _log.info("IsDB : %d trouvés, %d inséré(s)", nb_found, inserted)
    except Exception as exc:
        _log.exception("IsDB : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("IsDB : %d AO insérés", fetch_isdb_tenders())
