"""
Scraper AFD (Agence Française de Développement).
Projets actifs dans les pays de l'Océan Indien : Madagascar, Maurice,
Comores, La Réunion, Mayotte.
"""
import logging
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc

_log = logging.getLogger(__name__)

AFD_API = "https://opendata.afd.fr/api/explore/v2.1/catalog/datasets/les-projets-de-l-afd/records"

PAYS_OI = {
    "Madagascar": "madagascar",
    "Maurice": "maurice",
    "Île Maurice": "île maurice",
    "Comores": "comores",
    "La Réunion": "réunion",
    "Mayotte": "mayotte",
}

SECTEURS_PERTINENTS = [
    "santé", "sante", "education", "formation",
    "développement urbain", "developpement urbain",
    "gouvernance", "infrastructure", "eau", "énergie", "energie",
    "transport", "logement", "tourisme",
]


def _secteur_ok(record: dict) -> bool:
    desc = (record.get("description") or "").lower()
    return any(s in desc for s in SECTEURS_PERTINENTS)


def _build_tender(rec: dict, pays_label: str) -> Tender:
    raw_id = rec.get("iati_identifier") or rec.get("id_projet") or ""
    tender_id = f"AFD-{raw_id}"
    title = rec.get("title_narrative") or f"Projet AFD {raw_id}"
    secteur = rec.get("description") or "Non précisé"
    description = f"AFD — Pays : {pays_label} — Secteur : {secteur}"
    deadline = parse_date(rec.get("date_dachevement"))
    pub_date = (
        parse_date(rec.get("date_octroi"))
        or parse_date(rec.get("date_debut"))
        or parse_date(rec.get("date_demarrage"))
    )
    return Tender(
        id=tender_id,
        title=title,
        description=description,
        source=f"https://www.afd.fr/fr/carte-des-projets?query={raw_id}",
        publication_date=pub_date,
        date_extraction=now_utc(),
        deadline=deadline,
        status="À qualifier",
        relevance_score=0,
        is_maintenance=False,
        llm_analysis=None,
    )


def fetch_afd_projects(years_back: int = 3) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    _run_id = start_scraper_run(db, "AFD — Agence Française de Développement")

    try:
        existing_ids = load_existing_ids(db)

        for pays_label, pays_kw in PAYS_OI.items():
            offset = 0
            limit = 100

            while True:
                params = {
                    "where": f"cntry_name like '%{pays_kw}%' AND date_dachevement >= '{date_min}'",
                    "limit": limit,
                    "offset": offset,
                    "order_by": "date_dachevement DESC",
                }

                try:
                    r = retry_get(AFD_API, params=params, rate_delay=1.0)
                except Exception as exc:
                    _log.warning("AFD API (%s) inaccessible : %s", pays_label, type(exc).__name__)
                    break

                data = r.json()
                records = data.get("results", [])
                if not records:
                    break

                for rec in records:
                    if not _secteur_ok(rec):
                        continue

                    t = _build_tender(rec, pays_label)
                    if insert_if_new(db, t, existing_ids):
                        inserted += 1

                if len(records) < limit:
                    break
                offset += limit

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("AFD : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("AFD : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_afd_projects()
    _log.info("AFD terminé — %d projet(s)", count)
