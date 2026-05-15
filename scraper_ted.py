import hashlib
import logging

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from scraper_utils import parse_date, retry_post, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"

_METIERS = (
    "FT~SSI OR FT~CMSI OR FT~incendie OR FT~desenfumage"
    " OR FT~videosurveillance OR FT~camera OR FT~CCTV"
)

QUERIES = {
    "La Réunion": f"FT~974 AND ({_METIERS})",
    "Mayotte":    f"FT~Mayotte AND ({_METIERS})",
    "Madagascar": f"FT~Madagascar AND ({_METIERS})",
    "Maurice":    f"FT~Mauritius AND ({_METIERS})",
    "Comores":    f"FT~Comoros AND ({_METIERS})",
}

_FIELDS = ["notice-title", "publication-number", "deadline-receipt-tender-date-lot", "description-glo"]


def _extract_fr(field_value) -> str:
    if not field_value:
        return ""
    if isinstance(field_value, list):
        return " ".join(_extract_fr(item) for item in field_value if item).strip()
    if isinstance(field_value, dict):
        return (field_value.get("fra") or field_value.get("eng")
                or next(iter(field_value.values()), "")) or ""
    return str(field_value)


def _fetch_query(db, query: str, existing_ids: set) -> int:
    inserted = 0
    page     = 1
    limit    = 100

    while True:
        payload = {"query": query, "fields": _FIELDS, "page": page, "limit": limit}
        r       = retry_post(TED_API_URL, json=payload, rate_delay=1.5)
        notices = r.json().get("notices", [])
        if not notices:
            break

        for notice in notices:
            pub_num     = notice.get("publication-number") or ""
            title       = _extract_fr(notice.get("notice-title"))
            description = _extract_fr(notice.get("description-glo"))

            if not is_relevant_def(f"{title} {description}"):
                continue

            tender_id = (f"TED-{pub_num}" if pub_num
                         else f"TED-{hashlib.md5(title.encode()).hexdigest()[:12]}")

            links  = notice.get("links", {})
            url_fr = ((links.get("html") or {}).get("FRA")
                      or f"https://ted.europa.eu/fr/notice/{pub_num}/html")

            t = Tender(
                id=tender_id,
                title=title or f"Avis TED {pub_num}",
                description=description,
                source=url_fr,
                publication_date=None,
                deadline=parse_date(notice.get("deadline-receipt-tender-date-lot")),
                status="À qualifier",
                relevance_score=0,
                is_maintenance=False,
                llm_analysis=None,
            )
            if insert_if_new(db, t, existing_ids):
                inserted += 1

        if len(notices) < limit:
            break
        page += 1

    return inserted


def fetch_ted_tenders(zones: list[str] | None = None) -> int:
    init_db()
    db    = SessionLocal()
    total = 0
    _run_id = start_scraper_run(db, "TED Europe")

    selected = {k: v for k, v in QUERIES.items() if zones is None or k in zones}

    try:
        existing_ids = load_existing_ids(db)
        for zone, query in selected.items():
            _log.info("TED : collecte zone '%s'", zone)
            total += _fetch_query(db, query, existing_ids)
        if total:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=total, nb_new=total)
        _log.info("TED : %d marché(s) inséré(s)", total)
    except Exception as exc:
        _log.exception("TED : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_ted_tenders()
    _log.info("TED terminé — %d marché(s)", count)
