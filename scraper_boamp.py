import hashlib
from datetime import datetime

import requests

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender

BOAMP_API_URL = (
    "https://boamp-datadila.opendatasoft.com/api/explore/v2.1"
    "/catalog/datasets/boamp/records"
)

# Mots-clés injectés directement dans la requête API pour limiter le volume
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


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def fetch_boamp_tenders(departments: list[str] | None = None, years_back: int = 2) -> int:
    if departments is None:
        departments = ["974", "976"]

    from datetime import timedelta
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "BOAMP — Journal Officiel")

    try:
        for dept in departments:
            offset = 0
            limit = 100

            while True:
                params = {
                    "where": (
                        f"code_departement_prestation='{dept}'"
                        f" AND ({_KEYWORD_FILTER})"
                        f" AND dateparution >= '{date_min}'"
                    ),
                    "limit": limit,
                    "offset": offset,
                    "order_by": "dateparution DESC",
                }

                response = requests.get(BOAMP_API_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                records = data.get("results", [])
                if not records:
                    break

                for record in records:
                    title = record.get("objet") or ""
                    descripteurs = record.get("descripteur_libelle") or []
                    description = " ".join(descripteurs) if isinstance(descripteurs, list) else str(descripteurs)
                    full_text = f"{title} {description}"

                    if not is_relevant_def(full_text):
                        continue

                    raw_id = (
                        record.get("id_lot")
                        or record.get("idweb")
                        or hashlib.md5(full_text.encode()).hexdigest()
                    )
                    tender_id = str(raw_id)

                    if db.query(Tender).filter(Tender.id == tender_id).first():
                        continue

                    tender = Tender(
                        id=tender_id,
                        title=title,
                        description=description,
                        source=record.get("url_avis") or "https://boamp.fr",
                        publication_date=_parse_date(record.get("dateparution")),
                        deadline=_parse_date(record.get("datelimitereponse")),
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                    )
                    db.add(tender)
                    inserted += 1

                db.commit()

                if len(records) < limit:
                    break
                offset += limit

        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
    except Exception as _e:
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    print("Lancement de la collecte BOAMP pour les départements 974 et 976...")
    count = fetch_boamp_tenders()
    print(f"Collecte terminée — {count} nouveau(x) marché(s) inséré(s).")
