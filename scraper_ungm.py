import hashlib
import logging

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from scraper_utils import parse_date, retry_post, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice/SearchNotices"

_UNGM_KEYWORDS = [
    "fire detection", "SSI", "fire alarm", "fire safety",
    "smoke detection", "CCTV", "surveillance", "access control",
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DEF-OI-Veille/1.0)",
    "Accept": "application/json, text/html, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def _search_ungm(keyword: str) -> list[dict]:
    """Tente un POST JSON sur l'API UNGM. Retourne [] si indisponible."""
    payload = {
        "Title": keyword,
        "Description": "",
        "GoodsServices": "",
        "Deadline": None,
        "PublishedFrom": None,
        "CountryCodes": [],
        "AgencyId": None,
        "Status": 0,
    }
    try:
        resp = retry_post(UNGM_SEARCH_URL, json=payload, rate_delay=1.5)
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("Notices", data.get("notices", data.get("results", [])))
    except Exception as exc:
        _log.warning("UNGM API inaccessible pour '%s' : %s", keyword, type(exc).__name__)
    return []


def fetch_ungm_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "UNGM")

    try:
        existing_ids = load_existing_ids(db)

        for keyword in _UNGM_KEYWORDS:
            notices = _search_ungm(keyword)

            for notice in notices:
                title = (notice.get("Title") or notice.get("title")
                         or notice.get("NoticeTitle") or "")
                description = (notice.get("Description") or notice.get("description")
                               or notice.get("GoodsServices") or "")
                full_text = f"{title} {description}"

                relevant, extra_tags = classify_relevance(full_text)
                if not full_text.strip() or not relevant:
                    continue

                uid = (notice.get("Id") or notice.get("id")
                       or notice.get("NoticeId")
                       or hashlib.md5(full_text.encode()).hexdigest())
                tender_id = f"UNGM-{uid}"

                deadline_raw = (notice.get("Deadline") or notice.get("deadline")
                                or notice.get("SubmissionDeadline"))
                pub_raw = (notice.get("PublishedOn") or notice.get("publishedOn")
                           or notice.get("PublicationDate"))
                url = (notice.get("Url") or notice.get("url")
                       or f"https://www.ungm.org/Public/Notice/{uid}")

                t = Tender(
                    id=tender_id,
                    title=title,
                    description=description,
                    source=url,
                    publication_date=parse_date(pub_raw),
                    deadline=parse_date(deadline_raw),
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Public",
                    type_opportunite="Marché International",
                    tags=extra_tags,
                )
                if insert_if_new(db, t, existing_ids):
                    inserted += 1

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("UNGM : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("UNGM : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_ungm_tenders()
    _log.info("UNGM terminé — %d marché(s)", count)
