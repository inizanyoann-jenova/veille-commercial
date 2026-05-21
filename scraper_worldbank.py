"""
Scraper Banque Mondiale — projets actifs à Madagascar, Maurice, Comores.
"""
import logging
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc

_log = logging.getLogger(__name__)

WB_API = "https://search.worldbank.org/api/v2/projects"

COUNTRIES = {
    "MG": "Madagascar",
    "MU": "Maurice",
    "KM": "Comores",
}

SECTORS_PERTINENTS = [
    "health", "education", "urban", "housing", "public administration",
    "information technology", "transport", "energy", "tourism", "water",
]


def _is_secteur_pertinent(project: dict) -> bool:
    for key in ("sector1", "sector2", "sector3", "sector4", "sector5"):
        s = project.get(key)
        if not s:
            continue
        # L'API retourne parfois une string au lieu d'un dict
        name = (s.get("Name") if isinstance(s, dict) else str(s)).lower()
        if any(k in name for k in SECTORS_PERTINENTS):
            return True
    return False


def fetch_worldbank_projects(years_back: int = 3) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    date_min = datetime.now() - timedelta(days=365 * years_back)
    _run_id = start_scraper_run(db, "Banque Mondiale")

    try:
        existing_ids = load_existing_ids(db)
        nb_found     = 0
        _rows        = 100

        for code, country_name in COUNTRIES.items():
            start = 0
            while True:
                params = {
                    "format":      "json",
                    "countrycode": code,
                    "rows":        _rows,
                    "start":       start,
                    "fl": "id,project_name,countryname,status,closingdate,approvaldate,boardapprovaldate,sector1,sector2,sector3,sector4,sector5",
                }

                try:
                    r = retry_get(WB_API, params=params, rate_delay=1.0)
                except Exception as exc:
                    _log.warning("Banque Mondiale API (%s) inaccessible : %s", country_name, type(exc).__name__)
                    break

                payload = r.json()
                items   = list((payload.get("projects") or {}).values())
                if not items:
                    break

                nb_found += len(items)

                for proj in items:
                    if not isinstance(proj, dict):
                        continue
                    if (proj.get("status") or "").lower() not in ("active", "en cours", ""):
                        continue
                    if not _is_secteur_pertinent(proj):
                        continue

                    closing = parse_date(proj.get("closingdate"))
                    if closing and closing < date_min:
                        continue

                    proj_id   = proj.get("id") or ""
                    tender_id = f"WB-{proj_id}"

                    sector1 = proj.get("sector1")
                    if isinstance(sector1, dict):
                        sector_label = sector1.get("Name") or "Infrastructure"
                    elif isinstance(sector1, str):
                        sector_label = sector1
                    else:
                        sector_label = "Infrastructure"
                    pub_date = (
                        parse_date(proj.get("approvaldate"))
                        or parse_date(proj.get("boardapprovaldate"))
                    )
                    t = Tender(
                        id=tender_id,
                        title=proj.get("project_name") or f"Projet BM {proj_id}",
                        description=f"Banque Mondiale — Pays : {country_name} — Secteur : {sector_label}",
                        source=f"https://projects.worldbank.org/en/projects-operations/project-detail/{proj_id}",
                        publication_date=pub_date,
                        date_extraction=now_utc(),
                        deadline=closing,
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                    )
                    if insert_if_new(db, t, existing_ids):
                        inserted += 1

                if len(items) < _rows:
                    break
                start += _rows

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=nb_found, nb_new=inserted)
        _log.info("Banque Mondiale : %d trouvés, %d inséré(s)", nb_found, inserted)
    except Exception as exc:
        _log.exception("Banque Mondiale : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_worldbank_projects()
    _log.info("Banque Mondiale terminé — %d projet(s)", count)
