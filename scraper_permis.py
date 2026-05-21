"""
Scraper Permis de Construire — DiDo v1 (SDES).
Remplace l'ancien endpoint Sit@del2 (Opendatasoft) remplacé par DiDo en mars 2026.
Récupère les permis déposés sur les départements 974 (La Réunion) et 976 (Mayotte).
"""
import hashlib
import logging
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc

_log = logging.getLogger(__name__)

DIDO_BASE = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1"

# Dataset "Liste des permis de construire et autres autorisations d'urbanisme"
DATAFILES = {
    "Locaux non résidentiels": "f8f0700f-806c-40a7-83b1-f21cf507e7c4",
    "Logements":               "8b35affb-55fc-4c1f-915b-7750f974446a",
}

_DEST_LABELS = {
    "1": "Habitation",
    "2": "Exploitation agricole",
    "3": "Bureaux",
    "4": "Commerce et services",
    "5": "Industrie",
    "6": "Industrie",
    "7": "Entrepôt",
    "8": "Service public / ERP",
    "9": "Divers",
}

_PAGE_SIZE = 100
_DATASET_URL = f"https://www.statistiques.developpement-durable.gouv.fr/catalogue?page=datafile&datafileRid={{}}"


def _fetch_datafile(db, rid: str, label: str, date_from: str, existing_ids: set) -> int:
    inserted = 0
    page = 1

    while True:
        params = {
            "pageSize": _PAGE_SIZE,
            "page":     page,
            "DEP_CODE": "in:974,976",
            "DATE_REELLE_AUTORISATION": f"gte:{date_from}",
        }
        try:
            r = retry_get(f"{DIDO_BASE}/datafiles/{rid}/rows", params=params, rate_delay=1.0)
        except Exception as exc:
            _log.warning("DiDo (%s) inaccessible page %d : %s", label, page, type(exc).__name__)
            break

        data    = r.json()
        records = data.get("data", [])
        if not records:
            break

        for rec in records:
            dep   = rec.get("DEP_CODE") or ""
            comm  = rec.get("ADR_LOCALITE_TER") or rec.get("COMM") or dep
            dest  = _DEST_LABELS.get(str(rec.get("DESTINATION_PRINCIPALE") or ""), "Bâtiment")
            surf  = (rec.get("SURF_LOC_CREEE") or rec.get("SURF_HAB_CREEE")
                     or rec.get("SURF_PUB_CREEE") or rec.get("SURF_COM_CREEE") or 0)
            surf_txt = f" — {surf} m²" if surf else ""
            raw_id   = rec.get("NUM_DAU") or hashlib.md5(str(rec).encode()).hexdigest()[:12]
            tender_id = f"PC-{dep}-{raw_id}"

            title = f"[PC] {dest}{surf_txt} — {comm} ({dep})"
            demandeur = rec.get("DENOM_DEM") or ""
            adresse = " ".join(filter(None, [
                rec.get("ADR_NUM_TER"), rec.get("ADR_LIBVOIE_TER"), comm,
                rec.get("ADR_CODPOST_TER"),
            ]))
            description = (
                f"Permis de construire — Département {dep}\n"
                f"Nature : {dest}{surf_txt}\n"
                f"Adresse : {adresse or 'Non renseignée'}\n"
                + (f"Demandeur : {demandeur}\n" if demandeur else "")
                + f"Type DAU : {rec.get('TYPE_DAU') or 'PC'}"
            )

            t = Tender(
                id=tender_id,
                title=title,
                description=description,
                source=_DATASET_URL.format(rid),
                publication_date=parse_date(rec.get("DATE_REELLE_AUTORISATION") or rec.get("DR_DEPOT")),
                date_extraction=now_utc(),
                deadline=None,
                status="À qualifier",
                relevance_score=0,
                is_maintenance=False,
                llm_analysis=None,
                secteur="Privé",
                type_opportunite="Permis Construire",
            )
            if insert_if_new(db, t, existing_ids):
                inserted += 1

        if len(records) < _PAGE_SIZE:
            break
        page += 1

    return inserted


def fetch_permis_construire(years_back: int = 1) -> int:
    init_db()
    db       = SessionLocal()
    inserted = 0
    date_from = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    _run_id   = start_scraper_run(db, "Permis de construire")

    try:
        existing_ids = load_existing_ids(db)
        for label, rid in DATAFILES.items():
            _log.info("Permis : collecte '%s' depuis %s", label, date_from)
            inserted += _fetch_datafile(db, rid, label, date_from, existing_ids)

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("Permis construire : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Permis construire : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_permis_construire()
    _log.info("Permis construire terminé — %d inséré(s)", count)
