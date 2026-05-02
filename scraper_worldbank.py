"""
Scraper Banque Mondiale — projets actifs à Madagascar, Maurice, Comores.
Chaque projet actif dans un secteur pertinent (santé, urbain, éducation…)
représente une opportunité potentielle de SSI/CCTV/courants faibles.
"""
import hashlib
from datetime import datetime

import requests

from database import SessionLocal, init_db
from models import Tender

WB_API = "https://search.worldbank.org/api/v2/projects"

# Pays Océan Indien hors territoire français
COUNTRIES = {
    "MG": "Madagascar",
    "MU": "Maurice",
    "KM": "Comores",
}

# Secteurs avec des bâtiments (= opportunités SSI/CCTV/courants faibles)
SECTORS_PERTINENTS = [
    "health", "education", "urban", "housing", "public administration",
    "information technology", "transport", "energy", "tourism", "water",
]


def _is_secteur_pertinent(project: dict) -> bool:
    for key in ("sector1", "sector2", "sector3", "sector4", "sector5"):
        s = project.get(key)
        if not s:
            continue
        name = (s.get("Name") or "").lower()
        if any(k in name for k in SECTORS_PERTINENTS):
            return True
    return False


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip()[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def fetch_worldbank_projects(years_back: int = 3) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    from datetime import timedelta
    date_min = datetime.now() - timedelta(days=365 * years_back)

    try:
        for code, country_name in COUNTRIES.items():
            params = {
                "format": "json",
                "countrycode": code,
                "rows": 100,   # max pour éviter la pagination instable
                "fl": "id,project_name,countryname,status,closingdate,sector1,sector2,sector3",
            }

            try:
                r = requests.get(WB_API, params=params, timeout=20)
                r.raise_for_status()
            except requests.RequestException as exc:
                raise RuntimeError(f"Banque Mondiale API ({country_name}) : {exc}") from exc

            items = list((r.json().get("projects") or {}).values())

            for proj in items:
                if (proj.get("status") or "").lower() not in ("active", "en cours", ""):
                    continue
                if not _is_secteur_pertinent(proj):
                    continue

                closing = _parse_date(proj.get("closingdate"))
                if closing and closing < date_min:
                    continue

                proj_id = proj.get("id") or ""
                tender_id = f"WB-{proj_id}"

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                sector_label = (proj.get("sector1") or {}).get("Name") or "Infrastructure"
                db.add(Tender(
                    id=tender_id,
                    title=proj.get("project_name") or f"Projet BM {proj_id}",
                    description=f"Banque Mondiale — Pays : {country_name} — Secteur : {sector_label}",
                    source=f"https://projects.worldbank.org/en/projects-operations/project-detail/{proj_id}",
                    publication_date=datetime.now(),
                    deadline=closing,
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                ))
                inserted += 1

            db.commit()

    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    print("Collecte Banque Mondiale (Madagascar, Maurice, Comores)…")
    count = fetch_worldbank_projects()
    print(f"Terminé — {count} projet(s) inséré(s).")
