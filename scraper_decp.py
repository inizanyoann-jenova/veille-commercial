import hashlib
from datetime import datetime, timedelta

import requests

from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp_augmente/records"
)

_DEPT_FILTER = 'codeDepartementAcheteur in ("974", "976")'

_KEYWORD_FILTER = (
    'objet like "%SSI%"'
    ' OR objet like "%CMSI%"'
    ' OR objet like "%incendie%"'
    ' OR objet like "%désenfumage%"'
    ' OR objet like "%desenfumage%"'
    ' OR objet like "%vidéosurveillance%"'
    ' OR objet like "%videosurveillance%"'
    ' OR objet like "%caméra%"'
    ' OR objet like "%camera%"'
    ' OR objet like "%CCTV%"'
    ' OR objet like "%courants faibles%"'
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


def fetch_decp_tenders(years_back: int = 2) -> int:
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    date_filter = f'dateNotification >= "{date_min}"'
    where = f"({_DEPT_FILTER}) AND ({_KEYWORD_FILTER}) AND ({date_filter})"

    init_db()
    db = SessionLocal()
    inserted = 0

    try:
        offset = 0
        limit = 100

        while True:
            params = {
                "where": where,
                "limit": limit,
                "offset": offset,
                "order_by": "dateNotification DESC",
            }
            response = requests.get(DECP_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            records = data.get("results", [])
            if not records:
                break

            for record in records:
                # Supporte les champs imbriqués et plats selon la version API
                acheteur = record.get("acheteur") or {}
                if isinstance(acheteur, dict):
                    acheteur_nom = acheteur.get("nom", "")
                else:
                    acheteur_nom = str(acheteur)

                objet = record.get("objet") or ""
                full_text = f"{objet} {acheteur_nom}"

                if not is_relevant_def(full_text):
                    continue

                uid = record.get("uid") or hashlib.md5(full_text.encode()).hexdigest()
                tender_id = f"DECP-{uid}"

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                url = record.get("urlpublication") or "https://data.economie.gouv.fr"

                db.add(Tender(
                    id=tender_id,
                    title=objet,
                    description=f"Acheteur : {acheteur_nom}",
                    source=url,
                    publication_date=_parse_date(record.get("dateNotification")),
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

    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    print("Lancement de la collecte DECP pour les départements 974 et 976...")
    count = fetch_decp_tenders()
    print(f"Collecte terminée — {count} nouveau(x) marché(s) inséré(s).")
