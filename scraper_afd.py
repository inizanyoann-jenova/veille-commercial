"""
AFD (Agence Française de Développement) — projets actifs dans les pays
de l'Océan Indien : Madagascar, Maurice, Comores, La Réunion, Mayotte.
Method: REST API (OpenData AFD v2.1)
"""

import os
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}

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
    "santé",
    "sante",
    "education",
    "formation",
    "développement urbain",
    "developpement urbain",
    "gouvernance",
    "infrastructure",
    "eau",
    "énergie",
    "energie",
    "transport",
    "logement",
    "tourisme",
]


def _secteur_ok(record: dict) -> bool:
    desc = (record.get("description") or "").lower()
    return any(s in desc for s in SECTEURS_PERTINENTS)


def fetch() -> list[dict]:
    """
    Returns a list of AFD projects for Indian Ocean countries.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []
    days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
    date_min = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%d"
    )

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
                resp = requests.get(AFD_API, headers=HEADERS, params=params, timeout=15)
            except requests.RequestException:
                break

            if resp.status_code != 200:
                break

            records = resp.json().get("results", [])
            if not records:
                break

            for rec in records:
                if not _secteur_ok(rec):
                    continue
                results.append(_normalise(rec, pays_label))

            if len(records) < limit:
                break
            offset += limit

    return results


def _normalise(raw: dict, pays_label: str = "") -> dict:
    """Convert raw AFD API record to standard schema."""
    raw_id = raw.get("iati_identifier") or raw.get("id_projet") or ""
    title = raw.get("title_narrative") or f"Projet AFD {raw_id}"
    secteur = raw.get("description") or "Non précisé"
    deadline = raw.get("date_dachevement", "")
    pub_date = (
        raw.get("date_octroi")
        or raw.get("date_debut")
        or raw.get("date_demarrage")
        or ""
    )

    return {
        "name": title,
        "url": f"https://www.afd.fr/fr/carte-des-projets?query={raw_id}",
        "source": "AFD",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "pays": pays_label,
        "secteur": secteur,
        "publication_date": pub_date,
        "deadline": deadline,
        "afd_id": raw_id,
    }
