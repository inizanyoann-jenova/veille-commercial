import hashlib
import logging
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp_augmente/records"
)

_DEPT_FILTER    = 'codedepartementexecution in ("974", "976")'
_KEYWORD_FILTER = (
    'search(objetmarche, "SSI")'
    ' OR search(objetmarche, "CMSI")'
    ' OR search(objetmarche, "incendie")'
    ' OR search(objetmarche, "desenfumage")'
    ' OR search(objetmarche, "videosurveillance")'
    ' OR search(objetmarche, "camera")'
    ' OR search(objetmarche, "CCTV")'
    ' OR search(objetmarche, "courants faibles")'
)


def fetch_decp_tenders(years_back: int = 3) -> int:
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    where    = f"({_DEPT_FILTER}) AND ({_KEYWORD_FILTER}) AND (datenotification >= \"{date_min}\")"

    init_db()
    db       = SessionLocal()
    inserted = 0
    _run_id  = start_scraper_run(db, "DECP / PLACE")

    try:
        existing_ids = load_existing_ids(db)
        offset = 0
        limit  = 100

        while True:
            params = {"where": where, "limit": limit, "offset": offset, "order_by": "datenotification DESC"}
            response = retry_get(DECP_API, params=params, rate_delay=1.0)
            records  = response.json().get("results", [])
            if not records:
                break

            for record in records:
                acheteur_nom = record.get("nomacheteur") or ""
                objet        = record.get("objetmarche") or ""
                full_text    = f"{objet} {acheteur_nom}"

                relevant, extra_tags = classify_relevance(full_text)
                if not relevant:
                    continue

                uid       = record.get("id") or hashlib.md5(full_text.encode()).hexdigest()
                tender_id = f"DECP-{uid}"

                t = Tender(
                    id=tender_id, title=objet,
                    description=f"Acheteur : {acheteur_nom}",
                    source="https://data.economie.gouv.fr",
                    publication_date=parse_date(record.get("datenotification")),
                    deadline=None, status="À qualifier",
                    relevance_score=0, is_maintenance=False, llm_analysis=None,
                    secteur="Public", type_opportunite="Marché Public",
                    tags=extra_tags,
                )
                if insert_if_new(db, t, existing_ids):
                    inserted += 1

            if len(records) < limit:
                break
            offset += limit

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("DECP : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("DECP : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_decp_tenders()
    _log.info("DECP terminé — %d marché(s)", count)
