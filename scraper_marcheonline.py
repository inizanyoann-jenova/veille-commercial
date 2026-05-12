import hashlib
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate

_URLS = [
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101",
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/mayotte-D976",
]
_CARD = ".annonce, .appel-offre, tr.ao-row, .liste-ao li, article"
_FIELDS = {
    "title": "h3, h2, .titre, .objet, td.objet",
    "description": ".description, .resume, td.organisme",
    "url": "a@href",
    "date": ".date, td.date, time",
}
_NEXT = "a.next, .pagination a[aria-label='Next'], li.page-item.active + li a"


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


def fetch_marcheonline_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
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
                                url = f"https://www.marchesonline.com{url}"
                            tid = f"MARCHEONLINE-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
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
    print(f"Marché Online : {fetch_marcheonline_tenders()} AO insérés")
