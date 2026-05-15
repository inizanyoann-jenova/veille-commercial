import hashlib
import logging
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

BOAMP_API_URL = (
    "https://boamp-datadila.opendatasoft.com/api/explore/v2.1"
    "/catalog/datasets/boamp/records"
)

_KEYWORD_FILTER = (
    "objet like '%SSI%'"
    " OR objet like '%CMSI%'"
    " OR objet like '%incendie%'"
    " OR objet like '%désenfumage%'"
    " OR objet like '%desenfumage%'"
    " OR objet like '%vidéosurveillance%'"
    " OR objet like '%videosurveillance%'"
    " OR objet like '%caméra%'"
    " OR objet like '%camera%'"
    " OR objet like '%CCTV%'"
    " OR objet like '%courants faibles%'"
)


def fetch_boamp_tenders(departments: list[str] | None = None, years_back: int = 2) -> int:
    if departments is None:
        departments = ["974", "976"]

    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    init_db()
    db = SessionLocal()
    inserted = 0
    nb_found  = 0
    _run_id = start_scraper_run(db, "BOAMP — Journal Officiel")

    try:
        existing_ids = load_existing_ids(db)

        for dept in departments:
            offset = 0
            limit  = 100

            while True:
                params = {
                    "where": (
                        f"code_departement_prestation='{dept}'"
                        f" AND ({_KEYWORD_FILTER})"
                        f" AND dateparution >= '{date_min}'"
                    ),
                    "limit":    limit,
                    "offset":   offset,
                    "order_by": "dateparution DESC",
                }

                response = retry_get(BOAMP_API_URL, params=params, rate_delay=1.0)
                data    = response.json()
                records = data.get("results", [])
                if not records:
                    break

                nb_found += len(records)

                for record in records:
                    title        = record.get("objet") or ""
                    descripteurs = record.get("descripteur_libelle") or []
                    description  = " ".join(descripteurs) if isinstance(descripteurs, list) else str(descripteurs)
                    full_text    = f"{title} {description}"

                    if not is_relevant_def(full_text):
                        continue

                    raw_id    = (record.get("id_lot") or record.get("idweb")
                                 or "BOAMP-" + hashlib.md5(full_text.encode()).hexdigest())
                    tender_id = str(raw_id)

                    _idweb       = record.get("idweb") or ""
                    _fallback_url = (
                        f"https://www.boamp.fr/aides-a-la-recherche/detail/{_idweb}"
                        if _idweb else "https://www.boamp.fr"
                    )
                    t = Tender(
                        id=tender_id,
                        title=title,
                        description=description,
                        source=record.get("url_avis") or _fallback_url,
                        publication_date=parse_date(record.get("dateparution")),
                        deadline=parse_date(record.get("datelimitereponse")),
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                    )
                    if insert_if_new(db, t, existing_ids):
                        inserted += 1

                if len(records) < limit:
                    break
                offset += limit

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=nb_found, nb_new=inserted)
        _log.info("BOAMP : %d trouvés, %d insérés", nb_found, inserted)
    except Exception as exc:
        _log.exception("BOAMP : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("Lancement collecte BOAMP — départements 974 et 976")
    count = fetch_boamp_tenders()
    _log.info("Collecte terminée — %d marché(s) inséré(s)", count)
