import hashlib
import json
from datetime import datetime

import requests

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender

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


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value)[:10], fmt[:10])
        except ValueError:
            continue
    return None


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
        "Status": 0,  # 0 = Active
    }
    try:
        resp = requests.post(
            UNGM_SEARCH_URL,
            headers=_HEADERS,
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("Notices", data.get("notices", data.get("results", [])))
    except Exception:
        pass
    return []


def fetch_ungm_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    seen_ids: set[str] = set()
    _run_id = start_scraper_run(db, "UNGM")

    try:
        for keyword in _UNGM_KEYWORDS:
            notices = _search_ungm(keyword)

            for notice in notices:
                # UNGM peut retourner des dicts avec divers noms de champs
                title = (notice.get("Title") or notice.get("title")
                         or notice.get("NoticeTitle") or "")
                description = (notice.get("Description") or notice.get("description")
                               or notice.get("GoodsServices") or "")
                full_text = f"{title} {description}"

                if not full_text.strip() or not is_relevant_def(full_text):
                    continue

                uid = (notice.get("Id") or notice.get("id")
                       or notice.get("NoticeId")
                       or hashlib.md5(full_text.encode()).hexdigest())
                tender_id = f"UNGM-{uid}"

                if tender_id in seen_ids:
                    continue
                seen_ids.add(tender_id)

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                deadline_raw = (notice.get("Deadline") or notice.get("deadline")
                                or notice.get("SubmissionDeadline"))
                pub_raw = (notice.get("PublishedOn") or notice.get("publishedOn")
                           or notice.get("PublicationDate"))
                url = (notice.get("Url") or notice.get("url")
                       or f"https://www.ungm.org/Public/Notice/{uid}")

                db.add(Tender(
                    id=tender_id,
                    title=title,
                    description=description,
                    source=url,
                    publication_date=_parse_date(pub_raw),
                    deadline=_parse_date(deadline_raw),
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Public",
                    type_opportunite="Marché International",
                ))
                inserted += 1

        if inserted:
            db.commit()

        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
    except Exception as _e:
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))
        raise
    finally:
        db.close()

    return inserted
