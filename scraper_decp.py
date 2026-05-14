import hashlib
from datetime import datetime, timedelta

import requests

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_relevant_def
from models import Tender

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp_augmente/records"
)

_DEPT_FILTER = 'codedepartementexecution in ("974", "976")'

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


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    s = str(value)
    for fmt, length in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(s[:length], fmt)
        except ValueError:
            continue
    return None


def fetch_decp_tenders(years_back: int = 3) -> int:
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    date_filter = f'datenotification >= "{date_min}"'
    where = f"({_DEPT_FILTER}) AND ({_KEYWORD_FILTER}) AND ({date_filter})"

    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "DECP / PLACE")

    try:
        offset = 0
        limit = 100

        while True:
            params = {
                "where": where,
                "limit": limit,
                "offset": offset,
                "order_by": "datenotification DESC",
            }
            response = requests.get(DECP_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            records = data.get("results", [])
            if not records:
                break

            for record in records:
                acheteur_nom = record.get("nomacheteur") or ""
                objet = record.get("objetmarche") or ""
                full_text = f"{objet} {acheteur_nom}"

                if not is_relevant_def(full_text):
                    continue

                uid = record.get("id") or hashlib.md5(full_text.encode()).hexdigest()
                tender_id = f"DECP-{uid}"

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                url = "https://data.economie.gouv.fr"

                db.add(Tender(
                    id=tender_id,
                    title=objet,
                    description=f"Acheteur : {acheteur_nom}",
                    source=url,
                    publication_date=_parse_date(record.get("datenotification")),
                    deadline=None,
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Public",
                    type_opportunite="Marché Public",
                ))
                inserted += 1

            if len(records) < limit:
                break
            offset += limit

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
    print("Lancement de la collecte DECP pour les départements 974 et 976...")
    count = fetch_decp_tenders()
    print(f"Collecte terminée — {count} nouveau(x) marché(s) inséré(s).")
