"""
Banque Mondiale — projets actifs à Madagascar (MG), Maurice (MU), Comores (KM).
Method: REST API (World Bank Projects API v2).
"""

import os
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}

WB_API = "https://search.worldbank.org/api/v2/projects"

COUNTRIES = {
    "MG": "Madagascar",
    "MU": "Maurice",
    "KM": "Comores",
}

SECTORS_PERTINENTS = [
    "health",
    "education",
    "urban",
    "housing",
    "public administration",
    "information technology",
    "transport",
    "energy",
    "tourism",
    "water",
]

_ROWS = 100


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


def _to_iso(raw) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(str(raw)[:10]).date().isoformat()
    except ValueError:
        return str(raw)


def fetch() -> list[dict]:
    """
    Returns active World Bank projects for Indian Ocean countries.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
    date_min = datetime.now(timezone.utc) - timedelta(days=days_back)
    results = []

    for code, country_name in COUNTRIES.items():
        start = 0
        while True:
            params = {
                "format": "json",
                "countrycode": code,
                "rows": _ROWS,
                "start": start,
                "fl": (
                    "id,project_name,countryname,status,closingdate,"
                    "approvaldate,boardapprovaldate,"
                    "sector1,sector2,sector3,sector4,sector5"
                ),
            }

            try:
                resp = requests.get(WB_API, headers=HEADERS, params=params, timeout=15)
            except requests.RequestException:
                break

            if resp.status_code != 200:
                break

            items = list((resp.json().get("projects") or {}).values())
            if not items:
                break

            for proj in items:
                if not isinstance(proj, dict):
                    continue
                if (proj.get("status") or "").lower() not in ("active", "en cours", ""):
                    continue
                if not _is_secteur_pertinent(proj):
                    continue

                # Exclure les projets déjà clôturés
                closing_raw = proj.get("closingdate") or ""
                if closing_raw:
                    try:
                        closing_dt = datetime.fromisoformat(closing_raw[:10]).replace(
                            tzinfo=timezone.utc
                        )
                        if closing_dt < date_min:
                            continue
                    except ValueError:
                        pass

                results.append(_normalise(proj, country_name))

            if len(items) < _ROWS:
                break
            start += _ROWS

    return results


def _normalise(proj: dict, country_name: str) -> dict:
    """Convert raw World Bank project to standard schema."""
    proj_id = proj.get("id") or ""

    sector1 = proj.get("sector1")
    if isinstance(sector1, dict):
        sector_label = sector1.get("Name") or "Infrastructure"
    elif isinstance(sector1, str):
        sector_label = sector1
    else:
        sector_label = "Infrastructure"

    pub_date = _to_iso(proj.get("approvaldate") or proj.get("boardapprovaldate"))

    return {
        "name": proj.get("project_name") or f"Projet BM {proj_id}",
        "url": f"https://projects.worldbank.org/en/projects-operations/project-detail/{proj_id}",
        "source": "Banque Mondiale",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": pub_date,
        "deadline": _to_iso(proj.get("closingdate")),
        "pays": country_name,
        "secteur": sector_label,
        "wb_id": proj_id,
    }
