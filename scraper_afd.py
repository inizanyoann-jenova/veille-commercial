"""
Scraper AFD (Agence Française de Développement).
Projets actifs dans les pays de l'Océan Indien : Madagascar, Maurice,
Comores, La Réunion, Mayotte.
L'AFD finance des infrastructures (santé, eau, urbain, énergie…)
qui nécessitent des systèmes SSI/CCTV/courants faibles.
"""
from datetime import datetime, timedelta

import requests

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from models import Tender

AFD_API = "https://opendata.afd.fr/api/explore/v2.1/catalog/datasets/les-projets-de-l-afd/records"

PAYS_OI = {
    "Madagascar": "madagascar",
    "Maurice": "mauritius",     # anglais dans la base AFD
    "Île Maurice": "île maurice",
    "Comores": "comores",
    "La Réunion": "réunion",
    "Mayotte": "mayotte",
}

# Secteurs pertinents (champ `description` de l'AFD)
SECTEURS_PERTINENTS = [
    "santé", "sante", "education", "formation",
    "développement urbain", "developpement urbain",
    "gouvernance", "infrastructure", "eau", "énergie", "energie",
    "transport", "logement", "tourisme",
]


def _secteur_ok(record: dict) -> bool:
    desc = (record.get("description") or "").lower()
    return any(s in desc for s in SECTEURS_PERTINENTS)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            continue
    return None


def fetch_afd_projects(years_back: int = 3) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    _run_id = start_scraper_run(db, "AFD — Agence Française de Développement")

    try:
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
                    r = requests.get(AFD_API, params=params, timeout=20)
                    r.raise_for_status()
                except requests.RequestException as exc:
                    raise RuntimeError(f"AFD API : {exc}") from exc

                data = r.json()
                records = data.get("results", [])
                if not records:
                    break

                for rec in records:
                    if not _secteur_ok(rec):
                        continue

                    raw_id = rec.get("iati_identifier") or rec.get("id_projet") or ""
                    tender_id = f"AFD-{raw_id}"

                    if db.query(Tender).filter(Tender.id == tender_id).first():
                        continue

                    title = rec.get("title_narrative") or f"Projet AFD {raw_id}"
                    secteur = rec.get("description") or "Non précisé"
                    description = f"AFD — Pays : {pays_label} — Secteur : {secteur}"
                    deadline = _parse_date(rec.get("date_dachevement"))

                    db.add(Tender(
                        id=tender_id,
                        title=title,
                        description=description,
                        source=f"https://www.afd.fr/fr/carte-des-projets?query={raw_id}",
                        publication_date=datetime.now(),
                        deadline=deadline,
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                    ))
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
    print("Collecte AFD (Océan Indien)…")
    count = fetch_afd_projects()
    print(f"Terminé — {count} projet(s) AFD inséré(s).")
