import hashlib
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate
from credential_manager import CredentialManager

_URLS = [
    "https://www.vaao.fr/departement/la-reunion",
    "https://www.vaao.fr/departement/mayotte",
]
_CARD = ".views-row, article.node--type-appel-offre, .appel-offre-item, article"
_FIELDS = {
    "title": "h3, h2, .node__title, .title",
    "description": ".field--name-body, .description, .body",
    "url": "a@href",
    "date": "time, .date, .field--name-field-date",
}
_NEXT = "a[rel='next'], li.pager__item--next > a, .pager-next a"


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


def fetch_vaao_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    seen_ids: set[str] = set()
    _run_id = start_scraper_run(db, "VAAO")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for base_url in _URLS:
                    page = browser.new_page()
                    page.goto(base_url, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or base_url
                            if url and not url.startswith("http"):
                                url = f"https://www.vaao.fr{url}"
                            tid = f"VAAO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
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
                                llm_analysis=None, secteur="Public",
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
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
    except Exception as _e:
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"VAAO : {fetch_vaao_tenders()} AO insérés")
