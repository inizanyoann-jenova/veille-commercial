import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate

log = logging.getLogger(__name__)

_URL = "https://www.marches-publics.info/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnouncement[query]=SSI+incendie+CMSI+videosurveillance&searchAnnouncement[dptList][]=974&searchAnnouncement[dptList][]=976"
_CARD = "tr.annonce, .annonce-row, li.annonce, .search-result-item"
_FIELDS = {
    "title": "td.objet, .objet, h3, .titre",
    "description": "td.pa, .organisme, .acheteur",
    "url": "a@href",
    "date": "td.date, .date, time",
}
_NEXT = "a.next, a[title='Page suivante'], .pagination-next a"


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


def fetch_marchespublicsinfo_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    page.goto(_URL, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception as exc:
                    log.warning("Marchés Public Info inaccessible : %s", exc)
                    return 0
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _URL
                        if url and not url.startswith("http"):
                            url = f"https://www.marches-publics.info{url}"
                        tid = f"MARCHESPUBLICSINFO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
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
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Marchés Public Info : {fetch_marchespublicsinfo_tenders()} AO insérés")
